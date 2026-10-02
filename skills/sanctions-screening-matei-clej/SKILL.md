---
name: sanctions-screening
description: "Screen a client, counterparty, payer or corporate against the sanctions lists published by the designating authorities themselves — the UK Sanctions List (FCDO), OFSI, the UN Security Council, the EU consolidated list and OFAC's SDN and non-SDN lists. Use when onboarding, before taking a payment, before completing a transaction, or whenever a name must be checked against sanctions. Produces candidates and provenance, never a clearance: the record names every list searched with its publication date and count, states what was NOT searched, and ends at a blank decision block. Fails closed — a cache that is missing, damaged, truncated or stale is reported NOT SEARCHED and the process exits non-zero, so nothing can read an incomplete run as clean. Matches across transliteration, diacritics, homoglyphs and initials, because nobody spells a name the way the publisher does. Standard library only; screening opens no network connection."
---

# Open-source sanctions screening

Three Python files, standard library only. No install step, no API key, no
account, and no third-party screening vendor in the path — so there is no
per-search cost and no reason to leave anybody unscreened.

**The tool produces candidates and provenance. It never clears anybody.** The
comparison of a candidate against what is actually known of the subject, the
decision that follows, and the record of that decision belong to the fee earner.

## Running it

```bash
python3 screen.py refresh                       # fetch + parse the default six lists (~30s)
python3 screen.py status                        # freshness, designation counts, failures
python3 screen.py sources                       # the registry, coverage and licences

python3 screen.py check "Ivan Petrov" --dob 1975-03-02 --nationality Russia
python3 screen.py check "Acme Trading LLC" --type entity --threshold 80
python3 screen.py check "Ramzan Kadyrov" --dob 05/10/1976 \
    --client MATTER-2026-0099 --matter "immigration advice" \
    --report ./screening/kadyrov-2026-09-01.md

python3 screen.py batch subjects.csv --report-dir ./screening/   # name,dob,nationality,type,client,matter
```

Exit codes: `0` complete search and nothing found, `2` candidates, `3` the search
cannot be relied on, `4` the request was refused.

Switches: `--source uk-sanctions-list,ofsi` (restrict, or reach the non-default
lists), `--threshold` (default 88 — see below), `--include-delisted`, `--max-age-hours`
(default 24), `--strict`, `--json`, `--verbose`.

The default threshold is set from measurement. Recall is identical at every
cut-off from 85 to 92 (99.7%) while false positives fall from 20% to 2%, and no
true match scored between 85 and 92. Lower it to 82 to catch a query as thin as
an initial plus one name, at a 40% false-positive rate; raise it to 92 for a
first pass over a large book of clients.

Requires Python 3.11 or later (3.9 parses but is not tested). Nothing else. The cache lives in
`~/.claude/sanctions-data` (override with `SANCTIONS_DATA`) and is about 100 MB
for the eight government lists; a run holds roughly 230 MB in memory while
scanning.

## The completeness gate

Every route out of this tool — text, JSON, a written record, a batch summary, an
exit code — is rendered from one Outcome object, and an Outcome knows whether the
search was complete. There is no path that reports "nothing found" without also
carrying whether anything was actually searched.

A search is complete only if the request was valid and every list asked for was
read in full, matched the digest recorded when it was fetched, and is current.
Anything else is incomplete, and an incomplete search never exits 0.

| Exit | Meaning |
|---|---|
| 0 | Complete search, no candidate at or above the threshold |
| 2 | Candidates to consider |
| 3 | The search cannot be relied on — a list was missing, damaged, altered, short, stale or never fetched |
| 4 | The request itself was refused — an unusable option, a name with nothing searchable in it, a CSV with no name column |

The cache is bound to its metadata by digest and parser version, so a list that
has been altered, truncated or parsed by a different version of this code is
refused rather than searched. **Upgrading the tool therefore requires a
`refresh`** — that is the gate working, not a fault.

