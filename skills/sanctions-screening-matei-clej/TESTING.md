# Test report — sanctions-screening

Testing carried out 01–07.09.2026 against the live lists (38,524 designations
across the six default sources) before publication.

## Summary

690 assertions across three suites, on Python 3.11, 3.13 and 3.14
(440 on 3.9 on 01.09.2026), plus three measurement harnesses that produce numbers rather than
pass/fail. Seventeen defects were found and fixed. Four of them would have been
silent in ordinary use, and one of those would have produced a screening record
stating that a designated person was not on a list that had in fact never been
read.

```
tests/test_screen.py       130 assertions   matching, dates, the gate, parser output, controls, script
tests/integrity.py         186 assertions   field mapping, refresh, tampering, licence, separators, chronology
tests/adversarial.py       374 assertions   hostile input, cache damage, injection, privacy, terminal, batch
tests/release_gate.py                       every published name retrieves its own designation (pre-tag)
tests/benchmark.py                          recall and precision
tests/prefilter_safety.py                   margin the speed filter leaves on true pairs
tests/threshold_sweep.py                    where the default threshold belongs
```

## Defects found and fixed

### 1. A deleted list produced a clean nil return (critical)

With `meta.json` recording a successful fetch but the parsed list deleted, the
tool printed **"Lists searched: 1 of 1 (5,135 records)"** and gave Vladimir Putin
a clean nil return. `provenance()` trusted the metadata while `screen()` silently
read nothing.

This is the exact failure the design exists to prevent, and it survived the first
round of testing because the test that should have caught it passed for the wrong
reason — it ran against six default sources, four of which were legitimately
absent, so the expected "NOT SEARCHED" string appeared regardless.

**Fixed.** The claim that a list was searched is now earned by reading the cached
copy in full and finding the number of designations recorded when it was fetched.
Missing, damaged, truncated, or short of that count is a failed read: it is
reported as NOT SEARCHED, its hits are discarded rather than half-reported, and
the run exits 3.

### 2. Corrupt cache files crashed with a traceback

A corrupt or truncated parsed list, or a corrupt `meta.json`, produced a Python
stack trace. Loud, but not usable, and the run gave no screening record at all.
**Fixed** — each is caught and reported as NOT SEARCHED with the reason.

### 3. "No candidate" printed when nothing had been searched

Where every list failed to load, the tool still printed a nil return and exited
0, so a calling script would read the run as clean. **Fixed** — it now says
NOTHING WAS SEARCHED, the record says the check did not run rather than that the
subject is absent, and it exits 3 whether or not `--strict` was passed.

### 4. A long name never returned (denial of service)

A 5,000-character name — 700 parts — was scored part-by-part against every
designation on every list. On Python 3.9 the process was still running after 180
seconds. **Fixed** by deduplicating query parts and capping the number
considered. The cap is set from the data: the longest name published on any of
these lists has 34 parts, so a cap of 40 cannot truncate a real one. The same
input now completes in 1.9 seconds.

### 5. A patronymic the list did not hold defeated the match (recall)

Where a client gave a name in fuller form than the listing held — "Ivan
Sergeyevich Petrov" against a listing for "Ivan Petrov" — recall was **46.7%**.
Nearly half of those designations were missed.

**Fixed** by first-and-last anchoring: where the first and last parts of the
query both match strongly, the parts in between are discounted. That deformation
now recalls **100%**.

### 6. Ordinary names matched too readily (precision)

The false-positive rate on ordinary names that should match nothing was
**29.3%** — 44 of 150. The rewritten matcher, measured on the same seeded
sample, brings this to **20.0%** at the old threshold, and to **10.7%** at the
threshold the sweep in defect 11 settled on.

### 7. A third-party dependency, undeclared

The first version imported `rapidfuzz` and exited with an error if it was
missing — and the documentation never mentioned installing it. For a package
that goes through a platform security review, a dependency is also an install
step and more code to vouch for.

**Fixed.** `matching.py` implements Jaro-Winkler and the scoring model in the
standard library. The rewrite is also more accurate on both axes (defects 5 and
6) and faster in batch.

### 8. Two caches that cleared themselves on every call

`sources.read_source()` and `screen._index()` each cleared their cache before
storing, so with six lists only the last survived. Every screen re-read and
re-indexed all six. Found by profiling, not by a test. **Fixed** — batch
screening went from 1,030 ms to about 700 ms per subject.

### 9. A single initial returned everyone

Screening the query `X` returned 71 candidates at 88. An initial corroborates a
name; it never identifies one, and that rule was already applied everywhere
except a single-token query. **Fixed** — `X` now returns nothing.

### 10. `--json` crashed, and the test compared two identical crashes

`searched` was defined only in the branch that prints human-readable output, so
`--json` raised `UnboundLocalError`. The determinism test ran the same command
twice and compared the results — two identical stack traces compare equal, so it
passed. **Fixed**, and the test now parses the JSON and asserts it carries both
the candidates and the provenance.

### 11. The default match threshold was set by habit, not measurement

`tests/threshold_sweep.py` screens once at a low floor and evaluates the same
scores at several cut-offs. It samples **Latin-script individuals only** — which
is the right cohort for choosing where a score cut-off belongs, since the
question is where genuine and spurious scores separate, but it is not a measure
of the tool's recall. For that, see the benchmark figures in round three below.

| cut-off | recall | false positives |
|---:|---:|---:|
| 82 | 100.0% | 40.0% |
| 85 | 99.7% | 20.0% |
| 86 | 99.7% | 18.7% |
| **88** | **99.7%** | **10.7%** |
| 90 | 99.7% | 4.0% |
| 92 | 99.7% | 2.0% |

**Re-measured 08.09.2026**, after §65 widened the run-together comparison: the
benchmark's own 200-name precision sample gives **8.0%** (16 of 200) at the
shipped cut-off of 88, against the 10.7% this table records for the sweep's
sample. The two samples are different and not directly comparable, but the
direction matters: none of the sixteen false positives involves the widened
branch — each was checked pair by pair — so §65 bought three published spellings
at no measured cost in precision.

Recall is identical from 85 to 92, and **no true match scored anywhere between
85 and 92** — genuine matches cluster at 92 and above, the noise sits just above
85. The original default of 85 was therefore taking every false positive the
band had to offer and buying no recall with it.

**Changed to 88**, which removes half the noise at no measured cost and still
leaves four points of margin below the lowest genuine match observed. The one
search missed at any cut-off from 85 up is a query as thin as an initial plus a
single name ("A Yusuf" for "Al-Madani Yusuf"), recoverable at 82 by anyone
willing to accept a 40% false-positive rate.

### 12-14. Matching defects found in the first round

- **Initials alone scored 92.** "Mian Mithoo" matched "ASHRAF, Haji M." because
  both query parts "matched" the single letter M.
- **A bare alias scored 100.** A listing whose only alias is "John" scored 100
  against "John Smith", because everything the listing held was matched.
- **Cyrillic homoglyphs split surnames.** The EU list publishes `ROMASHKІN` with
  a Cyrillic `І`; stripping it rather than folding it broke the surname in two.

### 15-17. Parser defects found in the first round

- **Both UK CSVs open with a preamble line before the header** — handing the
  first line to a `DictReader` yields one column and no matches.
- **The Swiss whole-list file ships 1,559 de-listed targets** among 8,667. They
  are parsed with a status and excluded unless asked for; reporting them as
  sanctioned would be the most damaging error the tool could make.
- **The EU list publishes every name in every official language**, so a
  Bulgarian rendering was being chosen as the display name.

## Non-defects — two assertions that were wrong, not the code

Recorded because a test that fails for a bad reason is worth as much attention
as one that passes for a bad reason.

- An assertion that the CSV null token `-0-` never survives into a record failed
  on three lists. All three were the same legitimate value: a Swiss federal
  company number reads `CH-2 17-0-431-423-3`. The assertion was rewritten to test
  what it meant — that no *field value* is the null token.
- A test that a failed refresh leaves the previous list intact was passing while
  actually downloading the list over the network. It was replaced with an
  in-process failure injection.

## Code that would otherwise have shipped untested

The two OpenSanctions parsers can never run unless someone acknowledges the
CC BY-NC licence, so they would have gone to publication having never executed.
They are exercised against a synthetic file written in the publisher's own
`targets.simple` schema — no download, no licence position asserted — which
checks the schema-to-type mapping for people, companies and vessels, semicolon-
separated aliases, the separation of Cyrillic aliases from Latin ones, dates,
identifiers, listing dates and quoted addresses. Eleven assertions, all passing
first time.

## Fail-closed behaviour, as tested

Each of these is asserted in `tests/adversarial.py`:

| Cache state | Result |
|---|---|
| Parsed list deleted | NOT SEARCHED, exit 3 |
| Parsed list corrupt (not gzip) | NOT SEARCHED, exit 3, no traceback |
| Parsed list truncated mid-record | NOT SEARCHED, exit 3 |
| `meta.json` corrupt | NOT SEARCHED, no traceback |
| Cache entirely absent | NOT SEARCHED, exit 3, no nil return printed first |
| Data 40 days old | STALE on the record; exit 3 under `--strict` |
| Refresh fails | Previous parsed list untouched; failure written to metadata |

## Hostile input

Fourteen inputs — empty, whitespace, a single character, punctuation only, emoji,
right-to-left Arabic, Cyrillic, Chinese, an embedded newline, a markdown table
breaker, a spreadsheet formula injection, 5,000 characters, escape sequences, and
a SQL-shaped string — none produced a traceback. Seven malformed dates, an
unknown `--type`, an unknown `--source`, `--threshold 0` and `--limit 0` are
handled. A CSV with commas, quotes, apostrophes and a formula in the name column
parses, and one screening record is written per subject.

## Privacy

`check` and `batch` open no socket at all. The test replaces
`socket.socket.connect`, `socket.create_connection` and `socket.getaddrinfo`
with functions that raise, then screens a name and asserts that the run
completed and found its candidates. Network access is confined to `refresh`,
which contacts eight hosts, each the publisher of the list it serves.

## Performance

Measured on the six default lists, 38,516 designations, in isolation.

| | |
|---|---|
| Refresh, all six lists | 27 s |
| Single check, cold | 2.0 s |
| Batch, per subject once indexed | ~0.7 s |
| Peak memory while screening | 226 MB |
| Cache on disk, eight lists | 102 MB |

