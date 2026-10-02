# uk-citation-verification

An agent skill that verifies UK case-law citations, pinpoints and quotations
against the official public register — The National Archives' [Find Case
Law](https://caselaw.nationalarchives.gov.uk/) — and statutory references
against [legislation.gov.uk](https://www.legislation.gov.uk/), before a
document that cites them is relied on, served or filed.

*Built by [Matei Clej](https://mateiclej.substack.com), a practising
extradition barrister in London, for use in live casework.*

## Why graded verdicts

There are two ways to get citation checking wrong: letting a fabricated case
through, and declaring a **real** case fabricated because one database does
not hold it. So every check returns one of five verdicts — **VERIFIED**,
**MISMATCH** (the citation resolves to a different case, or the quotation is
not verbatim), **NOT ON REGISTER**, **OUTSIDE COVERAGE** (the register cannot
answer; absence proves nothing), **UNCHECKABLE** (a law-report citation) —
and the skill's instructions forbid collapsing them into "real" and "fake".

## What it checks

- **Existence** — the neutral citation resolves on the official register
- **Identity** — the register's case name matches the name in the document
  (catches the classic miscitation: a real citation stitched to the wrong case)
- **Pinpoint** — the cited paragraph exists in the judgment
- **Quotation** — the quoted passage appears verbatim; a near miss prints the
  source text so the quote is corrected from the source, not from memory
- **Statutes** — the provision exists, which revised version was retrieved,
  and whether enacted amendments are not yet applied to the text

## Quick start

Python 3.9+, standard library only — nothing to install.

```bash
python3 scripts/ukcite.py scan skeleton.docx   # .docx read natively; PDFs refused honestly
python3 scripts/ukcite.py check "[2015] EWHC 1274 (Admin)" --name "Celinski" --para 13
python3 scripts/ukcite.py find "Celinski"
python3 scripts/ukcite.py statute "Extradition Act 2003" --section 2
```

Every run writes a dated report to `~/.cache/uk-citation-verification/`.

## Footing

The tool contacts exactly two hosts, both operated by The National Archives,
sends only the citation being checked, and throttles to ~1 request/second.
Records are used under the Open Justice Licence v2.0 — one-at-a-time
retrieval, the expressly permitted use. It must not be looped across a corpus:
bulk computational analysis needs The National Archives' separate (free)
licence. Software is MIT licensed.