## The lists

| id | List | Authority | Default |
|---|---|---|---|
| `uk-sanctions-list` | UK Sanctions List | FCDO | ✓ |
| `ofsi` | Consolidated List of Financial Sanctions Targets | HM Treasury / OFSI | ✓ |
| `un` | Security Council Consolidated List | United Nations | ✓ |
| `eu` | Consolidated financial sanctions list | European Commission | ✓ |
| `ofac-sdn` | Specially Designated Nationals | US Treasury / OFAC | ✓ |
| `ofac-cons` | Consolidated non-SDN (SSI, FSE, NS-PLC, CAPTA) | US Treasury / OFAC | ✓ |
| `canada` | SEMA / JVCFOA consolidated list | Global Affairs Canada | |
| `swiss` | SECO sanctions list | Swiss Confederation | |
| `opensanctions-sanctions` | ~90 sources, deduplicated | OpenSanctions (aggregator) | |
| `opensanctions-peps` | Politically exposed persons | OpenSanctions (aggregator) | |

The UK Sanctions List and the OFSI list are not the same thing and neither
subsumes the other: the FCDO list is the legal list and carries every measure
imposed (travel ban, arms, trade, transport, director disqualification), while
the OFSI list carries the financial-sanctions targets and the asset-freeze
detail. Both are searched by default.

**The OpenSanctions datasets are CC BY-NC 4.0.** Screening fee-earning client
work is commercial use. Those two sources refuse to refresh until
`SANCTIONS_OPENSANCTIONS_LICENCE` is set — set it to `noncommercial` for
genuinely non-commercial work, or to your commercial licence reference once one
is held. They are also the only PEP source here.

Per-source detail, quirks and failure modes: `reference/sources.md`.

## What the law requires, and of whom

Verified against the in-force text on legislation.gov.uk on 02.09.2026. This is
a UK-facing tool; practitioners elsewhere should read the equivalents.

**The prohibitions reach the work, whoever the client is.** UK regimes are made
under the Sanctions and Anti-Money Laundering Act 2018 s.1, and s.21(1) sets
their reach: prohibitions may be imposed in relation to conduct in the United
Kingdom or its territorial sea **by any person**, and to conduct elsewhere
**only where it is by a United Kingdom person** — s.21(2)-(3): a UK national
(a British citizen, British overseas territories citizen, British National
(Overseas) or British Overseas citizen, a British subject under the British
Nationality Act 1981, or a British protected person), or a body incorporated or
constituted under the law of any part of the UK. Read the two limbs separately.
Limb (a) catches everything done in this jurisdiction whoever does it, so it
reaches work carried out here regardless of counsel's nationality. Limb (b)
reaches conduct abroad only if the actor is a United Kingdom person: practising
here does not by itself make a foreign national one, though a UK-incorporated
entity is one whatever the nationality of those behind it. Dealing with a
designated person's funds, or making funds or
economic resources available to or for the benefit of one, is prohibited by the
regime regulations themselves. There is no client-type threshold and no de
minimis, so this catches a fee taken from a third-party payer as readily as a
corporate retainer.

**Much litigation practice sits outside the MLR customer due diligence duty.** An
"independent legal professional" is defined in reg 12(1) of the Money Laundering
Regulations 2017 (SI 2017/692) by reference to *participation in* financial or
real property transactions — buying and selling property or business entities,
managing client money or assets, opening or managing accounts, organising
company contributions, and creating or managing trusts and companies. The test
is what the retainer involves, not what the practice area is called: ordinary
criminal, extradition and immigration advocacy will not usually engage that
limb, but a matter that turns on any of those transactions does, whatever it is
filed under. Where it is
engaged, reg 33(1)(d) and reg 35 make PEP status an enhanced due diligence
trigger (a trigger, never a prohibition), and reg 40(2)(a) with reg 40(3)
require the CDD material to be kept for five years — running from the end of the
business relationship for a relationship (reg 40(3)(b)), but from completion of
the transaction for an occasional transaction (reg 40(3)(a)), which is the limb
a one-off retainer falls into. Reg 40(4) caps relationship records at ten years,
and reg 40(5) requires the personal data to be **deleted** once the period
expires unless another duty or a legal-proceedings ground keeps it. Retention is
a duty in both directions: keeping a screening record indefinitely is its own
breach.