The prefilter — a character-bigram mask per designation — is what makes a
standard-library matcher viable. It is a speed optimisation, so it was tested
for the only thing that matters: whether it costs recall.
`tests/prefilter_safety.py` takes 3,000 real designations, deforms each of their
names seven ways, and asks the filter directly whether it would have let the
right designation through. **0 blocked of 16,888 true pairs**, median margin
14 shared bigrams above the requirement. The demand is capped at four shared
bigrams however long the query, because without that ceiling the tightest
realistic margin was one.

---

# Round two — independent adversarial review

The work above was my own testing. It was then put to an independent reviewer
(Codex, `gpt-5.6-sol`) under the prompt in `CODEX_REVIEW_PROMPT.md`, which
forbids criticism without a verbatim quotation and requires a concrete failure
scenario for every finding. The full response is in `CODEX_REVIEW.md`.

It returned 21 findings and refused to sign its name to publication. **Every
finding I could reproduce, reproduced.** One did not: its Cyrillic example was a
different Kadyrov, not a miss. The rest were real, and the most serious of them
were in code my own 173 assertions had walked straight past.

## The worst of it

**The batch command had no fail-closed behaviour at all.** Batch is the path you
would use on a whole client book. With an empty cache and `--strict`, screening
Vladimir Putin printed:

```
Vladimir Putin  0  —
1 subjects, 0 candidate matches.
```

and exited **0**. No "NOT SEARCHED". `--strict` was accepted by the parser and
never read. A CSV headed `full_name` skipped every row and reported the same
thing. `--limit 0` or `--threshold nan` did it too, on the single-check path.
Each of those is a machine-readable false clearance.

Three more of my tests turned out to pass for the wrong reason, on top of the
three I had already found — including one I had reported as fixed. It set
`SANCTIONS_TEST_BREAK_URL` to simulate a network failure; production code never
reads that variable, so the test downloaded the real list, and its condition
`before == after or rc == 0` passed either way.

## What changed

The fix is the one the reviewer asked for: **a single completeness gate**. Every
route out of the program — text, JSON, a written record, a batch summary, an exit
code — is now rendered from one `Outcome` object that knows whether the search
was complete. There is no path that reports "nothing found" without also
carrying whether anything was searched.

| # | Finding | Resolution |
|---|---|---|
| 1 | Batch ignored `--strict` and exited 0 having searched nothing | Batch renders from the Outcome; incomplete exits 3 |
| 2 | Bad CSV headers and wrong-case types silently skipped every row | `name` column required, types case-folded, refusal exits 4 |
| 3 | `--limit 0` / `--threshold nan` erased real hits, exit 0 | Options validated; refusal exits 4 |
| 4 | A line-truncated download became the whole list | Per-source minimum sizes, alias presence, >20% shrink quarantined |
| 5 | Same-count substitution in the cache went undetected | Digest and parser version recorded and verified on every read |
| 6 | `--type any` missed exact entity names | Names tokenised both ways; the candidate's own type selects |
| 7 | Native-script names were never indexed | Non-Latin names indexed; Cyrillic queries romanised and screened both ways |
| 8 | Partial or stale searches exited 0 | Incomplete always exits 3; JSON carries `complete` at top level |
| 9 | Batch reports overwrote each other | Row index plus a digest of the name |
| 10 | Swiss spelling variants became isolated name parts | Whole names rebuilt per language and script |
| 11 | Canadian vessels were typed as entities, IMO discarded | Vessels typed as vessels, IMO kept, build year is not a date of birth |
| 12 | Download time was reported as the list's publication date | Reported as "not published in this file" where the publisher gives none |
| 13 | A conflicting date of birth deleted a real candidate | The threshold applies to the name; dates annotate and rank only |
| 14 | Shared fixed `.part` paths across processes | Unique temp files, fsync, and a lock around refresh and commit |
| 15 | Unescaped data could forge a signed decision block | Markdown escaped in every interpolated field |
| 16 | Nine tests gave false assurance | Rewritten; suites now 68 + 129 + 157 = 354 assertions |
| 17 | "The prohibitions bind everyone" was territorially wrong | Restated from SAMLA 2018 s.21(1); the MLR limb restated as transactional |
| 18 | Swiss identifiers discarded | Identification and BIC numbers kept |
| 19 | `status` trusted metadata and always exited 0 | Reads the cache; exits 3 when a search now would be incomplete |
| 20 | `--json --report` corrupted stdout | The written-record line goes to stderr |
| 21 | Names printed to stdout | Kept — it is a CLI — and the privacy claim scoped to network traffic |

## Hardening done while the second review ran

Five further routes were closed without waiting to be told about them, because
the second review's own prompt points at them:

- `enabled_sources()` called `sys.exit()` on an unknown `--source`, which is an
  exit that never passes the gate. It now raises and is refused with exit 4.
- A list named twice on `--source` was searched twice and counted twice in the
  provenance. Sources are de-duplicated.
- A source that raised while being indexed or scanned killed the whole run. It is
  now reported NOT SEARCHED, its partial hits are discarded, and the rest of the
  search continues.
- The digest was computed by reading the file, and the parse then re-opened it —
  a window in which a concurrent writer could substitute what was actually
  parsed. Both now operate on the same bytes.
- Integrity is verified in full whenever data is loaded, and the verified copy is
  reused only while the file on disk is unchanged.

# Round four — the third review answered

The third review refused to sign again, on the same charge and with a better
example. It is the most useful of the three.

## The example

`LADY R` is an exact, character-for-character vessel designation on the UK
Sanctions List (RUS2185) and on OFAC's SDN list (37095). Both lists were read,
both were fresh, the requested type was right, and no alias or transliteration
was needed. The tool returned **no candidates, complete, exit 0**.

Two causes, both small and both fatal. `LADY` sits in the personal-title list
and was stripped from every record type, including ships. What remained was `R`,
a single character, which the matcher caps at 70 as an uncorroborated initial.

Personal titles are now stripped from individuals only, and an exact published
name scores 100 before any cap can touch it — a query that IS the designation is
not a similarity judgment to be damped.

## The invariant that should have existed from the start

The reviewer's suggestion, and the single most valuable thing to come out of
three reviews: **every name a publisher prints must be findable by typing that
name.** It sounds too obvious to test, which is why nobody had.

Scored across the whole corpus, **54 published designations could not find
themselves** — `E. S. Co.`, `T.R.O.S`, `M.A.C.`, `G-9`, `1-P`, `LADY R` and
others, every one a name that reduces to initials. All 54 now retrieve at 100.

It is a release gate: all **117,498** published names must be indexed under the
form `screen()` will look for. It found a second defect on its first run — OFSI
files the Arabic alias of SOURUH COMPANY under `aliases` rather than `nonlatin`,
so it entered neither the Latin index nor the native one and no query could
reach it. Fixed at index level, where a parser filing a name in the wrong field
can no longer make it unsearchable.

## The rest of the third review

| Finding | Now |
|---|---|
| OFAC's alias file could vanish and validation still pass — every alias lost while `complete` stayed true | Every file the parse reads is fingerprinted into the manifest by digest, size and line count, with an alias floor per source. A missing alias file and a 35% erosion are both refused |
| One ASCII letter defeated the script refusal: `يحيى السنوار A` was screened, and the unchanged Arabic string was reported as its "romanisation" | The gate no longer asks whether a name is *mostly* non-Latin. Every non-Latin letter must be mappable, or the request is refused naming the script |
| A tuple protects only its slots — clearing a record's dictionary left the length intact and the exact query returned nothing, complete | Records are read-only mappings with tuple fields, frozen on the read that verifies the digest |
| `batch` printed a clean row, then failed to write its record | Delivery precedes rendering, as in `check`; the row prints INCOMPLETE and the failure is named |
| `batch --json` was accepted and ignored | Emits JSON: one object per row with its own provenance, plus the run's exit code |
| A flag that refuses every batch row exited 3, where `check` exits 4 | Exits 4 |
| `status` had its own freshness comparison and none of the validation, so `--max-age-hours nan` called a six-year-old list `ok` | One decision function, used by both |
| All 8,667 Swiss records had an empty regime and no listing date — the lookup keyed on a `sanctions-program` ssid against a `sanctions-set` reference | 8,667 regimes, 8,637 listing dates |

## A defect in the repair itself

The coverage-complete script gate over-refused. `Đ` in `Međunarodna` is a Latin
letter that does not decompose under NFKD, so an ASCII test read it as a script
this tool cannot romanise, and an EU designation was refused **its own published
name** — with a message reading "contains LATIN letters, which this tool cannot
render into Latin".

The gate now asks what Unicode script a letter belongs to, and `normalise` folds
the Latin letters whose mark lives inside the glyph — `đ ø ł þ ß æ œ ð ħ` — rather
than cutting them to spaces. `Međunarodna` normalises to `MEDUNARODNA`, not
`ME UNARODNA`, which is a matching improvement independent of the gate.

It was not a review that caught this. The benchmark's `exact` cohort fell from
100% to 99.2% and the single missing row was chased down. A harness that reports
100% tells you nothing; one that reports 99.2% tells you where to look.

## Where it stands, measured

```
RECALL — 582 screens, threshold 88, cohorts drawn from all six lists
  exact                          100.0%     reordered              100.0%
  lowercased                     100.0%     initial                100.0%
  dropped middle name            100.0%     extra patronymic       100.0%
  punctuation dropped            100.0%     diacritics stripped    100.0%
  vessel searched as its type    100.0%     aircraft as its type   100.0%
  transliterated                  95.6%
  run together                    73.7%
  native script, own source       73.2%
  OVERALL                         95.9%

PRECISION  12 of 200 ordinary names produced a candidate — 6.0%
SPEED      median 1,150 ms   mean 1,531 ms
```

**The native-script figure is the price of a decision, not a defect.** Every one
of the eleven misses is a name the lists really do publish in its own script —
`אלישע ירד` for Elisha YERED on the EU list, `جودت صلبي مواس` for MAWAS Jawdat
Salbi — which the tool would match at 100 if it searched them. It refuses
instead, because it cannot romanise those scripts and cannot therefore reach the
same person on OFAC, which publishes no non-Latin name at all. The refusal buys
a guarantee that no unromanisable query yields a clean nil; it costs about a
quarter of native-script retrievals that were previously possible. A
source-by-source capability assessment would keep both, and is not built.

