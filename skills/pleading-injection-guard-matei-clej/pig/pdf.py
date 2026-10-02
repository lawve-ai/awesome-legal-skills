"""PDF scanning: per-word render verification, extraction-view diff, OCR backstop."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait

import fitz
import numpy as np

from .core import (LINK, OCR_DIFF, OCR_LAYER, VISIBLE, VISIBLE_OCR, Report, Segment, Unscannable,
                   fold, letters, pattern_hits, show, words)

RENDER_DPI = 120          # for the ink test
INK_MIN = 0.006
INK_MAX = 0.62            # above this the "ink" is a painted box, not glyphs           # fraction of a word's bbox that must carry text-coloured ink
CONTRAST_MIN = 40         # max-channel distance (0-255) between text colour and background
TINY_PT = 4.0
MAX_PIXELS = 30_000_000


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _render(page, dpi):
    r = page.rect
    px = (r.width * dpi / 72) * (r.height * dpi / 72)
    if px > MAX_PIXELS:
        dpi = max(24, int(dpi * (MAX_PIXELS / px) ** 0.5))
    pix = page.get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csRGB)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    return arr, dpi / 72.0


def _ink(arr, scale, bbox, color):
    """Return (ink_fraction, contrast). ink = pixels close to the text colour and away from
    the local background; background = median of a ring just outside the bbox."""
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = (int(bbox[0] * scale), int(bbox[1] * scale), int(bbox[2] * scale + 0.999), int(bbox[3] * scale + 0.999))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 - x0 < 1 or y1 - y0 < 1:
        return 0.0, 0
    reg = arr[y0:y1, x0:x1].astype(np.int16)
    m = 2
    rx0, ry0, rx1, ry1 = max(0, x0 - m), max(0, y0 - m), min(w, x1 + m), min(h, y1 + m)
    ring = arr[ry0:ry1, rx0:rx1].astype(np.int16).copy()
    mask = np.ones(ring.shape[:2], bool)
    mask[y0 - ry0:y1 - ry0, x0 - rx0:x1 - rx0] = False
    ringpx = ring[mask] if mask.any() else reg.reshape(-1, 3)
    bg = np.median(ringpx.reshape(-1, 3), axis=0)
    c = np.array(color[:3] if color else (0, 0, 0), dtype=float) * 255
    contrast = int(np.abs(bg - c).max())
    d_text = np.abs(reg - c).max(axis=2)
    d_bg = np.abs(reg - bg).max(axis=2)
    ink = float(((d_text < 70) & (d_bg > 35)).mean())
    return ink, contrast


def _covered_later(bboxlog, seq_index, bbox):
    """True if a fill drawn after the text entry covers >= 90% of bbox."""
    r = fitz.Rect(bbox)
    if r.is_empty:
        return False
    for kind, b in bboxlog[seq_index + 1:]:
        if kind.startswith("fill-") and kind != "fill-text":
            inter = fitz.Rect(b) & r
            if not inter.is_empty and inter.get_area() >= 0.9 * r.get_area():
                return True
    return False


def _span_key(sp):
    col = tuple(round(c, 2) for c in (sp.get("color") or (0, 0, 0)))
    return (sp.get("type", 0), col, round(sp.get("opacity", 1.0), 2), round(sp.get("size", 12) * 2) / 2)


def _page_words(trace):
    """Assemble words across the whole page from glyph geometry (kerned / justified PDFs put
    each glyph in its own span). Yields (text, bbox, span_index). A word also breaks where the
    rendering attributes change, so a hidden fragment never hides inside a visible word."""
    out, cur, box, si0 = [], [], None, None
    prev = None   # (origin, bbox, size, key)
    for si, sp in enumerate(trace):
        key = _span_key(sp)
        size = max(sp.get("size", 12), 1.0)
        for c in sp.get("chars") or []:
            u = chr(c[0])
            b = fitz.Rect(c[3])
            o = c[2]
            brk = False
            if prev is not None:
                po, pb, ps, pk = prev
                if abs(o[1] - po[1]) > 0.5 * max(size, ps) or o[0] - pb.x1 > 0.25 * max(size, ps) \
                        or o[0] < po[0] - 0.5 * max(size, ps) or pk != key:
                    brk = True
            if u.isspace() or brk:
                if cur:
                    out.append(("".join(cur), box, si0))
                cur, box, si0 = [], None, None
            if not u.isspace():
                cur.append(u)
                box = fitz.Rect(b) if box is None else box | b
                si0 = si if si0 is None else si0
            prev = (o, b, size, key)
    if cur:
        out.append(("".join(cur), box, si0))
    return out


def _deletes(w):
    return {w[:i] + w[i + 1:] for i in range(len(w))}


class _Vocab:
    """Fuzzy word support: exact, or edit distance 1 via deletion neighbourhoods."""
    def __init__(self, ws):
        self.exact = set(ws)
        self.dels = set()
        for w in self.exact:
            if len(w) >= 4:
                self.dels |= _deletes(w)
                self.dels.add(w)

    def has(self, w):
        if w in self.exact:
            return True
        if len(w) < 4:
            return False
        return w in self.dels or bool(_deletes(w) & self.dels)


def _tesseract(png, lang, timeout):
    r = subprocess.run(["tesseract", png, "stdout", "-l", lang], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def scan_pdf(data: bytes, rep: Report, opts, child_cb, depth: int):
    t_start = time.time()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise RuntimeError(f"PDF could not be opened: {type(e).__name__}: {e}")
    if doc.needs_pass:
        if not (opts.password and doc.authenticate(opts.password)):
            raise Unscannable("encrypted PDF: obtain the password and rerun with --password")
    rep.pages = doc.page_count
    segs: list[Segment] = []

    # ---- document-level channels -------------------------------------------------
    md = {k: v for k, v in (doc.metadata or {}).items() if v and k not in ("format", "encryption")}
    if md:
        segs.append(Segment(" | ".join(f"{k}: {v}" for k, v in md.items()), "hidden-metadata", "document info"))
    try:
        xmp = doc.get_xml_metadata()
        if xmp:
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xmp)).strip()
            if txt:
                segs.append(Segment(txt, "hidden-metadata", "XMP"))
    except Exception:
        pass
    try:
        toc = doc.get_toc(simple=True)
        if toc:
            segs.append(Segment(" | ".join(t[1] for t in toc), "hidden-outline", "bookmarks"))
    except Exception:
        pass
    # embedded files -> scanned as children
    try:
        for i in range(doc.embfile_count()):
            info = doc.embfile_info(i)
            name = info.get("filename") or info.get("name") or f"embedded{i}"
            segs.append(Segment(" ".join(filter(None, (info.get("name"), info.get("filename"), info.get("desc")))),
                                "hidden-embedded-name", f"embedded file {i}"))
            child_cb(doc.embfile_get(i), name, depth + 1, rep)
    except Exception as e:
        rep.notes.append(f"embedded files could not be fully extracted: {e}")
    # actions / scripts (one pass over xrefs)
    acts = Counter()
    action_text = []
    for x in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(x, compressed=True)
        except Exception:
            continue
        for m in re.finditer(r"/(JavaScript|JS|Launch|SubmitForm|ImportData|GoToR|OpenAction|XFA)\b", obj):
            acts[m.group(1)] += 1
        for key in ("JS", "F", "P"):
            if f"/{key}" not in obj:
                continue
            try:
                typ, val = doc.xref_get_key(x, key)
            except Exception:
                continue
            if typ == "string" and val:
                action_text.append(val)
            elif typ == "xref" and key == "JS":
                try:
                    ref = int(val.split()[0])
                    action_text.append((doc.xref_stream(ref) or b"")[:2_000_000].decode("latin-1", "replace"))
                except Exception:
                    pass
    if action_text:
        segs.append(Segment(" | ".join(action_text)[:2_000_000], "hidden-actions", "PDF actions / JavaScript"))
    if acts:
        risky = {k: v for k, v in acts.items() if k in ("JavaScript", "JS", "Launch", "ImportData", "XFA")}
        if risky:
            rep.add("medium", "pdf-active-content", "hidden-actions", "document", "",
                    "active content present: " + ", ".join(f"{k}×{v}" for k, v in sorted(risky.items()))
                    + (" (XFA form content is not scanned)" if "XFA" in risky else ""))
        rest = {k: v for k, v in acts.items() if k not in risky}
        if rest:
            rep.notes.append("PDF actions: " + ", ".join(f"{k}×{v}" for k, v in sorted(rest.items())))
    revs = data.count(b"%%EOF")
    if revs > 1:
        rep.notes.append(f"{revs} revisions (incremental updates); extractors read only the latest, earlier revisions not scanned")

    # ---- optional-content layers that are OFF --------------------------------------
    ocg_words = {}
    try:
        ocgs = doc.get_ocgs() or {}
        if any(not v.get("on", True) for v in ocgs.values()):
            d2 = fitz.open(stream=data, filetype="pdf")
            if d2.needs_pass and opts.password:
                d2.authenticate(opts.password)
            for cfg in d2.layer_ui_configs():
                if not cfg.get("on"):
                    d2.set_layer_ui_config(cfg["number"], action=0)
            for pno in range(d2.page_count):
                on_words = words(d2[pno].get_text("text"), 1)
                ocg_words[pno] = on_words
            d2.close()
    except Exception as e:
        rep.notes.append(f"optional-content check failed: {e}")

    # ---- per page --------------------------------------------------------------------
    tmp = tempfile.TemporaryDirectory(prefix="pig-ocr-")
    ocr_jobs = {}
    pool = ThreadPoolExecutor(max_workers=opts.ocr_workers) if opts.ocr else None
    page_state = {}
    try:
        for pno in range(doc.page_count):
            if opts.max_pages and pno >= opts.max_pages:
                rep.pages_unverified.append(pno + 1)
                if rep.status != "partial":
                    rep.notes.append(f"PARTIAL: --max-pages {opts.max_pages} left pages unanalysed; not a clearance")
                rep.status = "partial"
                continue
            page = doc[pno]
            prect = page.rect
            where = f"p.{pno + 1}"
            try:
                trace = page.get_texttrace()
            except Exception:
                trace = []
            bboxlog = page.get_bboxlog()
            text_idx = [i for i, (k, _) in enumerate(bboxlog) if "text" in k]
            images = [fitz.Rect(i["bbox"]) for i in page.get_image_info() if not i.get("has-mask")]
            arr, scale = _render(page, RENDER_DPI) if trace else (None, 1)

            classified = []   # (channel, reason, word_text)
            vis_words, layer_words, min_size = [], [], 99.0
            vis_ink = []
            for wtext, wbox, si in _page_words(trace):
                sp = trace[si]
                typ = sp.get("type", 0)
                opacity = sp.get("opacity", 1.0)
                size = sp.get("size", 12)
                color = sp.get("color") or (0, 0, 0)
                seq = text_idx[si] if si < len(text_idx) else len(bboxlog) - 1
                reason, ch = None, VISIBLE
                ink, contrast = 0.0, 0
                if typ == 3:
                    over_img = any((img & wbox).get_area() >= 0.8 * max(wbox.get_area(), 1e-6) for img in images)
                    if over_img:
                        ch, reason = OCR_LAYER, "OCR layer over scanned image"
                    else:
                        ch, reason = "hidden-format", "invisible render mode"
                elif typ == 2:
                    ch, reason = "hidden-format", "clip-only render mode"
                elif opacity <= 0.15:
                    ch, reason = "hidden-format", f"opacity {opacity:.2f}"
                elif not wbox.intersects(prect):
                    ch, reason = "hidden-offpage", "positioned off the page"
                elif size < TINY_PT:
                    ch, reason = "hidden-format", f"font size {size:.2f}pt"
                elif len(wtext) >= 3 and wbox.width / len(wtext) < 0.6:
                    ch, reason = "hidden-format", "horizontally compressed to a sliver"
                else:
                    ink, contrast = _ink(arr, scale, wbox, color)
                    if ink > INK_MAX and len(wtext) >= 2:
                        # glyph-shaped ink never fills most of a word box: this is a same-colour fill
                        ch, reason = "hidden-covered", "text drawn over a fill of its own colour (bar or box)"
                    elif ink < INK_MIN:
                        if contrast < CONTRAST_MIN:
                            ch, reason = "hidden-format", "text colour matches the background"
                        elif _covered_later(bboxlog, seq, wbox):
                            ch, reason = "hidden-covered", "covered by a later shape or image"
                        else:
                            ch, reason = "hidden-covered", "not rendered on the page (covered or clipped)"
                if ch == VISIBLE:
                    vis_words.append(wtext)
                    vis_ink.append((wtext, ink, contrast))
                    min_size = min(min_size, size)
                elif ch == OCR_LAYER:
                    layer_words.append(wtext)
                classified.append((ch, reason, wtext))

            hidden_groups = {}
            for ch, reason, wtext in classified:
                if ch in (VISIBLE, OCR_LAYER):
                    continue
                hidden_groups.setdefault((ch, reason), []).append(wtext)
            for (ch, reason), ws in hidden_groups.items():
                segs.append(Segment(" ".join(ws), ch, where, reason, pno + 1))
            if vis_words:
                segs.append(Segment(" ".join(vis_words), VISIBLE, where, "", pno + 1))
            if layer_words:
                segs.append(Segment(" ".join(layer_words), OCR_LAYER, where, "sender's OCR layer", pno + 1))

            # ---- extraction view vs drawn glyphs ----
            # A word an extractor returns that is not in the stream of drawn glyphs was never drawn:
            # ActualText substitution, clip-mode (7) text, or text with no glyphs at all.
            ext_words_raw = [w[4] for w in page.get_text("words", clip=fitz.INFINITE_RECT())]
            glyphs = "".join(fold("".join(chr(c[0]) for sp in trace for c in (sp.get("chars") or []))).split())
            extra_words = [w for w in ext_words_raw
                           if any(len(t) >= 2 and t not in glyphs for t in words(w))]
            txt = " ".join(extra_words)
            if letters(txt) >= 4:
                segs.append(Segment(txt, "hidden-extraction-only", where,
                                    "in the extracted text (what an AI reads) but never drawn: "
                                    "ActualText replacement or clip-mode text", pno + 1))
            if not trace and ext_words_raw:
                segs.append(Segment(" ".join(ext_words_raw), "hidden-extraction-only", where,
                                    "page has extractable text but nothing is drawn", pno + 1))
            if pno in ocg_words:
                base = Counter(words(page.get_text("text")))
                extra_ocg = Counter(ocg_words[pno]) - base
                if extra_ocg:
                    segs.append(Segment(" ".join(extra_ocg.elements()), "hidden-ocg", where,
                                        "text in an optional-content layer that is switched off", pno + 1))

            # ---- annotations / fields / links ----
            for a in page.annots() or []:
                info = a.info or {}
                txt = " ".join(filter(None, (info.get("content"), info.get("title"), info.get("subject"))))
                if txt.strip():
                    flag = " (hidden flag)" if a.flags & (fitz.PDF_ANNOT_IS_HIDDEN | fitz.PDF_ANNOT_IS_NO_VIEW) else ""
                    segs.append(Segment(txt, "hidden-annotation", f"{where} {a.type[1]} annotation{flag}", "", pno + 1))
            for wdg in page.widgets() or []:
                txt = " ".join(filter(None, (str(wdg.field_value or ""), wdg.field_label or "")))
                if txt.strip():
                    segs.append(Segment(txt, "hidden-form-field", f"{where} field {wdg.field_name}", "", pno + 1))
            for ln in page.get_links():
                uri = ln.get("uri")
                if not uri:
                    continue
                segs.append(Segment(uri, LINK, where, "", pno + 1))
                anchor = page.get_textbox(ln["from"]) if ln.get("from") else ""
                m = re.search(r"(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})", anchor or "", re.I)
                t = re.search(r"https?://(?:www\.)?([^/:?#]+)", uri, re.I)
                if m and t and "." in m.group(1) and not t.group(1).lower().endswith(m.group(1).lower()):
                    rep.add("medium", "link-text-mismatch", LINK, where, show(anchor, 120),
                            f"link shows {m.group(1)!r} but goes to {t.group(1)!r}", pno + 1)

            # ---- OCR job ----
            has_images = bool(page.get_image_info())
            needs_ocr = bool(vis_words or layer_words) or (has_images and not trace)
            page_state[pno] = {"vis": vis_words, "vis_ink": vis_ink, "layer": layer_words, "image_only": has_images and not trace
                               and not ext_words_raw, "min_size": min_size}
            if pool and needs_ocr:
                dpi = opts.ocr_dpi or (300 if min_size < 7 else 200)
                png = os.path.join(tmp.name, f"p{pno}.png")
                try:
                    pix_arr_png(page, dpi, png)
                    ocr_jobs[pno] = pool.submit(_tesseract, png, opts.lang, 180)
                except Exception as e:
                    rep.notes.append(f"p.{pno + 1}: render for OCR failed: {e}")
                    rep.pages_unverified.append(pno + 1)

        # ---- collect OCR ----
        ocr_text = {}
        if pool:
            remaining = max(5.0, opts.time_budget - (time.time() - t_start))
            done, not_done = wait(list(ocr_jobs.values()), timeout=remaining)
            for pno, fut in ocr_jobs.items():
                if fut in done and not fut.exception():
                    ocr_text[pno] = fut.result()
                else:
                    rep.pages_unverified.append(pno + 1)
                    if fut in done:
                        rep.notes.append(f"p.{pno + 1}: OCR failed: {fut.exception()}")
                    fut.cancel()
        rep.pages_ocr = len(ocr_text)
        _compare_ocr(doc, page_state, ocr_text, segs, rep)

        # ---- emit-visible model ----
        diff_pages = {s.page for s in segs if s.channel == OCR_DIFF}
        for pno in sorted(page_state):
            st = page_state[pno]
            if pno in ocr_text and (pno in diff_pages or st["layer"] or st["image_only"]):
                why = ("text layer disagrees with the rendered page" if pno in diff_pages
                       else "scanned page" if st["layer"] else "image-only page")
                rep.visible_text.append(f"[p.{pno + 1}: {why}; OCR of the rendered page substituted]")
                rep.visible_text.append(ocr_text[pno])
            elif st["layer"] and pno not in ocr_text:
                rep.visible_text.append(f"[p.{pno + 1}: scanned page, OCR not run; sender's OCR layer withheld]")
                if st["vis"]:
                    rep.visible_text.append(" ".join(st["vis"]))
            elif st["vis"]:
                rep.visible_text.append(" ".join(st["vis"]))
        image_only = [p + 1 for p, st in page_state.items() if st["image_only"]]
        if image_only:
            for p in image_only:
                if p - 1 in ocr_text:
                    segs.append(Segment(ocr_text[p - 1], VISIBLE_OCR, f"p.{p}", "OCR of image-only page", p))
            rep.add("low", "image-only-pages", "render", f"{len(image_only)} page(s)", "",
                    "pages with no text layer: text was OCR'd for pattern checks, but faint or tiny text "
                    "inside images (readable by a vision model) is not assessed", image_only[0])
        layer_unverified = [p + 1 for p, st in page_state.items() if st["layer"] and p not in ocr_text]
        if layer_unverified:
            rep.add("medium", "ocr-layer-unverified", OCR_LAYER, f"{len(layer_unverified)} page(s)", "",
                    "scanned pages carry a sender's OCR layer that was not checked against the image "
                    "(OCR off, failed, or out of time); a poisoned layer would pass", layer_unverified[0])
        if rep.pages_unverified:
            unv = sorted(set(rep.pages_unverified))
            rep.pages_unverified = unv
            if opts.ocr or opts.max_pages:
                rep.add("medium", "unverified-render", "render", f"{len(unv)} page(s)", "",
                        f"pages not checked against their rendering (time budget, max-pages or OCR failure): "
                        f"{', '.join(map(str, unv[:20]))}{'…' if len(unv) > 20 else ''}", unv[0])
        if not opts.ocr:
            rep.notes.append("OCR backstop off (--no-ocr): per-word render check still ran; "
                             "scanned pages' OCR layers were not verified")
    finally:
        if pool:
            pool.shutdown(wait=False, cancel_futures=True)
        tmp.cleanup()
    doc.close()
    return segs


def pix_arr_png(page, dpi, png):
    r = page.rect
    px = (r.width * dpi / 72) * (r.height * dpi / 72)
    if px > MAX_PIXELS:
        dpi = max(72, int(dpi * (MAX_PIXELS / px) ** 0.5))
    page.get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csGRAY).save(png)


def _compare_ocr(doc, page_state, ocr_text, segs, rep):
    """Backstop: words presented as readable that the rendered page does not support."""
    for pno, text in ocr_text.items():
        st = page_state[pno]
        presented = [(w, ink, con) for w, ink, con in st["vis_ink"]] + [(w, 0.0, 0) for w in st["layer"]]
        tok_ev = [(t, ink, con) for w, ink, con in presented for t in words(w) if len(t) >= 3]
        tokens = [t for t, _, _ in tok_ev]
        if not tokens:
            continue
        vocab = _Vocab([t for t in words(text)])
        flags = [not vocab.has(t) for t in tokens]
        n = len(tokens)
        unsupported = sum(flags)
        where = f"p.{pno + 1}"
        scanned = bool(st["layer"]) and not st["vis"]
        if n >= 20 and unsupported / n > 0.7:
            rep.add("high", "render-unsupported", OCR_DIFF, where, show(" ".join(tokens[:40])),
                    f"{unsupported} of {n} text-layer words not found on the rendered page "
                    f"(check --lang; otherwise the text layer is not what the page shows)", pno + 1)
            segs.append(Segment(" ".join(t for t, f in zip(tokens, flags) if f), OCR_DIFF, where,
                                "text-layer words not on the rendered page", pno + 1))
            continue
        min_run = 5 if scanned else 4
        runs, i = [], 0
        while i < n:
            if flags[i]:
                j = i
                while j < n and flags[j]:
                    j += 1
                if j - i >= min_run:
                    runs.append((i, tokens[i:j]))
                i = j
            else:
                i += 1
        all_unsup = " ".join(t for t, f in zip(tokens, flags) if f)
        hits = list(pattern_hits(all_unsup, True)) if all_unsup else []
        for start, r in runs:
            if letters(" ".join(r)) < 12:
                continue
            ev = tok_ev[start:start + len(r)]
            inks = sorted(i for _, i, _ in ev)
            small_or_light = st["min_size"] < 9 or min(con for _, _, con in ev) < 160
            inked = (small_or_light and all(con >= 60 for _, _, con in ev)
                     and inks[len(ev) // 2] >= 0.02 and inks[-1] <= INK_MAX)
            if inked:
                rep.add("low", "ocr-unreadable", OCR_DIFF, where, show(" ".join(r)),
                        f"{len(r)} words OCR could not read, but the render check found clear, contrasting "
                        f"glyphs for each (small or light print)", pno + 1)
                continue
            segs.append(Segment(" ".join(r), OCR_DIFF, where,
                                f"{len(r)} consecutive text-layer words not on the rendered page", pno + 1))
            rep.add("high", "ocr-diff", OCR_DIFF, where, show(" ".join(r)),
                    f"{len(r)} consecutive text-layer words not visible on the rendered page", pno + 1)
        for group, name, mt, ex in hits:
            rep.add("critical", f"{group}:{name}", OCR_DIFF, where, show(ex),
                    f"unsupported (not visibly rendered) words match: {show(mt, 120)!r}", pno + 1)
