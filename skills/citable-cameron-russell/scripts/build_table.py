#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Cameron Russell (ccrnyc). See LICENSE.
"""citable — build a citation table (HTML + CSV) for one filed document.

Usage: build_table.py <case_folder> <filing.pdf> <citable-map.json> [--previous <old table.html>] [--out <path stem>] [--allow-no-citations]
       build_table.py --fingerprint <citable-map.json>     (prints the fingerprint to record when the user confirms the map)

The map (format: references/map-format.md) lists exhibits, documents cited by name, defined terms, authorities, unreported
decisions, treaties, dockets and NYSCEF numbers. It must carry "confirmed": {"by", "date", "sha256"}; the build stops if the
map has changed since it was confirmed. Output: citable-<filing>.html and .csv in the case folder (or --out); an existing
table (and its CSV) is first copied to citable-backups/ and its saved review work is carried forward. The build stops if the filing
yields no citations, unless --allow-no-citations is given (only after the user confirms the filing cites nothing). The build log
prints MAP WARNING, COVERAGE WARNINGS, FORMAT WARNINGS and POSSIBLY MISSED lines for the user; none of them goes into the page.

Scripts only; no model calls. Every link comes from the confirmed map.
"""
import collections, sys, os, re, json, csv, html, subprocess, datetime, urllib.parse, tempfile
import pdfplumber

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'vendor'))   # bundled third-party code (nupunkt, MIT); see vendor/*/LICENSE
import argparse, hashlib
def map_fingerprint(cfg):
    """sha256 (first 16 hex digits) of the map without its "confirmed" entry."""
    body = {k: v for k, v in cfg.items() if k != 'confirmed'}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:16]
if len(sys.argv) == 3 and sys.argv[1] == '--fingerprint':
    print(map_fingerprint(json.load(open(sys.argv[2])))); sys.exit(0)
_ap = argparse.ArgumentParser()
_ap.add_argument('case'); _ap.add_argument('doc'); _ap.add_argument('map')
_ap.add_argument('--previous', help='an earlier citable HTML table for this document; saved statuses and notes are carried forward')
_ap.add_argument('--out', help='output path stem, e.g. /tmp/x/citable-MoL (default: citable-<doc> in the case folder)')
_ap.add_argument('--allow-no-citations', action='store_true', help='build the table even if no citations are found (only after checking that the filing cites nothing)')
ARGS = _ap.parse_args()
CASE, DOC, MAPF = ARGS.case, ARGS.doc, ARGS.map
PREV = os.path.abspath(ARGS.previous) if ARGS.previous else None
OUT = os.path.abspath(ARGS.out) if ARGS.out else None   # resolved before the chdir below
if not DOC.lower().endswith('.pdf'):
    sys.exit(f'{os.path.basename(DOC)} is not a PDF. ' + 'citable v1.0 is designed to work with PDFs. If your draft is in Word, make a copy, accept all tracked changes, delete all comments, and save the copy as a PDF (File → Save As → PDF), and then run citable on that copy.')
_absdoc = os.path.abspath(DOC) if os.path.exists(DOC) else os.path.abspath(os.path.join(CASE, DOC))   # any path to the filing
_absmap = os.path.abspath(MAPF) if os.path.exists(MAPF) else os.path.abspath(os.path.join(CASE, MAPF))
if not os.path.exists(_absdoc): sys.exit(f'Filing not found: {DOC}')
os.chdir(CASE)
DOC = os.path.relpath(_absdoc, '.')    # stored relative to the case folder: no full local path in the table
CFG = json.load(open(_absmap))
_conf = CFG.get('confirmed')
if not (isinstance(_conf, dict) and _conf.get('sha256')):
    sys.exit('The map has not been confirmed. Show it to the user; once they confirm it, record '
             '"confirmed": {"by": "<name>", "date": "<YYYY-MM-DD>", "sha256": "<output of build_table.py --fingerprint <map>>"} in the map.')
if _conf['sha256'] != map_fingerprint(CFG):
    sys.exit('The map has changed since it was confirmed. Show the changes to the user and, once they confirm them, '
             'record the new fingerprint (build_table.py --fingerprint <map>) in "confirmed".')
_txt = subprocess.run(['pdftotext', '-layout', DOC, '-'], capture_output=True, text=True).stdout
_np = max(1, _txt.count('\f'))
if len(re.sub(r'\s', '', _txt)) < 100 * _np:
    sys.exit(f'{os.path.basename(DOC)} has no usable text layer (an image-only scan?). OCR it first, then run citable again.')
def safe_url(u):
    """Only http(s) addresses from the map become links."""
    return u if isinstance(u, str) and re.match(r'https?://', u) else None
for _sec, _keys in (('authorities', ('url',)), ('treaties', ('url',)), ('unreported', ('recap', 'docket_url'))):
    for _e in CFG.get(_sec, []):
        for _k in _keys:
            if _e.get(_k) and not safe_url(_e[_k]):
                print(f'MAP WARNING: {_sec} entry {_e.get("cite")!r}: {_k} is not an http(s) address; ignored'); _e.pop(_k)
for _k, _d in CFG.get('dockets', {}).items():
    if _d.get('url') and not safe_url(_d['url']):
        print(f'MAP WARNING: dockets {_k!r}: url is not an http(s) address; ignored'); _d.pop('url')
# (the map is loaded once, from the file whose fingerprint was checked; URLs dropped above stay dropped)
def _spec(v):   # a map entry may point to a page range inside a file
    if isinstance(v, dict): return v['file'] + (f"#pages={v['pages']}" if v.get('pages') else '')
    return v
EXMAP = {k: _spec(v) for k, v in CFG['exhibits'].items()}
DOCS = {k: _spec(v) for k, v in CFG.get('docs', {}).items()}
def realfile(spec):
    """-> (file, first page, last page or None)"""
    m = re.match(r'(.*?)#pages=(\d+)(?:\s*[–-]\s*(\d+))?$', spec or '')
    if not m: return spec, 1, None
    return m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
def abs_page(spec, pg): return realfile(spec)[1] + pg - 1
def href_of(spec, pg): return urllib.parse.quote(realfile(spec)[0]) + f'#page={abs_page(spec, pg)}'
STAMP = re.compile(r'^(?:Case:?\s+\S+\s+Document\s+(?:#\s*:?\s*)?\S+\s+Filed:?\s+\S+\s+Page\s*\d+\s+of\s+\d+(?:\s+Page\s*ID\s*#?:?\s*\d*)?|#:\s*\d+)$')   # the court's header (incl. N.D. Ill. "Case: … Document #: 43 Filed: …"), and a PageID number on its own line
BODY = 12.0   # reset per document to the most common font size (see read_doc)

# ================================================================ 1. read a filed document
def is_heading(t):
    letters = re.sub(r'[^A-Za-z]', '', t)
    return len(letters) >= 4 and letters.isupper() and not re.search(r'\d', t) and len(t) < 90 and not re.search(r'\):$|[,;]$', t.strip())   # "BBPOS & AC):" ends a parenthetical

SMALL = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'v.', 'with', 'from'}
def nice_title(t):
    ws = t.lower().split()
    return ' '.join(w.upper() if re.fullmatch(r'[ivx]+\.', w) else (w if (i and w in SMALL) else (w[:1].upper() + w[1:])) for i, w in enumerate(ws))

def title_case(t):
    """most words capitalised, as in a heading (not a bold sentence of quoted text)"""
    ws = [w for w in re.findall(r"[A-Za-z][\w’'-]*", t) if w.lower() not in SMALL]
    return bool(ws) and sum(w[0].isupper() for w in ws) >= .6 * len(ws)

def is_bold_line(ln):
    cs = [c for c in ln['chars'] if c['text'].strip()]
    return bool(cs) and all(re.search(r'bold|black', c['fontname'].split('+')[-1].lower()) for c in cs) and len(ln['text']) < 200

def is_title(h):
    return bool(re.search(r'\b(Declaration|Petition|Memorandum|Motion|Brief|Complaint)\b', h))

def style_of(w, unders):
    f = w['fontname'].split('+')[-1].lower()
    flags = (1 if ('italic' in f or 'oblique' in f or re.search(r'-it$|,it$', f)) else 0) | (2 if ('bold' in f or 'black' in f) else 0)
    for (x0, x1, top) in unders:
        if w['bottom'] - 1.5 <= top <= w['bottom'] + 3 and min(x1, w['x1']) - max(x0, w['x0']) > 0.5 * (w['x1'] - w['x0']):
            flags |= 4; break
    return flags

def line_text(ln, words, unders=()):
    """Rebuild a line from words: superscript footnote markers become [[FNn]]; also returns the line's
    non-space characters and a parallel flag string (1 italic, 2 bold, 4 underline) so the brief's
    formatting can be shown in the table."""
    ws = [w for w in words if w['top'] >= ln['top'] - 5 and w['bottom'] <= ln['bottom'] + 3 and w['x0'] >= ln['x0'] - 1 and w['x1'] <= ln['x1'] + 1]
    ws.sort(key=lambda w: w['x0'])
    out, nsc, nsf, prev = '', [], [], None
    for w in ws:
        fnm = w['size'] < BODY - 2 and re.fullmatch(r'\d{1,3}', w['text'])
        piece = f'[[FN{w["text"]}]]' if fnm else w['text']
        gap = (w['x0'] - prev['x1']) if prev else 0
        out += ((' ' if (prev is not None and (gap > 1.0 or fnm)) else '') + piece)
        if not fnm:
            fl = style_of(w, unders)
            for ch in w['text']:
                if not ch.isspace(): nsc.append(ch); nsf.append(str(fl))
        prev = w
    return out, ''.join(nsc), ''.join(nsf)

WARN = {}
# what follows a number that is part of a citation, not a footnote number: "28 U.S.C.", "35 F.3d", "12 C.F.R.", "5 §", "540 U.S."
FN_CITE_CONT = re.compile(r'\s*(?:U\.\s?S\.|C\.\s?F\.\s?R\.|F\.\s?(?:\d|Supp|App)|S\.\s?Ct\.|L\.\s?Ed\.|Fed\.\s?(?:Reg|Cl|Appx)|Stat\.|B\.\s?R\.|F\.\s?R\.\s?D\.|T\.\s?C\.|'
                          r'A\.\s?\d|P\.\s?\d|N\.\s?[EYW]\.|S\.\s?[EW]\.|So\.\s?\d|[A-Z][a-z]{1,6}\.\s?(?:2d|3d|4th|App\.|Supp\.)|[§¶]|n\.\s?\d|at\s|[,;:–-]|$)')
HEAD_FNS = {}   # path -> [(footnote number called in a heading, index of the next group)]
COVERW = {}     # path -> {key: coverage warning raised while reading}
STOPINFO = {}   # path -> (PDF page where reading stopped, page count, stop line) or None
BODYHEAD = (r'^(?:(?:[IVX]+|[A-H])\.\s+)?(?:INTRODUCTION|PRELIMINARY STATEMENT|(?:LEGAL )?ARGUMENT|BACKGROUND|(?:CONCISE )?STATEMENT OF (?:THE )?(?:UNDISPUTED |MATERIAL |RELEVANT )*FACTS|'
            r'SUMMARY OF (?:THE )?(?:MATERIAL FACTS|ARGUMENT)|LEGAL STANDARD|STANDARD OF REVIEW|DISCUSSION|CONCLUSION)\b')