## Still not fixed

- **Run-together names, 73.7%.** The residue is entity names whose corporate
  suffix is stripped from the listing but present in the query, which defeats the
  length guard, and names with internal punctuation
  (`Chinaoil(HongKong)CorporationLimited`).
- **Single-token pairs inflate on the Winkler prefix bonus.** `JohnSmith`
  against a listing holding only `John` scores 88.9. Predates this work; fixing
  it means retuning the prefix bonus across the whole matcher.
- **No cross-source identity.** Nothing measures whether a person found on one
  list is found on another that spells them differently, because the lists share
  no identifier that would let a harness check it.
- **The subject's name is printed to stdout.** Three reviews have marked this
  unfixed; it is intended. A screening result has to say what was screened, and
  the tool opens no socket at all — the name never leaves the machine. Redirect
  or use `--json` if a transcript is being kept.

# Round three — the second review answered

The second review refused to sign, on one charge: the gate certified transport
integrity rather than search integrity. `complete=True` meant the cached bytes
were read, not that the query could have found what was in them. It proved the
point with three exact designations returning a clean nil and exit 0. All three
are now regression tests running through the real `screen()` against the real
cache.

## What the charge cost, and what fixed it

| The false negative | Why | Now |
|---|---|---|
| `AN SAN 1 --type vessel` missed OFSI DPR0097 | 81 rows with `Group Type = Ship` were emitted as `entity`, so a typed search skipped them | Exhaustive per-source type tables; **2,219 vessels and 342 aircraft recovered**. An unmapped word raises `ParseError` and quarantines the list rather than defaulting to `entity` |
| `Юрий Викторович Федоров` missed OFAC 36783 | One romanisation system produced `IUrii Viktorovich Fedorov`, scoring **87.8** against a threshold of 88 | Four real publisher systems (iso9, BGN/PCGN, press, scholarly), each keeping its own prefilter. Found at **98.3** on OFAC and **100.0** on the UK list, the latter through the `ё → yo` system |
| `يحيى السنوار` missed SINWAR on two lists | An unromanisable script was screened against native aliases and the shortfall carried as a footnote, while the run reported itself complete | **Refused at the door**, exit 4, nothing searched |

The refusal is the deliberate choice, and it costs something: a query in an
unromanisable script no longer reaches the native aliases that some publishers
do supply. It was taken on a fact neither review found — **OFAC's SDN file
carries no non-Latin name at all, 0 of 19,321 records.** Native-script matching
is structurally impossible against the largest list, so a nil return from an
Arabic or Chinese spelling could never have meant anything there.

## Measured, at the threshold the tool actually ships with

The previous figures in this report — 99.7% recall — were measured by a harness
that drew only Latin-script individuals and deformed them in ways that only make
sense for a person. It could not see a missed ship, a missed aeroplane, or a
missed cross-script name, which is why it read 99.7% while the CLI missed three
exact designations. The harness now screens each record under **its own type**
and carries vessel, aircraft, entity and native-script cohorts, and it defaults
to the shipped threshold of 88 rather than 85.

```
RECALL — 536 screens over 40 designations and their cohorts, threshold 88
  exact                          100.0%
  lowercased                     100.0%
  reordered                      100.0%
  initial                        100.0%
  dropped middle name            100.0%
  extra patronymic               100.0%
  punctuation dropped            100.0%
  vessel searched as its type    100.0%
  transliterated                  95.4%
  native script as published      82.1%
  run together                    62.5%
  OVERALL                         95.3%

PRECISION  12 of 200 ordinary names produced a candidate — 6.0%
SPEED      median 1,425 ms   mean 1,859 ms
```

That is a smaller number than 99.7% and a truer one. The two cohorts below 100%
are both real.

## A recall gap neither review found

Measuring the honest cohorts surfaced one: a name typed **without its spaces**
scored as a fragment. `JieShun` against the listing `Jie Shun` recovered 37.5% of
the cohort. `score_tokens` now also compares the two strings run together, which
takes the cohort to **62.5%** with no movement in precision.

The comparison is guarded on a length ratio of 0.8, because the unguarded
version drove straight through the subset-inflation defence installed in the
first round: `John Smith` against a listing holding the bare forename `John`
concatenates to JOHNSMITH vs JOHN and scores 88.9 on the Winkler prefix bonus
alone. A name missing its spaces is very nearly the same length as the name that
has them; a fragment is not. Five assertions hold both halves.

## Tests that were passing for the wrong reason

The second review listed twenty. The suite had been green while all three false
negatives were live, which is the only fact about it that mattered.

- An unrefreshed default list was a **skip**. It is now a **failure**: a suite
  that quietly executes fewer assertions passes just as loudly as one that
  checked everything.
- The non-Latin assertion was negative only — deleting all non-Latin extraction
  satisfied it, because a record with no native name cannot be a bad one. It now
  carries a **positive floor** per source.
- Hostile input asserted "no traceback", which a clean nil satisfies. Every
  hostile input now has to land on a defined exit code and show its provenance
  block, and seven of them have their right answer asserted by name.
- The batch test permitted exit 0 and never required its known designation.
  Returning a complete nil for every row wrote three files and passed all four
  assertions. It now requires the hit, by name, with a non-zero count.
- Injection was tested through `--matter` alone. It is now tested through the
  name, the client, the nationality and the date of birth.
- Two "no traceback" assertions read stdout only, though Python writes
  tracebacks to stderr.
- The tampering tests all passed `use_cache=False`, so they could not reach the
  cached path at all — which is where the mutable-cache poisoning lived.
- The refresh-failure test asserted against the dictionary the function had just
  mutated; removing the manifest commit entirely still passed it. It now goes
  through `refresh_and_commit()` and reads the file back off disk.
- `prefilter_safety.py` called itself a "Direct proof". It samples. It now
  reports what it is — a measurement on the pairs drawn — and prints that its
  tightest observed margin is +0.

## Two of the review's claims did not survive checking

- The Swiss variant-overwrite defect was **real**, and its figure exact: 3,669
  name-parts carry more than one spelling variant under the same
  `(lang, script)` key, and each overwrote the last. Fixed — variants are kept as
  coordinated lists. But the example given for it was wrong: the Arabic string
  said to have been lost from target 11641 appears nowhere in the Swiss file, and
  that target carries one English-language name with no variants at all.
- The reviewer reported the Swiss parser as reading the wrong element. It was:
  `identification` where the live schema says `identification-document`, and
  nationality was never read at all. Both fixed — **0 → 724** records with
  identifiers, **0 → 2,306** with a nationality.

## Known and not fixed

- **Run-together entity names whose corporate suffix is stripped.**
  `MyanmarEconomicCorporation` still misses `Myanmar Economic Corporation`,
  because the listing's tokens have the suffix removed before the length guard
  compares them, and the guard then reads the two as different lengths. The
  narrow residue of the 62.5%.
- **Single-token pairs inflate on the Winkler prefix bonus.** `JohnSmith`
  against a listing holding only `John` scores 88.9. This predates the
  run-together work and is untouched by it; fixing it means retuning the prefix
  bonus across the whole matcher.
- **Native script recall is 82.1%.** Where a publisher's native spelling differs
  from the client's, the tool compares strings rather than aligned tokens.

## What is still not fixed (as at round two)

- **Arabic and Chinese queries are not romanised.** Names publishers supply in
  those scripts are searchable in them, but there is no cross-script bridge as
  there now is for Cyrillic. The tool says so on the record and requires a
  Romanised spelling to be searched separately, rather than returning a bare nil.
- **The wider matcher gaps the reviewer listed remain** — fused particles
  (`Jan van der Waals` / `Jan Vanderwaals`), married and maiden names, entity
  names in translation, vessel name conventions. These are disclosed rather than
  silently absent.
- **Rollback is not detected.** A server or proxy serving a genuine but older
  list resets the retrieval clock. Publication date is now reported honestly
  where the publisher gives one, which makes a stale list visible on the record.
- **Concurrency is protected but not stress-tested.** The lock and the unique
  temporary files are in; a 12-thread hammer test is not.

# Round four — before publication

The third review closed with LADY R: an exact primary designation on two lists,
zero hits, exit 0. It listed nine new findings and thirteen ways the suites gave
false assurance. Everything in it was addressed on 02.09.2026 — the exact-name
rule, the self-retrieval gate, per-file digests and an alias floor for OFAC,
frozen records, delivery before rendering in batch, `status` validation, batch
`--json`, Swiss regimes and listing dates, cohorts that say when they are
empty. Two more defects were found by hand on 03.09.2026 before the fourth
review was fired, and are the reason the counts moved from 440 to 471.

## 18. Publisher bytes reached the terminal unsanitised (P21, open since round one)

`md()` escaped names on their way into the Markdown record. Nothing escaped
them on their way to stdout. A designation whose name carried an ANSI sequence
could recolour the line, a carriage return could overwrite it, a bidi override
could reverse it, and a newline could forge a line of the tool's own output —
"No candidate at or above 88." — beneath a real candidate. Worse, `normalise()`
did not strip the sequence either: an ESC-wrapped LADY R was indexed as the
parts 32MLADY, 0M and R, so the sequence's own digits became searchable name
and the real one did not.

`matching.strip_control()` removes C0 controls, DEL, C1, ESC/CSI/OSC sequences
and the bidi overrides U+202D/U+202E, and is applied inside `normalise()` and
`native_key()`. `screen.term()` applies it and folds all whitespace to one space
wherever a publisher or subject string is placed on stdout, and `render_text()`
passes its whole block through it once more at the door, so a field added later
without `term()` cannot carry an escape — only, at worst, a line break. Bidi
embeddings (U+202B/U+202C), which the UK, OFSI and EU lists really carry around
Arabic script, are left alone. JSON is untouched: the encoder escapes C0 by
specification and JSON is read by programs.

Tested with a throwaway cache in which a real OFSI record is renamed to carry a
CSI colour sequence, a carriage return, a bidi override, an OSC hyperlink and a
U+2028: the designation is still found (exit 2); no escape byte, carriage
return, override or separator reaches stdout; the letters survive on one line.
The assertion is made on the raw bytes, because `subprocess` in text mode
translates a lone `\r` to `\n`, and an assertion about `\r` on decoded output
passes for nothing. Twelve assertions in `test_screen.py`, ten in
`adversarial.py`.

