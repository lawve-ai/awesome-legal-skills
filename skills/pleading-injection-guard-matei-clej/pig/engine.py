"""Dispatch, fail-closed wrapper, child handling and rendering."""
from __future__ import annotations

import hashlib
import os
import time
import traceback
from dataclasses import asdict

from .core import (CITE_RE, VISIBLE_LIKE, Report, Unscannable, analyse_segment, cite_key, decide,
                   finalise_unicode, group_findings, new_stats, overall, repeated_template_downgrade,
                   SCANNER_VERSION, SCHEMA_VERSION, exit_code, SEV_ORDER)
from . import containers

MAX_DEPTH = 6
CONVERT_VIA_LO = {"doc": ("doc", "docx"), "odf": ("odt", "docx"), "iwork": ("pages", "docx"),
                  "xls": ("xls", "xlsx"), "ppt": ("ppt", "pptx")}


def scan_bytes(data: bytes, name: str, opts, depth: int = 0, parent: str | None = None,
               embedded: bool = False) -> Report:
    t0 = time.time()
    rep = Report(file=name, display_name=os.path.basename(name) or name, parent=parent, embedded=embedded)
    rep.sha256 = hashlib.sha256(data).hexdigest()
    rep.size = len(data)
    try:
        kind = containers.sniff(data, name)
        rep.sniffed_type = kind
        segs = _dispatch(kind, data, rep, opts, depth)
        visible_cites = {}
        for s in segs:
            if s.channel in VISIBLE_LIKE:
                for m in CITE_RE.finditer(s.text):
                    visible_cites.setdefault(cite_key(m.group(0)), m.group(0))
        segs += _aggregate_hidden(segs)
        stats = new_stats()
        for s in segs:
            analyse_segment(s, rep, set(visible_cites), stats)
        finalise_unicode(rep, stats)
        repeated_template_downgrade(rep)
        rep.visible_citations = sorted(set(visible_cites.values()))
    except Unscannable as e:
        rep.status = "unscanned"
        rep.notes.append(f"UNSCANNED: {e}")
    except Exception as e:
        rep.status = "error"
        tb = traceback.extract_tb(e.__traceback__)[-1]
        rep.notes.append(f"ERROR: {type(e).__name__}: {str(e)[:300]} (at {os.path.basename(tb.filename)}:{tb.lineno})")
    decide(rep)
    rep.duration_ms = int((time.time() - t0) * 1000)
    return rep


def _aggregate_hidden(segs):
    """A payload split into many small hidden fragments (distinct formatting per run, per page)
    is reassembled in document order so patterns and the prose test see it whole."""
    from .core import BODY_HIDDEN, Segment, letters
    frags = [s for s in segs if s.channel in BODY_HIDDEN and letters(s.text) < 25]
    if len(frags) < 2:
        return []
    txt = " ".join(s.text for s in frags)
    if letters(txt) < 12:
        return []
    locs = sorted({s.where for s in frags})
    return [Segment(txt, "hidden-aggregate", f"{len(frags)} fragments: {', '.join(locs[:5])}{'…' if len(locs) > 5 else ''}",
                    "small hidden fragments joined in document order")]


def _strings_segments(data: bytes):
    from .core import Segment
    import re as _re
    out = [m.group(0).decode("ascii", "replace") for m in _re.finditer(rb"[\x20-\x7e]{20,}", data[:50_000_000])]
    out += [m.group(0).decode("utf-16-le", "replace") for m in _re.finditer(rb"(?:[\x20-\x7e]\x00){20,}", data[:50_000_000])]
    return [Segment(" | ".join(out)[:2_000_000], "hidden-binary-strings", "printable strings")] if out else []