def read_doc(path):
    """-> (groups, footnotes). groups: [{label, para, page, text, chunks:[(page,text)]}] in reading order.
    footnotes: {n: {page, text}}. Footnote zone = below the short separator rule in the lower half."""
    groups, fns = [], {}
    cur, cur_fn, heading = None, None, None
    global BODY
    with pdfplumber.open(path) as pdf:
        import collections
        sizes = collections.Counter(round(c['size'], 1) for pg in pdf.pages[:6] for c in pg.chars if c['text'].strip())
        if sizes: BODY = sizes.most_common(1)[0][0]
        gaps = collections.Counter()
        for pg in pdf.pages[:8]:
            tops = [l['top'] for l in pg.extract_text_lines() if l['top'] < pg.height * .6]
            gaps.update(round(b - a) for a, b in zip(tops, tops[1:]) if 8 <= b - a <= 40)
        LINEGAP = gaps.most_common(1)[0][0] if gaps else 0
        DOUBLE = LINEGAP > 1.6 * BODY   # double-spaced body text: single-spaced footnote text is then recognisable by its spacing
        started = not re.search(r'(?m)^\s*(Respondents?|Defendants?)\.?\s*$', pdf.pages[0].extract_text() or '')
        expected, stop = 1, False
        # A "Dated:" / "/s/" line ends the body once the body has begun (a numbered paragraph or a body heading read: "strong";
        # or about a page of text, unless a table of contents follows within two pages). Before that it is a cover page's counsel
        # block, and reading goes on, unless the signature ends the filing (next text page is a slip sheet, a new caption or a
        # certificate, or there is none). A signature line ignored for any other reason is reported (COVERAGE WARNINGS).
        _lay = subprocess.run(['pdftotext', '-layout', realfile(path)[0], '-'], capture_output=True, text=True).stdout.split('\f')
        toc_pages = [i for i, t in enumerate(_lay, 1) if len(re.findall(r'(?m)(?:\.{6,}|…{2,}|(?:\.\s){5,})\s*[\d,\s–-]*$', t)) >= 3]
        def _body_lines(q):
            return [l.strip() for l in (_lay[q - 1] if q - 1 < len(_lay) else '').splitlines() if l.strip() and not ECF_HDR.search(l) and not STAMP.match(l.strip())
                    and not re.fullmatch(r'\d{1,3}|[ivxlc]{1,5}', l.strip())]
        def _ends_here(q):   # does the filing end on PDF p. q?
            for r in range(q + 1, len(_lay) + 1):
                bl = _body_lines(r)
                if not bl: continue
                if len(bl) <= 4 and any(re.fullmatch(r'(?i)(?:exhibit|appendix|attachment|annex|tab)\s+[A-Z0-9-]{1,4}', l) for l in bl): return True
                return any(re.match(r'(?i)(?:UNITED STATES (?:DISTRICT|BANKRUPTCY) COURT|IN THE .{0,60}COURT|SUPREME COURT|CERTIFICATE OF (?:SERVICE|COMPLIANCE))', l) for l in bl[:8])
            return True
        body_begun, body_strong, read_chars, skip_page = False, False, 0, 0
        STOPINFO[path] = None; COVERW.setdefault(path, {})
        called, in_toc, last_zone_page, called_all = {}, False, -1, {}
        calls, texts_n, cur_fd = {}, collections.Counter(), None   # every call of a footnote number (PDF page, top); footnote texts read per number; the footnote text being read
        prefix = ''   # a second numbered series after a heading (e.g. a counterstatement) gets its own labels
        for pno, p in enumerate(pdf.pages, 1):
            if stop: break
            # FOOTNOTES. Primary signal: footnote numbers called in the text (small raised digits right after a word or punctuation)
            # matched to a line, lower on the page, that starts with the same number. The divider rule is only a hint: for
            # footnotes whose numbers are set in body-size type, and for a footnote continued from the previous page.
            rules = [l['top'] for l in p.lines if l['top'] > p.height * .45 and l['x0'] < 90 and l['x1'] - l['x0'] >= 125] + \
                    [r['top'] for r in p.rects if r['height'] < 2 and r['top'] > p.height * .45 and r['x0'] < 90 and r['x1'] - r['x0'] >= 125]
            words = p.extract_words(extra_attrs=['size', 'fontname'])
            for w in words:
                if w['size'] < BODY - 2 and re.fullmatch(r'\d{1,3}', w['text']) and any(
                        u['size'] >= BODY - 1.5 and u['top'] < w['bottom'] and u['bottom'] > w['top'] and -0.5 <= w['x0'] - u['x1'] <= 3 for u in words):
                    called.setdefault(w['text'], (pno, w['top'])); called_all.setdefault(w['text'], []).append(pno)
                    calls.setdefault(w['text'], []).append((pno, w['top']))
            plines = p.extract_text_lines()
            acc = collections.Counter()   # footnote texts accepted on this page, per number
            def _is_called(n, top):   # more calls of n before this line than footnote texts numbered n already read: the next text of n starts here
                before = sum(1 for cp, ct in calls.get(n, []) if cp < pno or ct < top)
                return before > texts_n[n] + acc[n]
            def _new_fn_line(ln, n_):
                # N8-F/N8-W: may this line, which begins with the number of a footnote just read on this page, start a second footnote
                # with that number? Only if the line above it ends a sentence and what follows the number does not read as a citation:
                # a wrapped footnote line such as "28 U.S.C. § 1331, …" inside footnote 28 stays part of that footnote.
                above = [l2 for l2 in plines if l2['top'] < ln['top'] - 1 and l2['text'].strip()]
                ends = bool(above) and bool(re.search(r'[.?!][”"’)\]]*\s*$', max(above, key=lambda l2: l2['top'])['text']))
                cite = bool(FN_CITE_CONT.match(ln['text'].strip()[len(n_):]))
                return ends and not cite, cite
            starts = []
            for ln in plines:
                fw = ln['chars'][0] if ln['chars'] else None
                mm = re.match(r'^(\d{1,3})(?!\d)', ln['text'].strip())
                if not (fw and mm) or ln['top'] < p.height * .3: continue
                n_ = mm.group(1)
                # N8 (a): a second footnote text on this page with the number of one just read (called only once); only a number set small, so that
                # a wrapped footnote line that begins with that number ("35 U.S.C. …") is not split off
                dup = False
                if not _is_called(n_, ln['top']) and acc[n_] > 0:
                    dup, cite_like = _new_fn_line(ln, n_)
                    if not dup and not cite_like:
                        WARN.setdefault(f'fn {n_} line p{pno}', f'A line in footnote {n_} on PDF p. {pno} begins with "{n_}", which may start a second footnote {n_}; '
                                                              f'it was read as part of the footnote above it: check the filing\'s footnote numbering.')
                if not (_is_called(n_, ln['top']) or dup): continue
                nxt = next((l2 for l2 in plines if l2['top'] > ln['top'] + 1), None)
                single = DOUBLE and nxt is not None and nxt['top'] - ln['top'] < .75 * LINEGAP   # single-spaced text under it, in a double-spaced filing
                if dup or fw['size'] < BODY - 2 or any(t < ln['top'] < t + 30 for t in rules) or single:   # small number; or full-size number under a rule or opening single-spaced text
                    starts.append(ln['top']); acc[n_] += 1
            texts_n.update(acc)
            zone = [min(starts) - 0.5] if starts else []
            fn_open = last_zone_page == pno - 1 and cur_fd is not None and not re.search(r'[.?!][”"’)\]]*\s*$', cur_fd['text'])
            if fn_open:   # the last footnote on the previous page may continue here
                top = None
                body_ = [ln for ln in plines if ln['text'].strip() and not STAMP.match(ln['text'].strip()) and not re.fullmatch(r'\d{1,3}|[ivxlc]{1,5}|#:\s*\d+', ln['text'].strip())]
                for i in range(len(body_) - 1, -1, -1):   # walk up from the bottom of the page
                    ln = body_[i]
                    cs = [ch for ch in ln['chars'] if ch['text'].strip()]
                    small_type = bool(cs) and sum(ch['size'] < BODY - 1 for ch in cs) >= .7 * len(cs)
                    tight = DOUBLE and i > 0 and ln['top'] - body_[i - 1]['top'] < .75 * LINEGAP
                    below_tight = DOUBLE and top is not None
                    if small_type or tight or below_tight: top = ln['top']
                    if not (small_type or tight): break
                if top is not None: zone.append(top - 0.5)
                elif rules: zone.append(min(rules))
                else: WARN.setdefault(f'n.{cur_fn} p{pno}', f'Footnote {cur_fn} may continue onto PDF p. {pno}, but its continuation could not be located; check that page.')
            fn_top = min(zone) if zone else None
            if fn_top is not None: last_zone_page = pno
            fn_starts = set(starts)
            unders = [(l['x0'], l['x1'], l['top']) for l in p.lines if abs(l['top'] - l['bottom']) < 1.5 and (l['x1'] - l['x0']) < p.width * .8] + \
                     [(r['x0'], r['x1'], r['top']) for r in p.rects if r['height'] < 1.5 and (r['x1'] - r['x0']) < p.width * .8]
            leaders = sum(1 for l in plines if re.search(r'(?:\.{6,}|…{2,}|(?:\.\s){5,})\s*[\d,\s]*$', l['text']))
            if leaders >= 3 or (in_toc and leaders >= 1):
                # table of contents / authorities page (or its last page, with only a few entries): skip it; anything captured before it
                # was cover material, unless the body had begun: then the contents page belongs to an attached document, and reading stops
                if started and body_strong and not in_toc:
                    stop = True; STOPINFO[path] = (pno - 1, len(pdf.pages), 'a table of contents')
                    COVERW[path]['toc'] = (f'A table of contents on PDF p. {pno}, after the body of the filing, was read as the start of an attached '
                                           f'document: reading stopped there. If the filing continues after it, the table is incomplete.')
                    continue
                if started:
                    _cleared = sum(len(g['text']) for g in groups)
                    if _cleared > 2500:
                        COVERW[path][f'toc{pno}'] = (f'The text before the table of contents on PDF p. {pno} ({_cleared} characters) was treated as cover '
                                                     f'material and left out of the table: check that it holds no cited passages.')
                    groups.clear(); cur, heading, expected = None, None, 1; HEAD_FNS[path] = []
                in_toc = True
                continue
            in_toc = False
            prev_head = False
            for ln in plines:
                raw = ln['text'].strip()
                if not raw or STAMP.match(raw) or re.fullmatch(r'\d{1,3}|[ivxlc]{1,5}', raw):
                    continue
                if (skip_page == pno or stop) and not (fn_top is not None and ln['top'] > fn_top):
                    continue   # the rest of a cover page's counsel block, or of the signature page
                if fn_top is not None and ln['top'] > fn_top:
                    m = re.match(r'^(\d{1,3})\s*(.*)', raw)
                    t, c, f = line_text(ln, words, unders)
                    if m and ln['top'] in fn_starts:
                        cur_fn = m.group(1)
                        t0 = t; t = re.sub(r'^\[\[FN\d+\]\]\s*', '', t)
                        _k = re.match(re.escape(cur_fn) + r'(?!\d)\s*', t) if t == t0 else None
                        if _k:   # a footnote number set in body-size type ("35See also …" when the number and the text touch): not part of the text
                            t = t[_k.end():]; c, f = c[len(cur_fn):], f[len(cur_fn):]
                        t = re.sub(r'\s?\[\[FN(\d+)\]\]', r' \1', t)   # digits in footnote-size type are text, not markers
                        cur_fd = {'page': pno, 'text': t, 'nsc': c, 'nsf': f}
                        if cur_fn in fns: fns[cur_fn].setdefault('more', []).append(cur_fd)   # a second footnote text with this number: kept, never overwritten
                        else: fns[cur_fn] = cur_fd
                    elif cur_fd is not None:
                        t = re.sub(r'\s?\[\[FN(\d+)\]\]', r' \1', t).lstrip()   # a continuation line that begins with small digits: no double space
                        cur_fd['text'] += ' ' + t; cur_fd['nsc'] += c; cur_fd['nsf'] += f
                    continue
                if not started:
                    if re.match(r'^(Respondents?|Defendants?)\.?$', raw): started = True
                    continue
                if re.match(r'^Civil Action No', raw): continue
                if re.match(r'^(Dated:|Executed on:|I declare under penalty|By:|/s/)', raw):
                    toc_next = any(pno < tp <= pno + 2 for tp in toc_pages)
                    if body_strong or (body_begun and not toc_next) or _ends_here(pno):
                        stop = True; STOPINFO[path] = (pno, len(pdf.pages), raw[:40]); continue   # footnotes below the signature on this page are still read
                    if skip_page != pno and not toc_next:
                        COVERW[path][f'sig{pno}'] = (f'The signature line "{raw[:40]}" on PDF p. {pno} came before much body text and was read as part of a cover '
                                                     f'page, so reading went on past it. If the filing ends there, the pages after it were read as part of it: check.')
                    skip_page = pno; continue   # cover page: skip the rest of its counsel block and read on
                t, c, f = line_text(ln, words, unders)
                mnum = re.match(r'^(\d{1,3})\.\s+(\S.*)$', raw)
                # a numbered sub-heading ("1. BBPOS", an underlined "1. Standard of Review (Counts I and II)") is a heading, not a
                # paragraph: a short line without closing punctuation, set in bold or underlined, or out of the paragraph sequence
                styled = mnum and c[len(mnum.group(1)) + 1:] and all(int(x) & 6 for x in f[len(mnum.group(1)) + 1:])
                subhead = bool(mnum) and started and len(raw) < 70 and not re.search(r'[.;,”"’]$', raw) and \
                    (styled or (int(mnum.group(1)) != expected and title_case(mnum.group(2))))
                # a bold line is a heading only if it starts with an outline marker, continues a heading, or reads like a title:
                # bold quoted text (testimony, contract language) is not a heading
                bold_head = started and not mnum and is_bold_line(ln) and (
                    re.match(r'^(?:[IVX]+|[A-Z]|[a-z]|\d{1,2})\.\s|^\([a-z0-9]{1,4}\)\s', raw) or
                    (prev_head and heading and not re.search(r'[.:]$', heading)) or
                    (raw[:1].isupper() and not re.search(r'[a-z]\.\s+[A-Z]|[,;:”"’]$|\.”?$', raw) and len(raw) < 90 and title_case(raw)))
                if is_heading(raw) or bold_head or subhead:
                    rawh = re.sub(r'\s*\[\[FN\d+\]\]', '', t).strip() or raw   # a footnote number called in a heading is not part of its text
                    txt = nice_title(rawh) if is_heading(raw) else rawh
                    for _n in re.findall(r'\[\[FN(\d+)\]\]', t): HEAD_FNS.setdefault(path, []).append((_n, len(groups)))   # read with the passage that follows
                    new_section = re.match(r'^([IVX]+|[A-H]|\d{1,2})\.\s', raw) or (is_heading(raw) and len(raw) < 30 and not (prev_head and heading and not re.search(r'[.:]$', heading)))
                    if heading and cur is None and (not groups or (prev_head and not new_section)): heading += ' ' + txt
                    else: heading = txt
                    if re.search(BODYHEAD, raw, re.I): body_begun = body_strong = True
                    cur = None; prev_head = True
                    continue
                prev_head = False
                read_chars += len(raw)
                if read_chars >= 2500: body_begun = True
                m = re.match(r'^(\d{1,3})\.\s+(.*)', t)
                if m and m.group(1) == str(expected): body_begun = body_strong = True
                if m and CFG.get('numbered_paragraphs') is False and path == DOC: m = None
                if m and int(m.group(1)) == 1 and expected > 3 and cur is None and heading:
                    expected = 1
                    prefix = ('Counterstatement ' if re.search(r'counter', heading, re.I) else (heading[:40] + ' '))
                if m and cur is not None and expected < int(m.group(1)) <= expected + 2:   # numbering resumes after a gap
                    WARN.setdefault(f'¶ {m.group(1)}', f'Paragraph numbering skips from ¶ {expected - 1} to ¶ {m.group(1)}: check the brief.')
                    expected = int(m.group(1))
                if m and int(m.group(1)) == expected:
                    expected += 1
                    k = len(m.group(1)) + 1
                    cur = {'label': f'{prefix}¶ {m.group(1)}', 'para': int(m.group(1)), 'page': pno, 'text': m.group(2), 'chunks': [(pno, t)], 'nsc': c[k:], 'nsf': f[k:]}
                    groups.append(cur); continue
                if cur is None:
                    lbl = 'Preamble' if (not heading or (is_title(heading) and not re.match(r'^([IVX]+|[A-H1-9])\.\s', heading))) else heading
                    n_same = sum(1 for g in groups if g['label'] == lbl or g['label'].startswith(lbl + ' ('))
                    if n_same: lbl = f'{lbl} ({n_same + 1})'
                    cur = {'label': lbl, 'para': None, 'page': pno, 'text': '', 'chunks': [], 'nsc': '', 'nsf': ''}
                    groups.append(cur)
                tail = re.search(r'(?<!¶)(?<!¶¶)(?<!\bat)\s(\d{1,3})\.\s*$', t)
                if tail and int(tail.group(1)) == expected and cur is not None and cur['para'] is not None:
                    # a paragraph number stranded at the end of the previous paragraph's last line
                    k = len(tail.group(1)) + 1
                    cur['text'] += ' ' + t[:tail.start()]; cur['nsc'] += c[:-k]; cur['nsf'] += f[:-k]; cur['chunks'].append((pno, t[:tail.start()]))
                    WARN[f'¶ {tail.group(1)}'] = (f'The number “{tail.group(1)}.” sits at the end of the last line of ¶ {expected - 1} instead of starting '
                                                  f'¶ {tail.group(1)} on its own line: check the brief\'s formatting.')
                    cur = {'label': f'{prefix}¶ {tail.group(1)}', 'para': expected, 'page': pno, 'text': '', 'chunks': [], 'nsc': '', 'nsf': ''}
                    groups.append(cur); expected += 1
                    continue
                cur['text'] += ' ' + t
                cur['nsc'] += c; cur['nsf'] += f
                cur['chunks'].append((pno, t))
    for g in groups: g['text'] = g['text'].strip()
    for _n, _i in HEAD_FNS.get(path, []):   # a footnote called in a heading is read just before the first passage under that heading
        if _i < len(groups): groups[_i].setdefault('head_fns', []).append(_n)
    for n in sorted(set(called_all) | set(fns), key=int):   # a footnote number called more than once, or two footnote texts with one number
        pgs = called_all.get(n, [])
        ft = ([fns[n]] + fns[n].get('more', [])) if n in fns else []
        tp = ', '.join(map(str, sorted({x['page'] for x in ft})))
        pp = lambda t: ('PDF pp. ' if ',' in t else 'PDF p. ') + t
        if len(pgs) > 1 and int(n) <= max([int(k) for k in fns] + [0]) + 1:
            cp = ', '.join(map(str, sorted(set(pgs))))
            if len(ft) >= len(pgs):
                WARN.setdefault(f'fn {n} twice', f'Footnote number {n} is called {len(pgs)} times ({pp(cp)}) and {len(ft)} footnote texts start with {n} ({pp(tp)}): '
                                                 f'each call is read with the next of those texts' + (' (the last call also with those left over)' if len(ft) > len(pgs) else '') +
                                                 f', all under n.{n}; check the filing\'s footnote numbering.')
            else:
                WARN.setdefault(f'fn {n} twice', f'Footnote number {n} is called {len(pgs)} times ({pp(cp)}) but only {len(ft)} footnote text{"s" if len(ft) != 1 else ""} '
                                                 f'starting with {n} {"were" if len(ft) != 1 else "was"} found' + (f' ({pp(tp)})' if tp else '') +
                                                 f': the table has rows for {"those" if len(ft) != 1 else "that footnote"} only; check the other call{"s" if len(pgs) - len(ft) > 1 else ""}.')
        elif len(ft) > 1:
            WARN.setdefault(f'fn {n} twice', f'{len(ft)} footnote texts start with {n} ({pp(tp)}), but the text calls footnote {n} only once: '
                                             f'all of them are in the table under n.{n}; check the filing\'s footnote numbering.')
    return groups, fns

# ================================================================ 2. sentences
ABBR = r'(?:Dep|Tr|Hr’g|Hr\'g|[ENSWCM]\.D\. (?:Va|Pa|Tex|Cal|Ill|Mich|La|Fla|Ga|Wis|Wash|Okla|Ala|Miss|Tenn|Ky|Ark|Mo|Ohio|N\.Y|N\.C)|[ENSWCM]\.D|F\. Supp|F\. App|D\.C\. Cir|D\.C|Cir|App|Div|Props|Eng’g|Eng\'g|P\.C|Assocs|Cos|Mut|Ent|Found|Gov’t|Gov\'t|Dep’t|Dep\'t|Auth|Admin|Cont’l|Cont\'l|Distrib|Lab|Mach|Med|Mem’l|Mun|Res|Ret|Techs|Tech|Trs|Am|Ass’n|Ass\'n|Assur|Bros|Ctr|Cmty|Comm’n|Comm\'n|Dev|Educ|Elec|Emps|Enters|Envtl|Equip|Fin|Grp|Hosp|Indus|Ins|Int’l|Int\'l|Inv|Mfg|Mgmt|Mktg|Nat’l|Nat\'l|Pharms|Prods|Pub|Ry|R\.R|Sav|Sch|Servs|Serv|Sols|Sys|Tel|Transp|Univ|Utils|[ENSWCM]\. D|Ala|Ariz|Ark|Colo|Ga|Haw|Ind|Kan|Ky|La|Miss|Mo|Mont|Neb|Nev|N\.H|N\.M|N\.C|N\.D|Okla|R\.I|S\.C|S\.D|Tenn|Vt|W\. ?Va|Wyo|Sup|Cnty|Super|Rptr|Misc|Cal|Mass|Ill|Tex|Del|Ch|Pa|Fla|Conn|Md|Minn|Mich|Wash|Wis|Ohio St|N\.J|N\.E|N\.W|S\.E|S\.W|A\.D|N\.Y\.S|Invs|Supp|Prop|Ukr|Trin|Neth|Venez|Va|Assn|Dist|Ct|Fed\. R\. Civ\. P|Fed\. R\. Evid|Fed\. R\. App\. P|S\.D\.N\.Y|E\.D\.N\.Y|D\.D\.C|N\.D\. Cal|U\.S\.C|U\.S\.T|U\.N\.T\.S|U\.S|N\.Y|S\.A|B\.V|L\.P|e\.g|i\.e|et al|v|Inc|Corp|Co|Ltd|No|Nos|Ex|Exs|Art|Arts|p|pp|n|see|See|cf|Cf|Decl|Dec|Doc|Docs|Dkt|Aff|Mar|Nov|Dec|Jan|Feb|Aug|Sept|Oct|LLP|St|Mr|Ms|Dr|Jr)'
try:
    from nupunkt import sent_tokenize as _NUPUNKT
except Exception as _e:   # e.g. an older Python: fall back to the built-in splitter
    _NUPUNKT = None; print('nupunkt unavailable, using the built-in sentence splitter:', _e)
_SENT_END = re.compile(r'(?:\b[Ii]d|\b(?:Exh?s?<DOT>|Exhibits?)\s+(?:[A-Z]{1,2},?\s+(?:and\s+|&\s+)?)*[A-Z]{1,2})\.$')
def _resplit(x):
    """nupunkt reads a closing 'Id.' or exhibit letter ('… as Exhibit A.', 'Exs. A, C, G.') as an abbreviation; in a brief they end the sentence."""
    out, start = [], 0
    for mm in re.finditer(r'(?<=\.)\s+(?=[A-Z“"(][a-z]*)', x):
        nxt = x[mm.end():mm.end() + 60]
        if _SENT_END.search(x[start:mm.start()]) or re.match(r'(?:See|Cf<DOT>|Id\.|Exh?s?<DOT>\s*[A-Z\d]|' + DOCNAMES.replace('\\.', '<DOT>') + r')', nxt):
            out.append(x[start:mm.start()]); start = mm.end()
    return out + [x[start:]]
def sentences(text):
    prot = re.sub(r'\b(' + ABBR + r')\.', lambda m: m.group(1).replace('.', '<DOT>') + '<DOT>', text)
    prot = re.sub(r'(\d)\.(\d)', r'\1<DOT>\2', prot)
    # a statute's initialism and chapter ("M.G.L.A. ch. 93, §4") do not end a sentence
    prot = re.sub(r'\b((?:[A-Z]\.\s?){2,})(?=\s*(?:(?:[cC]h?\.|[cC]hapter)\s*\d|§))', lambda m: m.group(1).replace('.', '<DOT>'), prot)
    prot = re.sub(r'\b([cC]h?)\.(?=\s*\d)', r'\1<DOT>', prot)
    prot = re.sub(r'(<DOT>[A-Z])\.(?=\s*§)', r'\1<DOT>', prot)   # "U.S.C.A. § 1836(d)" (U.S.C. already protected above)
    # a single-letter initial inside a case name ("Seaboard C. Railroad", "Charles A. Krause Milling Co. v. …") is not a sentence end
    prot = re.sub(r'(\sv<DOT>\s(?:[^;()]{0,80}?\s)?[A-Z])\.(?=\s[A-Z])', r'\1<DOT>', prot)
    prot = re.sub(r'(\s[A-Z])\.(?=\s[A-Z][^;()]{0,80}?\sv<DOT>\s)', r'\1<DOT>', prot)
    prot = re.sub(r'\.\s\.\s\.', '<DOT> <DOT> <DOT>', prot)
    if _NUPUNKT:   # legal-text sentence splitter (ALEA nupunkt, MIT), run on the protected text
        parts = []
        for chunk in prot.split('\n'):
            for x in _NUPUNKT(chunk):
                lead = re.match(r'^\s*((?:\[\[FN\d+\]\])+)', x)   # a footnote marker stays with the sentence it ends
                if lead and parts:
                    parts[-1] += lead.group(1); x = x[lead.end():]
                if x.strip(): parts += [y for y in _resplit(x) if y.strip()]
    else:
        parts = [x for chunk in prot.split('\n') for x in re.split(r'(?:(?<=[.?!])|(?<=[.?!][”"])|(?<=[.?!]\)))\s+(?=[A-Z(\[“])', chunk)]
    merged = []
    for x in parts:   # a fragment that opens with a closing quote or bracket, or "(quoting …", belongs to the sentence before it
        if merged and re.match(r'\s*(?:[”"’)\]]|\([a-z])', x): merged[-1] += ' ' + x.strip()
        else: merged.append(x)
    return [p.replace('<DOT>', '.').strip() for p in merged if p.strip()]

# ================================================================ 3. citation grammar
NUM = r'\d+(?:\([a-z0-9]+\))*(?:\s*[–-]\s*\(?\d+\)?)?'
PARA = r'¶¶?\s*' + NUM + r'(?:\s*,\s*' + NUM + r')*(?:\s*n\.\s*\d+)?'
LOC = r'(?:' + PARA + r'|pp?\.\s*\d+(?:\s*[–-]\s*\d+)?|Arts?\.\s*\d+(?:\(\d+\))*(?:\s*[–-]\s*\(\d+\))?|Rules?\s*\d+(?:\(\d+\))*(?:\s*[–-]\s*\(\d+\))?)'
TR = r'\d{1,4}:\d{1,2}(?:\s*[–-]\s*(?:\d{1,4}:)?\d{1,2})?'          # transcript page:line, e.g. 49:3–51:21
TRS = TR + r'(?:\s*[,;]\s*' + TR + r')*'                                  # "8:11-23; 9:24-10:1": one citation to one transcript
PGS = r'\*?\d+(?:\s*[–-]\s*\*?\d+)?(?:,\s*\*?\d+(?:\s*[–-]\s*\*?\d+)?(?!\s*[A-Z\d]))*'   # "at 69–71, 73"
# Bates numbers: a prefix of capitals (or a word ending in "_") glued to the number, e.g. DEF000430–432, ABC123456, Hunter_000079
BATES = re.compile(r'(?<![\w])((?:[A-Z][A-Za-z]*_)|(?:[A-Z]{2,}))\s?(\d{3,12})(?:\s*[–-]\s*(\d{1,12}))?(?![\w])')
SECP = r'(?:§§?|Sections?|Secs?\.)\s*\d+(?:\.\d+)*[a-z]?(?:\s*[–-]\s*\d+(?:\.\d+)*[a-z]?)?(?:\s*(?:,|and|&)\s*(?:§\s*)?\d+(?:\.\d+)*[a-z]?(?![\d:]))*'   # "at §1.2", "§§3.1, 6.1", "Section 4"
PLOC = r'(?:' + TRS + r'|' + LOC + r'|' + SECP + r'|(?<=at )' + PGS + r')'   # "Ex. A at 5": a bare number after "at" is a page
DOCNAMES = '(?<![\\w])(?:' + ('|'.join(re.escape(k) for k in sorted(DOCS, key=len, reverse=True)) or 'NO_DOCS_CONFIGURED') + ')(?![\\w])'
RECORD_TERMS = CFG.get('record_terms', {})     # defined term in the brief -> exhibit letter (e.g. "ICSID Convention": "B", "Vavra Dep.": "A")
RTNAMES = '(?<![\\w])(?:' + ('|'.join(re.escape(k) for k in sorted(RECORD_TERMS, key=len, reverse=True)) or 'NO_TERMS_CONFIGURED') + ')'
TOKEN = re.compile(
    r'(?P<rt>' + RTNAMES + r'\s*,?\s*(?:at\s*)?(?P<rtloc>' + TRS + r'))'      # "Vavra Dep. 124:19-21": a defined deposition name with page:line
    r'|(?P<docex>(?:' + DOCNAMES + r')\.?,?\s*(?:' + PARA + r'\s*(?:,|and)\s*)?Exh?s?\.\s*(?P<dex>[A-Z]{1,2}|\d{1,3})(?![\w])(?:\s*,?\s*(?:at\s*)?(?P<dexloc>' + PLOC + r'))?)'
    r'|(?P<doc>(?:' + DOCNAMES + r')\.?(?:,?\s*(?:at\s*)?(?P<docloc>' + PLOC + r'))?)'
    r'|(?P<ex>(?<![A-Za-z])(?:Exh?s?\.|(?:Group\s+)?Exhibits?)\s*(?P<exl>[A-Z]{1,2}|\d{1,3})(?P<exu>_)?(?![\w])(?:\s*,?\s*(?:at\s*)?(?P<exloc>' + PLOC + r'))?)'
    r'|(?P<blank>(?<![A-Za-z])Exh?\.\s*_{2,})'
    r'|(?P<id>\b[Ii]d\.(?:\s*,?\s*(?:at\s*)?(?P<idloc>' + TRS + r'|' + LOC + r'|(?<=at )' + PGS + r'))?)')