## 19. A U+2028 inside one Canadian designation made the whole list unreadable

Found while counting control characters in the live lists for §18. One record
on the Canadian list carries U+2028 (LINE SEPARATOR) inside a field.
`json.dumps(ensure_ascii=False)` writes it raw; `str.splitlines()`, which
`read_source()` used to split the decompressed file, treats U+2028 — and
U+2029, NEL, VT, FF, FS, GS and RS — as a line break. The record split in two,
the second half was not JSON, and the reader refused the whole list as
"damaged". Every Canadian screen since the fetch was NOT SEARCHED. Fail-closed,
exit 3 — but a refresh had validated 5,690 designations, written them, and
committed a file its own reader could never read, and `status` never showed it
because Canada is not a default list.

Two changes. `read_source()` splits on `"\n"` only, the one line ending the
writer emits (`json.dumps` escapes `\n` and `\r` inside strings by
specification). And `refresh()` now reads the written file back through
`read_source()` and compares the count BEFORE the manifest entry is marked ok;
a reader that cannot read what the writer wrote is a failed refresh, recorded
with its reason and preserving the last good copy. The cached Canadian list
reads in full (5,690 of 5,690) without a refresh, because the file was always
whole; only the reader was wrong.

Tested in `integrity.py` with a copy of the OFSI list whose first record carries
all eight separators: `splitlines()` is shown to see more lines than records
(the control), `read_source()` reads it whole, and the separator survives inside
the record. The round trip is tested by stubbing the downloader and parser and
running the real `refresh()`: a list carrying separators is committed and reads
back; then, with `read_source` wrapped to drop one record, the same refresh
records `ok=false`, zero records and an error naming the round trip. The live
Canadian list is a regression assertion wherever it is cached. Nine assertions.

## Where the counts stand

```
tests/test_screen.py       113 assertions
tests/integrity.py         152 assertions
tests/adversarial.py       206 assertions
```

471 assertions, all passing on 03.09.2026 on Python 3.11, 3.13 and 3.14 (the
3.9 figure of 440 dates from 01.09.2026; 3.9 is no longer installed on the
build machine). The fourth review was fired on this tree, with a writable
temporary directory so that all three suites could run under it.

# Round five — the fourth review answered

The fourth review was the first that could not construct an exact Latin-name
clean nil on the untouched cache. It refused on two CRITICALs, five HIGHs and
four MEDIUMs, and asked for one thing above all: an exhaustive, refresh-bound,
end-to-end retrieval gate. Every finding was accepted except the whole-string
native scoring, which is documented rather than fixed.

## 20. One alias per designation passed for the whole alias file (critical)

`alias_floor()` counted designations carrying AT LEAST ONE alias. Keep the first
ALT row for each of OFAC's 8,811 aliased designations and drop the other 11,336
— 56% of the file — and the floor, the 20% shrink rule, the readback and the
manifest commit all passed. The exact published alias CUBAN FREIGHT ENTERPRISE
(UID 1287) then returned a clean nil, complete, exit 0. `parse_ofac` now returns
the ALT rows read and the aliases emitted; `alias_delta()` refuses a refresh
below 13,000 / 700 rows (live 20,147 / 1,110) or more than 20% below the last
good rows or aliases, and the baselines are carried across a failed refresh.
The review's scenario fails the floor and the shrink rule; a 30% fall in
emitted aliases with the row count intact fails on its own. Eight assertions.

## 21. A Latin-majority name with a Cyrillic surname was never romanised (critical)

`is_native()` asked whether a name was MOSTLY non-Latin. "Yury Viktorovich
Федоров" is Latin by count, so no romanisation ran, the homoglyph residue was
searched instead, and a fresh OFAC list returned a clean nil, exit 0 — while
"Yury Viktorovich Fedorov" found him at 100. `has_romanisable()` now triggers
the four romanisation systems on ANY Cyrillic letter. The review's query is a
regression test through the real `screen()` and through the CLI.

## 22. The index was a list (high)

The source records were frozen; the index built from them was a plain list,
and clearing it left the source "searched" in full with an exact vessel query
returning no hits, complete, exit 0 — AN SAN 1 again, one layer down.
`_index()` returns a tuple of tuples of tuples. Tested by attempting to clear,
append and mutate it, then re-screening AN SAN 1.

## 23. A rolled-back list read as fresh (high)

A publisher date is read from every dated list and was never compared. An OFSI
list dated 01/01/2000 committed over one dated 03/06/2026; `status` said age 0,
ok. `parse_list_date()` reads the UK, OFSI (day-first) and ISO forms;
`chronology()` refuses a refresh dated earlier than the last good one, carries
the baseline across failed refreshes, and yields to SANCTIONS_ALLOW_ROLLBACK=1
for a verified publisher correction. Where the publisher dates nothing (OFAC,
Canada) the manifest records that chronology cannot be established rather than
pretending. Seventeen assertions across seven scenarios.

## 24. A de-listed Swiss target looked like any other candidate (high)

Under `--include-delisted` a de-listed target was printed and written as an
ordinary candidate; the record said "Designated 2012-12-12" and nothing else.
The Swiss parser now keeps `delisted_on`; a de-listed hit prints a DE-LISTED
line on stdout, in the batch top-candidate column and in the record, with the
date. Parser version 3; every list refreshed.

## 25. The terminal sanitiser left the parameters behind (high)

`\x9b31mLADY\x9b0m R` became `31mLADY0m R` — the 8-bit introducer went and its
parameters stayed as name, scoring 70 against LADY R. Bidi isolates, marks and
embeddings survived. The batch `Screening records in …` line was raw. JSON
carried C1 and bidi characters raw under `ensure_ascii=False`. `CONTROL` now
consumes 8-bit CSI and OSC sequences whole and strips every bidi format
control — the embeddings the UK, OFSI and EU lists carry around Arabic script
included, because a terminal honours them and none is a letter; the outdir
line goes through `term()`; `json_safe()` escapes C1 and bidi characters as
`\uXXXX` in both JSON routes, so a parser reads the published bytes back
exactly and a terminal never sees them. One of my own assertions was wrong:
it expected the `D` in `\x9bD` to survive, and `D` is a valid CSI final byte.

## 26. The readback ran after the candidate had replaced the last good file (medium)

Repair 19 read back the INSTALLED file. A failed readback recorded `ok:false`
correctly — with the old file already gone. The normalised file is now written
to a `.candidate` path, read back through `_load_norm()` (the function
`read_source()` itself uses), and only then moved over the last good file; a
failed readback deletes the candidate. Tested: the last good bytes are
unchanged after a forced short readback, no candidate lingers, and the last
good count is carried on the failed entry.

## 27. Batch: a blank row corrupted `--json`; a bad request exited 3 (medium)

The blank-row line was printed as human text inside JSON output.
`validate_args()` — threshold, max-age, limit — now runs once before any row,
`--default-type` is validated, and a bad request exits 4 whether or not any row
could be screened.

## 28. The frozen-cache test ran no assertions (medium — a test, not the code)

`if entry.get("ok")` read whatever `entry` the previous test had left: a
deliberately failed refresh. The block printed its heading and asserted
nothing, and my earlier statement that freezing was "verified" rested on it.
It now reads the live manifest entry and fails loudly if OFSI is not cached.
The early refresh test also left `S.DATA` at the live cache, so the suite
tried to lock the real cache and aborted under a sandbox; it now redirects
`S.DATA` too.

## The release gate

`tests/release_gate.py` runs the real `screen()` — request validation, the
script gate, the record's own type, `include_delisted`, the prefilter, the
matcher, threshold 88 and `--limit 40` — for every primary name, alias and
native-script name on the selected lists, against the list that publishes it,
and requires the same source and uid back. Names the script gate refuses are
counted and listed separately, never as retrieved. It writes an attestation
bound to each list's normalised digest, the parser version and the digests of
the three code files. Every name is a full screen of its list — about 131,000
screens over the six defaults, hours single-threaded, so it runs across
processes (`--workers`, one pool per list) and is a pre-tag gate rather than a
unit test. `--sample N` gives a seeded quick run. On 03.09.2026 a 200-name sample from each of OFSI, the UN
and OFAC consolidated — 600 names — retrieved every accepted name; 22 were
refused by the script gate (native Arabic and Chinese spellings, by design).
The full run over the six default lists was started for the tag.

## 29. The parser's choice of field decided which queries could reach a name (critical)

A published spelling entered the Latin index or the native index according to
which field the parser had filed it in, and the two indexes are opened by
different queries. Both directions leaked. A native-script name filed under
`aliases` normalised to nothing and entered neither — the SOURUH COMPANY defect,
repaired at §11 by routing it to the native index. The reverse was never
repaired: a LATIN name filed under `nonlatin` went only to the native index,
which a Latin query never opens. OFSI files the Azerbaijani spelling of Ali
Akbar Salehi, `Əli Əkbər Salehi`, under `nonlatin` because of the schwa, and
that exact published spelling returned nothing on a healthy list — complete,
exit 0 — against OFSI UID 10955, which holds him.

`_index()` no longer reads the field. It takes every published spelling —
primary name, alias and `nonlatin` alike — and derives from each the
representations that spelling can actually support: the Latin form unless the
spelling is written mostly outside Latin, and a native key wherever it carries
any letter outside A-Z. `has_native_letters()` gates the second so that 19,329
ASCII OFAC designations are not each given a key no native query could match,
and `is_native()` gates the first so that homoglyph residue
("Александр Петров" → "A EKCA P ETPOB") is never searched as though it were a
name. Both directions are asserted, and asserted exhaustively rather than on
the one name the review supplied: every Latin-script spelling filed under
`nonlatin` across the lists — 353 of them — must be present in its own source's
Latin index, and every native-script name filed under `aliases` must carry its
native key. Four assertions, two of them over the whole corpus.

## 30. Romanisation replaced the query instead of adding to it (critical)

The mixed-script repair at §21 was built to stop homoglyph residue being
searched in place of a romanisation, and it did that by discarding the original
normalised query outright. That threw away the one form that reaches a
published Latin name written with a Cyrillic homoglyph. The EU publishes the
alias `JSС Krasmash` — the final "С" is Cyrillic U+0421 — which folds to
`JSC KRASMASH` and is its own listing under EU UID 179301. The tool romanised
it to `JSS KRASMASH`, deleted the original, and returned nothing: complete,
exit 0, on the exact published alias.

