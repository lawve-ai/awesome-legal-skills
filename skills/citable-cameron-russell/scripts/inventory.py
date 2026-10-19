#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Cameron Russell (ccrnyc). See LICENSE.
"""citable — inventory a case folder so the map can be drafted.

Usage: inventory.py <case_folder>
For every PDF: pages, text layer, ECF stamp, likely role, how paragraph numbers can be found
(margin images vs text), and exhibit labels mentioned ("attached … as Exhibit X").
Prints JSON. Read-only."""
import sys, os, re, json, subprocess, collections
import pdfplumber

case = sys.argv[1]
out = []
def stamps(p):
    """Court filing stamps on each page: other courts' ECF documents and NYSCEF document numbers -> first page."""
    raw = subprocess.run(['pdftotext', '-raw', p, '-'], capture_output=True, text=True).stdout.split('\f')
    lay = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout.split('\f')
    seen = {}
    for pno, (tr, tl) in enumerate(zip(raw, lay), 1):
        for mm in re.finditer(r'(\d:\d{2}-[a-z]{2}-\d+)[\w-]*\s*Document\s*(?:#\s*:?\s*)?(\d+(?:-\d+)?)\b', tr):
            seen.setdefault(f'{mm.group(1)} Doc {mm.group(2)}', pno)
        mm = re.search(r'NYSCEF DOC\. NO\.\s*(?:Case\s*)?\n?\s*(?:[A-Z ]+?\s)?(\d{1,4})\s', tl)
        if mm: seen.setdefault(f'NYSCEF {mm.group(1)}', pno)
    return seen
paths = sorted(os.path.relpath(os.path.join(r, f), case) for r, _, fs in os.walk(case) for f in fs if f.lower().endswith('.pdf'))
for f in paths:
    p = os.path.join(case, f)
    try:
        with pdfplumber.open(p) as pdf:
            n = len(pdf.pages)
            imgs = sum(len([im for im in pg.images if im['x0'] < pg.width * .25 and (im['x1'] - im['x0']) < 60]) for pg in pdf.pages)
            first = pdf.pages[0].extract_text() or ''
    except Exception as e:
        out.append(dict(file=f, error=str(e))); continue
    txt = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
    pages = txt.split('\f')
    empty = [i + 1 for i, t in enumerate(pages[:n]) if len(re.sub(r'Case:?\s+\S+\s+Document.*', '', t).strip()) < 40]
    markers = [int(m) for m in re.findall(r'(?m)^\s{0,14}(\d{1,4})\.\s+[A-Z“"(]', txt)]
    stamp = re.search(r'Case:?\s+(\S+)\s+Document\s+(?:#\s*:?\s*)?(\S+)', txt)
    role = ('brief' if re.search(r'MEMORANDUM|POINTS AND AUTHORITIES|BRIEF', first) else
            'declaration' if re.search(r'DECLARATION|AFFIDAVIT', first) else
            'petition/complaint' if re.search(r'PETITION|COMPLAINT', first) else 'exhibit/other')
    out.append(dict(file=f, pages=n, empty_pages=empty[:20], ecf=(stamp.group(1) + ' Doc ' + stamp.group(2)) if stamp else None,
                    role_guess=role, margin_para_images=imgs, text_para_markers=len(markers), max_marker=max(markers) if markers else None,
                    exhibit_refs=sorted(set(re.findall(r'as Exhibit ([A-Z]{1,2}|\d{1,3})', txt))), stamps_first_page=stamps(p)))
print(json.dumps(out, indent=1))
