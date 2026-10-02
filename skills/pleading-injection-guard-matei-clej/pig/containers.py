"""Type sniffing and container / secondary-format handlers (email, zip, OLE, xlsx, pptx, images, text)."""
from __future__ import annotations

import email
import io
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from email import policy

from lxml import etree

from .core import VISIBLE, VISIBLE_OCR, Report, Segment, Unscannable, letters, words
from .html import scan_html

PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)
MAX_MEMBERS = 2000
MAX_MEMBER = 200 * 1024 * 1024
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}


# --------------------------------------------------------------------------
# sniffing
# --------------------------------------------------------------------------
def sniff(data: bytes, name: str) -> str:
    if not data:
        return "empty"
    head = data[:16]
    if b"%PDF-" in data[:1024]:
        return "pdf"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        try:
            names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
        except zipfile.BadZipFile:
            return "zip-corrupt"
        if "word/document.xml" in names or any(n.endswith("document.xml") and n.startswith("word/") for n in names):
            return "docx"
        if "xl/workbook.xml" in names:
            return "xlsx"
        if "ppt/presentation.xml" in names:
            return "pptx"
        if "mimetype" in names:
            try:
                mt = zipfile.ZipFile(io.BytesIO(data)).read("mimetype")[:80]
            except Exception:
                mt = b""
            if b"opendocument" in mt:
                return "odf"
        if any(n.startswith("Index/") and n.endswith(".iwa") for n in names) or "index.xml" in names:
            return "iwork"
        return "zip"
    if head.startswith(OLE):
        u = lambda s: s.encode("utf-16-le")
        if u("EncryptedPackage") in data:
            return "encrypted-office"
        if u("__substg1.0_") in data:
            return "msg"
        if u("WordDocument") in data:
            return "doc"
        if u("Workbook") in data or u("Book") in data:
            return "xls"
        if u("PowerPoint Document") in data:
            return "ppt"
        return "ole"
    if data.lstrip()[:5] == b"{\\rtf":
        return "rtf"
    if head.startswith(b"\x89PNG") or head[:3] == b"\xff\xd8\xff" or head[:4] in (b"GIF8", b"II*\x00", b"MM\x00*") \
            or head[:2] == b"BM" or (head[:4] == b"RIFF" and data[8:12] == b"WEBP") or data[4:12] in (b"ftypheic", b"ftypmif1", b"ftypheix"):
        return "image"
    sample = data[:4096]
    if sample.count(b"\x00") > len(sample) // 20 and not sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "binary"
    text = decode_text(data[:1_000_000]).lstrip("\ufeff \t\r\n")
    text = re.sub(r"^(?:<!--.*?-->\s*)+", "", text[:200_000], flags=re.S)
    if re.search(r"(?im)^(?:received|mime-version|from|message-id|return-path|x-[\w-]+):\s", text[:3000]) and \
            re.search(r"(?im)^(?:subject|mime-version|message-id|received):", text[:4000]):
        return "eml"
    if re.search(r"<(?:!doctype html|html|body|head|div|span|table|p|style)\b", text[:4000], re.I) or \
            (name.lower().endswith((".html", ".htm", ".xhtml")) and re.search(r"<(?:html|body|div|p|span)\b", text, re.I)):
        return "html"
    return "text"


def decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