DEPEX = r'\s*,\s*(?:(?:[A-Z][\w’\'-]*\s+){0,3}(?:Dep(?:o)?\.?|Deposition)\s+)?(?=Exh?\.\s*\d{1,3}\b)'   # ", Ex. 6" / ", Vavra Dep Ex. 11" / ", Smith Dep. Ex. 6" after an exhibit letter
HISTORY = re.compile(r"(?:aff[’']d|rev[’']d|vacated|modified|cert\. denied|cert\. granted|reh[’']g denied|appeal dismissed)(?:\s+in part)?(?:\s+(?:on other grounds|mem\.|per curiam|sub nom\.[^,]{0,60}))?,?\s*$")
ATTACH = re.compile(r'\b(?i:attached(?:,?\s*collectively,?)? (?:hereto |to (?:this|the|my) (?:declaration|affidavit|motion|petition) )?(?:as|at) (?:exhibit ))([A-Z]{1,2}|\d{1,3})(?:(?i: and exhibit )([A-Z]{1,2}|\d{1,3}))?(?![\w])')
# an exhibit to an exhibit: "Exhibit A to Exhibit BB", "Exhibit A to the Declaration of …, which is attached as Exhibit BB", "… Declaration at Exhibit BB"
NESTED = re.compile(r'\s+to\s+(?:(?:the|his|her|their)\s+)?(?:(?:Exh?\.|Exhibit)\s*(?P<o1>[A-Z]{1,2}|\d{1,3})(?![\w])|'
                    r'[^;()]{0,110}?(?:,\s*which\s+is\s+(?:itself\s+)?attached(?:\s+hereto)?\s+as|\s+at)\s+(?:Exh?\.|Exhibit)\s*(?P<o2>[A-Z]{1,2}|\d{1,3})(?![\w]))')
NESTED_NOUN = re.compile(r"\s+to\s+(?:(?:the|his|her|their)\s+)?(?:[A-Z][\w.’'-]*\s+){0,5}(?:(?:Declaration|Affidavit|Exhibit|Report)\b|(?:Decl|Aff|Ex)\.)")
def nested_outer(sc, pos):
    """An exhibit letter at sc[pos] that is an exhibit to another exhibit. -> None (not nested: an exhibit to the declaration that
    introduces the record, e.g. "attached as Exhibit A to the Friedman Declaration", is the record's Ex. A); (outer letter, end of the
    outer reference) for "Exhibit A to Exhibit BB" / "… to the Declaration of X, which is attached as Exhibit BB" / "… Declaration at
    Exhibit BB"; (None, None) when it sits in a parenthetical that follows another exhibit cite ("Ex. BB (…, Exhibit A to the Bozeman
    Declaration)"), whose row already links the outer exhibit."""
    mm = NESTED.match(sc, pos)
    if mm: return (mm.group('o1') or mm.group('o2')), mm.end()
    if NESTED_NOUN.match(sc, pos):
        op = sc.rfind('(', 0, pos)
        if op >= 0 and ')' not in sc[op:pos] and re.search(r'(?:Exh?s?\.|Exhibits?)\s*(?:[A-Z]{1,2}|\d{1,3})\s*$', sc[:op]):
            return None, None
    return None
USC = re.compile(r'(\d+)\s+U\.S\.(?:C\.(?:A\.)?|\s+Code)\s+§+\s*(\d+[a-z]?)((?:\([a-z0-9]+\))*)(\s+et seq\.)?')
TREATY = re.compile(r'\d+\s+U\.S\.T\.\s+\d+(?:,\s*\d+\s+U\.N\.T\.S\.\s+\d+)?|\b\d+\s+U\.N\.T\.S\.\s+\d+')
DOCKET = re.compile(r'(?P<name>[A-Z][\w\.\'’ ,&-]*? v\. [\w\.\'’ ,&-]+?), No\. (?P<no>\d:\d{2}-[a-z]{2}-\d+) \((?P<court>[A-Z][\w\.]+(?: [A-Z][\w\.]*)*)\s+(?P<date>[A-Z][a-z]+\.? \d{1,2}, \d{4})\)(?:, ECF No\. (?P<ecf>\d+))?')
# reporter abbreviations and their variants come from Free Law Project's reporters-db (BSD-2-Clause; data/LICENSE-reporters-db)
_RDB = json.load(open(os.path.join(SCRIPT_DIR, 'data', 'reporters.json'), encoding='utf-8'))['reporters']   # variant -> [canonical editions]
def _rep_rx(k):
    return r'\s?'.join(re.escape(part).replace("'", "['’]").replace('’', "['’]") for part in k.split(' '))
REPS = r'(?:' + '|'.join(_rep_rx(k) for k in sorted(_RDB, key=len, reverse=True)) + r')'
def _rnorm(r): return re.sub(r'\s+', '', r).replace('’', "'")
_CANON = {}
for _k, _v in _RDB.items(): _CANON.setdefault(_rnorm(_k), set()).update(_rnorm(x) for x in _v)
def rep_canon(r):
    """all canonical forms of a reporter abbreviation as written ('Fed. Appx.' -> {"F.App'x"})"""
    n = _rnorm(r)
    return _CANON.get(n) or {n}
CASE_FULL = re.compile(r'\b(?P<vol>\d+)\s+(?P<rep>' + REPS + r')\s+(?P<page>\d+)(?![\w])(?:,\s*(?P<pin>\d+(?:\s*[–-]\s*\d+)?))?(?:\s*\((?P<paren>[^()]*?\d{4})\))?')
CASE_SHORT = re.compile(r'(?P<vol>\d+)\s+(?P<rep>' + REPS + r')\s+at\s+(?P<pin>\d+(?:\s*[–-]\s*\d+)?)')
DKT = CFG.get('dockets', {})   # {"2:25-cv-02222": {"name":..., "url":..., "entries": {"24": "desc"}}, "_this": {...}}
NYSCEF = CFG.get('nyscef', {})  # {"index": "659206/2025", "files": {"2": "file.pdf"}}
EXT = re.compile(
    r'(?P<dk>(?:Docket|ECF|Dkt\.|Doc\.) Nos?\.\s*(?P<dkn>\d+(?:\s*(?:,|and|&)\s*\d+)*)\s*\((?:[A-Z][\w\.]*(?:\s[A-Z][\w\.]*)*\s+Case\s*)?(?P<dkc>\d:\d{2}-[a-z]{2}-\d+)[\w-]*(?:\s+[A-Za-z][\w-]*)?\))'
    r'|(?P<gen>(?:See generally,?\s*)?[A-Z]\.D\.\s*[A-Z][a-z]+\.\s*Case\s*(?P<genc>\d:\d{2}-[a-z]{2}-\d+)(?:-\s?[A-Za-z]+)*)'
    r'|(?P<ny>NYSCEF Doc\. Nos?\.\s*(?P<nyn>\d+)(?:\s*\([^()]*Index No\.\s*(?P<nyi>[\d/]+)\))?)'
    r'|(?P<own>(?<!NYSCEF )(?:(?:Docket|ECF|Dkt\.?|Doc\.)\s+(?:Nos?\.\s*)?|ECF\s*)(?P<ownn>\d+(?:\s*(?:[–-]|,|and|&)\s*\d+)*)(?![\d\s,&and–-]*\()'
    r'(?:,?\s*(?:at\s+(?P<ownpg>\d+)(?:\s*[–-]\s*\d+)?|¶¶?\s*(?P<ownpara>\d+)(?:\s*[–-]\s*\d+)?)(?![\d:]))?)'
    r'|(?P<cplr>CPLR\s+(?P<cplrn>R?\d{3,4}))'
    r'|(?P<rule>(?i:F\s?ed)\.\s*(?i:R)\.\s*(?P<rset>(?i:Civ|App|Evid|Crim))\.\s*(?i:P)?\.?\s*(?P<rno>\d+)(?P<rsub>(?:\([a-zA-Z0-9]+\))*))'
    r'|(?P<rulew>Federal\s+Rules?\s+of\s+(?P<wset>Civil|Appellate|Criminal)\s+Procedure\s+(?P<wno>\d+)(?P<wsub>(?:\([a-zA-Z0-9]+\))*)'
    r'|Federal\s+Rules?\s+of\s+(?P<wset2>Evidence)\s+(?P<wno2>\d+)(?P<wsub2>(?:\([a-zA-Z0-9]+\))*)'
    r'|Rule\s+(?P<wno3>\d+)(?P<wsub3>(?:\([a-zA-Z0-9]+\))*)\s+of\s+the\s+Federal\s+Rules\s+of\s+(?P<wset3>Civil\s+Procedure|Appellate\s+Procedure|Criminal\s+Procedure|Evidence))'
    r'|(?P<usc>(?P<ut>\d+)\s+U\.S\.(?:C\.(?:A\.)?|\s+Code)\s+§+\s*(?P<us>\d+[a-z]?)(?P<ussub>(?:\([a-z0-9]+\))*)(?P<etseq>\s+et seq\.)?)')
EXT_LINKS = {}
SIG_RE = re.compile(r'^(?:See generally,?|See also|see also|See,? e\.g\.,|see,? e\.g\.,|See|see|Cf\.|cf\.|But see|but see|Accord|accord|Compare|compare)\s+')
def strip_sig(t): return SIG_RE.sub('', t or '')   # signals belong in the passage, never in a link label
def site_of(href):
    host = urllib.parse.urlparse(href or '').netloc
    return {'www.law.cornell.edu': 'Cornell LII', 'www.courtlistener.com': 'CourtListener', 'storage.courtlistener.com': 'CourtListener (RECAP)', 'www.nysenate.gov': 'NY Senate',
            'treaties.un.org': 'UN Treaty Series'}.get(host, host)
CASE_RE = r'\d:\d{2}-[a-z]{2}-\d+'
def stamp_index():
    """Scan every PDF in the case folder for court filing stamps. -> {('ECF', case, doc): (file, page), ('NYSCEF', n): (file, page)}.
    Where a document appears in several files, prefer the file in which it starts on p. 1, then the first file by name."""
    if 'stamps' in _cache: return _cache['stamps']
    found = {}
    for root, _, fs in os.walk('.'):
        for f in sorted(fs):
            if not f.lower().endswith('.pdf'): continue
            path = os.path.normpath(os.path.join(root, f))
            raw = subprocess.run(['pdftotext', '-raw', path, '-'], capture_output=True, text=True).stdout.split('\f')
            lay = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout.split('\f')
            for pno, (tr, tl) in enumerate(zip(raw, lay), 1):
                for mm in re.finditer(r'(' + CASE_RE + r')[\w-]*\s*Document\s*(?:#\s*:?\s*)?(\d+(?:-\d+)?)\b', tr):
                    found.setdefault(('ECF', mm.group(1), mm.group(2)), []).append((path, pno))
                mm = re.search(r'NYSCEF DOC\. NO\.\s*(?:Case\s*)?\n?\s*(?:[A-Z ]+?\s)?(\d{1,4})\s', tl)
                if mm: found.setdefault(('NYSCEF', mm.group(1)), []).append((path, pno))
    out, allf = {}, {}
    for k, occ in found.items():
        firsts = {}
        for f, pg in occ: firsts.setdefault(f, pg)
        allf[k] = firsts
        out[k] = min(firsts.items(), key=lambda x: (x[1] != 1, x[0]))
    _cache['stamps'] = out; _cache['stamps_all'] = allf; return out
def this_case():
    mm = re.search(r'(' + CASE_RE + r')', subprocess.run(['pdftotext', '-raw', '-l', '1', os.path.basename(DOC) if os.path.exists(os.path.basename(DOC)) else DOC, '-'], capture_output=True, text=True).stdout)
    return mm.group(1) if mm else None
def ext_row(m):
    """-> (type, label, links) for a docket entry, NYSCEF document, federal rule or U.S.C. section."""
    if m.group('dk') or m.group('own'):
        spec = m.group('dkn') or m.group('ownn')
        nums = []
        for part in re.split(r'\s*(?:,|and|&)\s*', spec):
            rg = re.fullmatch(r'(\d+)\s*[–-]\s*(\d+)', part)
            if re.fullmatch(r'\d+-\d+', part) and int(rg.group(2)) <= int(rg.group(1)):   # "ECF No. 82-1": an attachment number, not a range
                nums.append(part); continue
            nums +=[str(x) for x in range(int(rg.group(1)), int(rg.group(2)) + 1)] if rg and int(rg.group(2)) - int(rg.group(1)) < 10 else re.findall(r'\d+', part)
        key = m.group('dkc') or '_this'
        d = DKT.get(key)
        links = []
        case = this_case() if key == '_this' else key
        tag = f' ({key})' if key != '_this' else ''
        for n in nums:
            local = (d or {}).get('files', {}).get(n)
            desc = (d or {}).get('entries', {}).get(n)
            st_hit = stamp_index().get(('ECF', case, n)) if case else None
            pin_pg = m.group('own') and len(nums) == 1 and m.group('ownpg')
            pin_para = m.group('own') and len(nums) == 1 and m.group('ownpara')
            if local or st_hit:
                path, start = (realfile(_spec(local))[0], realfile(_spec(local))[1]) if local else st_hit
                where = (f'Docket entry {n}, saved in the case folder' + (f': {desc}' if desc else '')) if local else \
                        (f'Docket entry {n} is in the case folder: {path}, PDF p. {start} (read from the court\'s filing stamp)' + (f'. {desc}' if desc else ''))
                pg, st, how, lab = start, 'exact', where, f'Dkt. {n}{tag}'
                if pin_pg:
                    P = int(pin_pg); lab += f' at {P}'; tgt = start + P - 1
                    if tgt > npages(path):
                        pg, st, how = None, 'unresolved', where + f'. p. {P} is past the end of the file'
                    elif re.search(r'Page\s*' + str(P) + r'\s+of\s+\d+', page_text(path, tgt)):
                        pg, how = tgt, where + f'. ECF p. {P} is PDF p. {tgt} (its stamp says Page {P})'
                    else:
                        pg, st, how = tgt, 'inferred', where + f'. p. {P} counted from the start of the entry: PDF p. {tgt} (no ECF page stamp to confirm it)'
                elif pin_para:
                    N = int(pin_para); lab += f' ¶ {N}'
                    q = text_para_map(path).get(N)
                    if q and q >= start: pg, how = q, where + f'. ¶ {N} is on PDF p. {q}'
                    else: st, how = 'inferred', where + f'. ¶ {N} not found in the text; opens the first page of the entry'
                links.append(dict(label=lab, page=pg, status=st, how=how,
                                  href=(urllib.parse.quote(path) + f'#page={pg}') if pg else urllib.parse.quote(path) + f'#page={start}'))
            elif d and d.get('url'):
                links.append(dict(label=f'Dkt. {n}{tag}', page=None, status='inferred',
                                  how=(f'CourtListener docket, entry {n}: {desc}. Opens the docket listing, not the document itself' if desc else f'CourtListener docket filtered to entry {n} (entry not confirmed); opens the docket listing, not the document itself'),
                                  href=d['url'] + ('&' if '?' in d['url'] else '?') + f'entry_gte={n}&entry_lte={n}'))
            else:
                links.append(dict(label=f'Dkt. {n}{tag}', page=None, status='inferred', how='docket not in the map; CourtListener search',
                                  href='https://www.courtlistener.com/?type=r&q=' + urllib.parse.quote(f'"{key}"')))
        lbl = ('Docket No. ' if len(nums) == 1 else 'Docket Nos. ') + ', '.join(nums) + (f' ({key})' if key != '_this' else '')
        return 'record', lbl, links
    if m.group('gen'):
        d = DKT.get(m.group('genc'))
        lbl = strip_sig(m.group('gen').strip())
        if d and d.get('url'):
            return 'record', lbl, [dict(label=f'Docket ({m.group("genc")})', page=None, status='inferred', how=f'CourtListener docket for {d.get("name", m.group("genc"))} (whole docket: "see generally"); opens the docket listing, not a document', href=d['url'])]
        return 'record', lbl, [dict(label='Docket search', page=None, status='inferred', how='docket not in the map; CourtListener search', href='https://www.courtlistener.com/?type=r&q=' + urllib.parse.quote(f'"{m.group("genc")}"'))]
    if m.group('ny'):
        n = m.group('nyn'); f = NYSCEF.get('files', {}).get(n)
        lbl = f'NYSCEF Doc. No. {n}'
        hit = stamp_index().get(('NYSCEF', n))
        if f:   # the confirmed map names a file: use the NYSCEF stamp inside that file if there is one
            ff = os.path.normpath(realfile(_spec(f))[0])
            inner = _cache['stamps_all'].get(('NYSCEF', n), {}).get(ff)
            hit = (ff, inner) if inner else None
        if hit:
            return 'record', lbl, [dict(label=lbl, page=hit[1], status='exact', how=f'NYSCEF Doc. No. {n} begins at {hit[0]}, PDF p. {hit[1]} (read from the NYSCEF stamp)', href=urllib.parse.quote(hit[0]) + f'#page={hit[1]}')]
        if f:
            return 'record', lbl, [dict(label=lbl, page=1, status='inferred', how=NYSCEF.get('how', {}).get(n, 'state-court document saved in the case folder; no NYSCEF stamp found, so it opens at the first page'), href=href_of(_spec(f), 1))]
        return 'record', lbl, [dict(label='NYSCEF', page=None, status='nolink', how=f'NYSCEF document {n} (Index No. {NYSCEF.get("index", m.group("nyi") or "?")}) is not in the case folder; NYSCEF documents cannot be linked directly', href=None)]
    if m.group('cplr'):
        n = m.group('cplrn'); lbl = f'CPLR {n}'
        return 'statute', lbl, [dict(label=lbl, page=None, status='exact', how='New York Senate site, Civil Practice Law and Rules', href=f'https://www.nysenate.gov/legislation/laws/CVP/{n}')]
    if m.group('rule') or m.group('rulew'):
        sets = {'Civ': 'frcp', 'App': 'frap', 'Evid': 'fre', 'Crim': 'frcrmp', 'Civil': 'frcp', 'Appellate': 'frap', 'Evidence': 'fre', 'Criminal': 'frcrmp'}
        if m.group('rule'):
            rset, rno, rsub = m.group('rset').capitalize(), m.group('rno'), m.group('rsub')
        else:
            rset = (m.group('wset') or m.group('wset2') or m.group('wset3')).split()[0]
            rno, rsub = m.group('wno') or m.group('wno2') or m.group('wno3'), m.group('wsub') or m.group('wsub2') or m.group('wsub3') or ''
        lbl = {'frcp': 'Fed. R. Civ. P.', 'frap': 'Fed. R. App. P.', 'fre': 'Fed. R. Evid.', 'frcrmp': 'Fed. R. Crim. P.'}[sets[rset]] + f' {rno}{rsub}'
        return 'statute', lbl, [dict(label=lbl, page=None, status='exact', how='LII page for the rule' + (f'; subdivision {rsub} is on that page' if rsub else ''),
                                     href=f'https://www.law.cornell.edu/rules/{sets[rset]}/rule_{rno}')]
    lbl = f'{m.group("ut")} U.S.C. § {m.group("us")}{m.group("ussub")}' + (' et seq.' if m.group('etseq') else '')
    return 'statute', lbl, [dict(label=lbl, page=None, status='exact', how='LII page for the section' + (f'; subsection {m.group("ussub")} is on that page' if m.group('ussub') else ''),
                                 href=f'https://www.law.cornell.edu/uscode/text/{m.group("ut")}/{m.group("us")}')]