def _child_cb(opts):
    def cb(data, name, depth, parent_rep, embedded=False):
        label = f"{parent_rep.display_name} › {name}"
        if depth > MAX_DEPTH:
            child = Report(file=label, display_name=label, parent=parent_rep.file, status="unscanned")
            child.notes.append(f"UNSCANNED: nested deeper than {MAX_DEPTH} levels; extract it and scan it directly")
            decide(child)
            parent_rep.children.append(child)
            return
        child = scan_bytes(data, label, opts, depth, parent_rep.file, embedded)
        parent_rep.children.append(child)
        if embedded and child.verdict in ("UNSCANNED", "ERROR"):
            # Unsupported embedded binaries (OLE objects etc.): scan their printable strings instead.
            segs = _strings_segments(data)
            if segs:
                stats = new_stats()
                for sg in segs:
                    analyse_segment(sg, child, set(), stats)
            worst = max((SEV_ORDER[f.severity] for f in child.findings), default=0)
            child.notes.append("embedded object of an unsupported type: printable strings scanned only")
            child.status = "scanned"
            decide(child)
            parent_rep.add("medium" if worst < 4 else "critical", "embedded-object-partially-scanned", "container",
                           name, "", f"embedded {child.sniffed_type} object: only its printable strings could be checked")
    return cb


def _dispatch(kind, data, rep, opts, depth):
    cb = _child_cb(opts)
    if kind == "empty":
        raise Unscannable("empty file (0 bytes): a OneDrive online-only placeholder? Download it and rescan")
    if kind == "pdf":
        from .pdf import scan_pdf
        return scan_pdf(data, rep, opts, cb, depth)
    if kind == "docx":
        from .docx import scan_docx
        return scan_docx(data, rep, opts, cb, depth)
    if kind == "xlsx":
        return containers.scan_xlsx(data, rep, opts, cb, depth)
    if kind == "pptx":
        return containers.scan_pptx(data, rep, opts, cb, depth)
    if kind == "rtf":
        from .rtf import scan_rtf
        return scan_rtf(data, "rtf", rep.visible_text)
    if kind == "html":
        from .html import scan_html
        return scan_html(containers.decode_text(data), "html", rep.visible_text)
    if kind == "eml":
        return containers.scan_eml(data, rep, opts, cb, depth)
    if kind == "zip":
        return containers.scan_zip(data, rep, opts, cb, depth)
    if kind == "image":
        return containers.scan_image(data, rep, opts, rep.display_name)
    if kind == "text":
        from .core import Segment, VISIBLE
        t = containers.decode_text(data)
        rep.visible_text.append(t)
        return [Segment(t, VISIBLE, "text")]
    if kind in CONVERT_VIA_LO:
        src_ext, target = CONVERT_VIA_LO[kind]
        conv = containers.lo_convert(data, src_ext, target, opts.cache_dir)
        if conv is None and kind == "doc":
            import shutil, subprocess, tempfile
            if shutil.which("textutil"):
                with tempfile.TemporaryDirectory(prefix="pig-tu-") as td:
                    src, out = os.path.join(td, "in.doc"), os.path.join(td, "out.docx")
                    open(src, "wb").write(data)
                    subprocess.run(["textutil", "-convert", "docx", src, "-output", out], capture_output=True, timeout=120)
                    if os.path.exists(out):
                        conv = open(out, "rb").read()
                        rep.add("medium", "legacy-conversion-lossy", "container", "document", "",
                                "converted with textutil, which silently DROPS hidden text: hidden-text payloads "
                                "cannot be seen. Install LibreOffice for a faithful conversion")
        if conv is None:
            raise Unscannable(f"{kind}: conversion failed (needs LibreOffice, run headless). "
                              "Export to PDF/DOCX and rescan")
        rep.notes.append(f"{kind} converted to {target} with headless LibreOffice before scanning")
        inner = _dispatch(containers.sniff(conv, "converted." + target), conv, rep, opts, depth)
        return inner
    if kind == "encrypted-office":
        raise Unscannable("password-protected Office file: obtain the password, save an unprotected copy, rescan")
    if kind == "msg":
        try:
            import extract_msg  # noqa: F401
        except ImportError:
            raise Unscannable("Outlook .msg: save it as .eml (or install extract-msg) and rescan")
        import extract_msg
        m = extract_msg.Message(data)
        return containers.scan_eml(m.as_email().as_bytes() if hasattr(m, "as_email") else b"", rep, opts, cb, depth)
    if kind == "zip-corrupt":
        raise Unscannable("corrupt ZIP / Office package")
    raise Unscannable(f"unsupported content type ({kind}); nothing was scanned")


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def to_json(rep: Report) -> dict:
    d = asdict(rep)
    d.pop("visible_text", None)
    d["findings"] = group_findings(sorted(rep.findings, key=lambda f: (-SEV_ORDER[f.severity], f.page or 0, f.kind)))
    d["overall_verdict"] = overall(rep)
    d["children"] = [to_json(c) for c in rep.children]
    return d