The romanisations are now added to the query rather than substituted for it,
and the original survives on the same test that governs the index — it is kept
where the name is genuine Latin text and dropped where the name is written
mostly outside Latin, which is where folding leaves nonsense. The empty-queries
path, which `min()` would have raised on, now falls back to the name as given.
Asserted end to end and at the point the defect lived, by capturing the exact
query forms: a Latin-dominant query carrying a Cyrillic letter must keep its own
normalised form AND gain the romanisations; `Кадыров` must NOT keep "KA POB"
and must still be searched as KADYROV. Five assertions.

## 31. Aggregate alias counters could not see a name leave (critical)

§20 replaced a count of aliased designations with counts of rows and emitted
aliases. The fifth review went under both. It deleted a single ALT row, and
separately substituted one name for another under the same UID; each preserved
every aggregate the tool checks — rows, emitted aliases, designations carrying
an alias, and that designation's own cardinality — and each made the exact
published alias CUBAN FREIGHT ENTERPRISE (UID 1287) a clean nil through the
real refresh path, complete, exit 0. No aggregate can catch this. Only the set
of names each designation carries can.

Every successful refresh now writes a ledger of exactly that — UID to the
normalised set of its published spellings — to `~/.claude/sanctions-data/
inventory/`, and writes it only after the list it describes is the list on
disk, so a refresh that fails its readback cannot baseline tomorrow's
comparison on names this machine never committed. `alias_removals()` refuses a
refresh in which a spelling has gone from a designation the list still carries,
and the refusal names what went. Three things are deliberately NOT losses: a
UID that has left the list entirely (de-listing is what these publishers do
every week, and the record count is where that is caught), a re-punctuation or
case change (the ledger is normalised, because that is the form a search
reaches), and a removal a human has authorised with
`SANCTIONS_ALLOW_ALIAS_REMOVAL=1`. That override is its own switch and not
`SANCTIONS_ALLOW_SHRINK`: letting a list shrink is not the same decision as
letting a published name vanish, and the suite asserts that the shrink override
does not open this door.

Enforcement is on the lists whose aliases come mechanically out of an auxiliary
file — OFAC SDN and consolidated, where the failure was demonstrated. Every
list writes a ledger, so the enforced set widens as each publisher's real alias
churn is measured. Nine assertions at unit level, plus both of the review's
attacks re-run end to end through `refresh()` against an isolated cache copy
with the download stubbed: each is refused, nothing is committed, the last good
cache is retained, and CUBAN FREIGHT ENTERPRISE stays findable at exit 2
throughout.

## 32. An exact published name lost its own search to approximations of it (high)

The fifth review's §B.4, repaired here because the release gate could not pass
without it. Hits were ordered by rank, then score, then the record's primary
name alphabetically. Nothing distinguished a name that IS the query from a name
that merely scores 100 against it: fuzzy containment gives a short query like
`Abdul` a score of 100 against every longer name containing it, and 173 UN
records tied there. The designation whose own published alias is `Abdul` — UID
113444 — sat at position 164 on an alphabetical tiebreak, and at the
operational `--limit 40` it was not returned at all. Fifteen names across five
lists failed the gate this way.

An exact hit already knew it was exact: `_scan` sets a score of 100 when a
candidate's own normalised name is in the query's exact set, before the fuzzy
matcher runs at all. That fact was simply discarded. It is now carried onto the
hit as `exact` and is the first term of the sort key, so an identity outranks
every approximation whatever the alphabet says. The flag is reported in the
JSON, where a fuzzy 100 and an exact 100 are now distinguishable to a caller
that cares about the difference.

Five assertions, and the one that would have caught the original defect is the
last: at `--limit 1`, the single hit returned for `Abdul` must be an exact
identity. The gate agrees — UN and OFAC consolidated went from FAIL to PASS on
the change alone.

## 33. Authorising a shrink authorised every name loss with it (critical)

The sixth review's N1. `refresh()` held one variable for two different
questions. `SANCTIONS_ALLOW_SHRINK=1` sets `previous = None` so that the record
count rules stand down — that is what the flag is for, and it is documented.
The per-UID ledger comparison was then handed the same nulled value, and
`alias_removals()` returns immediately on `previous is None`. So a flag that
says "this list is allowed to be smaller today" silently also said "and any
published spelling may vanish from a designation that is still on it". The
reviewer deleted CUBAN FREIGHT ENTERPRISE from the OFAC auxiliary file, ran the
real refresh under the flag, and got a committed list and a complete clean nil
on an exact published name.

There are now two baselines. `previous` is nulled for the count rules as
before; `prior` is passed to `alias_removals()` in full whatever the shrink
flag says. The only switch that reaches the name comparison is
`SANCTIONS_ALLOW_ALIAS_REMOVAL=1`, which is what it was always described as.

## 34. An unreadable ledger failed open, and the good refresh then destroyed it (critical)

The sixth review's N2. `read_alias_inventory()` answered an absent file, a
corrupt file and a genuinely empty ledger with the same `{}`, and the guard read
that as "nothing to compare against — proceed". The comment in the code said the
next good refresh would rewrite it, and that was the defect rather than the
mitigation: overwriting the file with invalid gzip both disabled the check and,
on the successful refresh that followed, replaced the evidence that it had been
disabled. Deleting a name under cover of it was accepted and produced a clean
nil.

`None` and `{}` are now different answers. `None` means there is no usable
ledger; the reader returns it for an absent file, an unreadable one, a
structurally wrong one, and — through a new `INVENTORY_VERSION` — for any
ledger written by an older build, since a version-1 ledger held no primary
names and must not be trusted as though it did. The guard fails closed on it:
where the list has a last good cache, the ledger is rebuilt from that cache,
whose digest the manifest already verifies, and the comparison is made against
the rebuild. Only where there is neither a ledger nor a cache — a genuinely
first refresh on this machine — is there nothing to compare, and only then does
the guard return.

## 35. A ledger of published names that did not hold the published name (critical)

The sixth review's N3, and the answer to a question five reviews had been
asking. `alias_inventory()` walked `aliases` and `nonlatin` and not `name`. A
designation with no aliases therefore had an entry of `[]` — OFAC UID 424,
BOUTIQUE LA MAISON, literally so on the live ledger — and its primary name could
be substituted through a refresh that passed the record counts, the alias
counts, the digest, the readback and the ledger comparison. No override, no
corruption, nothing damaged. Complete, zero hits, exit 0, on the exact name the
publisher had listed.

The inventory is now over `[name] + aliases + nonlatin`. The ledger version was
bumped in the same change so that every ledger written before it reads as absent
and is rebuilt from the last good cache rather than trusted.

## 36. ASCII membership is not a script test (high)

The sixth review's N4. `_LATIN_RE` was `[A-Za-z]`, and `is_native()` — a
majority-of-letters test — used it to decide whether a spelling was written
outside the Latin script. Every accented Latin letter counted against Latin. The
EU's `Černé září`, Latin script throughout, was classified as native, kept out
of the Latin index, and the ordinary folded query `Cerne zari` — the spelling
anyone without a Czech keyboard types — returned nothing on a healthy list.

The flaw had been latent for as long as the predicate existed. §29 promoted it
into a recall failure by making `is_native()` decide index admission. Unicode
already knows the answer: a Latin letter, however accented, has a character name
beginning LATIN. `is_latin_letter()` asks that question, with an ASCII fast path
and a cache, because it runs per character over about 100,000 published names.

## 37. A native-dominant query threw away the one spelling that reached its listing (high)

The sixth review's N5, and the mirror image of §30. A native-dominant query has
its folded form withheld, because folding Cyrillic leaves nonsense — "Кадыров"
becomes "KA POB" and that must never be screened as a name. But two questions
had one answer: whether the fold may be searched fuzzily, and whether it may be
recognised as an identity. A listing published as `CCC AB`, queried with three
Cyrillic homoglyphs, folds to exactly `CCC AB`, was romanised to `SSS AB`, and
returned nothing.

The exact key is now kept whenever it is non-empty. Only the fuzzy query form is
withheld from a native-dominant name, so homoglyph residue still cannot generate
approximations, but it can still reach a listing that literally carries that
spelling. Verified on live data: the wholly Cyrillic `ТАЕК РАК` returns UK
AQD0331 at 100.0 on the published alias `Taek Pak`.

## 38. A name published in its own script was not treated as an identity (high)

The sixth review's N6. §32 carried `exact` onto the hit and sorted on it, but
only the Latin-normalised branch ever set it. A native-script match that was
character-for-character the query — UN 2960872, `Умаров Доку Хаматович` —
scored 100 and reported `exact: false`, so it was ranked among the
approximations and, in a large enough collision, cut by `--limit`. The native
branch now sets the flag where the native key equals the query's.

`--limit` was tightened at the same time. §32 claims that an exact identity
survives the limit; sorting exact first makes that true for every list published
today, where the largest same-key collision is 28, but the claim is absolute and
"today" is not a guarantee. The limit now bounds approximations only: every
exact identity is returned however many there are.

## 39. An empty ledger is not a ledger, and a bootstrap must verify (critical)

The seventh review's R7-1, and §34 failing one level down. §34 separated absence
from emptiness in the READER — `None` for a file that is missing, unreadable,
structurally wrong or of an older version — and then the CALLER was written to
test only `old is None`. A syntactically perfect `{"version": 2, "uids": {}}` is
a dict, so it passed as data, the comparison iterated nothing, found nothing
missing, and let a deletion through. Writing a fix and then not asking what the
fix returns is how three of the last six criticals were made.

A source that has designations has spellings, so an empty ledger now reads as no
ledger. Two further bindings came with it. The ledger's digest, its designation
count and its version are written into the manifest by the refresh that produced
it, and a ledger that does not match what the manifest records is refused — a
false but well-formed ledger had otherwise only to be well-formed. And
`bootstrap_alias_inventory()` no longer reads through `load_records()`, which is
expressly tolerant and verifies neither digest, parser version nor count: it
reads through `_load_norm()`, against the recorded digest and the last good
count, so a readable-but-wrong cache can no longer launder a loss into the new
baseline.

