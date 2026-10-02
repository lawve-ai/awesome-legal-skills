---
name: "uk-citation-verification-matei-clej"
description: "Verifies UK case-law citations, pinpoint references and quotations against the official public register — The National Archives' Find Case Law — and statutory references against legislation.gov.uk, before a document that cites them is relied on, served or filed. Every check returns a graded verdict: VERIFIED, MISMATCH (the citation resolves to a different case — the classic AI miscitation), NOT ON REGISTER, OUTSIDE COVERAGE (the register cannot answer — absence proves nothing), or UNCHECKABLE (a law-report citation). The grading exists because there are two ways to get this wrong: citing a case that does not exist, and accusing a real case of not existing. Use when asked to check citations, verify a case exists, confirm a quotation is verbatim, check a pinpoint paragraph, audit a draft's authorities, screen a document for hallucinated cases, or check a statutory provision is in force. Not a substitute for reading the judgment: existence is not authority."
argument-hint: "[citation or file] [--name \"Case Name\"] [--para N] [--quote \"...\"]"
metadata:
  author: "Matei Clej"
  license: "mit"
  version: "2026-08-27"
---

# UK citation verification — against the official register

1. Establish what is being checked: a single citation, a quotation, or a whole
   document's authorities.
2. Run the check (`scripts/ukcite.py`), or work the register by hand where no
   shell is available.
3. Report the **graded verdict** for each citation — never collapse the grades
   into "real" and "fake".
4. For anything not VERIFIED, say exactly what the register could and could not
   answer, and what the user must still do.
5. Never treat a VERIFIED existence check as verification of the proposition
   the case is cited for. That requires reading the judgment.

---

## What this is for

In *Ayinde, R (on the application of) v The London Borough of Haringey* [2025]
EWHC 1383 (Admin), the Divisional Court dealt with lawyers who had put
AI-generated material before courts containing "false information (typically a
fake citation or quotation)", and said plainly that the duty to check is the
lawyer's and is not discharged by trusting the tool. Regulators in several
jurisdictions have since said the same.

This skill makes the checking mechanical where it can be mechanical. It
verifies citations against the **official public register of judgments for
England and Wales** — The National Archives' Find Case Law — and statutory
references against **legislation.gov.uk**. Both sources are operated by The
National Archives; nothing else is consulted, so every answer is traceable to
the official record.

**It is not for** finding authorities on a topic (use a research service), and
it is **never** a substitute for reading the judgment cited.

---

## The verdicts — what each one proves, and what it does not

There are two ways to fail at citation checking. The obvious one is letting a
fabricated case through. The less obvious one — and the one careless tooling
commits constantly — is declaring a **real** case fabricated because one
database does not hold it. The graded verdicts exist to keep those apart:

**✔ VERIFIED** — the citation resolves on the register; where a case name,
pinpoint or quotation was supplied, it matched. This proves the case exists and
says what was quoted. It does **not** prove the case is authority for the
proposition it is cited for, that it is still good law, or that it has not been
distinguished out of relevance. That is reading, not checking.

**✖ MISMATCH** — the citation resolves, but to a **different case**, a wrong
paragraph, or a quotation that is not verbatim. This is the most dangerous
failure mode in AI-assisted drafting: a real citation stitched to the wrong
case name, a tidied "quotation" that no longer matches the source. The verdict
prints what the register actually holds so the error can be repaired rather
than merely deleted.

**✖ NOT ON REGISTER** — no record, though the court and year fall inside the
register's stated coverage. Treat the citation as **unsafe to rely on until
the judgment is located somewhere** — but do not report it as fabricated on
this evidence alone. The register's own caveat is that coverage within a range
is incomplete: not every judgment is sent for publication. Cross-check by
party name (`find`), then on a subscription service, before any conclusion is
stated.

**◌ OUTSIDE COVERAGE** — the register cannot answer. House of Lords judgments
are not on Find Case Law at all; most courts' holdings begin in 2001–2003 and
several tribunals much later. For these citations the check is **not run and no
inference arises**. A tool that returns "not found" for *Kakis v Cyprus* has
not found a hallucination; it has found its own boundary.

**◌ UNCHECKABLE** — a law-report citation (`[1978] 1 WLR 779`). The register
resolves neutral citations only. Find the neutral citation by name where one
exists (post-2001), or verify in the printed series. Says nothing about whether
the case is real.

---

## Running it

The checker ships in this package; Python 3.9+, standard library only, nothing
to install:

```bash
# One citation, with everything checkable checked
python3 scripts/ukcite.py check "[2015] EWHC 1274 (Admin)" \
    --name "Polish Judicial Authorities v Celinski" \
    --para 13 \
    --quote "the public interest in ensuring that extradition arrangements are honoured is very high"

# Every citation in a draft — .docx is read natively; plain text and
# markdown too. A PDF is refused with instructions, never scanned as noise:
# a verification tool must not return a false clean bill because it could
# not read the file.
python3 scripts/ukcite.py scan skeleton.docx

# Find a neutral citation from a case name (party-name search first)
python3 scripts/ukcite.py find "Celinski"

# A statutory provision — existence, current version, unapplied amendments
python3 scripts/ukcite.py statute "Extradition Act 2003" --section 2
```

