# sanctions-screening

An agent skill that screens a name against the sanctions lists published by the
authorities that made the designations — the UK Sanctions List, the OFSI
consolidated list, the UN Security Council list, the EU consolidated list, and
OFAC's SDN and non-SDN lists, with Canada, Switzerland and the OpenSanctions PEP
dataset available on request.

Three Python files, standard library only. No install step, no API key, no
account, no vendor. Python 3.11 or later.

## Why

Commercial screening is priced per search, which is exactly the wrong incentive:
it makes a firm ration the checks it should be running on every client, every
third-party payer and every corporate counterparty. The underlying data is
published free by the designating authorities. This reads it directly.

## Quick start

```bash
python3 screen.py refresh                     # ~30 seconds, ~100 MB cached
python3 screen.py check "Ivan Petrov" --dob 1975-03-02 --nationality Russia
python3 screen.py check "Acme Trading LLC" --type entity --report ./acme.md
python3 screen.py batch subjects.csv --report-dir ./screening/
```

## What it produces

Candidates and provenance. Never a clearance.

The screening record names every list searched, the date that list was
published **where the publisher states one in the file** — OFAC and Canada do
not, and the record says "not published in this file" rather than substituting a
file timestamp for a publication date — the moment it was retrieved, and how many
designations it held. It
states on its face what was **not** searched. It sets out each candidate with the
regime, the measures imposed, the identifiers and the statement of reasons. Then
it stops, and leaves a blank decision block for the fee earner to complete and
sign.

That division is the whole design. A tool can find candidates; only a person can
compare a candidate against what is known of the client and decide.

## Failing closed

Every route out — text, JSON, a written record, a batch summary, an exit code —
is rendered from one outcome object that knows whether the search was complete.
There is no path that reports "nothing found" without also carrying whether
anything was actually searched.

A list that is missing, damaged, truncated, altered, stale, or parsed by a
different version of this code is reported as NOT SEARCHED; its hits are
discarded rather than half-reported, and the run exits 3. A request that cannot
be screened — an unusable threshold, a name with nothing searchable in it, a CSV
with no name column — is refused with exit 4 rather than reported as clean. Exit
0 means a complete search that found nothing, and nothing else.

This is tested by deleting, corrupting, truncating, tampering with and
back-dating the cache and asserting on what comes out.

## Matching

Per-token Jaro-Winkler in both directions, with three corrections that come from
watching it get things wrong:

- **First-and-last anchoring.** Where the first and last parts of the query both
  match strongly, the parts in between are discounted, so a client who gives a
  patronymic the list does not hold is still found.
- **Asymmetry damping.** A listing holding the bare alias "John" would otherwise
  score 100 against "John Smith", because everything the listing knows is
  matched.
- **Initials corroborate, they do not identify.** Without this, "Mian Mithoo"
  matches "ASHRAF, Haji M." at 92, and the results fill with noise.

A name given in Cyrillic is screened as published, and again under each of the
romanisation systems the publishers actually use, because they disagree and none
of them is authoritative; the names publishers supply in their own script are
indexed. A name in a script this tool cannot romanise is **refused**, not
screened: OFAC's SDN file carries no non-Latin name at all, so a nil return
against it from an Arabic or Chinese spelling would mean nothing. Dates of birth
annotate and rank candidates; they never suppress one, because a date that
disagrees is a reason for a person to discount a candidate, not a reason for the
tool to hide it.

Diacritics are folded, and so are the Cyrillic and Greek homoglyphs that appear
inside otherwise-Latin names on the EU list.

## Privacy

`refresh` contacts the publishing authorities and nothing else. `check` and
`batch` open no socket at all — a test replaces the socket layer with something
that raises, and screens a name. Client names never leave the machine, and
screening records are written only where you point them.

## Tests

```bash
python3 tests/test_screen.py     # matching, dates, parser output
python3 tests/integrity.py       # field mapping, refresh semantics, licence gate
python3 tests/adversarial.py     # hostile input, cache damage, privacy
python3 tests/benchmark.py       # recall and precision, measured against the lists
```

## Licensing

The code is MIT. The lists are not: each remains subject to the terms of the
body that publishes it, recorded per source in `reference/sources.md` and printed
by `python3 screen.py sources`. Most are Open Government Licence or public
domain. **The optional OpenSanctions datasets are CC BY-NC 4.0 — non-commercial
only** — and the tool refuses to fetch them until the licence position is
acknowledged in an environment variable, because screening fee-earning client
work is commercial use.

Contains public sector information licensed under the Open Government Licence
v3.0.

## What it does not do

Identity verification. Ownership and control — an unlisted company owned by a
designated person is caught by the ownership test in the regime regulations, not
by any name search. Sectoral and trade restrictions that attach to conduct
rather than to a named person. Adverse media. PEP screening, unless the optional
OpenSanctions PEP dataset is enabled.