URLRE = re.compile(r'https?://[^\s)]+')
_DB = r'\d{4}\s+(?:WL|LX|(?:[A-Z][\w\.’\']*\s+)*LEXIS)\s+\d+(?:,\s*at\s*\*\d+(?:\s*[–-]\s*\*?\d+)?)?'
_STATES = (r'(?:Ala|Alaska|Ariz|Ark|Cal|Colo|Conn|Del|D\.C|Fla|Ga|Haw|Idaho|Ill|Ind|Iowa|Kan|Ky|La|Me|Md|Mass|Mich|Minn|Miss|Mo|Mont|Neb|Nev|'
           r'N\.H|N\.J|N\.M|N\.Y|N\.C|N\.D|Ohio|Okla|Or|Pa|R\.I|S\.C|S\.D|Tenn|Tex|Utah|Vt|Va|Wash|W\.\s?Va|Wis|Wyo)\.?')
SEC = r'§§?\s*[\w.:–-]*\d[\w.:–-]*(?:\([a-zA-Z0-9]+\))*(?:\s+et\s+seq\.)?'
STATESTAT = re.compile(   # state statutes: listed for checking, not linked (v1.0)
    r'\b\d+\s+(?:ILCS|Ill\.\s*Comp\.\s*Stat\.(?:\s*Ann\.)?)\s*\d+/[\d.]+(?:[–-][\d.]+)?(?:\([a-zA-Z0-9]+\))*(?:\s+et\s+seq\.)?'
    r'|(?<![\w.])(?:M\.\s?G\.\s?L\.(?:\s?A\.)?|Mass\.\s*Gen\.\s*L(?:aws|\.)(?:\s+Ann\.)?|G\.\s?L\.)\s*,?\s*(?:[cC]h?\.|[cC]hapter)\s*\d+[A-Z]?(?:,?\s*' + SEC + r')?'
    r'|(?<![\w.])' + _STATES + r'\s+(?:(?:[A-Z][A-Za-z.]*|&)\s+){0,7}?(?:Code|Laws?|Stat\.|Stats\.|Statutes|Ann\.)(?:\s+Ann\.)?(?:\s+tit\.\s*\d+,?)?\s*' + SEC)
LOCALRULE = re.compile(r'(?<![\w.])(?:(?:Local\s+(?:Civil\s+)?Rule|L\.\s?(?:Civ\.\s?)?R\.|Loc\.\s*R\.)\s*\d+(?:\.\d+)*|LR\s+\d{1,3}\.\d+)(?:\([a-zA-Z0-9]+\))*')   # listed, not linked
NOLINK = re.compile(r'(?P<db>' + _DB + r'(?:,\s*' + _DB + r')?)|(?P<supra>\bsupra\b(?:\s+(?:note|n\.)\s+\d+)?(?:,?\s*at\s*\*?\d+(?:\s*[–-]\s*\*?\d+)?)?)')
AUTH = CFG.get('authorities', [])          # [{"cite": "735 F.3d 72", "short": "Blue Ridge", "url": "..."}]
AUTH_BY = {}
for a in AUTH:
    m = re.match(r'(\d+)\s+(.+?)\s+(\d+)$', a['cite'])
    if m:
        for c in rep_canon(m.group(2)): AUTH_BY[(m.group(1), c, m.group(3))] = a
AUTH_USED = set()
def auth_for(vol, rep, page):
    for c in rep_canon(rep):
        a = AUTH_BY.get((vol, c, page))
        if a: AUTH_USED.add(id(a)); return a
    return None
def find_auth(vol, rep, page=None, pin=None):
    if page: return auth_for(vol, rep, page), page
    cs = rep_canon(rep)
    cands = [(k, a) for k, a in AUTH_BY.items() if k[0] == vol and k[1] in cs and pin and int(k[2]) <= int(re.match(r'\d+', pin).group(0))]
    if not cands: return None, None
    k, a = max(cands, key=lambda x: int(x[0][2]))
    AUTH_USED.add(id(a))
    return a, k[2]
UNREP = {}   # Westlaw/Lexis-only decisions found on CourtListener (RECAP) when the map was drafted
for _u in CFG.get('unreported', []): UNREP[re.sub(r'\s+', ' ', _u['cite']).strip()] = _u
def unrep_key(db):
    mm = re.search(r'(\d{4})\s+((?:[A-Z][\w.’\']*\s+)*LEXIS|WL|LX)\s+(\d+)', db)
    return ' '.join([mm.group(1), re.sub(r'\s+', ' ', mm.group(2)), mm.group(3)]) if mm else None
def unrep_links(u, pins):
    """Links for a Westlaw/Lexis cite whose decision is on CourtListener. Always amber: a Westlaw star page has no equivalent
    in the court's PDF. Where the map records the PDF page holding the quoted passage, the link opens that page."""
    out = []
    for pin in (pins or [None]):
        star = re.match(r'\*?(\d+)', pin).group(1) if pin else None
        label = (u.get('short') + ', ' if u.get('short') else '') + u['cite'] + (f', at {pin}' if pin else '')
        if u.get('recap'):
            pg = (u.get('pages') or {}).get(f'*{star}') if star else None
            if pg:
                how = (f'Opens the decision on CourtListener ({u.get("entry", "RECAP copy")}) at PDF p. {pg["page"]}: page located by the quoted text '
                       f'({pg.get("how", "quote found on that page")}); Westlaw *{star} has no PDF equivalent: confirm the page')
                out.append(dict(label=label, page=None, status='inferred', how=how, href=u['recap'] + f'#page={pg["page"]}'))
            else:
                how = (f'Opens the decision on CourtListener ({u.get("entry", "RECAP copy")}) at the first page' +
                       (f'; Westlaw *{star} has no PDF equivalent: find the passage yourself' if star else ''))
                out.append(dict(label=label, page=None, status='inferred', how=how, href=u['recap']))
        elif u.get('docket_url'):
            out.append(dict(label=label, page=None, status='inferred', href=u['docket_url'],
                            how='The decision is not on CourtListener; the link opens the case docket there' + (f' ({u["note"]})' if u.get('note') else '')))
    return out

NAME_OK = {'of', 'de', 'del', 'la', 'and', '&', 'the', 'v.', 'et', 'al.', 'ex', 'rel.', 'for', 'in', 'on'}
def name_before(txt):
    """Case name immediately before a citation ('..., 735 F.3d 72'): walk back over name-like tokens."""
    t = txt.rstrip()
    if not t.endswith(','): return ''
    toks = t[:-1].split(' ')
    out = []
    for tok in reversed(toks):
        if not tok or ';' in tok or re.search(r'\d\)', tok): break   # the end of the previous citation
        if tok[0].isupper() or tok[0].isdigit() or tok in NAME_OK or tok[0] in '“"(' and tok[1:2].isupper():
            out.append(tok)
        else: break
    while out and out[-1] in ('and', '&', 'of', 'the', 'for', 'in', 'on', 'In', 'See', 'But', 'Cf.', 'Accord', 'Compare', 'The', 'This', 'That', 'Under'):
        out.pop()
    name = ' '.join(reversed(out)).lstrip('(')
    return name if name and len(name) < 160 else ''
CAPS = r'[A-Z][\w-]*(?: [A-Z][\w-]*)*'
NOTCITE = re.compile(r'(?:Article (?P<art>\d+(?:\(\d+\))?) of the (?P<artdoc>' + CAPS + r')|paragraph (?P<para>\d+) of the (?P<paradoc>' + CAPS + r')|ICSID Case No\. [A-Z()]+/\d+/\d+)')
FNREF = re.compile(r'(?:[Ss]ee (?:also )?)?(?:footnote|note|n\.) (\d+),? (?:above|below|supra|infra)')
TREATIES = CFG.get('treaties', [])             # [{"cite": "575 U.N.T.S. 159", "record": "B", "url": ..., "source": ...}]

def split_loc(loc):
    if not loc: return []
    loc = loc.strip()
    if re.fullmatch(TRS, loc): return ['tr. ' + x.strip() for x in re.findall(TR, loc)]
    if re.fullmatch(SECP, loc): return ['§ ' + x for x in re.findall(r'(?<![\d.])(\d+(?:\.\d+)*[a-z]?)(?:\s*[–-]\s*\d+(?:\.\d+)*[a-z]?)?', re.sub(r'^(?:§§?|Sections?|Secs?\.)\s*', '', loc))]
    if re.fullmatch(r'\*?\d+(?:\s*[–-]\s*\*?\d+)?', loc): return ['p. ' + loc]
    if re.fullmatch(PGS, loc): return ['p. ' + x.strip() for x in loc.split(',')]
    if loc.startswith('¶'):
        m = re.match(r'¶¶?\s*(.*?)(\s*n\.\s*\d+)?$', loc)
        items = ['¶ ' + x.strip() for x in m.group(1).split(',') if x.strip()]
        if m.group(2): items[-1] += ' ' + m.group(2).strip()
        return items
    return [loc]

# ================================================================ 4. locators -> PDF page
_cache = {}
def path_of(src): return EXMAP[src[1]] if src[0] == 'EX' else (DOCS[src[1]] if src[0] == 'DOC' else '')
def label_of(src):
    if src[0] in ('CASE', 'UNREP'): return src[2]
    if src[0] in ('NOLINK', 'EXT'): return src[1]
    if src[0] == 'EX': return f'Ex. {src[1]}'
    return src[1] + ('.' if re.search(r'\b(?:Decl|Dec|Aff|Mem|Br|Opp|Compl|Pet|Tr|Stmt)$', src[1]) else '')

def npages(path):
    if ('np', path) not in _cache:
        f, lo, hi = realfile(path)
        with pdfplumber.open(f) as pdf: _cache[('np', path)] = (hi or len(pdf.pages)) - lo + 1
    return _cache[('np', path)]

def page_text(path, pno):
    k = ('pt', path, pno)
    if k not in _cache:
        f, a = realfile(path)[0], abs_page(path, pno)
        _cache[k] = subprocess.run(['pdftotext', '-layout', '-f', str(a), '-l', str(a), f, '-'], capture_output=True, text=True).stdout
    return _cache[k]

def image_para_map(path):
    """isds-research method: margin ¶ numbers drawn as images; one per paragraph start."""
    k = ('ipm', path)
    if k in _cache: return _cache[k]
    m, n = {}, 0
    f, lo, hi = realfile(path)
    with pdfplumber.open(f) as pdf:
        for pno, p in enumerate(pdf.pages[lo - 1:hi], 1):
            for _ in [im for im in p.images if im['x0'] < p.width * .25 and (im['x1'] - im['x0']) < 60]:
                n += 1; m[n] = pno
    _cache[k] = m; return m

def text_para_map(path):
    """'N. ' markers in the text layer. Lists and TOC entries look the same, so keep the longest
    chain of markers that rises in small steps (1..8)."""
    k = ('tpm', path)
    if k in _cache: return _cache[k]
    cands = [(int(mm.group(1)), pno) for pno in range(1, npages(path) + 1)
             for mm in re.finditer(r'(?m)^\s{0,40}(\d{1,4})\.\s+[A-Z“"(]', page_text(path, pno))]
    best, prev = [1] * len(cands), [-1] * len(cands)
    for i in range(len(cands)):
        for j in range(max(0, i - 60), i):
            d = cands[i][0] - cands[j][0]
            if 1 <= d <= 8 and best[j] + 1 > best[i]: best[i], prev[i] = best[j] + 1, j
    m = {}
    if cands:
        i = max(range(len(cands)), key=lambda x: best[x])
        while i != -1: m.setdefault(cands[i][0], cands[i][1]); i = prev[i]
    _cache[k] = m; return m

def printed_page_map(path):
    """-> ({printed page: PDF page}, offset or None). Page numbers printed in the footer or header, kept only where they
    agree with the document's usual offset (so stray numbers are ignored). ECF 'Page x of y' stamps are not the document's own numbering."""
    k = ('pp', path)
    if k in _cache: return _cache[k]
    found = {}
    for pno in range(1, npages(path) + 1):
        lines = [l.strip() for l in page_text(path, pno).splitlines() if l.strip() and not ECF_HDR.search(l) and not is_ecf_count(path, l)]
        for l in lines[-4:][::-1] + lines[:3]:
            mm = re.fullmatch(r'(?:[Pp]age\s+|p\.\s*)?[-–—]?\s*(\d{1,4})(?:\s+of\s+\d{1,4})?\s*[-–—]?', l)
            if mm: found[pno] = int(mm.group(1)); break
    offs = collections.Counter(p - n for p, n in found.items())
    off = offs.most_common(1)[0][0] if offs and (offs.most_common(1)[0][1] >= 2 or npages(path) == 1) else None
    m = {n: p for p, n in found.items() if off is not None and p - n == off}
    _cache[k] = (m, off); return _cache[k]

# a court filing header ("Case 1:19-cv-00683 Document 1 Filed 03/11/19 Page 2 of 30 PageID #: 12"); a document's own
# "Page 2 of 5" footer is its printed numbering, not an ECF stamp
ECF_HDR = re.compile(r'(?:\bCase\b|\bDocument\b|\bDoc\.|\bFiled\b|Page\s*ID).*Page\s*\d+\s+of\s+\d+|Page\s*\d+\s+of\s+\d+.*(?:Page\s*ID|\bFiled\b)')
def is_ecf_count(path, l):
    """A stray "Page 3 of 20" line split off the court's header: the file is ECF-stamped and 20 is its page count."""
    mm = re.search(r'Page\s*\d+\s+of\s+(\d+)', l)
    return bool(mm) and int(mm.group(1)) == npages(path) and ecf_stamped(path)
def ecf_stamped(path):
    return bool(re.search(r'(?:\bCase\b|\bDocument\b|\bFiled\b).*Page\s*1\s+of\s+\d+', page_text(path, 1)))

CONDENSED = {}   # path -> {transcript page: [all transcript pages on its sheet]}
def transcript_page_map(path):
    """-> {transcript page: PDF page}. A transcript prints its page number alone at the top or bottom of each page, or at the
    end of a running header ("Davis - Cross/Fink 122"). Numbers are kept only while they increase. Pages whose number cannot be
    read are left out (not inferred)."""
    k = ('tpg', path)
    if k in _cache: return _cache[k]
    m, last = {}, 0
    for pno in range(1, npages(path) + 1):
        lines = [l.strip() for l in page_text(path, pno).splitlines() if l.strip()]
        lines = [l for l in lines if not re.search(r'Page\s*\d+\s+of\s+\d+', l)]
        # a condensed transcript prints two or four transcript pages on one sheet, each under its own "Page N" label
        # (some text layers double every character: "PPaaggee 99"); every label on the sheet maps to this PDF page
        labels = []
        for l in lines:
            if re.fullmatch(r'(?:\d{1,2}\s{2,})?(?:P{1,2}a{1,2}g{1,2}e{1,2}\s+\d{1,8}\s*)+', l):   # (a line number may sit beside a label)
                for mm in re.finditer(r'(P{1,2})a{1,2}g{1,2}e{1,2}\s+(\d{1,8})', l):
                    d = mm.group(2)
                    if len(mm.group(1)) == 2 and len(d) % 2 == 0 and d[::2] == d[1::2]: d = d[::2]
                    if len(d) <= 4: labels.append(int(d))
        if len(labels) >= 2:
            for n in labels:
                if n not in m: m[n] = pno; CONDENSED.setdefault(path, {})[n] = sorted(labels)
            last = max(last, max(labels)); continue
        n = None
        for l in lines[:4] + lines[-3:][::-1]:
            mm = re.fullmatch(r'(?:#:\s*\d+\s+)?(?:Page\s+)?(\d{1,4})', l) or re.fullmatch(r'[A-Z][\w .,\'’/()-]{0,60}?\s{3,}(\d{1,4})', l)
            if mm: n = int(mm.group(1)); break
        if n and n > last: m.setdefault(n, pno); last = n
    _cache[k] = m; return m

def bates_index(path, prefix):
    """-> {number: PDF page} for Bates stamps with this prefix in the text layer (exact reading; no OCR-error guessing)."""
    k = ('bates', path, prefix)
    if k in _cache: return _cache[k]
    m = {}
    for pno in range(1, npages(path) + 1):
        for mm in re.finditer(r'(?<![\w])' + re.escape(prefix.rstrip('_')) + r'_?\s?(\d{2,12})(?![\d])', page_text(path, pno)):
            m.setdefault(int(mm.group(1)), pno)
    _cache[k] = m; return m

def ocr_margin_has(path, pno, number):
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        a = abs_page(path, pno)
        subprocess.run(['pdftoppm', '-f', str(a), '-l', str(a), '-r', '200', '-gray', '-png', realfile(path)[0], f'{d}/p'], check=True)
        f = [x for x in os.listdir(d) if x.endswith('.png')][0]
        im = Image.open(f'{d}/{f}'); w, h = im.size
        im.crop((int(w * .08), 0, int(w * .25), h)).save(f'{d}/m.png')
        try:
            out = subprocess.run(['tesseract', f'{d}/m.png', '-', '--psm', '6', '-c', 'tessedit_char_whitelist=0123456789.'], capture_output=True, text=True).stdout
        except FileNotFoundError:
            return None   # tesseract not installed: the paragraph number cannot be confirmed
    return re.search(r'(?<!\d)' + str(number) + r'\.', out) is not None

DOC_PARSE = {}
def filed_doc(key):
    if key not in DOC_PARSE:
        if realfile(DOCS[key])[2]: raise ValueError('page range: use the exhibit paragraph maps')
        saved = dict(WARN); DOC_PARSE[key] = read_doc(DOCS[key]); WARN.clear(); WARN.update(saved)
    return DOC_PARSE[key]

