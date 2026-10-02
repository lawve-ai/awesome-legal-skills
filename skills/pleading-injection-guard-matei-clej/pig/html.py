"""HTML scanning: parsed tree + minimal CSS resolution."""
from __future__ import annotations

import re

import lxml.html
from lxml import etree

from .core import VISIBLE, Segment, Unscannable, letters

NAMED = {"white": "ffffff", "black": "000000", "red": "ff0000", "green": "008000", "blue": "0000ff",
         "yellow": "ffff00", "gray": "808080", "grey": "808080", "silver": "c0c0c0", "whitesmoke": "f5f5f5",
         "snow": "fffafa", "ivory": "fffff0", "ghostwhite": "f8f8ff", "azure": "f0ffff", "mintcream": "f5fffa",
         "floralwhite": "fffaf0", "seashell": "fff5ee", "linen": "faf0e6", "navy": "000080", "lightgray": "d3d3d3",
         "lightgrey": "d3d3d3", "gainsboro": "dcdcdc"}
SKIP_TAGS = {"script", "style", "template", "head", "title", "meta", "link", "noscript", "iframe", "object"}
BLOCK = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section",
         "article", "blockquote", "pre", "ul", "ol", "hr"}


def _color(v):
    v = (v or "").strip().lower()
    if not v or v in ("inherit", "initial", "currentcolor"):
        return None
    if v == "transparent":
        return "transparent"
    if v in NAMED:
        return NAMED[v]
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            if len(h) == 4 and h[3] == "0":
                return "transparent"
            return "".join(c * 2 for c in h[:3])
        if len(h) == 8 and int(h[6:], 16) < 40:
            return "transparent"
        return h[:6]
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)%?\s*[, ]\s*([\d.]+)%?\s*[, ]\s*([\d.]+)%?(?:\s*[,/]\s*([\d.]+%?))?\s*\)", v)
    if m:
        if m.group(4) is not None:
            a = m.group(4)
            a = float(a[:-1]) / 100 if a.endswith("%") else float(a)
            if a < 0.15:
                return "transparent"
        return "".join(f"{min(255, int(float(x))):02x}" for x in m.groups()[:3])
    m = re.fullmatch(r"hsla?\(\s*([\d.]+)(?:deg)?\s*[, ]\s*([\d.]+)%\s*[, ]\s*([\d.]+)%.*\)", v)
    if m:
        import colorsys
        r, g, b = colorsys.hls_to_rgb(float(m.group(1)) / 360, float(m.group(3)) / 100, float(m.group(2)) / 100)
        return "".join(f"{int(x * 255):02x}" for x in (r, g, b))
    return None


def _px(v, parent_px=16.0):
    v = (v or "").strip().lower()
    m = re.match(r"(-?[\d.]+)\s*(px|pt|em|rem|%|in|cm|mm|vw|vh)?", v)
    if not m:
        return None
    n = float(m.group(1))
    u = m.group(2) or "px"
    return n * {"px": 1, "pt": 4 / 3, "em": parent_px, "rem": 16, "%": parent_px / 100, "in": 96, "cm": 37.8,
                "mm": 3.78, "vw": 12, "vh": 8}[u]


def _decls(s, with_importance=False):
    out, imp = {}, {}
    for d in (s or "").split(";"):
        if ":" in d:
            k, v = d.split(":", 1)
            k = k.strip().lower()
            v = v.strip().lower()
            important = "!important" in v
            out[k] = v.replace("!important", "").strip()
            imp[k] = important
    return (out, imp) if with_importance else out