Exit code 0 means everything checked came back VERIFIED; 1 means something
needs attention. Every run writes a dated report to
`~/.cache/uk-citation-verification/` so that months later the user can say
what was checked, when, and what the register answered.

**Reading the output for the user.** Report MISMATCH and NOT ON REGISTER
prominently, with the register's actual holding alongside the claimed one.
Report OUTSIDE COVERAGE and UNCHECKABLE as *unverified, with the reason* —
never in the same breath as the failures. A quotation flagged NEAR MISS is
corrected from the source text the tool prints, not from memory.

**Without a shell** — in an assistant that cannot run Python — do not pretend
to check. A neutral citation maps to a register URL directly: `[2024] UKSC 12`
→ `https://caselaw.nationalarchives.gov.uk/uksc/2024/12`; `[2019] EWHC 100
(Admin)` → `.../ewhc/admin/2019/100`. Open it, confirm the case name and date,
and read the passage cited. For statutes, open
`https://www.legislation.gov.uk/ukpga/<year>/<chapter>/section/<n>` and check
the version notes. Consult `reference/coverage.md` before drawing anything
from a miss, and say plainly which citations were checked by hand and which
were not checked at all.

---

## Coverage — where the register can and cannot answer

`reference/coverage.md` holds the full table as stated by Find Case Law,
with the date it was read. The three traps, in descending order of frequency:

1. **The House of Lords is not there.** UKSC holdings begin 2009. A UKHL
   citation can never be verified — or impugned — from this register.
2. **Most courts begin 2001–2003; tribunals later.** EAT from 2021, UT (IAC)
   from 2007, UT (AAC) from 2011, Family Court from 2014. A miss on an early
   citation is a boundary, not a finding.
3. **Coverage within range is incomplete.** The register's own words: not
   every judgment is sent for publication. This is why NOT ON REGISTER is
   phrased as "unsafe until located", never "fabricated".

Where a verdict turns on a boundary, re-check the live page — holdings grow:
<https://caselaw.nationalarchives.gov.uk/courts-and-tribunals>.

**Why the register only, when other open sources exist.** This is a design
rule, not an omission. A verdict is only worth grading if resolution is
deterministic: Find Case Law resolves a neutral citation to a document, so a
miss *means* something. The open tribunal archives (gov.uk's Employment
Tribunal and EAT collections, the tribunals-decisions service) are search
engines, not citation-addressable registers — an automated miss there would
mean nothing, and folding them in would quietly weaken every verdict. BAILII
is excluded on different grounds: it is a mirror rather than the official
record, and its robots.txt disallows automated access to the very directories
holding England and Wales judgments. So where the register cannot answer, the
verdict *points* at the correct official archive for that citation type and
the user checks it by hand — the tool never pretends a search-engine miss is
a finding.

---

## What this sends, and where

The tool contacts exactly two hosts, both operated by The National Archives:
`caselaw.nationalarchives.gov.uk` and `www.legislation.gov.uk`. It sends the
citation, name or search terms being checked and nothing else. There is no
telemetry, no analytics, no credential, and no callback to the author. Reports
are written only to the user's own machine. It identifies itself with an
honest User-Agent (`ukcite/1.0 …`), throttles to about one request per second
— far inside Find Case Law's published limit of 1,000 requests per rolling
five minutes — and spaces legislation.gov.uk requests five seconds apart,
honouring that site's robots.txt crawl-delay even though a targeted lookup is
not a crawl. It stops rather than retries if rate-limited. It indexes nothing
and follows no links, so the register's `noindex,nofollow` directives are
satisfied by design; fetched content is parsed as data and never executed.

## Licensing footing — and the one prohibited use

Find Case Law records are used under the **Open Justice Licence v2.0**, which
expressly permits reading and downloading judgments one at a time as you need
them, using the search, and citing them in your work, including commercially.
Legislation is used under the Open Government Licence. Acknowledge the source
when output from this tool reaches a published document — the verdicts carry
the register URLs for exactly that purpose.

What the Open Justice Licence does **not** permit is computational analysis:
programmatic searching **in bulk** across the records to identify, extract or
enrich their contents. This tool checks the citations in the user's document,
one at a time, as they need them — the expressly permitted use. **Do not**
loop it across a corpus, use it to harvest judgment text, or build a dataset
with it. If a user asks for that, decline and point them to The National
Archives' computational-analysis licence, which is free to apply for.

## Files

| Path | What it holds |
|---|---|
| `scripts/ukcite.py` | The checker — citation parsing, register lookup, identity/pinpoint/quote verification, graded verdicts, dated reports |
| `reference/coverage.md` | The register's stated coverage per court, with the date it was read and where to re-check |

The author's write-up of the verification-duty engineering this skill grew out
of: <https://mateiclej.substack.com/p/ayinde-proofing-engineering-the-verification>.