def resolve(src, pin):
    """-> (pdf_page, status, how)"""
    path = path_of(src)
    if pin is None: return 1, 'exact', 'first page of the document'
    m = re.match(r'¶\s*(\d+)(?:\(([a-z0-9]+)\))?(?:\s*[–-]\s*\(?\d+\)?)?(?:\s*n\.\s*(\d+))?', pin)
    if m:
        n, sub, note = int(m.group(1)), m.group(2), m.group(3)
        if src[0] == 'DOC':
            try: groups, fns = filed_doc(src[1])
            except Exception: groups, fns = [], {}
            if note and note in fns: return fns[note]['page'], 'exact', f'footnote {note} of {label_of(src)}'
            series = CFG.get('doc_series', {}).get(src[1])
            if series:
                g = next((g for g in groups if g['label'] == f'{series} ¶ {n}'), None)
                if g: return g['page'], 'exact', f'{series} ¶ {n} of {label_of(src)} starts here'
                return None, 'unresolved', f'{series} ¶ {n} not found in {label_of(src)}'
            for g in groups:
                if g['para'] == n: return g['page'], 'exact', f'¶ {n} of {label_of(src)} starts here'
            if any(g.get('para') for g in groups) and n not in text_para_map(path): return None, 'unresolved', f'¶ {n} not found in {label_of(src)}'
            # not a numbered filing: fall through to the paragraph maps used for exhibits
        if src[1] in CFG.get('para_image_docs', []):
            pm = image_para_map(path)
            if n not in pm: return None, 'unresolved', f'¶ {n} not in paragraph map'
            pg, sub_found = pm[n], None
            if sub:
                for q in range(pg, min(pg + 4, npages(path)) + 1):
                    if re.search(r'^\s*\(?' + sub + r'[\.\)]\s', page_text(path, q), re.M): sub_found = q; break
                if sub_found: pg = sub_found
            ok = ocr_margin_has(path, pm[n], n)
            how = f'¶ {n} starts on PDF p.{pm[n]} (margin-image count; ' + ('number confirmed by OCR)' if ok else ('tesseract is not installed, so the number was not confirmed by OCR)' if ok is None else 'OCR could not confirm)'))
            if sub: how += f'; item {sub} ' + (f'found on PDF p.{sub_found}' if sub_found else 'not located; linked to ¶ start')
            return pg, ('exact' if ok and (not sub or sub_found) else 'inferred'), how
        pm = text_para_map(path)
        if n in pm:
            pg, how = pm[n], f'¶ {n} marker found in text'
            if sub:
                for q in range(pg, min(pg + 4, npages(path)) + 1):
                    if re.search(r'^\s*\(' + sub + r'\)\s', page_text(path, q), re.M): pg = q; how += f'; item ({sub}) on PDF p.{q}'; break
            return pg, 'exact', how
        last = max(pm) if pm else None
        return None, 'unresolved', (f'{label_of(src)} has no ¶ {n}: its paragraphs run to ¶ {last}' if last and n > last else f'¶ {n} not found in text')
    m = re.match(r'tr\. (\d+):\d+(?:\s*[–-]\s*(?:(\d+):)?\d+)?', pin)
    if m:
        tm, n = transcript_page_map(path), int(m.group(1))
        if not tm:
            return 1, 'inferred', f'no transcript page numbers could be read in {label_of(src)}; opens the first page: find transcript p. {n} yourself'
        if n not in tm:
            lo, hi = min(tm), max(tm)
            if lo < n < hi:
                below, above = max(k for k in tm if k < n), min(k for k in tm if k > n)
                if tm[above] - tm[below] <= 1:   # no PDF page between the neighbouring transcript pages: the page was not filed
                    return None, 'unresolved', f'transcript p. {n} is not in the excerpt filed as {label_of(src)} (it goes from p. {below} to p. {above})'
                return 1, 'inferred', f'transcript p. {n} should be in {label_of(src)} (its pages run {lo}–{hi}) but its page number could not be read; opens the first page: find p. {n} yourself'
            return None, 'unresolved', f'transcript p. {n} is not in the excerpt filed as {label_of(src)} (pages included: {lo}–{hi})'
        sheet = CONDENSED.get(path, {}).get(n)
        how = f'transcript p. {n} is PDF p. {tm[n]}' + (f' (a condensed sheet carrying transcript pp. {", ".join(map(str, sheet))})' if sheet else '')
        n2 = int(m.group(2)) if m.group(2) else None
        if n2 and n2 != n:
            how += f'; the cite runs to p. {n2}' + (f' (PDF p. {tm[n2]})' if n2 in tm else ', which is not in the excerpt')
            if n2 not in tm and n2 > max(tm): return tm[n], 'inferred', how
        return tm[n], 'exact', how
    m = re.match(r'Bates (\S+?)(\d+)(?:–(\d+))?\+p(\d+)$', pin)
    if m:   # page P of a document cited by its Bates range: counted from the first number (only within the range); amber, as the cite may use printed page numbers
        prefix, n0, P = m.group(1), int(m.group(2)), int(m.group(4))
        bi = bates_index(path, prefix)
        tgt = n0 + P - 1
        hi = int(m.group(2)[:len(m.group(2)) - len(m.group(3))] + m.group(3)) if m.group(3) else None   # "0000114-196" -> 0000196
        if hi is not None and tgt <= hi and tgt in bi:
            return bi[tgt], 'inferred', (f'p. {P} of the document that starts at Bates {prefix}{m.group(2)}: counted from that number, Bates {prefix}{str(tgt).zfill(len(m.group(2)))} '
                                         f'is on PDF p. {bi[tgt]}; the cite may use the document\'s printed page numbers: confirm the page')
        if n0 in bi:
            return bi[n0], 'inferred', f'p. {P} of the document that starts at Bates {prefix}{m.group(2)} (PDF p. {bi[n0]}); its p. {P} could not be placed: find it yourself'
        return 1, 'inferred', f'Bates {prefix}{m.group(2)} not found in the text layer of {label_of(src)}; opens the first page: find p. {P} of that document yourself'
    m = re.match(r'Bates (\S+?)(\d+)(?:–(\d+))?$', pin)
    if m:
        prefix, n = m.group(1), int(m.group(2))
        bi = bates_index(path, prefix)
        if n in bi: return bi[n], 'exact', f'Bates {prefix}{m.group(2)} found on PDF p. {bi[n]}'
        if bi:
            return 1, 'inferred', f'Bates {prefix}{m.group(2)} not found in the text layer of {label_of(src)} (other {prefix} numbers are there; it may be misread by OCR or missing); opens the first page'
        return 1, 'inferred', f'no {prefix} Bates number could be read in the text layer of {label_of(src)} (unstamped, misread by OCR, or an image without a text layer); opens the first page'
    m = re.match(r'pp?\.\s*\*?(\d+)', pin)
    if m and not printed_page_map(path)[0].get(int(m.group(1))) and int(m.group(1)) in transcript_page_map(path) and len(transcript_page_map(path)) >= 3:
        tm = transcript_page_map(path); n = int(m.group(1))   # "id. at 88" after a transcript cite
        return tm[n], 'exact', f'transcript p. {n} is PDF p. {tm[n]}'
    if m:
        (pm, off), n, N = printed_page_map(path), int(m.group(1)), npages(path)
        if off is None:
            return (n, 'inferred', f'the document has no printed page numbers; opens PDF p. {n} (check: a cover sheet or unnumbered pages would shift this)') if n <= N else (None, 'unresolved', f'p. {n} is past the end of the document ({N} pages)')
        pg = pm.get(n) or (n + off if 1 <= n + off <= N else None)
        if not pg: return None, 'unresolved', f'printed p. {n} not found (the document\'s own numbering)'
        how = f'printed p. {n} (the document\'s own page numbering) is PDF p. {pg}' + ('' if n in pm else '; number not printed on that page, inferred from the pages around it')
        st = 'exact' if n in pm else 'inferred'
        if pg != n and n <= N and ecf_stamped(path):   # offer the ECF reading as a second link
            _cache[('ecf_alt', path, pin)] = n; how += f'. Two readings of "p. {n}": this link uses the document\'s own page numbers; the second link uses the court\'s ECF page stamp (PDF p. {n}). Check which one the filing means'
        return pg, st, how
    m = re.match(r'its Ex\. ([A-Z]{1,2}|\d{1,3})$', pin)
    if m:   # an exhibit to this exhibit: look for its slip sheet ("EXHIBIT A" alone on a page)
        L = m.group(1)
        for q in range(1, npages(path) + 1):
            body = [l.strip() for l in page_text(path, q).splitlines() if l.strip() and not ECF_HDR.search(l) and not is_ecf_count(path, l)]
            if body and len(body) <= 3 and any(re.fullmatch(r'(?i)exhibit\s+' + re.escape(L), l) for l in body):
                return q, 'inferred', f'Exhibit {L} to {label_of(src)}: its slip sheet ("Exhibit {L}") is on PDF p. {q}; confirm that this is the document cited'
        return 1, 'inferred', f'Exhibit {L} to {label_of(src)}: no slip sheet for it was found, so the link opens the first page of {label_of(src)}: find Exhibit {L} yourself'
    m = re.match(r'§ (\d+(?:\.\d+)*[a-z]?)$', pin)
    if m:   # a section of a contract or other exhibit: its number at the start of a line
        num = m.group(1)
        rx = (r'(?m)^\s*(?:(?:Section|SECTION|Sec\.|§|Article|ARTICLE)\s*)?' + re.escape(num) + r'\.?(?=\s+[A-Z“"(_]|\s*$)') if '.' in num else \
             (r'(?m)^\s*(?:Section|SECTION|Sec\.|§|Article|ARTICLE)\s*' + re.escape(num) + r'\b')
        hits = [q for q in range(1, npages(path) + 1) if re.search(rx, page_text(path, q))
                and len(re.findall(r'(?m)(?:\.{6,}|(?:\.\s){5,})\s*\d*\s*$', page_text(path, q))) < 3]   # not a contents page
        if not hits:
            return 1, 'inferred', f'§ {num} was not found at the start of a line in the text layer of {label_of(src)}; opens the first page: find § {num} yourself'
        if len(hits) == 1 and '.' in num:
            return hits[0], 'exact', f'§ {num} starts on PDF p. {hits[0]} (its number found at the start of a line)'
        how = f'§ {num} found at the start of a line on PDF p. {hits[0]}'
        how += (f'; also on PDF p. {", ".join(map(str, hits[1:4]))}: check which one is cited' if len(hits) > 1 else '; a one-level section number may also be a list number: check')
        return hits[0], 'inferred', how
    m = re.match(r'(Arts?|Rules?)\.?\s*(\d+)', pin)
    if m:
        word = 'Article' if m.group(1).startswith('Art') else 'Rule'
        for q in range(1, npages(path) + 1):
            if re.search(r'^\s*' + word + r'\s+' + m.group(2) + r'\s*$', page_text(path, q), re.M):
                return q, 'exact', f'heading "{word} {m.group(2)}" on page'
        return None, 'unresolved', f'heading "{word} {m.group(2)}" not found'
    return None, 'unresolved', 'locator type not recognised'

# ================================================================ 5. walk the document
groups, fns = read_doc(DOC)
rows, not_cites = [], []
FN_CALLS = collections.Counter(n for g in groups for n in re.findall(r'\[\[FN(\d+)\]\]', g['text'])) + \
           collections.Counter(n for g in groups for n in g.get('head_fns', []))
FN_USE = collections.Counter()
def fn_texts(n):
    """The footnote text(s) to read at this call of footnote n: the k-th call reads the k-th text numbered n; the last call also reads any
    texts left over (two footnotes numbered n, called once: both are read). A further call of a footnote already read adds nothing."""
    if n not in fns: return []
    ft = [fns[n]] + fns[n].get('more', [])
    k = FN_USE[n]; FN_USE[n] += 1
    if k >= len(ft): return []
    return ft[k:] if k >= FN_CALLS[n] - 1 else [ft[k]]

QUIET = [False]   # True while reading a citation inside an explanatory parenthetical
class Chain:
    def __init__(self): self.src, self.pins, self.tr, self.inner = None, None, False, None
    def set(self, src, pins, via_id=False, inner=None):
        if QUIET[0]: return   # "(quoting Lass …)": a source cited in an explanatory parenthetical is not what a following Id. refers to
        # tr: the source was cited by transcript page:line (an Id. that repeats the same source keeps this, so "Id. at 1-8. Id. at 1-8." both count)
        tr = any(str(x).startswith('tr. ') for x in (pins or []))
        self.tr = (tr or (self.tr and src == self.src)) if via_id else tr
        self.src, self.pins = src, (pins or None)
        self.inner = inner   # N9-U: (number, named as a deposition exhibit) when the source is an unmapped exhibit inside the exhibit src
def in_explanatory(sc, pos):
    """Is sc[pos] inside an explanatory parenthetical ("(quoting …", "(citing …", "(holding …", "(“…” …")? Court-and-date
    parentheticals hold no citations, so any open parenthesis that starts with a lower-case word or a quotation qualifies."""
    depth, i = 0, pos - 1
    while i >= 0:
        ch = sc[i]
        if ch == ')': depth += 1
        elif ch == '(':
            if depth == 0: return bool(re.match(r'\(\s*(?:[a-z]|[“"‘\'])', sc[i:i + 3]))
            depth -= 1
        i -= 1
    return False
body_chain, read_chain = Chain(), Chain()

def add_record(loc, fn, docpage, prop, cite, src, pins, via_id=False, flag=None):
    if (src[0] == 'EX' and src[1] not in EXMAP) or (src[0] == 'DOC' and src[1] not in DOCS):
        rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite, type='record', src=None, links=[], link_status='unresolved', why=f'{label_of(src)} is not in the confirmed map', via_id=via_id,
                         missing=('MISSING', label_of(src)))); return
    links = []
    for pin in (pins or [None]):
        pg, st, how = resolve(src, pin)
        if flag and st == 'exact': st = 'inferred'
        links.append(dict(label=pin, page=pg, status=st, how=how + (f'. {flag}' if flag else ''),
                          href=href_of(path_of(src), pg) if pg else None))
        alt = _cache.get(('ecf_alt', path_of(src), pin))
        if alt:
            links.append(dict(label=f'ECF p. {alt}', page=alt, status='inferred' if flag else 'exact', how=f'Two readings of "p. {alt}": this link uses the court\'s ECF page stamp (PDF p. {alt}); the first link uses the document\'s own page numbers. Check which one the filing means',
                              href=urllib.parse.quote(realfile(path_of(src))[0]) + f'#page={alt}'))
    ls = 'unresolved' if any(l['status'] == 'unresolved' for l in links) else ('inferred' if any(l['status'] == 'inferred' for l in links) else 'exact')
    bad = '; '.join(l['how'] for l in links if l['status'] == 'unresolved')
    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite, type='record', src=src, links=links, link_status=ls, why='; '.join(x for x in [bad, flag] if x), via_id=via_id))

def inner_ex_start(path, X):
    """N9-U: where does exhibit X, attached inside the exhibit at path, start? Its slip sheet (a page holding little more than
    "Exhibit 9" / "Smith Dep. Ex. 9") or its exhibit sticker (such a line on a page with other text). -> (page found, first page of X, how)"""
    rx = re.compile(r'(?:[A-Z][\w’\'.-]*\s+){0,2}(?i:dep(?:o|osition)?\.?\s+)?(?i:exhibit|exh?\.)\s*(?i:no\.\s*)?' + re.escape(X))   # "EXHIBIT 9", "Smith Dep. Ex. 9", "Plaintiff's Exhibit No. 9"
    for q in range(1, npages(path) + 1):
        body = [l.strip() for l in page_text(path, q).splitlines() if l.strip() and not ECF_HDR.search(l) and not is_ecf_count(path, l)]
        hit = next((l for l in body if rx.fullmatch(l)), None)
        if not hit: continue
        if len(body) <= 3:
            if q < npages(path): return q, q + 1, f'its slip sheet ("{hit}") is on PDF p. {q}'
            continue
        return q, q, f'its exhibit sticker ("{hit}") is on PDF p. {q}'
    return None, None, None
def place_inner(row, inner, flag=None):
    """N9-U: the row cites exhibit inner[0] inside the exhibit row['src'], and inner[0] is not in the map. Its pinpoints are not applied
    to the outer exhibit: a page is counted from where the inner exhibit starts (amber, confirm), else the link opens the outer exhibit
    at its first page (amber, with the gap named). A Bates number read exactly in the outer exhibit keeps its link."""
    X, dep = inner; src = row['src']; path = path_of(src); outer = label_of(src)
    name = f'Dep. Ex. {X}' if dep else f'Ex. {X}'
    q, start, found = inner_ex_start(path, X)
    links = []
    for l in row['links']:
        lab = str(l.get('label') or '')
        if lab.startswith('ECF p.'): continue   # a second reading of a page of the outer exhibit: not a page of the inner one
        if lab.startswith('Bates') and l['status'] == 'exact': links.append(l); continue   # a Bates number places its page whatever the inner exhibit
        pm = re.match(r'pp?\.\s*\*?(\d+)', lab)
        if q is None and lab.startswith('Bates'):   # a Bates number not read in the outer exhibit: its own reason, and the gap named
            pg, how = l['page'] or 1, l['how'].split('. ' + flag)[0] if flag else l['how']
            how += f'. {name} is not in the confirmed map either: find {name} in {outer}'
        elif q is None:
            pg, how = 1, (f'{name} is not in the confirmed map, so ' + (f'its {lab}' if lab else 'it') + f' could not be placed; the link opens {outer} at its first page: '
                          f'find {name} in {outer}')
        elif pm and start + int(pm.group(1)) - 1 <= npages(path):
            pg = start + int(pm.group(1)) - 1
            how = f'{name} is not in the confirmed map; {found} of {outer}, so its p. {pm.group(1)} is taken to be PDF p. {pg}, counted from there: confirm the page'
        else:
            pg = q
            how = f'{name} is not in the confirmed map; {found} of {outer}: the link opens it there' + (f'; find its {lab} yourself' if lab else '; confirm that this is the document cited')
        links.append(dict(l, page=pg, status='inferred', how=how + (f'. {flag}' if flag else ''), href=href_of(path, pg)))
    row['links'] = links
    row['link_status'] = 'unresolved' if any(l['status'] == 'unresolved' for l in links) else ('inferred' if any(l['status'] == 'inferred' for l in links) else 'exact')
    row['why'] = '; '.join(dict.fromkeys(l['how'] for l in links if l['status'] != 'exact')) or row.get('why', '')
    row['inner'] = inner

_FEDERAL = {_rnorm(x) for x in ['U.S.', 'S. Ct.', 'L. Ed.', 'L. Ed. 2d', 'F.', 'F.2d', 'F.3d', 'F.4th', 'F. Supp.', 'F. Supp. 2d', 'F. Supp. 3d',
                                 "F. App'x", 'Fed. Cl.', 'Cl. Ct.', 'Ct. Cl.', 'B.R.', 'F.R.D.', 'T.C.', 'M.J.', 'Vet. App.', 'Ct. Int\'l Trade', 'F. Cas.']}
def is_federal(rep): return bool(rep_canon(rep) & _FEDERAL)
def case_link(auth, vol, rep, page, pin):
    first = re.search(r'\d+', pin).group(0) if pin and re.search(r'\d', pin) else None
    short = (auth or {}).get('short') or f'{vol} {rep} {page}'
    label = f'{short}, {vol} {rep} ' + (f'at {pin}' if pin else page)
    if auth and auth.get('no_link'):   # the map marks this citation "do not link" (e.g. CourtListener resolves it to another case)
        return dict(label=label, page=None, status='nolink', href=None, how=f'Not linked (map): {auth["no_link"]}')
    if auth and auth.get('url'):
        href = auth['url'] + (f'#:~:text={urllib.parse.quote("*" + first)}' if first and first != page else '')
        named = f'. CourtListener names it: {auth["cl_name"]}' if auth.get('cl_name') else ''
        how = 'Opens the opinion on CourtListener' + named
        if first and page.isdigit() and int(first) < int(page):
            return dict(label=label, page=None, status='unresolved', href=auth['url'],
                        how=how + f'. Pinpoint {first} comes before the first page of the opinion (p. {page}): check the pinpoint')
        if first and page.isdigit() and int(first) > int(page) + 150:
            return dict(label=label, page=None, status='inferred', href=auth['url'],
                        how=how + f'. Pinpoint {first} is more than 150 pages after the first page (p. {page}): check the pinpoint')
        if not (first and first != page):
            return dict(label=label, page=None, status='exact', how=how, href=auth['url'])
        if auth.get('stub'):
            return dict(label=label, page=None, status='inferred', href=auth['url'],
                        how=how + f'. CourtListener has little or no text for this opinion: check p. {first} in another source')
        if auth.get('marker_reporter'):
            return dict(label=label, page=None, status='inferred', href=auth['url'],
                        how=how + f'. CourtListener\'s copy is paginated by {auth["marker_reporter"]}, not {vol} {rep}, so the link opens at the start: find p. {first} yourself')
        if auth.get('markers') is True:
            caution = '' if is_federal(rep) else f'. Check that the highlighted marker is for {rep} (a state case may also carry a parallel reporter\'s page markers)'
            return dict(label=label, page=None, status='exact', href=href, how=f'Opens the opinion on CourtListener at the page marker *{first}' + named + caution)
        if auth.get('markers') is False:
            return dict(label=label, page=None, status='inferred', href=auth['url'],
                        how=how + f'. CourtListener\'s copy of this opinion has no page markers a link can jump to, so the link opens at the start: find p. {first} yourself')
        return dict(label=label, page=None, status='inferred', href=href,
                    how=how + f'. Page markers were not checked when the map was drafted: if Chrome does not jump to *{first}, find the page yourself')
    return dict(label=label, page=None, status='inferred', how='Not found in the map; CourtListener citation route (unverified)',
                href=f'https://www.courtlistener.com/c/{urllib.parse.quote(rep)}/{vol}/{page}/')