⚠ The LAST GOOD count, not the recorded one. A failed refresh records
`records: 0` — the number that attempt committed, which is true — and verifying
the file on disk against nought made every rebuild fail. One refusal would then
have left a source that could never refresh again. §45 carries the identifying
fields across a failure for the same reason.

## 40. Changing the key is not losing the designation (critical)

The seventh review's R7-2. The ledger compared spellings per UID and exempted a
UID that had gone from the list, because de-listing is what these publishers do
every week and a designation's disappearance is the record count's business.
That exemption was a door: renumbering OFAC UID 424 to 999999424 while
substituting its primary name took BOUTIQUE LA MAISON out of the comparison
along with the old key, passed every aggregate, and returned a complete clean
nil on an exact published name.

A vanished key is now read as a de-listing only where the list actually got
smaller. Where it did not, the spellings that key carried must still be findable
somewhere on the list — which is what a genuine re-keying leaves behind and what
a substitution does not. Both halves are asserted: the renumber-and-rename is
refused, and a renumber that keeps the names commits, after which the name is
found under its new key.

Canada showed the same problem structurally and its parser is fixed with it. Its
UIDs were `Country-Schedule-Item-<row index>`, so swapping two otherwise
untouched publisher rows changed both designations' identifiers — which, to any
guard keyed on the identifier, reads as two designations leaving the list and
two arriving. The row position is gone from the key.

## 41. Reaching a name is not being it (high)

The seventh review's R7-3, and a regression of my own making. §37 kept the folded
form of a native-dominant query so that a listing published as that spelling
could still be reached. It kept it in the set that means IDENTITY. So the seven
Cyrillic letters `ТАЕК РАК`, which fold to the published UK alias `Taek Pak`,
came back at 100.0 with `exact: true` against a record carrying no such
spelling — and since §32 and §38, `exact` sorts ahead of every approximation and
escapes `--limit`. A visual confusable inherited both privileges.

I had reported that very query as evidence the §37 repair worked. It was
evidence of that: the name is reachable, and screening a homoglyph spelling is
exactly how a name typed to evade a list gets caught. I checked that it was
found and never checked what the tool then said about it.

There are two sets now. `q_exact` is identity — the query itself where it is
genuine Latin, and its romanisations, which are the same name in another script.
`q_reach` is reachability — a cross-script fold, which forces the candidate into
consideration at 100 and is reported as the approximation it is.

## 42. The codepoint as typed is not the script (high)

The seventh review's R7-4, and the second time this predicate has been wrong in
the same direction. §36 replaced an ASCII test with `unicodedata.name()
.startswith("LATIN")`. FULLWIDTH LATIN CAPITAL LETTER A does not BEGIN "LATIN",
and neither do the letterlike or mathematical alphanumerics, so `ＡＣＭＥ` was
still filed outside the Latin script — although `normalise()` decomposes it to
plain `ACME` before any comparison happens, so an ordinary `ACME` query was
looking for it in an index it was not in.

The question is now asked of the form matching actually uses: NFKD first, then
the Unicode name of the pieces. Cyrillic is untouched by NFKD and stays native,
which is the distinction that has to survive. Eight characters are asserted
directly, in both directions.

## 43. Nothing after the install may cost us the last good file (high)

The seventh review's R7-5. §34's comment explains why the ledger is written after
`os.replace` and that reasoning still holds — a ledger written before the
readback would baseline tomorrow's comparison on names this machine never
committed. What it missed is that the install is not the last thing that can
fail. A ledger write raising after `os.replace` left the new file installed, the
manifest unwritten, the refresh reporting failure, and the last good file gone.
It failed closed and cost availability doing it.

A hard link now holds the old bytes from just before the install until
everything that can still fail has not, and restores them if anything does. The
test drives a real refresh with the ledger writer raising and compares the file
on disk, byte for byte, with what was there before.

## 44. The exact cohort is bounded, and the bound says so (medium)

The seventh review's R7-6. §38 promised that every exact identity is returned
however many there are, which left `--limit` unable to bound output at all: a
query exact against two thousand records returned two thousand, and 1.4 MB of
JSON. A safety property that becomes a denial of service on the reader is not
serving the reader.

The cohort is bounded at 500. What the bound withholds is counted and stated, on
every route, in the caveats block — because a withheld identity that announces
itself is a display limit, and a withheld identity that does not is the defect
the promise exists to prevent. `ANSAR AL SHARIA --limit 1` still returns all
sixteen of its exact identities.

## 45. What produced the RESULT, not only the file (critical — found in use, not in review)

On 07.09.2026 the copy of this tool installed as a skill was four rounds out of
date. It shared this cache, at the same `PARSER_VERSION`, so it did not fail
closed — and it reported `Lists searched: 6 of 6` and `No candidate`, exit 0, on
`Əli Əkbər Salehi` and on `Cerne zari`, both of which are on the lists. Nothing
in the record it produced could have told anyone which code had produced it.

`PARSER_VERSION` binds a cache to the code that wrote the parsed file. It has
never spoken for the matcher, the exactness rules, the completeness gate or the
ledger — and every defect in §§29-44 lives in those. `ENGINE_VERSION` is the
generation of the code that decides what a RESULT says. It is bumped for any
change to them, it is written into the manifest by the refresh that produced the
cache, and `read_source()` refuses a cache written by a different generation
exactly as it refuses a differently-parsed one. The digests of `screen.py`,
`sources.py` and `matching.py` go into the manifest beside it — auditability
rather than a gate, so a result can be tied to the code that produced it after
the fact.

Two smaller repairs belong to the same family. The manifest path is resolved at
call time rather than bound at import, so redirecting `DATA` moves the manifest
with it: the per-UID ledger had that bug and it was fixed there while the
manifest kept it, and an isolated refresh was writing its own `meta.json` and
reading the real one. And the ledger guard is enforced on all six default lists
rather than two — the seventh review answered its own standing question with
that gap, removing `Černé září` from otherwise valid EU raw XML and getting
exit 0 through a real parser and a real refresh.

⚠ **Four of those six publishers have never been replayed across consecutive
snapshots under this rule.** Ordinary churn that the rule reads as a loss will
REFUSE a refresh rather than accept it. That is the intended direction of
failure, and `SANCTIONS_ALLOW_ALIAS_REMOVAL=1` is the release valve — now
recorded in the manifest when used, since an override that leaves no trace is
indistinguishable afterwards from a refresh that had nothing to authorise.

## 46. Two version numbers meant old code checked neither (critical)

§45 introduced `ENGINE_VERSION` to close the drift of 07.09.2026 and closed half
of it. It stops NEW code reading an OLD cache. The incident was the reverse — a
four-round-stale install reading a CURRENT cache — and old code cannot check a
field it has never heard of. The eighth review proved it: a build from `df2e980`
read a manifest declaring `engine_version: 999` and returned complete, exit 0.
The stale install failed closed on the day only because `PARSER_VERSION` happened
to move 3→4 for an unrelated Canadian parser change.

There is now one number. `CACHE_GENERATION` is written into `parser_version` —
the field every build back to the first one validates — and into
`engine_version`, and a test asserts the three are equal so a future engine-only
bump cannot reopen it. The same old build, against today's cache:

```
Lists searched: 0 of 6 (0 designations)
  x NOT SEARCHED — UK Sanctions List: parsed by version 5, this is version 3
exit 3
```

Against this morning's cache it had said `Lists searched: 6 of 6`, `No candidate`,
exit 0.

## 47. An unbound manifest vouched for nothing, and was trusted anyway (critical)

§39 bound the ledger to its cache by digest and size — conditionally. `if
recorded and …` and `if n is not None` meant that a manifest which simply did not
carry those fields trusted whatever ledger was on disk. The eighth review put a
one-designation ledger beside a real list and a deletion passed: complete, zero
hits, exit 0. A binding that is skipped when absent is not a binding; no binding,
no ledger.

## 48. Nothing verified the manifest (critical)

Every check in `sources.py` verifies one artefact against what the manifest
records, and until now nothing verified the manifest. Replacing it wholesale with
an older, internally consistent generation — whose digests genuinely match an
older ledger and an older cache — moved a published name from one hit at exit 2
to zero hits at exit 0, with every individual binding still valid.

A monotonic `generation` is written into the manifest and a watermark kept beside
it. A manifest older than the highest this machine has committed is not read, and
an unreadable manifest already meant "nothing is known about the cache", which is
the same answer. The watermark is written AFTER the manifest, so a crash between
the two leaves it behind rather than ahead — behind reads as valid, ahead would
refuse a manifest this machine had just legitimately written. Restoring a whole
cache directory from a backup moves both together, which is a deliberate restore
rather than a substitution, and for dated feeds the chronology quarantine is the
check that then applies.

## 49. The protected region was not the whole commit (high)

§43 took a hard link before `os.replace` and restored it if the ledger write
raised. The eighth review raised in `raw_fingerprints()` instead — which sits in
the entry built AFTER that region, where `finally` had already unlinked the
backup — and the new file stayed installed on a refresh reporting failure, with
the retry then refusing for good. The whole commit, entry construction included,
is now inside the protected region.

## 50. Counting cannot tell removal from replacement (critical)

The eighth review's remaining bypass, and the end of a line. §40 corroborated a
vanished designation key against the record count: a key that disappears is a
de-listing where the list got smaller, and a substitution where it did not. The
answer was to make the count agree — renumber a designation and rename it, then
delete a second one so the total falls. 19,329 to 19,328, the exemption applies
to the designation that was actually replaced, and its published name is gone.
Complete, zero hits, exit 0.

Counts are the wrong instrument and no arrangement of them is the right one. The
ledger now records two things beside the spellings: **the publisher's own
reference**, and **a fingerprint of the fields that are not the name** — type,
regime, measures, date of birth, nationality, identifiers, address, listing date.
When a key disappears and its spellings have gone from the whole source, the
question is whether something ARRIVED wearing that reference or those fields. If
so the designation was replaced in place and the name it carried is a loss.

The reference is the stronger of the two and it is free: all six default lists
publish one, at 100% coverage, and on OFSI, the UN and the EU it is a different
value from the identifier this tool derives — so renumbering our key does not
touch it.

