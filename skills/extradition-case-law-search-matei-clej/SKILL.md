---
name: "extradition-case-law-search-matei-clej"
description: "Searches the domestic courts of 122 jurisdictions — 153 databases, 49 automated — for extradition and arrest-warrant surrender decisions, each in its own language and vocabulary. Answers the question no commercial database does: how are OTHER executing states treating this requesting state, or this ground? Searching by requesting state localises its name per jurisdiction (AE becomes 'Emiratele Arabe Unite' in Romania, 'Emirati Arabi Uniti' in Italy), so the sweep finds what those courts actually wrote. Every hit passes a relevance gate; every search leaves a dated report, so the research is reconstructable months later. Use when asked what foreign courts have said about surrender to a given state, whether any European court has refused extradition on prison conditions, assurances or Article 3, for comparative extradition research, or to build a foreign-authority section of an extradition argument. Not for domestic case law of the user's own jurisdiction, and never a substitute for reading the judgment."
argument-hint: "[requesting-state ISO] [--in NL,DE,IE] [--since YYYY-MM-DD]"
metadata:
  author: "Matei Clej"
  license: "mit"
  version: "2026-08-25"
---

# Foreign extradition case-law search

1. Establish what is actually being asked: which **requesting state**, which **executing states**, which **ground**.
2. Name the executing states. Never sweep everything by default — see *Scope it*.
3. Run the search (`scripts/xsearch.py`), or work the coverage map by hand where no shell is available.
4. Report hits as **leads with links**, grouped by jurisdiction, never as holdings.
5. Tell the user what did *not* answer, and what a nil return does and does not mean.

---

## What this is for

A recurring problem in extradition defence and prosecution is showing how *other*
executing states treat a given requesting state or a given ground: Rechtbank
Amsterdam on prison conditions, German OLG and Bundesverfassungsgericht decisions
on assurances, Irish High Court surrender judgments, Italian Cassazione, Polish
SAOS. That material sits in a hundred-plus national databases, each with its own
interface, language and vocabulary, and no commercial service searches them
together.

This skill drives an open-source engine — 153 adapters, MIT licensed — that does.

**It is not for** the domestic case law of the user's own jurisdiction (use a
national database or a commercial service), and it does not read, translate, or
interpret the judgments it finds.

---

## The rule that governs every output

**Every result is a lead, never an authority.** The engine reports that a
judgment exists and that its metadata matched extradition vocabulary. It does
not know what the judgment holds. Before anything from here reaches advice, a
pleading or a court:

1. **Open the decision and read the passage.** In the original language, with a
   translation if it will be relied on. A machine-matched title is not a ratio.
2. **Treat the relevance gate as sorting, not judgment.** `on_topic` means
   extradition vocabulary appeared in the title or snippet. It is not a finding
   that the case is about the user's point.
3. **Keep "failed" and "nil" apart.** A database that errored was unreachable
   that run: its material is *unsearched*, not absent. The report separates
   them; so must the answer.
4. **Read a genuine nil return carefully.** Publication practice varies
   enormously — in several states the surrender decision is never published at
   all. "Nothing found" is not "no such decisions", and must never be reported
   as though it were.
5. **Say what was not reached.** Flag anything unverified rather than presenting
   it with more confidence than it has earned. The user remains professionally
   responsible for every authority they cite; this skill never discharges that.

---

## Running it

One-off install, then search:

```bash
python3 scripts/xsearch.py install

# How are executing states treating Romania?
python3 scripts/xsearch.py search --issuing-state RO --countries NL,DE,IE

# A ground, in a state's own language, in its own courts
python3 scripts/xsearch.py search "detentie omstandigheden" --countries NL

# Non-arrest-warrant vocabulary — third-state extradition
python3 scripts/xsearch.py search --issuing-state TR --mode extradition

# Narrowed by date
python3 scripts/xsearch.py search --issuing-state PL --countries NL,DE --since 2023-01-01
```

Supporting commands: `preview AE --countries RO,IT,PL` (what a requesting state
is actually searched as), `sources --countries NL,DE` (which databases exist and
their status), `runs` (past searches), `show <run-id>` (a past report in full).

Options: `--mode both|eaw|extradition`, `--since` / `--until`, `--limit N` per
database, `--top N` printed, `--include-manual`, `--no-expand`.

**Without a shell** — in an assistant that cannot run Python — do not pretend to
sweep. Load `reference/jurisdictions.md`, identify the databases that cover the
executing states in question, and work them one at a time with whatever browsing
is available, using the localised vocabulary from `preview`'s logic: the
requesting state's name in that jurisdiction's language, plus that
jurisdiction's extradition terms. Say plainly that this is a partial search.

---

## How to search well

**Scope it.** An unconstrained sweep hits every database, and one source
(`pl-saos`, Poland) takes about 98 seconds on its own while every other adapter
answers in under five. Name the executing states whose practice is actually
needed. If Poland is wanted, warn the user about the wait rather than letting a
90-second silence read as a hang.

**Search by requesting state, not by keyword, when the question is about a
state.** `--issuing-state RO` localises "Romania" into each jurisdiction's
language and combines it with that jurisdiction's extradition vocabulary in the
source's own query syntax. A free-text search for "Romania" finds far less. Run
`preview` first to show the user what will be asked — and if it warns that
`babel` is missing, stop and install it: without it, localisation silently
degrades and every requesting-state search narrows without saying so.

**Read the arithmetic, not just the hits.** "19 results — 8 on point, 10 off
topic" means the sweep worked and that source is noisy. "20 results, 0 on point"
usually means the database sorted by date and stemmed loosely, and the run
established nothing: widen `--limit`, or go at it by free text in the local
language.

**Watch for deep-link sources.** 104 of the 153 databases cannot be automated.
Normally they are skipped. But if *every* database selected is deep-link only —
several jurisdictions have nothing else — they are returned anyway, and a "hit"
is a link to a court's **search page, not a decision**. Check the `ACCESS` column
in `sources` before treating a thin result as a nil return.

**Then do the real work.** Open the judgment. Get it translated if it will be
relied on. Test whether the foreign court's reasoning survives on facts like the
user's — a refusal resting on 2019 prison-monitoring data does not carry itself
into a later year without the intervening material.

---

## Every search leaves a report

`xsearch.py` writes a dated markdown report and a JSONL file per run, indexed in
`runs.jsonl`: what was asked, which databases answered, which failed, and every
hit with its relevance verdict. This exists so that months later the user can say
where a citation came from without re-running the sweep. Quote the run reference
in the case file.

---

## Politeness — a condition of use, not a suggestion

The engine queries public court databases on a deliberately low-volume footing:
one request per second per host, an honest User-Agent, and no automation at all
of sources whose terms bar it. An advisory lock prevents two sweeps at once.

**Do not** parallelise it, loop it unattended across a list of states, or raise
`--limit` into the hundreds to bulk-collect. Several of these databases will
block on far less, and they are a shared resource for every practitioner who
does this work. If a user asks for bulk harvesting, decline and explain why.

---

## Files

| Path | What it holds |
|---|---|
| `scripts/xsearch.py` | Installs and drives the engine; applies the relevance gate; writes the report |
| `scripts/quality.py` | The relevance gate, carried here so the skill works against any version of the engine |
| `reference/jurisdictions.md` | Coverage map — every jurisdiction, its databases, automated or deep-link |

Engine: <https://github.com/mateiclej-wq/eu-extradition-search> (MIT).