def add_case(loc, fn, docpage, prop, sc, m, kind):
    vol, rep_ = m.group('vol'), re.sub(r'\s+', ' ', m.group('rep'))
    pin = re.sub(r'\s+', '', m.group('pin')) if m.group('pin') else None
    if kind == 'full':
        auth, page = find_auth(vol, rep_, m.group('page'))
    else:
        auth, page = find_auth(vol, rep_, None, pin)
    name = name_before(sc[:m.start()])
    raw = (name + ', ' if name else '') + m.group(0)
    sig = re.search(r'(See also|see also|See, e\.g\.,|see, e\.g\.,|See|see|Cf\.|cf\.|But see|but see)\s*$', sc[:m.start() - (len(name) + 2 if name else 0)])
    cite = (sig.group(1) + ' ' if sig else '') + raw
    if page is None:
        link = dict(label=m.group(0), page=None, status='unresolved', how='Short-form citation with no matching full citation', href=None)
    else:
        link = case_link(auth, vol, rep_, page, pin)
    src = ('CASE', f'{vol} {rep_} {page}', (auth or {}).get('short') or f'{vol} {rep_} {page}')
    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite, raw=raw, type='case', src=src, pins=[pin] if pin else None,
                     links=[link] if link['status'] != 'nolink' else [], link_status=link['status'], why='' if link['status'] == 'exact' else link['how']))

def add_case_id(loc, fn, docpage, prop, shown, raw, src, pins, flag):
    mm = re.match(r'(\d+) (.+) (\d+)$', src[1])
    if not mm:   # the antecedent is a short-form cite whose full citation was not found
        rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=raw, type='case', src=src, links=[], link_status='unresolved',
                         why='Id. refers to a short-form citation with no matching full citation', via_id=True)); return
    vol, rep_, page = mm.groups()
    auth = auth_for(vol, rep_, page)
    ps = [re.sub(r'^(p\.|at)\s*', '', re.sub(r'\s+', '', p)) for p in pins] if pins else [None]   # "Id. at 69–71, 73": one link per pinpoint
    links = [case_link(auth, vol, rep_, page, p) for p in ps]
    if links and all(l['status'] == 'nolink' for l in links):
        rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=raw, type='case', src=src, pins=[p for p in ps if p] or None,
                         links=[], link_status='nolink', why=links[0]['how'], via_id=True)); return
    for link in links:
        if flag and link['status'] == 'exact': link['status'] = 'inferred'; link['how'] += '. ' + flag
    ls = 'unresolved' if any(l['status'] == 'unresolved' for l in links) else ('inferred' if any(l['status'] == 'inferred' for l in links) else 'exact')
    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=raw, type='case', src=src, pins=[p for p in ps if p] or None,
                     links=links, link_status=ls, why=flag or '', via_id=True))

def cite_tail(sc, end):
    """The text after a record citation, up to the next citation or the end of the clause -> (text, text without parentheticals)."""
    rest = sc[end:]
    stop = min([x.start() for x in re.finditer(r';|(?<![A-Za-z])Exh?s?\.\s*\d|\[\[FN|\b[Ii]d\.|\b(?:See|see|Cf\.|cf\.)\s|\b(?:ECF|Dkt|Docket|NYSCEF)\b|\bDoc\.\s*Nos?\.', rest)] +
               [x.start() for x in re.finditer(DOCNAMES, rest)] + [len(rest)])   # a docket cite or another record cite is read on its own
    while stop < len(rest) and rest[stop] == ';' and re.search(TR + r'\s*$', rest[:stop]) and re.match(r';\s*\d{1,4}:\d', rest[stop:]):
        nxt = [x.start() + stop + 1 for x in re.finditer(r';|(?<![A-Za-z])Exh?s?\.\s*\d|\[\[FN|\b[Ii]d\.|\b(?:See|see|Cf\.|cf\.)\s', rest[stop + 1:])]
        stop = min(nxt + [len(rest)])   # "8:11-23; 9:24-10:1": more page:line of the same transcript
    seg = rest[:stop]
    for x in re.finditer(r'\.\s+(?=\d{1,3}\.(?:\s+[A-Z“"]|\s*$)|[A-Z][a-z]+\s)', seg):   # the next numbered paragraph, or a new sentence
        w = re.search(r'(\S+)$', seg[:x.start()])
        if not w or not re.fullmatch(r'(?:[A-Z]|Exh?s?|Dep|Tr|Hr’g|Hr\'g|Decl|Dec|Aff|Doc|Docs|Dkt|No|Nos|p|pp|v|Inc|Co|Corp|Ltd|Mr|Ms|Dr|Jr|St|Vol)', w.group(1)) \
           or re.match(r'\s+\d', seg[x.start() + 1:]) or re.search(r'Exh?s?\.\s*[A-Z]{1,2}$', seg[:x.start()]):
            seg = seg[:x.start() + 1]; break
    return seg, re.sub(r'\([^()]*\)', lambda q: ' ' * len(q.group(0)), seg)   # dates inside parentheticals are not pinpoints

MONTHS = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?'
def unread_flag(segc):
    """A record cite followed by numbers that were not read as a pinpoint must not show as an exact link to p. 1."""
    t = re.sub(MONTHS + r'\s+\d{1,2},?\s+\d{4}', ' ', segc)
    t = re.sub(r'\b(?:19|20)\d{2}\b', ' ', t)
    t = re.sub(r'\b(?:Day|Vol\.?|Volume|Part)\s+\d+\b', ' ', t)
    d = re.search(r'\d', t)
    if not d: return None
    shown = re.sub(r'\s+', ' ', segc).strip(' ,.')[:80]
    return f'Pinpoint not read: the citation continues "{shown}", which the script could not place; opens the first page'