**A de-listing is earned, not assumed.** There is a third branch, and it is the
one that makes this hardening rather than a heuristic. OFAC UID 424 is one of
seventy-one Cuban entities carrying nothing but a type, a regime and a measure —
no date of birth, no nationality, no identifier, no address. Nothing
distinguishes it from the other seventy, so the absence of its fingerprint among
the arrivals is not evidence of anything. Where the evidence cannot speak, the
disappearance is refused and the name is named.

**Measured cost.** The proportion of designations whose fingerprint identifies a
class rather than a designation, and therefore the refusals to expect when one of
them is genuinely de-listed:

```
uk-sanctions-list   12.0%      ofac-sdn    39.3%
ofsi                10.2%      ofac-cons   36.2%
un                   9.2%
eu                   9.1%
```

Roughly two refusals per twenty European de-listings, roughly eight per twenty on
OFAC. Each names the spelling that went, and
`SANCTIONS_ALLOW_ALIAS_REMOVAL=1` authorises it and is recorded on the manifest.
That is a real operational cost, chosen deliberately over the alternative, which
is a guard that stays quiet by assuming the innocent explanation.

⚠ **This paragraph was wrong, in both directions, and §53 corrects it. It is
left standing because a limit stated wrongly is worse than one not stated at all,
and the record of that should be legible.** It read:

> Where a publisher's own reference moves with the identifier — the UK list and
> both OFAC lists, where they are the same field — and the designation is one of
> the unidentifiable ones, an attacker who rewrites the reference, the identifier
> and the name together is indistinguishable from a de-listing followed by an
> unrelated addition.

Rewriting reference, identifier and name together is in fact CAUGHT: the
fingerprint survives all three edits. And the unidentifiable designations are the
ones the third branch PROTECTS, not the ones it exposes — the exposure was the
other 60 to 91%, and it needed a fourth edit rather than a special kind of list.
See §53.

## 51. Bumping the generation made the tool unable to upgrade itself (critical, found in use)

Not a review finding: it appeared the moment §46's generation moved for the first
time. §39 rebuilds a missing ledger from the last good cache and requires that
cache to be at the current parser version — which, on an upgrade, it never is by
definition. Every enforced list refused: *"has a last good cache but no readable
ledger … refusing to commit"*. The tool could not refresh itself out of the state
its own version bump had created.

A generation change means there is no comparable baseline: the previous cache was
written by different code and its ledger may legitimately differ from what today's
parser produces, so treating it as a baseline would manufacture losses that never
happened. The comparison is skipped once, and the skip is written onto the
manifest as `alias_baseline` rather than passed over in silence. The refresh after
it has a current-generation ledger and is compared normally.

## 52. Identifiability is a fact about the ledger, not about what arrived (critical)

§50 refuses a disappearance it cannot account for, and decides whether it can by
asking how many designations share the vanished one's fingerprint. It counted
them in the NEW inventory — the file just supplied — which handed the test to the
party it exists to constrain.

OFAC UID 52749 sat in a fingerprint group of four, one above the threshold, so
its disappearance would have been refused. Renaming it, renumbering it and
restating one stable field in the same edit removed it from its own group: three
remained, the group read as specific, the designation read as identifiable, and
the substitution committed. `SICHUAN JUXINHE NETWORK TECHNOLOGY CO., LTD.`
returned complete, zero hits, exit 0.

Whether a designation was identifiable is a fact about the state being compared
FROM — the one this machine last verified and wrote a ledger for — and it is now
counted there. The regression test finds a designation sitting in a group of
exactly `FINGERPRINT_SPECIFIC + 1` on the live list, does all three edits at once,
and requires the refusal.

## 53. A conjunction breaks on any one term (critical)

The tenth review's first critical, found by a reviewer that could run to
completion. §50 rescues a vanished designation's name on three grounds: something
arrived carrying the same publisher reference, or the same fingerprint, or the
designation was never identifiable in the first place. The first two are written
by whoever supplies the file. The third protects only designations that nothing
distinguishes — 12.0% of the UK list, 9.1% of the EU's.

`designation_fingerprint()` is a digest over eight fields at once, so restating
**any one of them** changes it and `arrived_fp[old_fp]` is empty. Rename a
designation, renumber it, and append four characters to its programme code, and
none of the three grounds fires. Reproduced on OFAC SDN 10000, `CANO CORREA JHON
EIDELBER`, sitting in a fingerprint group of one: the refresh committed, no
override, nothing on the manifest, nothing on stderr, and the published name
returned `complete: true`, zero hits, exit 0.

The residual §50 described was therefore the wrong 10% of each list. The exposure
was the other 88 to 91%, and the paragraph is corrected above rather than quietly
replaced.

A digest of eight fields answers one question; the fields answer eight. The
ledger now carries `axes` — identifiers of at least four characters, addresses of
at least eight, and dates of birth paired with a nationality — and they are
compared **one at a time**, each filtered by its own frequency in the ledger so
that a date of birth shared with hundreds is not treated as evidence. Restating a
programme code is cosmetic; restating a passport number is not, and the previous
rule could not tell them apart. The same attack is now refused and the name is
retained.

## 54. Nothing guarded how the ledger got its fingerprints (critical)

The tenth review's second. §52 moved the identifiability test to the old ledger,
because the arriving file is written by the party the test constrains. Nothing
guarded how the ledger came by its fingerprints — and a designation that STAYS
was only ever checked for its names.

So the attack takes two refreshes. The first restates one stable field of a
designation that stays, which costs nothing because nothing looks, and moves it
out of a crowded fingerprint group; the ledger then records it as identifiable.
The second substitutes it on that footing. Reproduced on `BOUTIQUE LA MAISON` —
the suite's own canary, the designation §50's test asserts is protected precisely
because nothing distinguishes it.

Leaving a shared identity group without leaving the list is the one change to a
designation's non-name fields that always precedes a substitution and never
anything else. It is now refused on its own, before any name has gone, under the
existing override.

## 55. The ledger tracked a form the index never builds (high)

`alias_inventory()` recorded `M.normalise(cand) or M.native_key(cand)` — the
first that was non-empty. For a Cyrillic spelling `normalise()` is non-empty: it
is homoglyph residue. So the native key, which is the form the index actually
searches, was never recorded, for **78.3% of native-script spellings**. A ledger
that tracks a form no search reaches is answering a different question from the
one the user asks.

It now derives exactly what `screen._index()` derives — the Latin form unless the
spelling is native, the native key wherever it carries any letter outside A–Z,
both where both apply. Measured after the change: **0 of 34,692** index keys on
the UN and EU lists are absent from the ledger.

## 56. Losing the manifest stood the guard down (high)

`had_cache` was computed from the manifest entry alone, so a manifest that was
missing, unreadable or refused turned a full cache into "a genuinely first
refresh on this machine" and `alias_removals()` returned without comparing
anything. A parsed list on disk is itself evidence that this is not a first
refresh, whatever the manifest says. The bootstrap then runs, finds no recorded
digest to verify against, and the refresh is refused — which is the right
direction. The suite asserts both halves: with the file gone it is a first
refresh, and with the file present and no ledger it is refused.

## 57. The filter excluded what the scorer calls exact (critical)

**The worst defect in this document, and it survived ten reviews on the untouched
cache with nothing tampered with.**

OFAC SDN 48715 is a designated vessel, published as `K M A`, with no other name.
`score("KMA", "K M A", "entity")` is 100.0 — the scorer has a branch for names
whose parts have been split or run together, written for exactly this, and
`tests/test_screen.py` asserts it. The bigram prefilter sits above that branch,
and `"KMA"` and `"K M A"` share **no bigram at all**, so the record was discarded
before the branch could run:

```
$ python3 screen.py check "KMA" --type vessel
Lists searched: 6 of 6 (38,524 designations)
No candidate at or above 88.0.
$ echo $?
0
```

Thirteen published spellings across nine designations went the same way, four of
them OFAC vessels. `1P` returned a clean nil against `1-P`, published on four of
the six lists.

Ten rounds of review missed this, and the reason is worth recording: **every test
this project has ever written queried a name the way the publisher spells it.**
The suites, the release gate and every adversarial probe took a published
spelling and looked for it. Not one of them typed a name the way a person would.

`bigram_mask()` now includes the bigrams of the de-spaced form in both masks. It
costs 2.4 points of prefilter pass rate and changes no score. A cheap first gate
has no business excluding a name the scorer would call an exact match, and the
suite now asserts the general property over the whole corpus, not the one case.

## 58. Biography chose the page instead of ordering it (critical)

Hits were sorted by rank, and rank is the score adjusted by biographical
agreement: a conflicting date of birth costs six points. With `--limit`, ordering
selects. So supplying a date of birth for `Mohammed Ali` dropped **22 of the 40
designations shown**, including one scoring 95.5 on its name across five lists,
and promoted candidates at 89.8 — chosen because their listings publish no date
of birth at all. Two screening records for the same subject on the same day,
under identical headline text, one naming a designation five times and the other
not at all.

`README.md` says a date of birth never suppresses a candidate. It does now:
selection is by the name score, and rank orders what survived. Measured on the
same query: 22 dropped before, 0 after.

## 59. The publisher's own spelling was refused (high)

The UK list and OFSI publish Syria's president as `Baššār Ḥāfiẓ al-ʾAsad`. The
half ring is U+02BE, category Lm, with no Latin Unicode name, so the script gate
counted it unromanisable and refused the request at exit 4 — under a message
telling the user that "a search on this spelling could not find a designation
even if one exists". It normalises to `BASSAR HAFIZ AL ASAD`, which is the string
in the index. The release gate had filed it under "refused by design".

A name that already yields a searchable Latin form is searched. The refusal
remains for names that reach no Latin at all, and the suite asserts both.

## 60. Two more places the tool knew something and did not say it (high)

The identity/reachability split of §41 was written inside the romanisation
branch, which only Cyrillic reaches. A **Greek** homoglyph query took the default
above it and was reported `exact: true` — `ΙΜΑΜ ΝΑΙΒ` against UK AFG0014's
`Imam Naib` — while the identical Cyrillic case correctly reported false. A fold
across scripts is a fold across scripts; which alphabet it came from does not
change what it proves. The split now applies to any query written outside Latin.

And `batch` text was the only route that never rendered `Outcome.caveats`. A
Cyrillic subject printed `19  complete` and said nothing about the romanisations
the tool had guessed on the reader's behalf. A caveat that appears on five routes
out of six is a caveat the reader of the sixth does not have.

