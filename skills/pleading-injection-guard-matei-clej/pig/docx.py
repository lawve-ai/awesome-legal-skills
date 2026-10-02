"""DOCX scanning with full run-property resolution."""
from __future__ import annotations

import posixpath
import re
import zipfile

from lxml import etree

from .core import VISIBLE, Report, Segment, Unscannable, letters, show, words

PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True, remove_comments=True)
MAX_PART = 200 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
V = "{urn:schemas-microsoft-com:vml}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
# Strict OOXML -> Transitional namespace map (applied to every part before parsing)
STRICT = [(b"http://purl.oclc.org/ooxml/wordprocessingml/main", b"http://schemas.openxmlformats.org/wordprocessingml/2006/main"),
          (b"http://purl.oclc.org/ooxml/officeDocument/relationships", b"http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
          (b"http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing", b"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"),
          (b"http://purl.oclc.org/ooxml/drawingml/main", b"http://schemas.openxmlformats.org/drawingml/2006/main"),
          (b"http://purl.oclc.org/ooxml/spreadsheetml/main", b"http://schemas.openxmlformats.org/spreadsheetml/2006/main"),
          (b"http://purl.oclc.org/ooxml/presentationml/main", b"http://schemas.openxmlformats.org/presentationml/2006/main")]


def unstrict(b: bytes) -> bytes:
    if b"purl.oclc.org/ooxml" in b:
        for a, t in STRICT:
            b = b.replace(a, t)
    return b

HIGHLIGHT = {"yellow": "FFFF00", "green": "00FF00", "cyan": "00FFFF", "magenta": "FF00FF", "blue": "0000FF",
             "red": "FF0000", "darkBlue": "000080", "darkCyan": "008080", "darkGreen": "008000",
             "darkMagenta": "800080", "darkRed": "800000", "darkYellow": "808000", "darkGray": "808080",
             "lightGray": "C0C0C0", "black": "000000", "white": "FFFFFF"}
THEME_MAP = {"dark1": "dk1", "light1": "lt1", "dark2": "dk2", "light2": "lt2", "text1": "dk1", "background1": "lt1",
             "text2": "dk2", "background2": "lt2", "accent1": "accent1", "accent2": "accent2", "accent3": "accent3",
             "accent4": "accent4", "accent5": "accent5", "accent6": "accent6", "hyperlink": "hlink",
             "followedHyperlink": "folHlink"}
FIELD_OK = {"PAGE", "NUMPAGES", "SECTIONPAGES", "SECTION", "DATE", "TIME", "SAVEDATE", "PRINTDATE", "CREATEDATE",
            "AUTHOR", "TITLE", "SUBJECT", "FILENAME", "REF", "PAGEREF", "NOTEREF", "SEQ", "TOC", "TC", "XE", "INDEX",
            "STYLEREF", "HYPERLINK", "MERGEFIELD", "FORMTEXT", "FORMCHECKBOX", "FORMDROPDOWN", "SYMBOL", "LISTNUM",
            "AUTONUM", "AUTONUMLGL", "AUTONUMOUT", "EQ", "ADVANCE", "BIBLIOGRAPHY", "CITATION", "NUMWORDS",
            "NUMCHARS", "USERNAME", "USERINITIALS", "TA", "TOA", "IF", "COMPARE", "SET", "ASK", "FILLIN", "GOTOBUTTON",
            "ADDIN", "SHAPE", "EMBED", "KEYWORDS", "COMMENTS", "LASTSAVEDBY", "REVNUM", "EDITTIME", "DOCPROPERTY"}
FIELD_RISKY = {"INCLUDETEXT", "INCLUDEPICTURE", "IMPORT", "DDE", "DDEAUTO", "LINK", "RD", "AUTOTEXT", "AUTOTEXTLIST",
               "QUOTE", "DOCVARIABLE", "MACROBUTTON", "PRIVATE", "DATABASE", "INCLUDE"}


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def _rgb(h):
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, TypeError, IndexError):
        return None