def process(text, loc, fn, docpage, fn_chain=None):
    in_fn = fn_chain is not None
    text = re.sub(r'\b([Ss]ee|[Cc]f\.|[Aa]lso)(?=id\.|also\b)', r'\1 ', text)   # text extraction can run 'See id.' together as 'Seeid.'
    text = re.sub(r'\s+(\[\[FN\d+\]\])', r'\1', text)   # keep a footnote marker with the sentence it ends
    text = re.sub(r'([.?!][”"]?\)?\[\[FN\d+\]\])\s+', r'\1\n', text)   # …and end the sentence there
    sents = sentences(text)
    for i, s in enumerate(sents):
        r0, n0 = len(rows), len(not_cites)
        sc = re.sub(r'\s*\[\[FN\d+\]\]', '', s).strip()
        cite_sentence = bool(re.match(r'^(?:See also|See|see|Cf\.|cf\.|But see|Ex\.|Id\.|' + DOCNAMES + r')(?!\w)', sc)) or bool(re.match(r'^\d{4}\s+(?:WL|LX|[A-Z][\w.]*(?:\s+[A-Z][\w.]*)*\s+LEXIS)\s', sc)) or bool(re.match(r'^\d+\s+(?:U\.S\.C\.|' + REPS + r')', sc))
        if not cite_sentence:
            fm = min([m.start() for m in CASE_FULL.finditer(sc)] + [m.start() for m in CASE_SHORT.finditer(sc)] + [m.start() for m in NOLINK.finditer(sc) if m.group('db')] + [10**6])
            pre = sc[:fm]
            if fm < 10**6 and len(pre) < 180 and re.fullmatch(r'(?:(?:See also|See|See, e\.g\.,|Cf\.|But see)\s+)?[A-Z][^;:]*?,\s*', pre) \
               and not re.match(r'^(In|The|This|That|Under|As|Because|Accordingly|Pursuant)\b', pre) \
               and not re.search(r'\b(is|was|are|were|held|provides|has|have|applies|recognized|observed|noted|found)\b', pre):
                cite_sentence = True
        if not cite_sentence and i > 0:
            rest = sc
            rest = DOCKET.sub(lambda d: d.group(0)[:d.start('no') - d.start()].rsplit(',', 1)[0] + ' ', rest)   # keep the prose before the case number
            for rx in (TOKEN, EXT, CASE_FULL, CASE_SHORT, NOLINK, TREATY, URLRE):
                rest = rx.sub(' ', rest)
            rest = re.sub(r'\([^()]*\)', ' ', rest)
            rest = re.sub(r'\b(?:See generally|See also|see also|See|see|Cf|cf|But see|accord|Accord|e\.g|and|also|generally|at)\b', ' ', rest)
            if not re.search(r'[A-Za-z]{3,}', rest): cite_sentence = True
        prop = re.sub(r'\s*\[\[FN\d+\]\]', '', sents[i - 1]).strip() if (cite_sentence and i > 0) else sc
        _att, _nest = [(a.start(), a.end()) for a in ATTACH.finditer(sc)], []
        for m in ATTACH.finditer(sc):
            if any(a0 <= m.start() < a1 for a0, a1 in _nest): continue   # the outer exhibit of a nested exhibit already read
            for gi in (1, 2):
                ex = m.group(gi)
                if not ex: continue
                nest = nested_outer(sc, m.end(gi))
                if nest is None:
                    add_record(loc, fn, docpage, sc, f'Exhibit {ex}', ('EX', ex), None); continue
                outer, oend = nest
                if outer:   # "attached as Exhibit A to the Declaration of …, which is attached as Exhibit BB": a cite to Ex. BB, not to Ex. A
                    add_record(loc, fn, docpage, sc, sc[m.start():oend].strip(), ('EX', outer), [f'its Ex. {ex}'])
                    rows[-1]['raw'] = sc[m.start():oend].strip(); _nest.append((m.start(), oend))
        _att += _nest
        events = sorted([(m.start(), 'tok', m) for m in TOKEN.finditer(sc) if not any(a0 <= m.start() < a1 for a0, a1 in _att)] +
                        [(m.start(), 'ext', m) for m in EXT.finditer(sc) if not any(d.start() <= m.start() < d.end() for d in DOCKET.finditer(sc))] +
                        [(m.start(), 'full', m) for m in CASE_FULL.finditer(sc)] +
                        [(m.start(), 'short', m) for m in CASE_SHORT.finditer(sc)] +
                        [(m.start(), 'state', m) for m in STATESTAT.finditer(sc) if not any(e.start() <= m.start() < e.end() for e in EXT.finditer(sc))] +
                        [(m.start(), 'local', m) for m in LOCALRULE.finditer(sc)] +
                        [(m.start(), 'nolink', m) for m in NOLINK.finditer(sc)
                         if not any(f.start() <= m.start() < f.end() for f in FNREF.finditer(sc))], key=lambda e: e[0])
        PEND = []   # an exhibit letter waiting for the deposition exhibit number that follows it
        for _, kind, m in events:
            QUIET[0] = in_explanatory(sc, m.start())
            if kind == 'local':
                raw = m.group(0).rstrip(',;. ')
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=raw, raw=raw, type='statute', src=('NOLINK', raw), links=[],
                                 link_status='nolink', why='Local rule: listed for checking, not linked'))
                continue
            if kind == 'state':
                raw = m.group(0).rstrip(',;. ')
                sig = re.search(r'(See generally,?|See also|see also|See|see|Cf\.|cf\.|citing|quoting)\s*\(?$', sc[max(0, m.start() - 16):m.start()])
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=(sig.group(1) + ' ' if sig else '') + raw, raw=raw,
                                 type='statute', src=('NOLINK', raw), links=[], link_status='nolink',
                                 why='State statute: listed for checking, not linked (citable v1.0 links only federal statutes and rules and the CPLR)'))
                if not (not sig and re.match(r',?\s+[a-z]', sc[m.end():])):   # a statute named in running prose is not what a following Id. refers to
                    (fn_chain if in_fn else body_chain).set(('NOLINK', raw), None); read_chain.set(('NOLINK', raw), None)
                continue
            if kind == 'nolink':
                name = name_before(sc[:m.start()])
                raw = (name + ', ' if name else '') + m.group(0).rstrip(',;')
                sig = re.search(r'(See also|see also|See, e\.g\.,|see, e\.g\.,|See|see|Cf\.|cf\.|But see|but see|accord|Accord)\s*$', sc[:m.start() - (len(name) + 2 if name else 0)])
                uk = unrep_key(m.group('db')) if m.group('db') else None
                if uk and UNREP.get(uk) and (UNREP[uk].get('recap') or UNREP[uk].get('docket_url')):
                    pm = re.search(r'at\s*(\*\d+(?:\s*[–-]\s*\*?\d+)?)', m.group('db'))
                    pins = [re.sub(r'\s+', '', pm.group(1))] if pm else None
                    links = unrep_links(UNREP[uk], pins)
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=(sig.group(1) + ' ' if sig else '') + raw, raw=raw,
                                     type='case', src=('UNREP', uk, UNREP[uk].get('short') or uk), pins=pins, links=links, link_status='inferred', why=links[0]['how']))
                    (fn_chain if in_fn else body_chain).set(rows[-1]['src'], pins); read_chain.set(rows[-1]['src'], pins)
                    continue
                if m.group('db'):
                    why = 'Westlaw/Lexis citation: listed for checking, not linked'
                elif name:
                    why = 'supra: listed for checking, not linked (the full citation appears earlier)'
                else:
                    why = 'Cross-reference within this filing (supra): listed for checking, not linked'
                label = raw if len(raw) < 90 else raw[:87] + '…'
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=(sig.group(1) + ' ' if sig else '') + raw, raw=raw,
                                 type='case' if m.group('db') else 'other', src=('NOLINK', label), links=[], link_status='nolink', why=why))
                (fn_chain if in_fn else body_chain).set(('NOLINK', label), None); read_chain.set(('NOLINK', label), None)
                continue
            if kind == 'ext' and m.group('own'):
                back = re.split(r'[;]', sc[max([0, m.start() - 100] + [e.end() for e in EXT.finditer(sc) if e.end() <= m.start()]):m.start()])[-1]
                od = [x for x in re.finditer(r'\b((?:[A-Z][\w&.’\'-]*\s+){0,3}[A-Z][\w&.’\'-]*)\s+Docket\b', back)
                      if x.group(1).split()[-1].rstrip('’\'s') not in ('Court', 'This', 'Civil', 'ECF', 'CM/ECF', 'District', 'PACER', 'The', 'See', 'Our')]
                if od:   # "(IOEngine Docket) ref: pleadings at Doc. Nos. 1, 12, 93": entries of another case's docket, not of this one
                    raw = m.group(0).strip()
                    lbl = f'{raw} ({od[-1].group(1)} Docket)'
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=raw, raw=raw, type='record', src=('NOLINK', lbl),
                                     links=[], link_status='nolink', why=f'Docket entries of another case (the "{od[-1].group(1)} Docket" named before them): listed for checking, not linked to this case\'s docket'))
                    (fn_chain if in_fn else body_chain).set(('NOLINK', lbl), None); read_chain.set(('NOLINK', lbl), None)
                    continue
            if kind == 'ext':
                typ, lbl, links = ext_row(m)
                EXT_LINKS[lbl] = (typ, links)
                sig = re.search(r'(See generally,?|See also|see also|See|see|Cf\.|cf\.)\s*$', sc[max(0, m.start() - 16):m.start()])
                ctext = (sig.group(1) + ' ' if sig and not m.group(0).startswith('See') else '') + m.group(0).strip()
                st = 'unresolved' if not links else ('nolink' if all(l['status'] == 'nolink' for l in links) else ('inferred' if any(l['status'] == 'inferred' for l in links) else 'exact'))
                links = [l for l in links if l['status'] != 'nolink'] if st != 'nolink' else []
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=ctext, raw=m.group(0).strip(), type=typ, src=('EXT', lbl),
                                 links=links, link_status=st, why='' if st == 'exact' else ('; '.join(l['how'] for l in ext_row(m)[2] if l['status'] != 'exact'))))
                if typ == 'statute' and not sig and re.match(r',?\s+[a-z]', sc[m.end():]):
                    continue   # a statute named in running prose ("suit under 42 U.S.C. § 1983 alleging ...") is listed but is not what a following Id. refers to
                (fn_chain if in_fn else body_chain).set(('EXT', lbl), None); read_chain.set(('EXT', lbl), None)
                continue
            if kind != 'tok':
                add_case(loc, fn, docpage, prop, sc, m, kind)
                last = rows[-1]
                if kind == 'full' and HISTORY.search(sc[max(0, m.start() - 60):m.start()]):
                    continue   # subsequent history ("…, aff'd, 856 F. App'x 385"): a following Id. still refers to the decision cited
                (fn_chain if in_fn else body_chain).set(last['src'], last.get('pins'))
                read_chain.set(last['src'], last.get('pins'))
                continue
            cite_txt = m.group(0).strip().rstrip(',;')
            sig = re.search(r'(See also|see also|See|see|Cf\.|cf\.|But see|but see)\s*$', sc[max(0, m.start() - 14):m.start()])
            if sig: cite_txt = sig.group(1) + ' ' + cite_txt
            if m.group('rt'):
                term = next(k for k in sorted(RECORD_TERMS, key=len, reverse=True) if m.group(0).startswith(k))
                add_record(loc, fn, docpage, prop, cite_txt, ('EX', RECORD_TERMS[term]), split_loc(m.group('rtloc')))
                last = rows[-1]; pins_now = [l['label'] for l in last['links'] if l['label']] or None
                (fn_chain if in_fn else body_chain).set(last['src'], pins_now); read_chain.set(last['src'], pins_now)
                continue
            if any(a0 <= m.start() < a1 for a0, a1 in _nest): continue
            if m.group('blank'):   # "Ex. __ (Graylin Tr.)": the exhibit letter was left blank in the filing
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite_txt, raw=m.group(0), type='record', src=None, links=[],
                                 link_status='unresolved', why='The exhibit letter is left blank in the filing ("' + m.group(0) + '"): not linked'))
                continue
            if m.group('ex'):   # "Ex. BB (Decl. of Melissa Bozeman at Ex. A)": Ex. A of the declaration filed as Ex. BB, not the case's Ex. A
                op = sc.rfind('(', 0, m.start())
                om = re.search(r'(?:Exh?\.|Exhibit)\s*([A-Z]{1,2}|\d{1,3})\s*$', sc[:op]) if op >= 0 and ')' not in sc[op:m.start()] else None
                if om and re.search(r'(?i)\b(?:decl|declaration|affidavit|aff|report|dep|deposition|tr)\b', sc[op:m.start()]):
                    outer = om.group(1)
                    tgt = next((r for r in reversed(rows[r0:]) if r.get('src') == ('EX', outer)), None)
                    if tgt is not None:
                        pg, st, how = resolve(('EX', outer), f'its Ex. {m.group("exl")}')
                        tgt['links'] = [dict(label=f'its Ex. {m.group("exl")}', page=pg, status=st, how=how, href=href_of(EXMAP[outer], pg))]
                        if tgt['link_status'] != 'unresolved': tgt['link_status'] = 'inferred'
                        tgt['why'] = how
                    continue
            if m.group('ex') and not m.group('exloc'):
                nest = nested_outer(sc, m.end('exl'))
                if nest is not None:
                    outer, oend = nest
                    if outer:   # "Exhibit A to Exhibit BB" / "Ex. A to the Smith Declaration at Ex. BB"
                        add_record(loc, fn, docpage, prop, sc[m.start():oend].strip(), ('EX', outer), [f'its Ex. {m.group("exl")}'])
                        rows[-1]['raw'] = sc[m.start():oend].strip(); _nest.append((m.start(), oend))
                        last = rows[-1]; pins_now = [l['label'] for l in last['links'] if l['label']] or None
                        (fn_chain if in_fn else body_chain).set(last['src'], pins_now); read_chain.set(last['src'], pins_now)
                    continue   # an exhibit to another document is not this case's exhibit of that letter
            written = bool(m.group('ex')) and 'Exhibit' in m.group('ex')
            _dx = re.match(DEPEX, sc[m.end('exl'):]) if (m.group('ex') and not m.group('exloc')) else None
            if _dx:
                # "Ex. H, Ex. 6 to Vavra Dep., at Bates …" / "Exhibit B, Ex. 2 to …" / "Ex. H, Vavra Dep Ex. 11, at Bates …": one citation,
                # read with the deposition exhibit that follows
                PEND[:] = [m.group('exl'), m.start(), m.end('exl') + _dx.end()]
                continue
            if written:   # "Exhibit A, … 11:22-12:3" — but not "Exhibit D-13" or "Exhibit A to the Bozeman Declaration"
                after = sc[m.start('exl') + len(m.group('exl')):]
                if re.match(r'-\d|\s+(?:to|of|in)\s+(?:the\s+|his\s+|her\s+|their\s+)?[A-Z]', after):
                    continue
            if m.group('docex') or m.group('ex'):
                inner = None
                if m.group('docex'):
                    dm = re.match(r'(' + DOCNAMES + r')\.?,?\s*(' + PARA + r')\s*(?:,|and)\s*(?=Exh?s?\.)', m.group(0))
                    if dm:   # "Friedman Decl., ¶ 7 and Ex. D, ¶¶ …": the declaration ¶ is its own cite
                        add_record(loc, fn, docpage, prop, (sig.group(1) + ' ' if sig else '') + f'{dm.group(1)}., {dm.group(2)}', ('DOC', dm.group(1)), split_loc(dm.group(2)))
                        cite_txt = (sig.group(1) + ' ' if sig else '') + m.group(0)[dm.end():].strip().rstrip(',;')
                src = ('EX', m.group('dex') or m.group('exl'))
                if PEND and m.group('ex') and m.start() == PEND[2]:   # the second half of "Ex. H, Ex. 6 to … Dep." / "Ex. H, Vavra Dep Ex. 11"
                    sig0 = re.search(r'(See also|see also|See|see|Cf\.|cf\.|But see|but see)\s*$', sc[max(0, PEND[1] - 14):PEND[1]])
                    cite_txt = (sig0.group(1) + ' ' if sig0 else '') + sc[PEND[1]:m.start()] + strip_sig(cite_txt)
                    if src[1] not in EXMAP and PEND[0] in EXMAP:   # N9-U: the inner exhibit is not in the map: link the outer one, never at the inner one's pinpoint
                        if not re.match(r'\s+(?:to|of|in)\s', sc[m.end():]):   # not "Ex. H, Ex. 9 to Smith Dep., at 2", which keeps its own reading
                            inner = (src[1], bool(re.search(r'\bDep(?:o|osition)?\b', sc[PEND[1]:m.start()])))
                        src = ('EX', PEND[0])
                PEND[:] = []
                more = re.match(r'(?:\s*(?:,\s*(?:and\s+|&\s*)?|and\s+|&\s*)(?:[A-Z]{1,2}|\d{1,3})(?![\w]))+', sc[m.end():]) if re.search(r'Exh?s\.|Exhibits', m.group(0)) and not (m.group('dexloc') or m.group('exloc')) else None
                if more:
                    letters = [src[1]] + re.findall(r'(?:[A-Z]{1,2}|\d{1,3})(?![\w])', more.group(0))
                    for j, L in enumerate(letters):
                        add_record(loc, fn, docpage, prop, (cite_txt + more.group(0)) if j == 0 else f'Ex. {L}', ('EX', L), None)
                        rows[-1]['raw'] = cite_txt if j == 0 else L
                else:
                    pins = split_loc(m.group('dexloc') or m.group('exloc'))
                    flag = None
                    if not pins:   # "Ex. 1, Hunter Day 1 Dep. Tr. 49:3–51:21, 62:23–64:21" / "Ex. 13, Property Clerk Invoice, DEF000012"
                        seg, segc = cite_tail(sc, m.end())
                        trp = ['tr. ' + x.group(0) for x in re.finditer(r'(?<![\d:])' + TR, segc)]
                        btp = [f'Bates {b.group(1)}{b.group(2)}' + (f'–{b.group(3)}' if b.group(3) else '') for b in BATES.finditer(segc)]
                        scp = [x for b in re.finditer(r'(?:^\s*,?\s*|\bat\s+)(' + SECP + r')', segc) for x in split_loc(b.group(1))]
                        if trp and btp:
                            if all(resolve(src, x)[1] == 'exact' for x in trp):   # the transcript pages are placed: keep only Bates numbers that add a placed page
                                btp = [x for x in btp if resolve(src, x)[1] == 'exact']
                            else:                                                 # a transcript page is not legible: let the Bates numbers locate it
                                trp = [x for x in trp if resolve(src, x)[1] == 'exact']
                        pins = (trp + btp) if (trp and btp) else (trp or btp)
                        if scp and not trp: pins = scp + btp
                        bpg = re.search(r'\]\s*,?\s*at\s+(\d{1,4}(?:\s*[–-]\s*\d{1,4})?(?:\s*,\s*\d{1,4}(?:\s*[–-]\s*\d{1,4})?)*)(?![\d:])', segc)
                        if bpg and btp and not trp and not scp:   # "[IngenicoInc_0000114-196] at 9": a page of the document that starts at that Bates number
                            b0 = [b for b in BATES.finditer(segc) if b.start() < bpg.start()]
                            if b0:
                                b0 = b0[-1]
                                _pp = [re.match(r'\d+', x.strip()).group(0) for x in bpg.group(1).split(',')]
                                pins = [f'Bates {b0.group(1)}{b0.group(2)}' + (f'–{b0.group(3)}' if b0.group(3) else '') + f'+p{x}' for x in _pp]
                        if pins: cite_txt = cite_txt + seg.rstrip(' ,.')
                        flag = unread_flag(segc) if not pins else None
                        if written and not pins and not flag and not (sig or re.match(r'\s*(?:[;.)]|$)', sc[m.end():])):
                            continue   # "Exhibit A" named in prose, not cited
                    if m.group('exu'):   # "Ex. S_": a stray underscore after the letter
                        flag = ((flag + '. ') if flag else '') + f'Printed as "{m.group("exl")}_" in the filing: read as Ex. {m.group("exl")}; check the letter'
                    if pins and any(x.startswith('§') for x in pins) and re.search(r'\bas\s+amended\b', sc[m.end():m.end() + 250].split(';')[0]):
                        flag = ((flag + '. ') if flag else '') + 'The cite says "as amended": the amended text may be elsewhere in this exhibit; check which version is cited'
                    add_record(loc, fn, docpage, prop, cite_txt, src, pins or None, flag=flag)
                    if inner and rows[-1].get('src'): place_inner(rows[-1], inner, flag)
            elif m.group('doc'):
                if not m.group('docloc') and not (sig or re.match(r'\s*(?:[;.)]|$)', sc[m.end():])): continue   # a name used in prose, not a citation
                flag = unread_flag(cite_tail(sc, m.end())[1]) if not m.group('docloc') else None
                add_record(loc, fn, docpage, prop, cite_txt, ('DOC', re.match(DOCNAMES, m.group('doc')).group(0)), split_loc(m.group('docloc')), flag=flag)
            else:   # id.
                given = split_loc(m.group('idloc'))
                chain = fn_chain if (in_fn and fn_chain.src) else body_chain
                flag = 'Id. in a footnote with no earlier cite in that footnote; resolved to the last cite in the text' if (in_fn and not fn_chain.src) else None
                if chain.src is None:
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite_txt, type='record', src=None, links=[], link_status='unresolved', why='Id. with no antecedent', via_id=True)); continue
                if chain.src[0] == 'MISSING':
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite_txt + f'  [= {chain.src[1]}]', type='record', src=None, links=[], link_status='unresolved',
                                     why=f'Id. refers to {chain.src[1]}, which is not in the confirmed map', via_id=True, missing=chain.src)); continue
                src, pins = chain.src, (given or chain.pins)
                if not in_fn and read_chain.src:
                    alt = (read_chain.src, tuple(given or read_chain.pins or ()))
                    if alt != (src, tuple(pins or ())):
                        flag = (f'Id. is ambiguous: the last cite in the text is {label_of(src)} {", ".join(chain.pins or [])}'.rstrip() +
                                f'; a footnote in between cites {label_of(read_chain.src)} {", ".join(read_chain.pins or [])}'.rstrip() + '. Linked to the text antecedent')
                _in = chain.inner if src[0] == 'EX' else None   # N9-U: Id. to an unmapped exhibit inside an exhibit
                shown = cite_txt + f'  [= {label_of(src)}' + (f', {"Dep. " if _in[1] else ""}Ex. {_in[0]}' if _in else '') + (f', {", ".join(pins)}' if (pins and not given) else '') + ']'
                if src[0] == 'EXT':
                    typ, links = EXT_LINKS[src[1]]
                    st = 'nolink' if not [l for l in links if l['status'] != 'nolink'] else ('inferred' if (flag or any(l['status'] == 'inferred' for l in links)) else 'exact')
                    if given: flag = ((flag + '. ') if flag else '') + f'Id. gives a pinpoint ({", ".join(given)}) that is not applied to {src[1]}'; st = 'inferred' if st == 'exact' else st
                    _ls = [dict(l) for l in links if l['status'] != 'nolink']
                    if st == 'inferred':
                        for _l in _ls:
                            if _l['status'] == 'exact': _l['status'] = 'inferred'; _l['how'] += (f'. {flag}' if flag else '')
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=cite_txt + f'  [= {src[1]}]', raw=cite_txt, type=typ, src=src,
                                     links=_ls, link_status=st, why=flag or '', via_id=True)); continue
                if src[0] == 'UNREP':
                    ps = [re.sub(r'^(p\.|at)\s*', '', re.sub(r'\s+', '', x)) for x in pins] if pins else None
                    links = unrep_links(UNREP[src[1]], ps)
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=cite_txt, type='case', src=src, pins=ps, links=links,
                                     link_status='inferred', why=flag or links[0]['how'], via_id=True)); continue
                if src[0] == 'NOLINK':
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=cite_txt, type='other', src=src, links=[], link_status='nolink',
                                     why='Id. refers to a citation that is listed but not linked', via_id=True)); continue
                if src[0] == 'CASE' and given and given[0].startswith('¶'):   # cases are not cited by ¶: the antecedent is probably wrong
                    lastrec = next((r for r in reversed(rows) if r['type'] == 'record' and r.get('src')), None)
                    hint = f'; the last record citation before it is {lastrec["cite"].split("  [=")[0]}' if lastrec else ''
                    rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop, cite=shown, raw=cite_txt, type='record', src=None, links=[], link_status='unresolved',
                                     why=f'Id. {given[0]} follows a case citation ({label_of(src)}), but cases are not cited by ¶{hint}', via_id=True)); continue
                if src[0] == 'CASE':
                    add_case_id(loc, fn, docpage, prop, shown, cite_txt, src, pins, flag)
                else:
                    if given and chain.tr and all(re.match(r'pp?\.', x) for x in given):
                        # X1: "Id. at 1" after a transcript page:line cite: the literal link is kept, amber; no second, guessed link
                        x1 = (f'Id. gives a page pinpoint, but its source ({label_of(src)}) is cited by transcript page:line; '
                              f'the filing may mean another document. Check the source.')
                        flag = ((flag.rstrip('.') + '. ') if flag else '') + x1
                    add_record(loc, fn, docpage, prop, shown, src, pins, via_id=True, flag=flag)
                    if _in and rows[-1].get('src'): place_inner(rows[-1], _in, flag)
            last = rows[-1]
            if last.get('src'):
                pins_now = last.get('pins') if last['src'][0] == 'CASE' else ([l['label'] for l in last['links'] if l['label']] or None)
                (fn_chain if in_fn else body_chain).set(last['src'], pins_now, via_id=bool(last.get('via_id')), inner=last.get('inner'))
                read_chain.set(last['src'], pins_now, via_id=bool(last.get('via_id')), inner=last.get('inner'))
            elif last.get('missing'):   # a cite to an exhibit not in the map: a following Id. refers to it, not to an earlier source
                (fn_chain if in_fn else body_chain).set(last['missing'], None); read_chain.set(last['missing'], None)
        QUIET[0] = False
        for m in TREATY.finditer(sc):
            parts = {re.sub(r'\s+', ' ', x).strip() for x in re.findall(r'\d+\s+U\.(?:N\.T\.S|S\.T)\.\s+\d+', m.group(0))}
            t = next((t for t in TREATIES if re.sub(r'\s+', ' ', t['cite']).strip() in parts), None)   # exact volume and page
            links = []
            if t and t.get('record') in EXMAP:   # rule: the copy in the record first, then the official reporter
                links.append(dict(label=f'Ex. {t["record"]}', page=1, status='exact', how='treaty text in the record', href=href_of(EXMAP[t['record']], 1), rec=True))
            if t and t.get('url'):
                links.append(dict(label=t.get('source', 'Official reporter'), page=None, status='exact', how=t.get('how', 'official reporter copy'), href=t['url']))
            rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=sc, cite=m.group(0), type='treaty', links=links,
                             link_status='exact' if links else 'unresolved', why='' if links else 'Treaty not in the map: add the record exhibit or its UN Treaty Series link'))
        for m in FNREF.finditer(sc):
            n = m.group(1)
            if n in fns:
                rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=m.group(0), type='internal', link_status='exact', why='',
                                 links=[dict(label=f'n.{n}', page=fns[n]['page'], status='exact', how=f'footnote {n} of this document', href=urllib.parse.quote(DOC) + f'#page={fns[n]["page"]}')]))
        for m in DOCKET.finditer(sc):
            full = m.group(0); vpos = full.find(' v. ')
            cut = max(full.rfind(' in ', 0, vpos), full.rfind('See ', 0, vpos))
            q = urllib.parse.quote(f'"{m.group("no").split(":", 1)[1]}"')
            court = {'S.D.N.Y.': 'nysd', 'D.D.C.': 'dcd', 'N.D. Cal.': 'cand', 'E.D.N.Y.': 'nyed'}.get(m.group('court'), '')
            rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=sc, cite=(full[cut + 4:] if cut >= 0 else full), type='case', link_status='inferred', why='',
                             links=[dict(label='Docket search', page=None, status='inferred', how='no reporter citation; opens CourtListener search results',
                                         href=f'https://www.courtlistener.com/?type=r&q={q}' + (f'&court={court}' if court else ''))]))
        for m in URLRE.finditer(sc):
            u = m.group(0).rstrip('.,;')
            rows.append(dict(loc=loc, fn=fn, docpage=docpage, prop=prop if cite_sentence else sc, cite=u, raw=u, type='other', link_status='inferred', why='',
                             links=[dict(label=urllib.parse.urlparse(u).netloc, page=None, status='inferred', href=u,
                                         how='web address taken from the filing: not checked, and the page may have changed since it was cited')]))
        for m in NOTCITE.finditer(sc):
            links = []
            term = (m.group('artdoc') or m.group('paradoc') or '').strip()
            if term in RECORD_TERMS:
                ex = RECORD_TERMS[term]
                pin = f'Art. {m.group("art")}' if m.group('art') else f'¶ {m.group("para")}'
                pg, st, how = resolve(('EX', ex), pin)
                if pg: links.append(dict(label=pin, page=pg, status=st, how=how + f' ("{term}" = Ex. {ex})', href=href_of(EXMAP[ex], pg)))
                src = ('EX', ex)
            else:
                src = None
            not_cites.append(dict(loc=loc, fn=fn, docpage=docpage, text=m.group(0), prop=sc, src=src, links=links, ord=len(rows) - 0.5))
        prev = re.sub(r'\s*\[\[FN\d+\]\]', '', sents[i - 1]).strip() if i > 0 else ''
        passage = (prev + ' ' + sc) if (cite_sentence and prev) else sc
        for r in rows[r0:]: r['passage'] = passage
        for r in not_cites[n0:]: r['passage'] = passage
        for n in re.findall(r'\[\[FN(\d+)\]\]', s):
            if n in fns and not in_fn:
                for fd in fn_texts(n): process(fd['text'], loc, n, fd['page'], fn_chain=Chain())

def page_of(g, needle):
    norm = lambda t: re.sub(r'\s+', '', re.sub(r'\[\[FN\d+\]\]', '', t))
    n = norm(needle)[:14]
    for pg, txt in g['chunks']:
        if n and n in norm(txt): return pg
    return g['page']

for g in groups:
    start = len(rows)
    for _n in g.get('head_fns', []):
        for fd in fn_texts(_n): process(fd['text'], g['label'], _n, fd['page'], fn_chain=Chain())
    process(g['text'], g['label'], None, g['page'])
    nstart = getattr(page_of, 'nc', 0)
    for r in rows[start:]:
        if not r['fn']: r['docpage'] = page_of(g, re.sub(r'^(See|see)\s+', '', r['cite'].split('  [=')[0]))
    for nc in not_cites[nstart:]:
        if not nc['fn']: nc['docpage'] = page_of(g, nc['text'])
    page_of.nc = len(not_cites)

def page_index(g):
    if '_pi' not in g:
        chars, pages = [], []
        for pg, txt in g['chunks']:
            for ch in re.sub(r'\[\[FN\d+\]\]', '', txt):
                if not ch.isspace(): chars.append(ch); pages.append(pg)
        g['_pi'] = (''.join(chars), pages)
    return g['_pi']
def page_at(g, passage, offset):
    chars, pages = page_index(g)
    ns = re.sub(r'\s+', '', passage)
    pos = chars.find(ns)
    if pos < 0: pos = chars.find(ns[:40])
    if pos < 0: return None
    k = pos + len(re.sub(r'\s+', '', passage[:offset]))
    return pages[min(k, len(pages) - 1)] if pages else None

# ================================================================ 5b. passages (one block per passage, one sub-row per citation)
def find_span(passage, raw, frm=0):
    raw = raw.split('  [=')[0].strip()
    for cand in (raw, re.sub(r'^(See also|see also|See|see|Cf\.|cf\.|But see|but see)\s+', '', raw)):
        pat = r'\s*'.join(re.escape(w) for w in cand.split())
        for start in (frm, 0):
            m = re.compile(pat).search(passage, start)
            if m: return [m.start(), m.end()]
    return None

blocks, bkey = [], {}
for i, r in enumerate(rows):
    r['ord'] = i
    k = (r['loc'], r['fn'] or '', r['passage'])
    b = bkey.get(k)
    if b is None:
        last = blocks[-1] if blocks else None     # a sentence with inline cites, then its "See …" sentence: one passage
        if last and (last['loc'], last['fn'] or '') == k[:2] and r['passage'].startswith(last['passage']) and len(r['passage']) > len(last['passage']):
            del bkey[(last['loc'], last['fn'] or '', last['passage'])]
            last['passage'] = r['passage']; b = last
        else:
            b = dict(id=f'b{len(blocks)}', loc=r['loc'], fn=r['fn'], docpage=r['docpage'], passage=r['passage'], rows=[])
            blocks.append(b)
        bkey[k] = b
    b['rows'].append(r); r['block'] = b
GBL = {g['label']: g for g in groups}
for b in blocks:
    cur = 0
    for r in b['rows']:
        r['hl'] = find_span(b['passage'], r.get('raw') or r['cite'], cur)
        if r['hl']: cur = r['hl'][1]
    if not b['fn'] and b['loc'] in GBL:
        g = GBL[b['loc']]
        p0 = page_at(g, b['passage'], 0)
        if p0: b['docpage'] = p0
        for r in b['rows']:
            pr = page_at(g, b['passage'], r['hl'][0]) if r['hl'] else None
            if pr: r['docpage'] = pr