## 61. A country was matched as a substring (high)

`country_verdict()` was `q in hay`, a naked substring test over the nationality,
address and regime run together. `US` is inside `RUSSIA` and inside `BELARUS`, so
`--nationality US` reported "country match" against **5,989 designations**,
almost all of them Russian, and moved every one three points up the page. Since
§58 that no longer removes anything from view, but it still promoted the wrong
candidates to the top of it.

A country is compared as whole words now, and a two- or three-letter code is
expanded before comparison rather than matched as a fragment of somebody else's
country. `US` against the corpus: 5,989 designations before, 60 after. The map is
deliberately not exhaustive — a code that is not in it is compared as written,
which is the honest failure, because an annotation that is absent costs a reader
nothing and one that is wrong moves a candidate.

## 62. The default withheld nearly half the corpus and called it Complete (high)

`--type` defaulted to `individual`. Every entity, vessel and aircraft — **46.3%
of the designations** — was skipped, while the text said `Lists searched: 6 of 6
(38,524 designations)` and the record said Complete. A nil return that covered
half the designations is precisely the shape this tool exists to avoid, and it
was the shipped default.

The default is `any`. A narrowing the user asks for is still available and now
says what it cost: screening `Mohammed Ali` as an individual reports that 17,829
designations of other types were not compared. §57's vessel is the case in point
— `KMA` needed `--type vessel` to be found at all, and now finds it by default.

## 63. The manifest knew things the reader was never told (high)

`alias_baseline` and `alias_removal_override` were written onto the manifest by
`refresh()` and read by **nothing** — not `screen.py`, not `SKILL.md`, not
`README.md`. A result produced against a list whose refresh skipped the
published-name comparison, or was authorised to drop names, was indistinguishable
from one that passed it.

Both now appear on the source's provenance row and in the caveats, on every
route: *"the refresh that produced this cache did not fully verify that its
published names survived — …"*. Provenance the reader cannot see is not
provenance. The suite asserts all three states: the override, the
generation-change skip, and an ordinary refresh that carries no note.

## 64. Absence of evidence had become authorisation (critical)

The eleventh review's R11-1, and the end of the line §50 started. When a
designation's key vanished and its published names had gone from the whole
source, three things could excuse it: nothing arrived carrying the same
publisher reference, nothing arrived carrying the same fingerprint, and the
designation had been identifiable enough for those absences to mean something.

Every one of those is an absence of evidence, and each fell to editing one more
field — first the reference (§40), then a stable field (§53), then the field
that moved it out of its identity group (§54). The review then found two more:
the successor maps were built from ARRIVALS only, so substituting onto a
designation the ledger already knew went unseen; and a designation carrying a
full date of birth but no stated nationality had no identifying axis at all,
because dates were only recorded in company.

The reviewer put the principle better than the code did: **the absence of an
eligible axis must not convert an unexplained disappearance into an authorised
de-listing.** So it does not, and the three exemptions are gone. A published name
that leaves a list is quarantined and named, and a human authorises it.

Every current designation is now a possible carrier of identity, not only the
newly-arrived ones, and a sufficiently complete date is an axis on its own. What
that evidence is *for* has changed: it no longer decides whether to refuse — it
decides what the refusal SAYS. A refusal now tells the operator whether the
designations that went left their identifying detail behind on the list, which is
what a substitution looks like, or took it with them, which is what an ordinary
de-listing looks like. Both are quarantined; only one is worth an hour.

⚠ **This refuses more than any previous version.** A refresh in which any
designation is de-listed will now stop and name it. That is the cost of the rule
and it was chosen deliberately over a guard that stays quiet by assuming the
innocent explanation.

## 65. Initials run together are the ordinary spelling (critical)

§57's family, one layer down. The UK publishes `P.K.T. MUNGMEE CO., LTD`. A
person types `PKT MUNGMEE CO LTD`. The record normalises to six tokens and the
query to four, the initials score as fragments against whole words, and the name
reached **79.9** against a threshold of 88:

```
$ python3 screen.py check "PKT MUNGMEE CO LTD"
Lists searched: 6 of 6 (38,524 designations)
No candidate at or above 88.0.
[exit 0]
```

A complete nil, on a healthy cache, for the ordinary spelling of a designated
company. `CSG TRADING` and `SMS TELECOM` went the same way.

The scorer already knew to compare names with their spaces removed — §57 quotes
the branch — but it only looked when ONE side was a single token. It now looks
whenever the two sides are tokenised differently, under the same length-ratio
guard that stops a fragment inflating into a match. All three now retrieve at
100. This is the second time this family has produced a live clean nil, and both
times the cause was the same: the tests spelled names the way the publisher does.

## 66. A tie-break is a selection (high)

§58 moved rank out of the primary sort key so that biography could not remove a
candidate from view. It left rank as the tie-break — and at equal name scores a
tie-break decides who is shown. **34 of the 40 candidates displayed for `Abdul`
changed on supplying a date of birth**, every one of them scoring 100.0.

The tie-break is now the source and the uid, which no fact about the subject can
move. Asserted across a date of birth and a nationality: the designations shown
are identical.

## 67. Sudan is not South Sudan (medium)

§61 replaced a substring test with whole words, which distinguishes `US` from
`RUSSIA` because neither word of the one is a word of the other. It does not
distinguish `SUDAN` from `SOUTH SUDAN`, where every word of the query is a word
of the listing. They are different states with different regimes on the same
lists.

A country is now matched from the START of a published value: `IRAN` names
`IRAN (ISLAMIC REPUBLIC OF)` and `RUSSIA` names `RUSSIAN FEDERATION`, while
`SUDAN` does not name `SOUTH SUDAN`. An address, being free text, is still
searched for the country as a whole phrase anywhere inside it.

## 68. The record did not name the code that wrote it (medium)

§45 put the engine generation and the module digests on the manifest so a result
could be tied to its code after the fact — and the durable screening record, the
thing someone reads a year later, carried neither. A build identifier the reader
never sees answers nobody's question. The record now opens with what produced it.

## Where the counts stand

```
tests/test_screen.py       130 assertions
tests/integrity.py         186 assertions
tests/adversarial.py       374 assertions
```

690 assertions. 546 of them passed on 03.09.2026 on Python 3.11, 3.13 and 3.14;
the twenty-seven added on 05-06.09.2026 cover the fifth review's three criticals
(§§29-31); the sixteen added on 07.09.2026 cover the sixth review's six findings
(§§33-38); the thirty-two added later the same day cover the seventh review's
six (§§39-44) and the engine generation (§45).

**619 of the 621 pass. The two that do not are one publisher being down**, and
they are the same assertion in two suites: the Swiss whole-list endpoint has been
serving an HTML error page in place of its XML since 07.09.2026, so the refresh
is refused, the last good copy is kept, and the list is marked not searched.
Switzerland is not a default source and no default result depends on it.

⚠ Those two assertions used to ABORT their suites rather than fail. The guard
asked the manifest whether the last refresh had committed, which is not the same
question as whether the file on disk can be read by the code running now — and
when the answer diverged, `read_source()` raised in the middle of the run and
every assertion after it went unexecuted. The guard now asks the reader, fails
loudly, names the publisher error, and carries on. A suite that quietly executes
fewer assertions passes just as loudly as one that fails.

The same thing happened to EU three days earlier, and the record of it is kept
here because it is the honest account of what this tool does while a publisher is
down. **Between 05.09 and 07.09.2026 a run did not show them all passing, and the
reason was not this tool.** The EU consolidated endpoint returned HTTP 500
throughout that window; it came back on 07.09.2026 and the list refreshed
cleanly at 6,234 records, so the qualification below is now history rather than
a live caveat. It is kept because it is the honest record of what the tool did
while a publisher was down.
The tool does what it is built to do — refuses the refresh, keeps the last good
copy, marks the list not searched and every result incomplete, and exits 3
rather than 0 — and the EU-dependent assertions therefore either fail or do not
run at all. Measured on 06.09.2026 with the endpoint down: 112 of 113 in
`test_screen.py`, 182 of 183 in `integrity.py`, 232 of 250 in `adversarial.py`.
Every one of those failures was reproduced identically against the tree as it
stood BEFORE the §§29-31 repairs, so none of them is a regression; the two
failure sets are byte-identical. The §§29-31 assertions themselves all pass,
and the one that would otherwise depend on the EU endpoint puts its question to
the last good EU data on disk instead of skipping.

## Where the release gate stands

Run over EVERY published name — primary, alias and native-script — on all six
default lists, at the operational `--limit 40`, each name against the list that
publishes it and requiring the same source and uid back. Completed 08.09.2026 on
the round-eleven tree; the attestation records cache generation 7 and the digests
of the three modules that produced it, and those digests are the files on disk.

```
uk-sanctions-list   29,062 names   28,179 retrieved     883 refused   0 FAILED
ofsi                26,561 names   25,741 retrieved     820 refused   0 FAILED
un                   4,146 names    3,769 retrieved     377 refused   0 FAILED
eu                  30,686 names   29,491 retrieved   1,195 refused   0 FAILED
ofac-sdn            39,547 names   39,547 retrieved       0 refused   0 FAILED
ofac-cons            1,591 names    1,591 retrieved       0 refused   0 FAILED
                   ────────────────────────────────────────────────────────────
                   131,593 names  128,318 retrieved   3,275 refused   0 FAILED
```

**Every published name the tool accepts retrieves its own designation.**

The corpus is 94 names larger than the run of 07.09.2026 because the UK list and
OFAC SDN both grew between the two runs — ordinary publisher additions, which the
refresh committed without complaint.

The 3,275 refusals are the script gate declining names it cannot romanise —
Arabic, Han, Hebrew and the rest. They are counted and listed by name, never
scored as retrieved, and the gate treats them as not-a-failure. That is the fifth
review's §B.5: a question about what the gate certifies, not about the matcher.

⚠ **This gate is necessary and it is not sufficient.** It asks whether every
published name retrieves itself when typed EXACTLY as the publisher spells it,
and twice — §57 and §65 — the defect that mattered was a name typed the way a
person would type it, which this gate does not ask about and never found. Both
were caught by a reviewer, not by the gate. Read that limitation as the main
thing this section says.

Nothing enforces this gate at promotion or at runtime. It is a pre-tag capability
claim, run by hand, and the fifth and sixth reviews both said so.
