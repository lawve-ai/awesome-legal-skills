"""Minimal RTF decoder that keeps track of hidden (\\v), colour and size state."""
from __future__ import annotations

import re

from .core import VISIBLE, Segment

TOKEN = re.compile(rb"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}\r\n]+)|[\r\n]+", re.S)
SKIP_DEST = {b"fonttbl", b"stylesheet", b"pict", b"object", b"objdata", b"themedata", b"colorschememapping",
             b"latentstyles", b"datastore", b"listtable", b"listoverridetable", b"rsidtbl", b"generator",
             b"xmlnstbl", b"filetbl", b"revtbl", b"bkmkstart", b"bkmkend", b"shppict", b"nonshppict",
             b"blipuid", b"pgdsctbl", b"mmathPr", b"wgrffmtfilter", b"ftnsep", b"ftnsepc", b"aftnsep", b"aftnsepc",
             b"passwordhash", b"panose", b"falt"}
INFO = {b"info", b"title", b"subject", b"author", b"keywords", b"doccomm", b"comment", b"operator", b"company",
        b"manager", b"category"}


def _contrast(a, b):
    def lum(c):
        c = [v / 255 for v in c]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def scan_rtf(data: bytes, where: str, visible_out=None):
    colors = [None]
    m = re.search(rb"\{\\colortbl(.*?)\}", data, re.S)
    if m:
        colors = []
        for entry in m.group(1).split(b";")[:-1] or [b""]:
            r = re.search(rb"\\red(\d+)", entry)
            g = re.search(rb"\\green(\d+)", entry)
            b = re.search(rb"\\blue(\d+)", entry)
            colors.append((int(r.group(1)), int(g.group(1)), int(b.group(1))) if r and g and b else None)
    cp = "cp1252"
    mcp = re.search(rb"\\ansicpg(\d+)", data)
    if mcp:
        cp = f"cp{mcp.group(1).decode()}"
    state = {"v": False, "cf": 0, "fs": 24, "cb": 0, "hl": 0, "uc": 1, "dest": None, "skip": False}
    stack = []
    out = []   # (channel, reason, text)
    pending_skip = 0
    star = False

    def channel():
        if state["dest"] == "info":
            return "hidden-metadata", ""
        if state["dest"] == "annotation":
            return "hidden-comment", ""
        if state["dest"] == "fldinst":
            return "hidden-field-code", ""
        if state["v"]:
            return "hidden-format", "hidden text (\\v)"
        if state["fs"] <= 8:
            return "hidden-format", f"font size {state['fs'] / 2:g}pt"
        fg = colors[state["cf"]] if 0 <= state["cf"] < len(colors) else None
        bgi = state["hl"] or state["cb"]
        bg = colors[bgi] if bgi and 0 <= bgi < len(colors) and colors[bgi] else (255, 255, 255)
        if fg and _contrast(fg, bg) < 1.3:
            return "hidden-format", f"text colour {fg} on {bg}"
        return VISIBLE, ""

    def emit(txt):
        if state["skip"] or not txt:
            return
        ch = channel()
        if out and out[-1][0] == ch[0] and out[-1][1] == ch[1]:
            out[-1][2].append(txt)
        else:
            out.append((ch[0], ch[1], [txt]))

    for tok in TOKEN.finditer(data):
        word, num, hexb, sym, brace, text = tok.groups()
        if pending_skip and (hexb or text):
            if text:
                n = min(pending_skip, len(text))
                text = text[n:]
                pending_skip -= n
            else:
                pending_skip -= 1
                continue
        if brace == b"{":
            stack.append(dict(state))
            star = False
            continue
        if brace == b"}":
            if stack:
                state = stack.pop()
            continue
        if word is not None:
            n = int(num) if num is not None else None
            if star and word not in (b"fldinst",):
                state["skip"] = True
            star = False
            if word in SKIP_DEST:
                state["skip"] = True
            elif word in INFO:
                state["dest"] = "info"
            elif word in (b"annotation", b"atnid", b"atnauthor"):
                state["dest"] = "annotation"
            elif word == b"fldinst":
                state["dest"] = "fldinst"
                state["skip"] = False
            elif word == b"fldrslt":
                state["dest"] = None
            elif word == b"colortbl":
                state["skip"] = True
            elif word == b"v":
                state["v"] = n != 0
            elif word == b"cf":
                state["cf"] = n or 0
            elif word == b"fs":
                state["fs"] = n if n is not None else 24
            elif word in (b"cb", b"chcbpat"):
                state["cb"] = n or 0
            elif word == b"highlight":
                state["hl"] = n or 0
            elif word == b"plain":
                state.update(v=False, cf=0, fs=24, cb=0, hl=0)
            elif word == b"uc":
                state["uc"] = n if n is not None else 1
            elif word == b"u" and n is not None:
                emit(chr(n + 65536 if n < 0 else n))
                pending_skip = state["uc"]
            elif word in (b"par", b"line", b"sect", b"page", b"cell", b"row", b"tab"):
                emit("\n" if word != b"tab" else " ")
            elif word in (b"emdash",):
                emit("—")
            elif word in (b"endash",):
                emit("–")
            elif word in (b"lquote", b"rquote"):
                emit("'")
            elif word in (b"ldblquote", b"rdblquote"):
                emit('"')
            continue
        if hexb is not None:
            emit(bytes([int(hexb, 16)]).decode(cp, "replace"))
            continue
        if sym is not None:
            if sym == b"*":
                star = True
            elif sym in (b"\\", b"{", b"}"):
                emit(sym.decode())
            elif sym == b"~":
                emit("\u00a0")
            elif sym == b"-":
                pass
            elif sym in (b"\n", b"\r"):
                emit("\n")
            continue
        if text:
            emit(text.decode(cp, "replace"))
    segs = []
    for ch, why, parts in out:
        txt = "".join(parts)
        if txt.strip():
            segs.append(Segment(txt, ch, where, why))
            if ch == VISIBLE and visible_out is not None:
                visible_out.append(txt)
    return segs