def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    ra, rb = _rgb(a), _rgb(b)
    if not ra or not rb:
        return 21.0
    la, lb = _lum(ra), _lum(rb)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _tint(hexc, tint=None, shade=None):
    c = _rgb(hexc)
    if not c:
        return hexc
    if tint is not None:
        t = int(tint, 16) / 255
        c = tuple(int(v * t + 255 * (1 - t)) for v in c)
    if shade is not None:
        s = int(shade, 16) / 255
        c = tuple(int(v * s) for v in c)
    return "".join(f"{v:02X}" for v in c)


# --------------------------------------------------------------------------
# package access
# --------------------------------------------------------------------------
class Pkg:
    def __init__(self, data):
        import io
        try:
            self.z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise Unscannable("not a readable ZIP package (corrupt, or password-protected Office file)")
        self.names = set(self.z.namelist())
        total = sum(i.file_size for i in self.z.infolist())
        if total > MAX_TOTAL:
            raise Unscannable(f"package expands to {total:,} bytes (zip-bomb guard)")

    def read(self, name):
        info = self.z.getinfo(name)
        if info.file_size > MAX_PART:
            raise Unscannable(f"part {name} is {info.file_size:,} bytes (size guard)")
        return self.z.read(name)

    def xml(self, name):
        if name not in self.names:
            return None
        return etree.fromstring(unstrict(self.read(name)), PARSER)

    def rels(self, part):
        d, b = posixpath.split(part)
        rp = posixpath.join(d, "_rels", b + ".rels")
        root = self.xml(rp)
        out = {}
        if root is None:
            return out
        for r in root.iter(PR + "Relationship"):
            tgt = r.get("Target") or ""
            ext = r.get("TargetMode") == "External"
            full = tgt if ext else posixpath.normpath(posixpath.join(d, tgt)).lstrip("/")
            if tgt.startswith("/"):
                full = tgt.lstrip("/")
            out[r.get("Id")] = (r.get("Type", "").rsplit("/", 1)[-1], full, ext)
        return out


# --------------------------------------------------------------------------
# property resolution
# --------------------------------------------------------------------------
def _onoff(el):
    return el.get(W + "val") not in ("0", "false", "off")


def parse_rpr(rpr, theme):
    p = {}
    if rpr is None:
        return p
    for tag in ("vanish", "specVanish"):
        el = rpr.find(W + tag)
        if el is not None:
            p["vanish"] = _onoff(el)
    el = rpr.find(W + "webHidden")
    if el is not None:
        p["webHidden"] = _onoff(el)
    for tag in ("cs", "rtl"):
        el = rpr.find(W + tag)
        if el is not None:
            p["cs"] = p.get("cs", False) or _onoff(el)
    c = rpr.find(W + "color")
    if c is not None:
        val = (c.get(W + "val") or "").upper()
        p["color"] = val or None
        tc = c.get(W + "themeColor")
        if tc and THEME_MAP.get(tc) in theme:
            p["theme_color"] = _tint(theme[THEME_MAP[tc]], c.get(W + "themeTint"), c.get(W + "themeShade"))
        else:
            p.pop("theme_color", None)
    for tag, key in (("sz", "sz"), ("szCs", "szCs"), ("w", "w"), ("spacing", "spacing"), ("position", "position")):
        el = rpr.find(W + tag)
        if el is not None:
            try:
                p[key] = int(el.get(W + "val"))
            except (TypeError, ValueError):
                pass
    shd = rpr.find(W + "shd")
    if shd is not None:
        p["shd"] = _shd(shd, theme)
    hl = rpr.find(W + "highlight")
    if hl is not None:
        v = hl.get(W + "val") or "none"
        p["hl"] = HIGHLIGHT.get(v)
    return p


def _shd(shd, theme):
    """Effective shading colour, or None for no shading."""
    val = shd.get(W + "val") or "clear"
    if val == "nil":
        return None
    if val == "solid":
        c = (shd.get(W + "color") or "auto").upper()
        tc = shd.get(W + "themeColor")
        if tc and THEME_MAP.get(tc) in theme:
            return theme[THEME_MAP[tc]]
        return None if c == "AUTO" else c
    fill = (shd.get(W + "fill") or "auto").upper()
    tf = shd.get(W + "themeFill")
    if tf and THEME_MAP.get(tf) in theme:
        return _tint(theme[THEME_MAP[tf]], shd.get(W + "themeFillTint"), shd.get(W + "themeFillShade"))
    return None if fill == "AUTO" else fill


