# Foreign extradition case-law search

Search the domestic courts of **122 jurisdictions — 153 databases, 49 fully
automated** — for extradition and arrest-warrant surrender decisions, each in
its own language and vocabulary.

Built by [Matei Clej](https://github.com/mateiclej-wq), a practising extradition
barrister in London, for use in live casework.

## The question it answers

How are *other* executing states treating this requesting state, or this ground?

Rechtbank Amsterdam refusals on prison conditions. German OLG and
Bundesverfassungsgericht decisions on assurances. Irish High Court surrender
judgments. Italian Cassazione. Polish SAOS. That material is scattered across a
hundred-plus national databases, each with its own interface and language, and
no commercial service searches them together.

Searching by requesting state localises its name into each jurisdiction's own
language, so the sweep finds what those courts actually wrote — `AE` becomes
*Emiratele Arabe Unite* in Romania, *Emirati Arabi Uniti* in Italy,
*Zjednoczone Emiraty Arabskie* in Poland.

## What it gives you

```
19 results from 4/4 databases in 4s — 8 on point, 1 unclear, 10 off topic

  DE 2026-08-11  BVerfG      ECLI:DE:BVerfG:2026:rk20260811.2bvr150226
  DE ----        OLG Bamberg Auslieferungshaft – Auslieferung an Rumänien
```

Every hit passes a relevance gate — these databases sort by date and stem
loosely, so an ungated sweep returns competition appeals alongside surrender
decisions. Every search leaves a dated report on disk, so the research is
reconstructable months later without re-running it.

## What it is not

**Every result is a lead, never an authority.** The engine reports that a
judgment exists and that its metadata matched extradition vocabulary. It does
not know what the judgment holds, and it does not read, translate or interpret
anything. Open the decision, read the passage, have it translated if you will
rely on it. A nil return is not proof of absence: in several states the
surrender decision is never published at all.

## Install

```bash
python3 scripts/xsearch.py install     # clones the MIT engine into a cache dir
pip install requests babel             # babel is load-bearing for localisation
python3 scripts/xsearch.py search --issuing-state RO --countries NL,DE,IE
```

## Please use it politely

The engine queries public court databases at one request per second per host,
with an honest User-Agent, and does not automate any source whose terms bar it.
Do not parallelise it, loop it unattended, or bulk-collect. These databases are
a shared resource for everyone who does this work, and several will block on far
less.

## Licence and credit

MIT. The engine is at
<https://github.com/mateiclej-wq/eu-extradition-search>; the relevance gate is
carried in `scripts/quality.py` so the skill works against any version of it.
