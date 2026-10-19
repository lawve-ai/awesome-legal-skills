# Host degradation (LA-006)

`doctor` detects capabilities and never installs anything or changes permissions. Every value is tagged
`declared`, `observed` or `unverifiable`; persistence between sessions and the host level are never
reported as verified. `human_file` requires an *observed* permission denial when probing the review
directory with an exclusive-create probe file (never overwrites; only that probe file is removed). A
declaration, a read-only file attribute, a missing directory or any other write error does not qualify.
Without it the strongest evidence class is `human_via_agent`. This is conservative for level C as well.

<!-- matrix:start -->
| Capability | Condition | Behaviour | Code | Blocking |
| --- | --- | --- | --- | --- |
| python | version below 3.12 | every step except doctor refuses to run | `E_PYTHON_TOO_OLD` | yes |
| sqlite_json | SQLite lacks JSON functions | case database cannot be created | `E_SQLITE_JSON_MISSING` | yes |
| pdf_extractor | neither pypdf nor pdftotext found | PDF passages are flagged needs_text | `W_PDF_EXTRACTOR_MISSING` | no |
| ocr | tesseract not found | scanned pages are flagged needs_text | `W_OCR_MISSING` | no |
| jq | jq not found | P1 shell wrappers unavailable; P0 unaffected | `W_JQ_MISSING` | no |
| clingo | clingo not found | P1 constraint backend unavailable; P0 unaffected | `W_CLINGO_MISSING` | no |
| review_dir | directory missing or not given | human_file unavailable; strongest class human_via_agent | `W_REVIEW_DIR_MISSING` | no |
| review_dir | agent process can write to it | human_file unavailable; strongest class human_via_agent | `W_REVIEW_DIR_WRITABLE` | no |
| review_dir | write failed for a reason other than permission denial | read-only not proven; strongest class human_via_agent | `W_REVIEW_DIR_UNVERIFIED` | no |
| disk | free space not measurable | limit reported as unmeasured | `W_DISK_UNMEASURED` | no |
| disk | free space below the caller-supplied minimum | ingest and extract refuse to start | `E_DISK_LOW` | yes |
| memory | available memory not measurable | limit reported as unmeasured | `W_MEMORY_UNMEASURED` | no |
| persistence | level B (or undeclared level): persistence cannot be verified from inside | continuity only via case export; reminder after every review import | `W_PERSISTENCE_UNVERIFIED` | no |
| level | no host level declared | treated as A; no promise about G2 | `W_LEVEL_UNDECLARED` | no |
<!-- matrix:end -->

Level B: `status` shows an export reminder after every review import and (with `--session-end`) before
finishing. Real limits: memory/disk are measured only where the OS exposes them; a step budget is a
declaration, not a measured guarantee.