class Styles:
    def __init__(self, root, theme):
        self.r, self.p_shd, self.tc_shd, self.based, self.defaults = {}, {}, {}, {}, {}
        self.doc_r = {}
        self.theme = theme
        if root is None:
            return
        dd = root.find(W + "docDefaults")
        if dd is not None:
            self.doc_r = parse_rpr(dd.find(f"{W}rPrDefault/{W}rPr"), theme)
        for st in root.iter(W + "style"):
            sid = st.get(W + "styleId")
            typ = st.get(W + "type")
            b = st.find(W + "basedOn")
            self.based[sid] = b.get(W + "val") if b is not None else None
            self.r[sid] = parse_rpr(st.find(W + "rPr"), theme)
            ps = st.find(f"{W}pPr/{W}shd")
            if ps is not None:
                self.p_shd[sid] = _shd(ps, theme)
            ts = st.find(f"{W}tcPr/{W}shd")
            if ts is not None:
                self.tc_shd[sid] = _shd(ts, theme)
            if _onoff_attr(st.get(W + "default")):
                self.defaults[typ] = sid

    def chain(self, sid):
        out, cur = [], sid
        while cur and cur not in out and len(out) < 30:
            out.append(cur)
            cur = self.based.get(cur)
        return list(reversed(out))

    def rprops(self, sid):
        p = {}
        for s in self.chain(sid):
            p.update(self.r.get(s, {}))
        return p

    def lookup(self, table, sid):
        v = None
        for s in self.chain(sid):
            if s in table:
                v = table[s]
        return v


def _onoff_attr(v):
    return v in ("1", "true", "on")


def hidden_reason(p, bg):
    if p.get("vanish"):
        return "hidden text (vanish)"
    size = p.get("szCs") if p.get("cs") and p.get("szCs") else p.get("sz")
    if size is not None and size <= 8:
        return f"font size {size / 2:g}pt"
    if p.get("cs") and p.get("szCs") is not None and p["szCs"] <= 8:
        return f"complex-script font size {p['szCs'] / 2:g}pt"
    if p.get("w") is not None and p["w"] <= 25:
        return f"character width scaled to {p['w']}%"
    if p.get("spacing") is not None and p["spacing"] <= -100:
        return f"character spacing {p['spacing'] / 20:g}pt (glyphs overlap)"
    if p.get("position") is not None and abs(p["position"]) >= 400:
        return f"baseline shifted {p['position'] / 2:g}pt"
    fgs = [c for c in (p.get("theme_color"), p.get("color")) if c and c != "AUTO"]
    for fg in fgs:
        if contrast(fg, bg) < 1.3:
            src = "theme colour" if fg == p.get("theme_color") and fg != p.get("color") else "colour"
            return f"text {src} {fg} on background {bg} (contrast {contrast(fg, bg):.2f}:1)"
    return None


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def _anchor_hidden(anchor, pg):
    dp = anchor.find(WP + "docPr")
    if dp is not None and _onoff_attr(dp.get("hidden")):
        return "drawing object marked hidden"
    ext = anchor.find(WP + "extent")
    cx = int(ext.get("cx", "1")) if ext is not None else 1
    cy = int(ext.get("cy", "1")) if ext is not None else 1
    if cx <= 12700 or cy <= 12700:
        return "text box smaller than 1pt"
    if anchor.tag != WP + "anchor" or not pg:
        return None
    pw, ph, ml, mt = pg

    def off(axis):
        el = anchor.find(WP + ("positionH" if axis == "h" else "positionV"))
        if el is None:
            return None, None
        po = el.find(WP + "posOffset")
        rel = el.get("relativeFrom", "")
        return (int(po.text) if po is not None and (po.text or "").lstrip("-").isdigit() else None), rel

    x, rh = off("h")
    y, rv = off("v")
    if x is not None:
        ax = x + (0 if rh == "page" else ml)
        if ax >= pw or ax + cx <= 0:
            return "text box positioned off the page (horizontal)"
    if y is not None:
        ay = y + (0 if rv == "page" else mt)
        if (rv in ("page", "margin", "topMargin") and (ay >= ph or ay + cy <= 0)) or abs(y) > 2 * ph:
            return "text box positioned off the page (vertical)"
    return None