def envelope(reports, opts, tool_versions):
    return {"schema_version": SCHEMA_VERSION, "scanner_version": SCANNER_VERSION,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "tool_versions": tool_versions,
            "options": {"ocr": opts.ocr, "lang": opts.lang, "ocr_dpi": opts.ocr_dpi, "time_budget": opts.time_budget,
                        "max_pages": opts.max_pages},
            "reports": [to_json(r) for r in reports]}


def render(rep: Report, indent: int = 0, limit: int = 40) -> str:
    pad = "  " * indent
    v = overall(rep)
    L = [f"{pad}## {rep.display_name} — **{v}**" + (f" (own: {rep.verdict})" if v != rep.verdict else "")]
    meta = f"{pad}sha256 `{rep.sha256}` · {rep.size:,} bytes · {rep.sniffed_type}"
    if rep.pages:
        meta += f" · {rep.pages} pp · OCR {rep.pages_ocr} pp"
    L.append(meta + f" · {rep.duration_ms / 1000:.1f}s")
    for n in rep.notes:
        L.append(f"{pad}- note: {n}")
    groups = group_findings(sorted(rep.findings, key=lambda f: (-SEV_ORDER[f.severity], f.page or 0, f.kind)))
    shown = [g for g in groups if g["severity"] != "info"]
    if shown:
        cnt = {}
        for g in shown:
            cnt[g["severity"]] = cnt.get(g["severity"], 0) + 1
        L.append(f"{pad}findings: " + ", ".join(f"{k} {cnt[k]}" for k in sorted(cnt, key=lambda s: -SEV_ORDER[s])))
    elif rep.status == "scanned":
        L.append(f"{pad}- no findings")
    for g in shown[:limit]:
        pages = f" · pp.{','.join(map(str, g['pages'][:12]))}{'…' if len(g['pages']) > 12 else ''}" if len(g["pages"]) > 1 else ""
        L.append(f"{pad}- [{g['severity'].upper()}] {g['kind']} · {g['channel']} · {g['where']}{pages}"
                 + (f" ×{g['count']}" if g["count"] > 1 else ""))
        if g["detail"]:
            L.append(f"{pad}    {g['detail']}")
        if g["excerpt"]:
            L.append(f"{pad}    » {g['excerpt']}")
    if len(shown) > limit:
        L.append(f"{pad}- … {len(shown) - limit} more finding groups in the JSON report")
    for c in rep.children:
        L.append(render(c, indent + 1, limit))
    return "\n".join(L)


def visible_dump(rep: Report) -> list[str]:
    out = [f"===== {rep.display_name} (visible text only; sha256 {rep.sha256[:16]}; verdict {overall(rep)}) ====="]
    if rep.status != "scanned":
        out.append(f"[not scanned: {'; '.join(rep.notes)} — no text released]")
    else:
        from .core import redact, strip_invisible
        for t in rep.visible_text:
            clean, _ = redact(strip_invisible(t))
            out.append(clean)
    for c in rep.children:
        out += visible_dump(c)
    return out
