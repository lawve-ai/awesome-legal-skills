# Evaluation/preview distribution — v1 / Dystrybucja ewaluacyjna

**No public-ready claim, license grant, legal compliance, publication, commit
or tag. / Nie jest to gotowe publiczne wydanie ani potwierdzenie zgodności.**
This is a bounded distribution deliverable, not completion of LA-021/LA-025.
The ZIP includes a snapshot of existing runtime work, including dirty files;
packaging does not independently approve their contracts or DoD.

## Build and verify / Budowanie i kontrola

From `legal-abduction/`, Python >=3.12, stdlib:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONHASHSEED = '0'
New-Item -ItemType Directory -Path 'artifacts' -ErrorAction Stop
python -B -X utf8 scripts/package_preview.py --out artifacts/legal-abduction-preview-v1.zip --smoke
python -B -X utf8 scripts/package_preview.py --check artifacts/legal-abduction-preview-v1.zip --smoke
Get-FileHash artifacts/legal-abduction-preview-v1.zip -Algorithm SHA256
python -B -X utf8 tests/test_distribution.py -v
```

If `artifacts` already exists, omit `New-Item`; choose a **new** archive name
for another snapshot. The script never overwrites an existing ZIP.
Installed bundles exclude tests; run developer tests only from source.
The installed packager can reproduce the ZIP without tests/backlog.
Reproducibility means identical payload bytes → identical ZIP bytes: sorted
entries, fixed timestamps/modes, ZIP_STORED (no compressor variability),
canonical manifest, no machine paths or wall-clock time in archive metadata.

`--smoke` validates first, extracts only exact allowed entries to a fresh
temporary directory, runs three configured Python subprocesses (CLI version,
CLI help, schema/template/policy loading), and verifies no file changes or
case data in the extracted skill. This is **not** a clean independent host,
Agent Skills activation, full none E2E or reproduction of an exhibit.
Temporary extraction is disposable synthetic test material, not existing data.

## Inclusion/exclusion / Zawartość

An exact, reviewable per-file allowlist in `scripts/package_preview.py`
includes SKILL, README, launcher, all current runtime modules, schemas/SQL, required
lexicons, PL/EN locales/templates, policies, user/deployer/install docs,
workflow/legal references and proposed evaluation tools.
`BUNDLE-MANIFEST.json` records every payload SHA-256 and a canonical map digest.
The builder rejects missing/changed-during-read files, links/reparse paths,
known credential patterns and broken local Markdown links. ZIP verification
rejects duplicates, additions, missing files, traversal, nonregular/encrypted
entries, oversize archives and manifest/hash mismatches.

Excluded by construction: cases/corpus/reviews/runtime DBs, `.lacase`, originals,
capabilities, `.env`, credentials, Git/editor configuration, caches/bytecode,
tests/vendor fixtures, backlog/template/PRD, developer evidence, decisions,
architecture, traceability and the resulting ZIPs. Never broaden this to
recursive whole-directory packaging. Do not add case data under an allowed
source filename. Known-pattern scanning is not a proof of absence of secrets:
manually review every allowed file and retain the manifest.

## Gates / Bramki

| Gate | Evidence still required / Brakujące dowody | Owner / Właściciel |
| --- | --- | --- |
| LA-021 dependencies | LA-001 blocked; LA-005/006 review FAIL with later fixes awaiting re-review; LA-010/012/014 pending review. Historical snapshots do not prove current DoD | engineering + independent reviewer |
| REPORT_SOURCE | Missing real Report, enums/predictions/coverage/reference examples/report structure fidelity | product |
| LA-022 | Full regression, traps, SQLite/PostgreSQL and host/Windows envelope | engineering |
| LA-023 | Actual A/B activation, none workflow, injection and host-B resume; no synthetic fixture claimed as real-agent evidence | host owner + reviewer |
| LA-024 / Q4,Q8,Q9 | Approved synthetic corpus, quality harness, usage/tariffs, repetitions/CI, reviewer minutes; no measured savings yet | data + human reviewers |
| Q10 | Human provider/high-risk role decision, dated and scoped | legal + stakeholder |
| Q11 | Approved license and distribution permissions; no guessed LICENSE | legal + product |
| Q12 | Exhibit legal status and professional-ethics acceptance | legal |
| LEGAL_VERIFICATION | Official law/amendment identifiers and dates, independently verified | qualified legal reviewer |
| LA-025 | Complete go/no-go evidence and explicit separate publish authorization | release owner |

P1/P2 do not redefine P0, and the preview adds none of their dependencies.
Passing ZIP tests is not passing these gates. PL: wyniki testów pakowania nie
zamykają zadań, pomiarów ekonomicznych ani zgód prawnych.

## Known local regression / Znana regresja lokalna

During preview preparation, `tests/test_profile.py` ran 39 tests with 1 failure:
`CliTests.test_commands_exempt_from_corpus_gate_are_an_explicit_allowlist`.
Current existing CLI registers `case` as exempt in addition to the four names
expected by that test. This bounded deliverable does not change the existing
CLI or weaken its test. Review the case-command/consent trust boundary in its
own task before declaring technical P0. Other tested modules and counts are
recorded in developer evidence, deliberately excluded from the ZIP.