def _float_offpage(x, y, hanchor, vanchor, pg):
    """Frames / floating tables: positions in twips. pg is (w, h, left margin, top margin) in EMU."""
    if not pg:
        return None
    pw, ph, ml, mt = (v / 635 for v in pg)
    try:
        xv = int(x) if x not in (None, "") else None
        yv = int(y) if y not in (None, "") else None
    except ValueError:
        return None
    if xv is not None:
        ax = xv + (0 if hanchor == "page" else ml)
        if ax >= pw or ax <= -pw:
            return "positioned off the page (horizontal)"
    if yv is not None:
        ay = yv + (0 if vanchor == "page" else mt)
        if ay >= ph or ay <= -ph:
            return "positioned off the page (vertical)"
    return None


def _vml_hidden(shape):
    st = (shape.get("style") or "").replace(" ", "").lower()
    if "visibility:hidden" in st or "display:none" in st:
        return "VML shape hidden"
    for k in ("margin-left", "margin-top", "left", "top"):
        m = re.search(rf"(?:^|;){k}:(-?[\d.]+)(pt|in|px)?", st)
        if m:
            v = float(m.group(1)) * {"in": 72, "px": 0.75}.get(m.group(2) or "pt", 1)
            if v <= -300 or v >= 3000:
                return "VML shape positioned off the page"
    return None


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def scan_docx(data: bytes, rep: Report, opts, child_cb, depth: int):
    pkg = Pkg(data)
    segs: list[Segment] = []
    pkg_rels = pkg.rels("")
    main = next((t for (typ, t, e) in pkg_rels.values() if typ == "officeDocument"), "word/document.xml")
    if main not in pkg.names:
        raise Unscannable("no main document part")

    # theme
    theme = {}
    doc_rels = pkg.rels(main)
    theme_part = next((t for (typ, t, e) in doc_rels.values() if typ == "theme"), None)
    troot = pkg.xml(theme_part) if theme_part else None
    if troot is not None:
        cs = troot.find(f".//{A}clrScheme")
        if cs is not None:
            for el in cs:
                key = etree.QName(el).localname
                srgb = el.find(A + "srgbClr")
                sysc = el.find(A + "sysClr")
                if srgb is not None:
                    theme[key] = srgb.get("val", "").upper()
                elif sysc is not None:
                    theme[key] = (sysc.get("lastClr") or "").upper()
    styles_part = next((t for (typ, t, e) in doc_rels.values() if typ == "styles"), None)
    styles = Styles(pkg.xml(styles_part) if styles_part else None, theme)
    settings_part = next((t for (typ, t, e) in doc_rels.values() if typ == "settings"), None)
    settings = pkg.xml(settings_part) if settings_part else None
    even_odd = settings is not None and settings.find(W + "evenAndOddHeaders") is not None \
        and _onoff(settings.find(W + "evenAndOddHeaders"))
    show_bg = settings is not None and settings.find(W + "displayBackgroundShape") is not None
    if settings is not None:
        dv = [f"{v.get(W + 'name')}: {v.get(W + 'val')}" for v in settings.iter(W + "docVar")]
        if dv:
            segs.append(Segment(" | ".join(dv), "hidden-docvar", f"{settings_part} docVars"))
        for rid, (typ, tgt, ext) in pkg.rels(settings_part).items():
            if ext and typ in ("attachedTemplate",):
                rep.add("high", "remote-template", "hidden-rels", settings_part, tgt,
                        "document loads a template from a remote location when opened")

    # external / risky relationships of the main document
    for rid, (typ, tgt, ext) in doc_rels.items():
        if ext and typ in ("frame", "subDocument", "oleObject", "attachedTemplate"):
            rep.add("high", f"remote-{typ}", "hidden-rels", main, tgt, "external content pulled in when opened")
        if typ == "aFChunk" and not ext and tgt in pkg.names:
            child_cb(pkg.read(tgt), posixpath.basename(tgt), depth + 1, rep, embedded=False)

    root = pkg.xml(main)
    body = root.find(W + "body")
    raw_main = pkg.read(main)
    if body is None or (root.find(f".//{W}t") is None and re.search(rb"<(?:\w+:)?t[ >]", raw_main)):
        raise Unscannable("main document text is in a WordprocessingML dialect this scanner does not parse")
    page_bg = "FFFFFF"
    bgel = root.find(W + "background")
    if show_bg and bgel is not None and (bgel.get(W + "color") or "auto").upper() not in ("AUTO",):
        page_bg = bgel.get(W + "color").upper()

    # page geometry (EMU) from the last sectPr
    pg = None
    sect = body.find(W + "sectPr") if body is not None else None
    if sect is not None:
        sz, mar = sect.find(W + "pgSz"), sect.find(W + "pgMar")
        try:
            pw = int(sz.get(W + "w")) * 635
            ph = int(sz.get(W + "h")) * 635
            ml = int(mar.get(W + "left", "1440")) * 635 if mar is not None else 914400
            mt = int(mar.get(W + "top", "1440")) * 635 if mar is not None else 914400
            pg = (pw, ph, ml, mt)
        except (TypeError, ValueError, AttributeError):
            pg = None

    # which header/footer parts can ever be displayed
    visible_hf = set()
    for sp in root.iter(W + "sectPr"):
        title_pg = sp.find(W + "titlePg") is not None and _onoff(sp.find(W + "titlePg"))
        for ref in list(sp.iter(W + "headerReference")) + list(sp.iter(W + "footerReference")):
            t = ref.get(W + "type") or "default"
            if t == "first" and not title_pg:
                continue
            if t == "even" and not even_odd:
                continue
            rid = ref.get(R + "id")
            if rid in doc_rels:
                visible_hf.add(doc_rels[rid][1])

    # reachability over relationships
    reachable, queue = {main}, [main]
    while queue:
        part = queue.pop()
        for typ, tgt, ext in pkg.rels(part).values():
            if not ext and tgt not in reachable and tgt in pkg.names:
                reachable.add(tgt)
                queue.append(tgt)

    visible_lines = []

    def part_channel(name):
        typ = next((t for (t, tgt, e) in doc_rels.values() if tgt == name), None)
        if name == main:
            return VISIBLE
        if typ in ("header", "footer"):
            return VISIBLE if name in visible_hf else "hidden-orphan-part"
        if typ in ("footnotes", "endnotes"):
            return VISIBLE
        if typ == "comments" or "comments" in name.lower():
            return "hidden-comment"
        if typ == "glossaryDocument" or "/glossary/" in name:
            return "hidden-glossary"
        if name not in reachable:
            return "hidden-orphan-part"
        return None

    for name in sorted(pkg.names):
        if not name.endswith(".xml") or "/_rels/" in name or name.startswith("_rels/"):
            continue
        if name.startswith("docProps/"):
            r0 = pkg.xml(name)
            txt = " ".join(x.strip() for x in r0.itertext() if x and x.strip()) if r0 is not None else ""
            if txt:
                segs.append(Segment(txt, "hidden-metadata", name))
            continue
        if name.startswith("customXml/"):
            r0 = pkg.xml(name)
            txt = " ".join(x.strip() for x in r0.itertext() if x and x.strip()) if r0 is not None else ""
            if txt:
                segs.append(Segment(txt, "hidden-customxml", name))
            continue
        if name.startswith("word/webextensions") or "/webextension" in name:
            r0 = pkg.xml(name)
            txt = " ".join(x.strip() for x in r0.itertext() if x and x.strip()) if r0 is not None else ""
            if txt:
                segs.append(Segment(txt, "hidden-webextension", name))
            continue
        if not name.startswith("word/"):
            continue
        base = part_channel(name)
        if base is None:
            continue
        proot = root if name == main else pkg.xml(name)
        if proot is None or proot.find(f".//{W}t") is None and proot.find(f".//{W}delText") is None \
                and proot.find(f".//{W}instrText") is None and proot.find(f".//{W}fldSimple") is None:
            continue
        _scan_part(proot, name, base, styles, page_bg, pg, segs, rep, visible_lines if base == VISIBLE else None)

    num_part = next((t for (typ, t, e) in doc_rels.values() if typ == "numbering"), None)
    nroot = pkg.xml(num_part) if num_part else None
    if nroot is not None:
        for lvl in nroot.iter(W + "lvl"):
            lt = lvl.find(W + "lvlText")
            label = re.sub(r"%\d", "", lt.get(W + "val") or "") if lt is not None else ""
            if letters(label) >= 4:
                props = dict(styles.doc_r)
                props.update(parse_rpr(lvl.find(W + "rPr"), theme))
                why = hidden_reason(props, page_bg)
                segs.append(Segment(label, "hidden-format" if why else VISIBLE, f"{num_part} list label", why or ""))
    rep.visible_text.extend(visible_lines)
    for n in pkg.names:
        if "/embeddings/" in n:
            child_cb(pkg.read(n), posixpath.basename(n), depth + 1, rep, embedded=True)
        elif "vbaProject" in n or "activeX" in n:
            rep.add("medium", "macros-or-activex", "hidden-macro", n, "", "macro or ActiveX content present")
    return segs