nc_blocks = []
for nc in not_cites:
    b = next((b for b in blocks if (b['loc'], b['fn'] or '') == (nc['loc'], nc['fn'] or '') and nc['passage'] in b['passage']), None)
    if b is None:
        b = dict(id=f'n{len(nc_blocks)}', loc=nc['loc'], fn=nc['fn'], docpage=nc['docpage'], passage=nc['passage'], rows=[], ord=nc['ord'])
        nc_blocks.append(b)
    nc['block'] = b; nc['hl'] = find_span(b['passage'], nc['text'])

GROUP_BY_LABEL = {}
for g in groups: GROUP_BY_LABEL.setdefault(g['label'], g)
def style_runs(b):
    cands = ([fns[b['fn']]] + fns[b['fn']].get('more', [])) if (b['fn'] and b['fn'] in fns) else ([] if b['fn'] else [GROUP_BY_LABEL.get(b['loc'])])
    idx = [i for i, ch in enumerate(b['passage']) if not ch.isspace()]
    target = ''.join(b['passage'][i] for i in idx)
    src, pos = None, -1
    for cand in cands:   # a second footnote text with the same number keeps its own styles
        if cand and cand.get('nsc') and cand['nsc'].find(target) >= 0: src, pos = cand, cand['nsc'].find(target); break
    if src is None: return []
    fl = [0] * len(b['passage'])
    for n, i in enumerate(idx): fl[i] = int(src['nsf'][pos + n])
    for i, ch in enumerate(b['passage']):           # a space takes the style shared by its neighbours
        if ch.isspace() and 0 < i < len(fl) - 1: fl[i] = fl[i - 1] & fl[i + 1]
    runs, i = [], 0
    while i < len(fl):
        j = i
        while j < len(fl) and fl[j] == fl[i]: j += 1
        if fl[i]: runs.append([i, j, fl[i]])
        i = j
    return runs
for b in blocks + nc_blocks: b['style'] = style_runs(b)

# ================================================================ 5c. coverage safeguards (a filing read only in part must not pass as complete)
COVER = dict(COVERW.get(DOC, {}))
_np_doc = npages(DOC)
_read = sorted({pg for g in groups for pg, _ in g['chunks']} | {f['page'] for f in fns.values()} | {x['page'] for f in fns.values() for x in f.get('more', [])})
if not rows and not ARGS.allow_no_citations:
    sys.exit(f'STOPPED: no citations were found in {os.path.basename(DOC)} (text read on {len(_read)} of {_np_doc} PDF pages'
             + (f'; reading stopped at "{STOPINFO[DOC][2]}" on PDF p. {STOPINFO[DOC][0]}' if STOPINFO.get(DOC) else '') + '). '
             'This usually means the filing was not read correctly. No table was written. If the filing really cites nothing, '
             'confirm that with the user and run the build again with --allow-no-citations.')
if STOPINFO.get(DOC):
    _sp, _n, _line = STOPINFO[DOC]
    _left = []
    for q in range(_sp + 1, _n + 1):
        _body = [l.strip() for l in page_text(DOC, q).splitlines() if l.strip() and not ECF_HDR.search(l) and not STAMP.match(l.strip())]
        if len(_body) <= 4 and any(re.fullmatch(r'(?i)(?:exhibit|appendix|attachment|annex|tab)\s+[A-Z0-9-]{1,4}', l) for l in _body):
            break   # a slip sheet: what follows is attached to the filing, not part of its body
        if len(re.sub(r'\s', '', ''.join(_body))) > 300 and not re.search(r'(?i)certificate\s+of\s+(?:service|compliance)', ' '.join(_body)): _left.append(q)
    if len(_left) >= 2:
        COVER['stopped early'] = (f'Reading stopped at "{_line}" on PDF p. {_sp} of {_n}; {len(_left)} later pages with text were not read '
                                  f'(PDF pp. {_left[0]}–{_left[-1]}). If the body of the filing continues there, the table is incomplete.')
_cited = {r['docpage'] for r in rows if not r['fn']} | {fns[r['fn']]['page'] for r in rows if r['fn'] and r['fn'] in fns} | {r['docpage'] for r in rows if r['fn']}
_run = []
for q in _read + [None]:
    if q is not None and q not in _cited and (not _run or q == _run[-1] + 1): _run.append(q); continue
    if len(_run) >= 4:
        COVER[f'pp. {_run[0]}-{_run[-1]}'] = f'No citations were found on PDF pp. {_run[0]}–{_run[-1]} ({len(_run)} pages of text in a row): check those pages for missed citations.'
    _run = [q] if (q is not None and q not in _cited) else []

# ================================================================ 6. outputs
doc_name = os.path.splitext(os.path.basename(DOC))[0]
slug = re.sub(r'[^A-Za-z0-9]+', '-', doc_name).strip('-')
counts = {s: sum(1 for r in rows if r['link_status'] == s) for s in ['exact', 'inferred', 'unresolved', 'nolink']}
OUTSTEM = OUT or f'citable-{slug}'
if OUT: os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)

BACKUP = None
if os.path.exists(f'{OUTSTEM}.html') or os.path.exists(f'{OUTSTEM}.csv'):   # keep every earlier version of the table and its CSV (easy to delete)
    import shutil
    bdir = os.path.join(os.path.dirname(os.path.abspath(OUTSTEM)), 'citable-backups')
    os.makedirs(bdir, exist_ok=True)
    _stem = os.path.join(bdir, os.path.basename(OUTSTEM) + '.' + datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
    _k = 1
    while os.path.exists(_stem + ('' if _k == 1 else f'-{_k}') + '.html') or os.path.exists(_stem + ('' if _k == 1 else f'-{_k}') + '.csv'): _k += 1
    _stem += '' if _k == 1 else f'-{_k}'
    for _ext in ('html', 'csv'):
        if os.path.exists(f'{OUTSTEM}.{_ext}'):
            shutil.copy2(f'{OUTSTEM}.{_ext}', f'{_stem}.{_ext}')
            if _ext == 'html': BACKUP = f'{_stem}.html'
with open(f'{OUTSTEM}.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['row', 'location', 'footnote', 'doc_pdf_page', 'type', 'proposition', 'citation', 'target', 'pinpoint', 'target_pdf_page', 'link_status', 'how_resolved', 'href'])
    for i, r in enumerate(rows, 1):
        tgt = f"{label_of(r['src'])} ({path_of(r['src'])})" if r.get('src') else ''
        for l in (r['links'] or [dict(label='', page='', status=r['link_status'], how=r.get('why', ''), href='')]):
            w.writerow([i, r['loc'], r['fn'] or '', r['docpage'], r['type'], r['prop'], r['cite'], tgt, l['label'] or '', l.get('page') or '', l['status'], l['how'], l.get('href') or ''])

def chip(r, l):
    if r['type'] == 'record' and r.get('src'):
        if r['src'][0] == 'EXT': return strip_sig(l['label'] or ''), (f'PDF p. {l["page"]}' if l.get('page') else site_of(l.get('href')))
        return strip_sig(label_of(r['src']).rstrip('.') + (f', {l["label"]}' if l['label'] else '')), (f'PDF p. {abs_page(path_of(r["src"]), l["page"])}' if l.get('page') and r['src'][0] in ('EX', 'DOC') else (f'PDF p. {l["page"]}' if l.get('page') else ''))
    if r['type'] == 'treaty' and l.get('rec'): return l['label'], f'PDF p. {l["page"]}'
    if r['type'] == 'internal': return l['label'], f'PDF p. {l["page"]}'
    return strip_sig(l['label'] or ''), site_of(l.get('href'))

data_rows, seen = [], {}
for r in rows:
    base = f"{r['loc']}|{r['fn'] or ''}|{r['cite']}"
    seen[base] = seen.get(base, 0) + 1
    chips = [dict(zip(('label', 'sub'), chip(r, l)), href=l.get('href'), status=l['status'], how=l['how']) for l in r['links']]
    data_rows.append(dict(id=base + (f"|{seen[base]}" if seen[base] > 1 else ''), group=r['loc'], fn=r['fn'], docpage=r['docpage'],
                          docHref=urllib.parse.quote(DOC) + f"#page={r['docpage']}", prop=r['prop'], cite=r['cite'], type=r['type'],
                          viaId=bool(r.get('via_id')), chips=chips, linkStatus=r['link_status'], why=r.get('why', ''), ord=r['ord'], block=r['block']['id'], hl=r['hl']))
nc_rows = []
for k, nc in enumerate(not_cites):
    chips = [dict(label=(label_of(nc['src']).rstrip('.') + ', ' + l['label']), sub=f'PDF p. {l["page"]}', href=l['href'], status=l['status'], how=l['how']) for l in nc['links']]
    _base = f"nc|{nc['loc']}|{nc['fn'] or ''}|{nc['text']}"
    seen[_base] = seen.get(_base, 0) + 1
    nc_rows.append(dict(id=_base + (f"|{seen[_base]}" if seen[_base] > 1 else ''), group=nc['loc'], fn=nc['fn'], docpage=nc['docpage'],
                        docHref=urllib.parse.quote(DOC) + f"#page={nc['docpage']}", prop=nc['prop'], cite=nc['text'], type='record' if nc['src'] else 'other',
                        viaId=False, chips=chips, linkStatus=('exact' if chips and all(c['status'] == 'exact' for c in chips) else ('inferred' if chips else 'unresolved')),
                        why='' if chips else 'No source link: reference only', ord=nc['ord'], promoted=True, block=nc['block']['id'], hl=nc['hl']))
bl = lambda b, o: dict(id=b['id'], group=b['loc'], fn=b['fn'], docpage=b['docpage'], docHref=urllib.parse.quote(DOC) + f"#page={b['docpage']}", passage=b['passage'], ord=o, style=b.get('style', []))
blocks_out = [bl(b, b['rows'][0]['ord']) for b in blocks] + [bl(b, b['ord']) for b in nc_blocks]
REL = os.path.relpath(os.getcwd(), os.path.dirname(os.path.abspath(OUTSTEM)))
if REL != '.':   # --out elsewhere: local links must still reach the case folder
    _fx = lambda h: h if (not h or re.match(r'[a-z]+:', h)) else urllib.parse.quote(REL) + '/' + h
    for r in data_rows + nc_rows:
        r['docHref'] = _fx(r['docHref'])
        for c in r['chips']: c['href'] = _fx(c.get('href'))
    for b in blocks_out: b['docHref'] = _fx(b['docHref'])
# ================================================================ 7. carry reviewer work forward from an earlier table
import difflib
def _json_script(htm, sid):
    m = re.search(r'<script id="' + sid + r'" type="application/json">(.*?)</script>', htm, re.S)
    return json.loads(m.group(1).replace('<\\/', '</')) if m and m.group(1).strip() else {}
NORM = lambda t: re.sub(r'[\W_]+', '', (t or '').lower())
def prop_key(passage, spans):
    out, pos = '', 0
    for s0, e0 in sorted(sp for sp in spans if sp):
        if s0 >= pos: out += passage[pos:s0]; pos = e0
    return NORM(out + passage[pos:])
def cite_key(c): return NORM((c or '').split('  [=')[0])
def target_key(r, filing):
    """Where a row's links lead: web addresses as they are; local files by file name and page (so --out does not matter);
    links into the filing itself as "<filing>" (a revised draft has a new file name)."""
    out = []
    for c in r.get('chips') or []:
        h = c.get('href') or ''
        if not h or re.match(r'[a-z]+:', h): out.append(h); continue
        path, _, frag = urllib.parse.unquote(h).partition('#')
        base = os.path.basename(path)
        out.append(('<filing>' if base == filing else base) + ('#' + frag if frag else ''))
    return out
def target_label(r):
    return '; '.join(f"{c.get('label') or ''} → {urllib.parse.unquote((c.get('href') or '').split('/')[-1]) or 'no link'}" for c in r.get('chips') or [])

init_state, removed, carry = {}, [], None
if not PREV and os.path.exists(f'{OUTSTEM}.html'):     # rebuilding over an existing table: never discard its saved work
    PREV = os.path.abspath(f'{OUTSTEM}.html')
if PREV:
    old = open(PREV).read()
    ometa, orows, ostate = _json_script(old, 'citable-meta'), _json_script(old, 'citable-rows'), _json_script(old, 'citable-state')
    if not ometa.get('blocks'): PREV = None                  # table from an older citable version: nothing to match against
if PREV:
    oblocks = {b['id']: b for b in ometa.get('blocks', [])}
    ospans = {}
    for r in orows: ospans.setdefault(r['block'], []).append(r.get('hl'))
    O = [dict(r=r, st=(ostate.get('rows') or {}).get(r['id']), passage=oblocks[r['block']]['passage'],
              pk=prop_key(oblocks[r['block']]['passage'], ospans[r['block']]), ck=cite_key(r['cite'])) for r in orows if r['block'] in oblocks]
    nspans = {}
    for r in data_rows: nspans.setdefault(r['block'], []).append(r.get('hl'))
    bpass = {b['id']: b['passage'] for b in blocks_out}  # (all blocks, incl. reference-only)
    N = [dict(r=r, passage=bpass[r['block']], pk=prop_key(bpass[r['block']], nspans[r['block']]), ck=cite_key(r['cite'])) for r in data_rows]
    used, now = set(), int(datetime.datetime.now().timestamp() * 1000)
    def take(n, o, kind):
        used.add(id(o)); n['o'] = o; n['kind'] = kind
    for n in N:                                   # A. same proposition, same citation
        o = next((o for o in O if id(o) not in used and o['pk'] == n['pk'] and o['ck'] == n['ck']), None)
        if o: take(n, o, 'unchanged')
    for n in N:                                   # B. same citation, proposition reworded (same ¶, or similar wording)
        if 'o' in n: continue
        cands = [o for o in O if id(o) not in used and o['ck'] == n['ck']]
        score = lambda o: difflib.SequenceMatcher(None, o['pk'], n['pk']).ratio() + (0.5 if o['r']['group'] == n['r']['group'] else 0)
        cands = [o for o in cands if score(o) >= 0.6]
        if cands: take(n, max(cands, key=score), 'reworded')
    for n in N:                                   # C. same proposition, citation changed
        if 'o' in n: continue
        score = lambda o: difflib.SequenceMatcher(None, o['pk'], n['pk']).ratio() + (0.2 if o['r']['group'] == n['r']['group'] else 0)
        cands = [o for o in O if id(o) not in used and score(o) >= 0.95]
        if cands: take(n, max(cands, key=lambda o: (score(o), difflib.SequenceMatcher(None, o['ck'], n['ck']).ratio())), 'changed')
    for n in N:
        r, o = n['r'], n.get('o')
        kind = n.get('kind', 'new')
        st = (o or {}).get('st') or {}
        if kind == 'unchanged' and 'chips' in o['r'] and target_key(o['r'], os.path.basename(ometa.get('docFile') or '')) != target_key(r, os.path.basename(DOC)):
            kind = n['kind'] = 'relinked'           # same text, but the map now sends the citation somewhere else
        if kind == 'unchanged':
            if st: init_state[r['id']] = dict(cc=st.get('cc', 'check pending'), note=st.get('note', ''), t=now)
            continue
        init_state[r['id']] = dict(cc='check pending', note=st.get('note', ''), t=now)
        if kind == 'reworded':
            r['change'] = dict(kind='reworded', was=o['passage'], wasStatus=st.get('cc', 'check pending'),
                               msg='Proposition reworded since the last review; status reset')
        elif kind == 'relinked':
            r['change'] = dict(kind='relinked', was=target_label(o['r']), wasStatus=st.get('cc', 'check pending'),
                               msg='Link target changed since the last review (the map changed); status reset')
        elif kind == 'changed':
            r['change'] = dict(kind='changed', was=o['r']['cite'].split('  [=')[0], wasStatus=st.get('cc', 'check pending'),
                               msg='Citation changed since the last review; status reset')
        else:
            r['change'] = dict(kind='new', msg='New since the last review')
    for o in O:
        if id(o) not in used:
            st = o['st'] or {}
            removed.append(dict(group=o['r']['group'], fn=o['r'].get('fn'), passage=o['passage'], cite=o['r']['cite'].split('  [=')[0],
                                cc=st.get('cc', 'check pending'), note=st.get('note', '')))
    promoted = {}
    onc = {n['id']: n for n in ometa.get('notCites', [])}
    for k, v in (ostate.get('promoted') or {}).items():
        if not v.get('on') or k not in onc: continue
        o = onc[k]; opass = oblocks.get(o['block'], {}).get('passage', '')
        cands = [n for n in nc_rows if NORM(n['cite']) == NORM(o['cite'])]
        if cands:
            best = max(cands, key=lambda n: difflib.SequenceMatcher(None, NORM(bpass.get(n['block'], '')), NORM(opass)).ratio())
            promoted[best['id']] = dict(on=True, t=now)
    carry = dict(previous=os.path.basename(PREV), previousDoc=ometa.get('docFile'), previousBuilt=ometa.get('builtAt') or ometa.get('generated'), date=datetime.date.today().isoformat(),
                 counts={k: sum(1 for n in N if n.get('kind', 'new') == k) for k in ['unchanged', 'relinked', 'reworded', 'changed', 'new']} | {'removed': len(removed)},
                 hadSaved=bool(ostate.get('savedAt') or ostate.get('carriedAt')))   # carried statuses count as saved review work
    init_state = dict(rows=init_state, promoted=promoted, carriedAt=now)
    if not carry['hadSaved']:
        carry, init_state = None, {}                         # the earlier table was never saved: no review work to carry or compare
        removed = []
        for r in data_rows: r.pop('change', None)

meta = dict(doc=doc_name, docFile=DOC, matter=os.path.basename(os.path.abspath(CASE)), slug=slug,
            generated=datetime.date.today().isoformat(), counts=counts, notCites=nc_rows, blocks=blocks_out, carry=carry, removed=removed,
            builtAt=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'))
js = lambda o: json.dumps(o, ensure_ascii=False).replace('</', '<\\/')
tpl = open(os.path.join(SCRIPT_DIR, 'template.html')).read()
page = tpl.replace('__TITLE__', html.escape(f'citable — {doc_name}')).replace('__META__', js(meta)).replace('__ROWS__', js(data_rows))
if init_state:
    page = page.replace('<script id="citable-state" type="application/json">{}</script>', '<script id="citable-state" type="application/json">' + js(init_state) + '</script>')
open(f'{OUTSTEM}.html', 'w').write(page)
if BACKUP: print('BACKUP: the earlier table was copied to', os.path.relpath(BACKUP))
if COVER: print('COVERAGE WARNINGS (tell the user; build log only, not shown in the table):', json.dumps(COVER, ensure_ascii=False))
if WARN: print('FORMAT WARNINGS (build log only, not shown in the table):', json.dumps(WARN, ensure_ascii=False))
_alltext = ' '.join([g['text'] for g in groups] + [f['text'] for f in fns.values()])
_missed = []
for a in AUTH:   # an authority in the map whose volume and first page appear in this filing, but which no row reads
    mm = re.match(r'(\d+)\s+(.+?)\s+(\d+)$', a['cite'])
    if mm and id(a) not in AUTH_USED and re.search(r'\b' + mm.group(1) + r'\s+[A-Za-z][^\d;]{0,20}?\s' + mm.group(3) + r'\b', _alltext):
        _missed.append(a['cite'] + (f" ({a['short']})" if a.get('short') else ''))
if _missed: print('POSSIBLY MISSED (in the map and in the text, but not read as a citation; check):', '; '.join(_missed))
if carry: print('CARRY:', json.dumps(carry), 'REMOVED:', [(x['group'], x['cite']) for x in removed])

print(json.dumps(dict(rows=len(rows), counts=counts), ensure_ascii=False))
for i, r in enumerate(rows, 1):
    print(f"{i:>3} {r['loc']}{' n.' + r['fn'] if r['fn'] else ''} p{r['docpage']} | {r['cite']} | " +
          '; '.join(f"{l['label']}->{l.get('page')}:{l['status']}" for l in r['links']) + (f" | {r['why']}" if r.get('why') else ''))
print('NOT CITES:', [(n['loc'], n['fn'], n['docpage'], n['text'], [(l['label'], l['page']) for l in n['links']]) for n in not_cites])