# --------------------------------------------------------------------------
# conversion via headless LibreOffice (no window; private profile)
# --------------------------------------------------------------------------
def soffice_path():
    for p in (shutil.which("soffice"), "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if p and os.path.exists(p):
            return p
    return None


def lo_convert(data: bytes, ext: str, target: str, cache_dir: str, timeout=180) -> bytes | None:
    so = soffice_path()
    if not so:
        return None
    with tempfile.TemporaryDirectory(prefix="pig-lo-") as td:
        src = os.path.join(td, "in." + ext)
        with open(src, "wb") as f:
            f.write(data)
        prof = os.path.join(cache_dir, "lo-profile")
        os.makedirs(prof, exist_ok=True)
        try:
            subprocess.run([so, "--headless", "--norestore", "--nologo", "--nodefault",
                            f"-env:UserInstallation=file://{prof}", "--convert-to", target, "--outdir", td, src],
                           capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        out = os.path.join(td, "in." + target.split(":")[0])
        if os.path.exists(out) and os.path.getsize(out) > 0:
            with open(out, "rb") as f:
                return f.read()
    return None


# --------------------------------------------------------------------------
# email
# --------------------------------------------------------------------------
DISPLAYED = ("from", "to", "cc", "subject", "date")


def scan_eml(data: bytes, rep: Report, opts, child_cb, depth: int):
    msg = email.message_from_bytes(data, policy=policy.default)
    segs = []
    shown, other = [], []
    for k, v in msg.items():
        (shown if k.lower() in DISPLAYED else other).append(f"{k}: {v}")
    if shown:
        segs.append(Segment(" | ".join(shown), VISIBLE, "headers"))
        rep.visible_text.append("\n".join(shown))
    if other:
        segs.append(Segment(" | ".join(other), "hidden-header", "headers (not displayed)"))
    try:
        rt, fr = msg["Reply-To"], msg["From"]
        if rt and fr and getattr(rt, "addresses", None) and getattr(fr, "addresses", None):
            d1 = rt.addresses[0].addr_spec.rsplit("@", 1)[-1].lower()
            d2 = fr.addresses[0].addr_spec.rsplit("@", 1)[-1].lower()
            if d1 and d2 and d1 != d2:
                rep.add("medium", "reply-to-mismatch", VISIBLE, "headers", f"From {fr} / Reply-To {rt}")
    except Exception:
        pass
    plain, html_vis = [], []
    leaves = []

    def walk(part):
        ctype = part.get_content_type()
        if ctype == "message/rfc822":
            fn = part.get_filename() or f"forwarded{len(leaves)}.eml"
            pl = part.get_payload()
            cte = (part.get("Content-Transfer-Encoding") or "").strip().lower()
            if cte in ("base64", "quoted-printable"):
                import base64 as _b64, quopri
                body = re.split(r"\r?\n\r?\n", part.as_string(), maxsplit=1)
                body = body[1] if len(body) > 1 else ""
                try:
                    raw = _b64.b64decode(re.sub(r"\s+", "", body)) if cte == "base64" else quopri.decodestring(body.encode())
                except Exception:
                    raw = body.encode("utf-8", "replace")
            elif isinstance(pl, list) and pl:
                raw = pl[0].as_bytes()
            else:
                raw = part.get_payload(decode=True) or (pl.encode("utf-8", "replace") if isinstance(pl, str) else b"")
            if raw:
                child_cb(raw, fn, depth + 1, rep, embedded=False)
            return
        if part.is_multipart():
            for sub in part.get_payload():
                walk(sub)
            return
        leaves.append(part)

    walk(msg)
    for part in msg.walk():
        for attr in ("preamble", "epilogue"):
            v = getattr(part, attr, None)
            if v and v.strip():
                segs.append(Segment(v, "hidden-mime", f"MIME {attr}", "outside the displayed parts"))
    for i, part in enumerate(leaves):
        ctype = part.get_content_type()
        fn = part.get_filename()
        disp = part.get_content_disposition()
        try:
            payload = part.get_payload(decode=True) or b""
        except Exception:
            payload = b""
        if fn or disp == "attachment" or not ctype.startswith("text/") or sniff(payload, "") == "eml":
            if payload:
                child_cb(payload, fn or f"part{i}", depth + 1, rep, embedded=False)
            continue
        cs = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(cs, "replace")
        except LookupError:
            text = payload.decode("utf-8", "replace")
        where = f"part {i} {ctype}"
        if ctype == "text/html":
            segs += scan_html(text, where, html_vis)
        elif ctype == "text/plain":
            segs.append(Segment(text, VISIBLE, where))
            plain.append(text)
        else:
            segs.append(Segment(text, VISIBLE, where, ctype))
            rep.visible_text.append(text)
    if plain and html_vis:
        hw = set(words(" ".join(html_vis)))
        ptxt = re.sub(r"https?://\S+|\[[^\]]*\]|<[^>]*>", " ", " ".join(plain))
        extra = [w for w in words(ptxt) if w not in hw]
        if letters(" ".join(extra)) >= 40:
            segs.append(Segment(" ".join(extra), "hidden-alternative", "text/plain alternative",
                                "words in the plain-text alternative that the HTML version (what a mail client shows) lacks"))
        rep.visible_text.extend(html_vis)
    else:
        rep.visible_text.extend(html_vis or plain)
    return segs


# --------------------------------------------------------------------------
# zip
# --------------------------------------------------------------------------
def scan_zip(data: bytes, rep: Report, opts, child_cb, depth: int):
    z = zipfile.ZipFile(io.BytesIO(data))
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > MAX_MEMBERS:
        raise Unscannable(f"archive has {len(infos)} members (limit {MAX_MEMBERS})")
    for info in infos:
        base = os.path.basename(info.filename)
        if info.filename.startswith("__MACOSX/") or base in JUNK:
            continue
        if info.flag_bits & 0x1:
            rep.add("medium", "encrypted-member", "container", info.filename, "", "password-protected archive member not scanned")
            continue
        if info.file_size > MAX_MEMBER or (info.compress_size and info.file_size / info.compress_size > 200 and info.file_size > 50_000_000):
            rep.add("medium", "member-not-scanned", "container", info.filename, "", "size/compression guard")
            continue
        child_cb(z.read(info), info.filename, depth + 1, rep, embedded=False)
    return []


# --------------------------------------------------------------------------
# xlsx (native, partial)
# --------------------------------------------------------------------------
X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _col_index(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    n = 0
    for ch in (m.group(1) if m else ""):
        n = n * 26 + ord(ch) - 64
    return n


def scan_xlsx(data: bytes, rep: Report, opts, child_cb, depth: int):
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    from .docx import unstrict
    x = lambda n: etree.fromstring(unstrict(z.read(n)), PARSER) if n in names else None
    segs = []
    sst = []
    root = x("xl/sharedStrings.xml")
    if root is not None:
        for si in root.iter(X + "si"):
            sst.append("".join(t.text or "" for t in si.iter(X + "t")))
    # styles: xf -> (font white?, tiny?, hidden numfmt?)
    xf_hidden = {}
    st = x("xl/styles.xml")
    if st is not None:
        numfmts = {n.get("numFmtId"): n.get("formatCode", "") for n in st.iter(X + "numFmt")}
        fonts = []
        for f in st.iter(X + "font"):
            col = f.find(X + "color")
            rgb = (col.get("rgb") or "")[-6:].upper() if col is not None else ""
            theme = col.get("theme") if col is not None else None
            sz = f.find(X + "sz")
            size = float(sz.get("val")) if sz is not None and sz.get("val") else 11
            fonts.append((rgb, theme, size))
        fills = []
        for fl in st.iter(X + "fill"):
            pf = fl.find(X + "patternFill")
            fg = pf.find(X + "fgColor") if pf is not None else None
            fills.append((fg.get("rgb") or "")[-6:].upper() if fg is not None and pf.get("patternType") == "solid" else "")
        cx = st.find(X + "cellXfs")
        for i, xf in enumerate(cx if cx is not None else []):
            why = None
            nf = numfmts.get(xf.get("numFmtId"), "")
            if re.fullmatch(r"\s*;\s*;\s*;\s*", nf or ""):
                why = "number format ';;;' hides the cell value"
            fi = int(xf.get("fontId", 0))
            if not why and fi < len(fonts):
                rgb, theme, size = fonts[fi]
                bg = fills[int(xf.get("fillId", 0))] if int(xf.get("fillId", 0)) < len(fills) else ""
                bg = bg or "FFFFFF"
                if size < 4:
                    why = f"font size {size}pt"
                elif rgb and rgb == bg:
                    why = f"font colour {rgb} equals cell fill"
                elif rgb in ("FFFFFF", "FEFEFE", "FDFDFD", "FCFCFC") and bg == "FFFFFF":
                    why = "white text on white cell"
                elif theme == "0" and bg == "FFFFFF" and not rgb:
                    why = "theme colour background1 (white) text on white cell"
            if why:
                xf_hidden[i] = why
    wb = x("xl/workbook.xml")
    rels = {}
    rr = x("xl/_rels/workbook.xml.rels")
    if rr is not None:
        for r in rr.iter(PR + "Relationship"):
            rels[r.get("Id")] = "xl/" + r.get("Target").lstrip("/").replace("xl/", "", 1) if not r.get("Target", "").startswith("/") else r.get("Target").lstrip("/")
    if wb is not None:
        for dn in wb.iter(X + "definedName"):
            if dn.text and letters(dn.text) > 12:
                segs.append(Segment(f"{dn.get('name')}: {dn.text}", "hidden-metadata", "defined name"))
        for sh in wb.iter(X + "sheet"):
            name = sh.get("name")
            state = sh.get("state") or "visible"
            part = rels.get(sh.get(RNS + "id"))
            sroot = x(part) if part else None
            if sroot is None:
                continue
            hidden_cols = set()
            for c in sroot.iter(X + "col"):
                if c.get("hidden") in ("1", "true") or (c.get("width") and float(c.get("width")) < 0.5):
                    hidden_cols |= set(range(int(c.get("min", 0)), int(c.get("max", 0)) + 1))
            buckets = {}
            for row in sroot.iter(X + "row"):
                row_hidden = row.get("hidden") in ("1", "true") or (row.get("ht") and row.get("customHeight") and float(row.get("ht")) < 1)
                for c in row.iter(X + "c"):
                    t = c.get("t")
                    v = c.find(X + "v")
                    if t == "s" and v is not None and (v.text or "").isdigit() and int(v.text) < len(sst):
                        val = sst[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(tt.text or "" for tt in c.iter(X + "t"))
                    elif t == "str" and v is not None:
                        val = v.text or ""
                    else:
                        continue
                    if state != "visible":
                        key = ("hidden-format", f"sheet '{name}' is {state}")
                    elif row_hidden:
                        key = ("hidden-format", "hidden row")
                    elif _col_index(c.get("r")) in hidden_cols:
                        key = ("hidden-format", "hidden column")
                    elif c.get("s") and int(c.get("s")) in xf_hidden:
                        key = ("hidden-format", xf_hidden[int(c.get("s"))])
                    else:
                        key = (VISIBLE, "")
                    buckets.setdefault(key, []).append(val)
            for (ch, why), vals in buckets.items():
                segs.append(Segment(" | ".join(vals), ch, f"sheet '{name}'", why))
                if ch == VISIBLE:
                    rep.visible_text.append(" | ".join(vals))
    for n in names:
        if re.match(r"xl/comments\d*\.xml|xl/threadedComments/", n):
            r0 = x(n)
            if r0 is not None:
                segs.append(Segment(" ".join(t for t in r0.itertext() if t.strip()), "hidden-comment", n))
        elif n.startswith("docProps/"):
            r0 = x(n)
            if r0 is not None:
                segs.append(Segment(" ".join(t.strip() for t in r0.itertext() if t.strip()), "hidden-metadata", n))
        elif "vbaProject" in n:
            rep.add("medium", "macros-or-activex", "hidden-macro", n, "", "macro content present")
        elif n.startswith("xl/drawings/") and n.endswith(".xml"):
            r0 = x(n)
            if r0 is not None:
                txt = " ".join(t.strip() for t in r0.itertext() if t.strip())
                if txt:
                    segs.append(Segment(txt, VISIBLE, n, "drawing/text box (position not assessed)"))
    rep.notes.append("xlsx: hidden sheets/rows/columns, ';;;' formats, white/tiny fonts and comments checked; "
                     "conditional formats and shape geometry not assessed")
    return segs


# --------------------------------------------------------------------------
# pptx (native, partial)
# --------------------------------------------------------------------------
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
AA = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def scan_pptx(data: bytes, rep: Report, opts, child_cb, depth: int):
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    from .docx import unstrict
    x = lambda n: etree.fromstring(unstrict(z.read(n)), PARSER) if n in names else None
    segs = []
    pres = x("ppt/presentation.xml")
    sw, sh = 12192000, 6858000
    if pres is not None and pres.find(P + "sldSz") is not None:
        sw = int(pres.find(P + "sldSz").get("cx", sw))
        sh = int(pres.find(P + "sldSz").get("cy", sh))
    slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
    for n in slides:
        root = x(n)
        slide_hidden = root.get("show") in ("0", "false")
        bg = "FFFFFF"
        b = root.find(f".//{P}bg//{AA}srgbClr")
        if b is not None:
            bg = b.get("val", "FFFFFF").upper()
        for sp in root.iter(P + "sp"):
            why_shape = "hidden slide" if slide_hidden else None
            off = sp.find(f".//{AA}xfrm/{AA}off")
            ext = sp.find(f".//{AA}xfrm/{AA}ext")
            if not why_shape and off is not None and ext is not None:
                ox, oy = int(off.get("x", 0)), int(off.get("y", 0))
                cx, cy = int(ext.get("cx", 1)), int(ext.get("cy", 1))
                if ox >= sw or oy >= sh or ox + cx <= 0 or oy + cy <= 0:
                    why_shape = "shape positioned off the slide"
            nv = sp.find(f".//{P}cNvPr")
            if nv is not None and nv.get("hidden") in ("1", "true"):
                why_shape = why_shape or "shape marked hidden"
            buckets = {}
            for r in sp.iter(AA + "r"):
                t = r.find(AA + "t")
                if t is None or not t.text:
                    continue
                why = why_shape
                rpr = r.find(AA + "rPr")
                if not why and rpr is not None:
                    if rpr.get("sz") and int(rpr.get("sz")) < 400:
                        why = f"font size {int(rpr.get('sz')) / 100:g}pt"
                    col = rpr.find(f"{AA}solidFill/{AA}srgbClr")
                    if not why and col is not None and col.get("val", "").upper() == bg:
                        why = f"text colour {bg} equals slide background"
                    alpha = rpr.find(f"{AA}solidFill/{AA}srgbClr/{AA}alpha")
                    if not why and alpha is not None and int(alpha.get("val", "100000")) < 15000:
                        why = "text nearly transparent"
                key = ("hidden-format" if why else VISIBLE, why or "")
                buckets.setdefault(key, []).append(t.text)
            for (ch, why), vals in buckets.items():
                segs.append(Segment(" ".join(vals), ch, n, why))
                if ch == VISIBLE:
                    rep.visible_text.append(" ".join(vals))
    for n in sorted(names):
        if n.startswith("ppt/notesSlides/") and n.endswith(".xml"):
            r0 = x(n)
            txt = " ".join(t.text for t in r0.iter(AA + "t") if t.text) if r0 is not None else ""
            if txt.strip():
                segs.append(Segment(txt, "hidden-speaker-notes", n))
        elif n.startswith("ppt/comments") and n.endswith(".xml"):
            r0 = x(n)
            if r0 is not None:
                segs.append(Segment(" ".join(t for t in r0.itertext() if t.strip()), "hidden-comment", n))
        elif n.startswith("docProps/"):
            r0 = x(n)
            if r0 is not None:
                segs.append(Segment(" ".join(t.strip() for t in r0.itertext() if t.strip()), "hidden-metadata", n))
        elif "vbaProject" in n:
            rep.add("medium", "macros-or-activex", "hidden-macro", n, "", "macro content present")
    rep.notes.append("pptx: hidden slides, off-slide/hidden shapes, tiny/transparent/background-coloured text and "
                     "speaker notes checked; theme colours, layouts and grouped-shape offsets not assessed")
    return segs


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------
def scan_image(data: bytes, rep: Report, opts, name: str):
    with tempfile.TemporaryDirectory(prefix="pig-img-") as td:
        src = os.path.join(td, "img")
        with open(src, "wb") as f:
            f.write(data)
        if data[4:12] in (b"ftypheic", b"ftypmif1", b"ftypheix"):
            png = os.path.join(td, "img.png")
            subprocess.run(["sips", "-s", "format", "png", src, "--out", png], capture_output=True, timeout=60)
            src = png
        if not opts.ocr:
            raise Unscannable("image: OCR disabled (--no-ocr), nothing to scan")
        r = subprocess.run(["tesseract", src, "stdout", "-l", opts.lang], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise Unscannable(f"image could not be OCR'd: {r.stderr.strip()[:120]}")
    text = r.stdout
    rep.visible_text.append(text)
    rep.add("low", "image-only", "render", name, "",
            "image: visible text OCR'd for pattern checks; faint or tiny text readable by a vision model is not assessed")
    return [Segment(text, VISIBLE_OCR, "image", "OCR")] if text.strip() else []