**The reporting duty is wider than the CDD duty, and does reach a legal
practice.** Under the Russia (Sanctions) (EU Exit) Regulations 2019 (SI
2019/855), reg 71(1)(d)(ii) makes a firm or sole practitioner providing "legal or
notarial services" by way of business a *relevant firm* — with no transaction
limb — and reg 70(1) requires a relevant firm to inform the Treasury as soon as
practicable where it knows or has reasonable cause to suspect that a person is a
designated person or has breached a prohibition, and the knowledge or suspicion
came to it in the course of its business. Verified for the Russia regime; other
regimes follow the same drafting, but the regime in play must be checked rather
than assumed.

**Ownership and control are not screened by any name search.** Under reg 7 of SI
2019/855 a non-individual is owned or controlled by a designated person where
that person holds, directly or indirectly, more than 50% of the shares or voting
rights, or the right to appoint or remove a majority of the board — or, on the
second limb, where it is reasonable to expect that they could achieve the result
that the company's affairs are conducted in accordance with their wishes. An
unlisted company can therefore be caught by a listed shareholder. That has to be
worked out from the ownership structure; no list holds it.

## The discipline

1. **A candidate is not a match.** The score measures name similarity, nothing
   else. Adopting or discounting a candidate is a human comparison against date
   of birth, nationality, address, identifiers and the statement of reasons.
2. **A nil return is bounded, and the record says by what** — the lists actually
   searched, the date each was published, and the spelling used. It is not a
   statement that the subject is not sanctioned.
3. **A failed read never reads as a clean result.** A list that is missing,
   damaged, truncated, or short of the count recorded when it was fetched is
   reported as NOT SEARCHED on the face of the screening record, its hits are
   discarded rather than half-reported, and the run exits 3.
4. **Search more than one spelling** of a transliterated name. The tool itself
   romanises Cyrillic only — under four systems, each searched — and any
   Cyrillic letter in a name triggers that. Arabic, Chinese and every other
   script are NOT romanised: a query in them is refused, and the passport or
   publisher spelling must be searched in Latin script. OFAC's files are
   entirely ASCII, so a non-Latin name can never match there except through a
   romanisation. The matcher folds diacritics and homoglyphs but cannot invent
   a spelling nobody gave it. Search the passport spelling and the common
   alternative.
5. **Screen the payer, not only the client.** Third-party payers, corporate
   parents, funders and the opponent in a matter where money will move.
6. **Re-screen.** Designations are made weekly. A screen done at intake says
   nothing about the position when the fee is taken.
7. **Never complete the decision block on the fee earner's behalf**, and never
   describe a subject as "cleared". Fill in the search; leave the decision.

## Privacy

Screening is entirely local. `refresh` contacts the eight publishing authorities
listed above and nothing else; `check` and `batch` open no socket at all, which
is asserted by a test that replaces the socket layer with something that raises.
The name of a client is never sent anywhere. Screening records are written only
where you point them.

## Tests

```bash
python3 tests/test_screen.py        # 130  matching, dates, the gate, parser output
python3 tests/integrity.py          # 186  field mapping, refresh, tampering, licence gate
python3 tests/adversarial.py        # 374  hostile input, cache damage, injection, privacy
python3 tests/release_gate.py       #      every published name retrieves its designation — run before a tag
python3 tests/benchmark.py          #     recall and precision against the lists
python3 tests/prefilter_safety.py   #     measures whether the speed filter costs recall
python3 tests/threshold_sweep.py    #     where the default threshold belongs
```
