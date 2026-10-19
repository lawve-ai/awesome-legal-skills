#!/usr/bin/env python3
"""Read official-style extracted text; print judicial turns and approximate words.

Requires a PROCEEDINGS marker and ORAL/REBUTTAL ARGUMENT OF headings.
Text only: no PDF conversion. Counts include administrative remarks. Verify every
section, speaker, and extraction boundary manually before reporting results.
"""
import argparse
import collections
from pathlib import Path
import re

START = re.compile(r'^P\s*R\s*O\s*C\s*E\s*E\s*D\s*I\s*N\s*G\s*S\s*[:.]?$')
SECTION = re.compile(r'^(ORAL|REBUTTAL) ARGUMENT OF(?:\s+(.*))?$')
SPEAKER = re.compile(r"^((?:CHIEF JUSTICE|JUSTICE|MR\.|MS\.|MRS\.|GENERAL)\s+[A-Za-z][A-Za-z'’\-. ]*?):\s*(.*)$")
NOISE = re.compile(r'^(?:Heritage Reporting Corporation|Official(?: - Subject to Final Review)?|\d{1,4})$')


def parse(text):
    lines = [re.sub(r'^\s*\d{1,2}(?: {2,}|\t+)', '', line).strip()
             for line in text.splitlines()]
    start = next((i for i, line in enumerate(lines) if START.fullmatch(line)), None)
    if start is None:
        raise ValueError('No PROCEEDINGS marker; use manual analysis rather than risk counting the index.')
    sections = []
    current = None
    speaker = None
    in_header = False
    for line in lines[start + 1:]:
        if not line or NOISE.fullmatch(line):
            continue
        if line.startswith('(Whereupon'):
            break
        if line.startswith('('):
            continue
        heading = SECTION.fullmatch(line)
        if heading:
            current = {'kind': heading[1], 'heading': heading[2] or '',
                       'tally': collections.defaultdict(lambda: [0, 0]),
                       'speakers': set()}
            sections.append(current)
            speaker, in_header = None, True
            continue
        match = SPEAKER.fullmatch(line)
        if current is None:
            continue
        if in_header and not match:
            current['heading'] = (current['heading'] + ' ' + line).strip()
            continue
        in_header = False
        if match:
            speaker, line = match[1], match[2]
            current['speakers'].add(speaker)
            if speaker.startswith(('JUSTICE ', 'CHIEF JUSTICE ')):
                current['tally'][speaker][0] += 1
        elif re.match(r'^[A-Z][A-Z .\-]+:', line):
            raise ValueError('Unrecognized speaker label: ' + line.split(':')[0])
        if speaker and speaker.startswith(('JUSTICE ', 'CHIEF JUSTICE ')):
            current['tally'][speaker][1] += len(line.split())
    if not sections:
        raise ValueError('No argument headings after PROCEEDINGS; use manual analysis.')
    if any(not section['speakers'] or not section['heading'] for section in sections):
        raise ValueError('An argument section lacks a heading name or recognized speech; inspect extraction.')
    return sections


def render(sections):
    output = ['# Raw judicial speaking tally',
              'Turns are speaking turns, not questions. Words are approximate.',
              'Administrative remarks are included. Verify all sections against the transcript.',
              'Speech before the first argument heading is excluded. Missing rows do not establish absence.']
    for number, section in enumerate(sections, 1):
        heading = section['heading'].replace('|', '/')
        output += [f'\n## {number}. {section["kind"]}: {heading}',
                   '| Justice | Turns | Words |', '|---|---:|---:|']
        tally = section['tally']
        for justice, (turns, words) in sorted(tally.items(), key=lambda pair: (-pair[1][1], pair[0])):
            output.append(f'| {justice} | {turns} | {words} |')
        output.append(f'| TOTAL | {sum(v[0] for v in tally.values())} | {sum(v[1] for v in tally.values())} |')
        if not tally:
            output.append('No judicial speech detected in this section; verify before reporting zero.')
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcript', type=Path, help='UTF-8 extracted text, with original line breaks')
    args = parser.parse_args()
    try:
        data = args.transcript.read_bytes()
        if data.startswith(b'%PDF') or args.transcript.suffix.lower() == '.pdf':
            parser.error('Text only. Extract the PDF with available host facilities first.')
        print(render(parse(data.decode('utf-8-sig'))))
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