def _rules(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@media[^{]*\{((?:[^{}]*\{[^{}]*\})*)\s*\}", r"\1", css)   # flatten media queries
    rules = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        decl, imp = _decls(m.group(2), True)
        for sel in m.group(1).split(","):
            sel = sel.strip()
            if sel and not sel.startswith("@"):
                rules.append((sel, decl, imp))
    return rules


class Unsupported(Exception):
    pass


BENIGN_PSEUDO = {"link", "visited", "root", "first-child", "last-child", "only-child", "first-of-type",
                 "last-of-type", "only-of-type", "empty", "is", "where", "nth-child", "nth-of-type",
                 "nth-last-child", "nth-last-of-type"}
DYNAMIC_PSEUDO = {"hover", "focus", "active", "focus-within", "focus-visible", "target", "checked", "disabled",
                  "enabled", "before", "after", "first-line", "first-letter", "selection", "placeholder",
                  "marker", "backdrop"}


def _simple_match(el, comp):
    nots = re.findall(r":not\(([^()]*)\)", comp)
    comp = re.sub(r":not\([^()]*\)", "", comp)
    for pseudo, arg in re.findall(r"::?([\w-]+)(\([^)]*\))?", comp):
        if pseudo in DYNAMIC_PSEUDO:
            return False          # not in effect in the default rendering
        if pseudo not in BENIGN_PSEUDO:
            raise Unsupported(pseudo)
        if pseudo in ("first-child", "last-child", "only-child"):
            par = el.getparent()
            sibs = [c for c in par if isinstance(c.tag, str)] if par is not None else [el]
            if (pseudo == "first-child" and sibs[0] is not el) or (pseudo == "last-child" and sibs[-1] is not el) \
                    or (pseudo == "only-child" and len(sibs) != 1):
                return False
        elif pseudo not in ("link", "visited", "root", "is", "where"):
            raise Unsupported(pseudo)
    comp = re.sub(r"::?[\w-]+(\([^)]*\))?", "", comp)
    for n in nots:
        if all(_simple_match(el, part.strip()) for part in [n] if part.strip()):
            return False
    m = re.fullmatch(r"([\w-]+|\*)?((?:[.#][\w-]+|\[[^\]]+\])*)", comp)
    if not m:
        return False
    tag, rest = m.group(1), m.group(2)
    if tag and tag != "*" and el.tag != tag:
        return False
    classes = set((el.get("class") or "").split())
    for kind, name in re.findall(r"([.#])([\w-]+)", rest):
        if kind == "." and name not in classes:
            return False
        if kind == "#" and el.get("id") != name:
            return False
    for attr in re.findall(r"\[([^\]=~|^$*]+)", rest):
        if el.get(attr.strip()) is None:
            return False
    return True


def _matches(el, sel):
    if re.search(r"[+~]", re.sub(r"\([^)]*\)", "", sel)):
        raise Unsupported("sibling combinator")
    parts = re.split(r"\s*>\s*|\s+(?![^(]*\))", sel.strip())
    if not parts or not _simple_match(el, parts[-1]):
        return False
    anc = el.getparent()
    for comp in reversed(parts[:-1]):
        while anc is not None and not _simple_match(anc, comp):
            anc = anc.getparent()
        if anc is None:
            return False
        anc = anc.getparent()
    return True


def _hidden_by(st, font_px, color, bg, attrs):
    if attrs.get("hidden") is not None:
        return "hidden attribute"
    if st.get("display") == "none":
        return "display:none"
    if st.get("visibility") in ("hidden", "collapse"):
        return "visibility:hidden"
    op = st.get("opacity")
    try:
        if op is not None and float(op.rstrip("%")) / (100 if op.endswith("%") else 1) < 0.15:
            return f"opacity:{op}"
    except ValueError:
        pass
    m = re.search(r"opacity\(\s*([\d.]+)(%?)\s*\)", st.get("filter", ""))
    if m and float(m.group(1)) / (100 if m.group(2) else 1) < 0.15:
        return f"filter:{st.get('filter')}"
    if _color(st.get("-webkit-text-fill-color")) == "transparent":
        return "-webkit-text-fill-color: transparent"
    if font_px is not None and font_px < 4:
        return f"font-size {font_px:.1f}px"
    if color == "transparent":
        return "transparent text"
    if color and bg and bg != "transparent" and _contrast(color, bg) < 1.3:
        return f"text colour #{color} on background #{bg}"
    for k in ("left", "top", "right", "margin-left", "margin-top", "text-indent"):
        v = _px(st.get(k)) if st.get(k) else None
        if v is not None and (v <= -500 or (k in ("left", "top", "margin-left", "margin-top") and v >= 5000)):
            return f"{k}:{st.get(k)} (off-screen)"
    tr = st.get("transform", "")
    m = re.search(r"translate[xy]?\(\s*(-?[\d.]+)", tr)
    if m and abs(float(m.group(1))) >= 1000:
        return f"transform:{tr}"
    if re.search(r"scale[xy]?\(\s*0(?:\.0+)?\s*[,)]", tr):
        return f"transform:{tr}"
    cp = st.get("clip-path", "") + " " + st.get("clip", "")
    if re.search(r"inset\(\s*(?:50|100)%|circle\(\s*0|rect\(\s*0(?:px)?[ ,]+0(?:px)?[ ,]+0(?:px)?[ ,]+0", cp):
        return f"clipped ({cp.strip()})"
    of = st.get("overflow", "")
    for k in ("height", "width", "max-height", "max-width"):
        v = _px(st.get(k)) if st.get(k) else None
        if v is not None and v <= 1 and ("hidden" in of or "clip" in of or k.startswith("max")):
            return f"{k}:{st.get(k)} with overflow hidden"
    return None


def _contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    try:
        la, lb = lum(a), lum(b)
    except (ValueError, IndexError):
        return 21
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def scan_html(html: str, where: str, visible_out=None):
    segs = []
    for m in re.finditer(r"<!--(.*?)-->", html, re.S):
        c = m.group(1).strip()
        if c and not c.startswith("[if") and not c.startswith("<![endif]"):
            segs.append(Segment(c, "hidden-html-comment", where))
    try:
        parser = lxml.html.HTMLParser(encoding="utf-8", huge_tree=True)
        doc = lxml.html.document_fromstring(html.encode("utf-8", "replace"), parser=parser)
        fatal = [e for e in parser.error_log if e.level_name == "FATAL"]
        if fatal:
            raise Unscannable(f"HTML could not be parsed completely: {fatal[0].message[:120]}")
    except (etree.ParserError, ValueError):
        return segs + [Segment(re.sub(r"<[^>]+>", " ", html), VISIBLE, where, "unparseable HTML")]
    rules = []
    for st in doc.iter("style"):
        rules += _rules(st.text_content())
    for el in doc.iter("title"):
        if el.text_content().strip():
            segs.append(Segment(el.text_content(), "hidden-metadata", f"{where} <title>"))
    for el in doc.iter("meta"):
        if el.get("content") and len(el.get("content")) > 12:
            segs.append(Segment(el.get("content"), "hidden-metadata", f"{where} <meta {el.get('name') or el.get('property') or ''}>"))
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for a in ("alt", "title", "aria-label"):
            if el.get(a) and len(el.get(a)) >= 12:
                segs.append(Segment(el.get(a), "hidden-alt-text", f"{where} <{el.tag} {a}>"))

    out = []   # (channel, reason, text)

    def walk(el, inherited, hidden_reason):
        if not isinstance(el.tag, str):
            return
        tag = el.tag.lower()
        st, st_imp = {}, {}
        for sel, decl, imp in rules:
            try:
                if _matches(el, sel):
                    for k, v in decl.items():
                        if imp.get(k) or not st_imp.get(k):
                            st[k] = v
                            st_imp[k] = imp.get(k, False)
            except Unsupported as u:
                if any(k in decl for k in ("display", "visibility", "opacity", "font-size", "color", "clip-path",
                                           "clip", "transform", "position", "filter", "height", "width")):
                    unsupported.add(f"{sel} (:{u})")
            except re.error:
                continue
        inl, inl_imp = _decls(el.get("style"), True)
        for k, v in inl.items():
            if inl_imp.get(k) or not st_imp.get(k):
                st[k] = v
        font = inherited["font"]
        if "font-size" in st:
            v = _px(st["font-size"], font)
            font = v if v is not None else font
        elif "font" in st:
            m = re.search(r"(-?[\d.]+(?:px|pt|em|rem|%))", st["font"])
            if m:
                font = _px(m.group(1), font) or font
        color = _color(st.get("color")) or inherited["color"]
        bgv = _color(st.get("background-color") or (st.get("background", "").split() or [None])[0]) \
            or _color(el.get("bgcolor"))
        bg = bgv if bgv and bgv != "transparent" else inherited["bg"]
        if tag in ("font",) and el.get("color"):
            color = _color(el.get("color")) or color
        why = hidden_reason
        if why is None and tag == "input":
            val = el.get("value") or ""
            if val.strip():
                hidden_input = (el.get("type") or "").lower() == "hidden"
                out.append(("hidden-css" if hidden_input else VISIBLE, "hidden form input" if hidden_input else "", val))
        if why is None and tag in ("title", "desc") and el.getparent() is not None and \
                str(el.getparent().tag).lower() in ("svg", "g", "text"):
            out.append(("hidden-css", "SVG title/description (tooltip only)", el.text_content()))
            return
        if why is None:
            if tag in ("template", "noscript"):
                why = f"<{tag}> content"
            elif tag in SKIP_TAGS:
                return
            else:
                why = _hidden_by(st, font, color, bg, el.attrib)
                if why and st.get("display") != "none" and st.get("visibility") in ("visible",) and "visibility" in why:
                    why = None
        elif tag in ("script", "style"):
            return
        ctx = {"font": font, "color": color, "bg": bg}
        if el.text:
            out.append(("hidden-css" if why else VISIBLE, why or "", el.text))
        closed_details = tag == "details" and el.get("open") is None
        for c in el:
            cwhy = why
            if closed_details and cwhy is None and isinstance(c.tag, str) and c.tag.lower() != "summary":
                cwhy = "inside a closed <details>"
            walk(c, ctx, cwhy)
            if c.tail:
                out.append(("hidden-css" if why else VISIBLE, why or "", c.tail))
        if tag in BLOCK:
            out.append((VISIBLE if not why else "hidden-css", why or "", "\n"))

    unsupported = set()
    body = doc.find("body")
    try:
        walk(body if body is not None else doc, {"font": 16.0, "color": "000000", "bg": "ffffff"}, None)
    except RecursionError:
        raise Unscannable("HTML nested too deeply to analyse")
    if unsupported:
        segs.append(Segment("; ".join(sorted(unsupported))[:500], "hidden-metadata", f"{where} CSS",
                            "unsupported selectors that may hide content"))
        segs.append(Segment("", "css-unverified", where, "; ".join(sorted(unsupported))[:300]))
    src_letters = letters(re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", html, flags=re.S | re.I))
    got_letters = sum(letters(t) for _, _, t in out)
    if src_letters > 200 and got_letters < 0.5 * src_letters:
        raise Unscannable(f"HTML analysis recovered {got_letters} of ~{src_letters} letters; refusing a partial result")
    # merge consecutive pieces of the same channel/reason
    merged = []
    for ch, why, t in out:
        if merged and merged[-1][0] == ch and merged[-1][1] == why:
            merged[-1][2].append(t)
        else:
            merged.append((ch, why, [t]))
    for ch, why, parts in merged:
        txt = " ".join(p.strip() for p in parts if p.strip())
        if txt:
            segs.append(Segment(txt, ch, where, why))
            if ch == VISIBLE and visible_out is not None:
                visible_out.append(txt)
    return segs