def _nearest_p(el):
    p = el.getparent()
    while p is not None and p.tag != W + "p":
        p = p.getparent()
    return p


def _scan_part(proot, part, base, styles, page_bg, pg, segs, rep, visible_lines):
    # alt text
    for el in proot.iter(WP + "docPr"):
        alt = " ".join(filter(None, (el.get("descr"), el.get("title"))))
        if alt.strip():
            segs.append(Segment(alt, "hidden-alt-text", f"{part} object {el.get('name', '')}"))
    # simple fields
    for fs in proot.iter(W + "fldSimple"):
        _field(fs.get(W + "instr") or "", part, segs, rep)

    # AlternateContent: Fallback-only text is hidden
    fallback_ps = set()
    for ac in proot.iter(MC + "AlternateContent"):
        ch_words, fb_ps = set(), []
        for choice in ac.findall(MC + "Choice"):
            ch_words |= set(words(" ".join(choice.itertext())))
        for fb in ac.findall(MC + "Fallback"):
            for p in fb.iter(W + "p"):
                fallback_ps.add(p)
                fb_ps.append(p)
        fb_text = " ".join(" ".join(t.text or "" for t in p.iter(W + "t")) for p in fb_ps)
        extra = [w for w in words(fb_text) if w not in ch_words]
        if letters(" ".join(extra)) >= 4:
            segs.append(Segment(fb_text, "hidden-fallback", f"{part} mc:Fallback",
                                "text present only in the compatibility fallback (not rendered by Word 2010+)"))

    for pi, p in enumerate(proot.iter(W + "p")):
        if p in fallback_ps:
            continue
        channel, reason_ctx = base, ""
        cell_bg, tbl_style = None, None
        anc = p.getparent()
        while anc is not None:
            tag = anc.tag
            if tag in (WP + "anchor", WP + "inline") and channel == base:
                why = _anchor_hidden(anc, pg)
                if why:
                    channel, reason_ctx = "hidden-offpage", why
            elif tag == V + "shape" or tag == V + "rect" or tag == V + "textbox":
                why = _vml_hidden(anc)
                if why and channel == base:
                    channel, reason_ctx = "hidden-offpage", why
            elif tag == W + "tc" and cell_bg is None:
                s = anc.find(f"{W}tcPr/{W}shd")
                if s is not None:
                    cell_bg = _shd(s, styles.theme) or None
            elif tag == W + "tbl" and tbl_style is None:
                ts = anc.find(f"{W}tblPr/{W}tblStyle")
                tbl_style = ts.get(W + "val") if ts is not None else "__none__"
                tp = anc.find(f"{W}tblPr/{W}tblpPr")
                if tp is not None and channel == base:
                    why = _float_offpage(tp.get(W + "tblpX"), tp.get(W + "tblpY"), tp.get(W + "horzAnchor"),
                                         tp.get(W + "vertAnchor"), pg)
                    if why:
                        channel, reason_ctx = "hidden-offpage", f"floating table {why}"
            anc = anc.getparent()
        ppr = p.find(W + "pPr")
        fp = ppr.find(W + "framePr") if ppr is not None else None
        if fp is not None and channel == base:
            why = _float_offpage(fp.get(W + "x"), fp.get(W + "y"), fp.get(W + "hAnchor"), fp.get(W + "vAnchor"), pg)
            if why:
                channel, reason_ctx = "hidden-offpage", f"text frame {why}"
        pstyle = None
        if ppr is not None and ppr.find(W + "pStyle") is not None:
            pstyle = ppr.find(W + "pStyle").get(W + "val")
        pstyle = pstyle or styles.defaults.get("paragraph")
        p_shd = None
        if ppr is not None and ppr.find(W + "shd") is not None:
            p_shd = _shd(ppr.find(W + "shd"), styles.theme)
        if p_shd is None and pstyle:
            p_shd = styles.lookup(styles.p_shd, pstyle)
        if cell_bg is None and tbl_style and tbl_style != "__none__":
            cell_bg = styles.lookup(styles.tc_shd, tbl_style)
        base_props = dict(styles.doc_r)
        if tbl_style and tbl_style != "__none__":
            base_props.update(styles.rprops(tbl_style))
        if pstyle:
            base_props.update(styles.rprops(pstyle))

        buckets: dict = {}
        order = []
        reasons_seen = []
        instr, in_instr = [], False
        for r in p.iter(W + "r"):
            if _nearest_p(r) is not p:
                continue
            rpr = r.find(W + "rPr")
            props = dict(base_props)
            rs = rpr.find(W + "rStyle") if rpr is not None else None
            cstyle = rs.get(W + "val") if rs is not None else styles.defaults.get("character")
            if cstyle:
                props.update(styles.rprops(cstyle))
            props.update(parse_rpr(rpr, styles.theme))
            bg = props.get("hl") or props.get("shd") or p_shd or cell_bg or page_bg
            in_del = any(a.tag in (W + "del", W + "moveFrom") for a in r.iterancestors())
            why = hidden_reason(props, bg) if channel == VISIBLE else None
            if in_del:
                key = ("hidden-tracked-deletion", "tracked deletion")
            elif channel != VISIBLE:
                key = (channel, reason_ctx)
            elif why:
                key = ("hidden-format", "")
                reasons_seen.append(why)
            else:
                key = (VISIBLE, "")
            for t in r:
                if t.tag == W + "fldChar":
                    ft = t.get(W + "fldCharType")
                    if ft == "begin":
                        in_instr, instr = True, []
                    elif ft in ("separate", "end"):
                        if in_instr:
                            _field("".join(instr), part, segs, rep)
                        in_instr = False
                    continue
                if t.tag == W + "instrText":
                    instr.append(t.text or "")
                    continue
                if in_instr:
                    continue
                if t.tag in (W + "t", W + "delText"):
                    txt = t.text or ""
                elif t.tag in (W + "tab", W + "br", W + "cr"):
                    txt = " "
                elif t.tag == W + "noBreakHyphen":
                    txt = "-"
                else:
                    continue
                if key not in buckets:
                    buckets[key] = []
                    order.append(key)
                buckets[key].append(txt)
        for key in order:
            ch, why = key
            txt = "".join(buckets[key])
            if not txt.strip():
                continue
            if ch == "hidden-format" and not why:
                why = "; ".join(dict.fromkeys(reasons_seen))[:200]
            segs.append(Segment(txt, ch, f"{part} ¶{pi + 1}", why))
            if ch == VISIBLE and visible_lines is not None:
                visible_lines.append(txt)


def _field(instr, part, segs, rep):
    s = instr.strip()
    if not s:
        return
    ftype = s.split()[0].upper().lstrip("\\")
    if ftype in FIELD_OK:
        m = re.search(r'HYPERLINK\s+"([^"]+)"', s, re.I)
        if m:
            segs.append(Segment(m.group(1), "link", f"{part} field"))
        return
    if ftype in FIELD_RISKY:
        rep.add("high", "risky-field", "hidden-field-code", part, show(s, 160),
                f"{ftype} field pulls or displays content from elsewhere")
    segs.append(Segment(s, "hidden-field-code", f"{part} field {ftype}"))
