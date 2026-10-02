# Testing

Run on macOS, Python 3.14.3, PyMuPDF 1.27.2, tesseract 5.5.2, 28.09.2026.

| Suite | Command | Result |
|---|---|---|
| Fixtures and emit-visible leak check | `bash tests/run_tests.sh` | all pass |
| Hook path tests (watched root, symlink escape, folder named `Internal`, outside roots) | `python3 tests/test_hook.py` | 5/5 |
| Adversarial corpus | `python3 tests/run_attacks.py --jobs 6` | **153/153** |

The adversarial corpus has two parts:

* **121 cases from a red-team review** (`tests/attacks/attacks/`, generators
  `gen_*.py`, expectations in `manifest.tsv`): white and near-white text,
  covered and clipped text, invisible render mode, ActualText substitution,
  off-page and 1pt text, Word inheritance (document defaults, table styles,
  cell and paragraph shading, theme colours, scaling), `mc:Fallback`, unused
  headers, CSS classes and `:not()`, paraphrased and Romanian/Polish payloads,
  base64/rot13/homoglyph/fullwidth encodings, nested email and zip, crashes on
  encrypted, corrupt and oversized files.
* **32 cases from an independent coverage audit** (`tests/attacks/codex/`,
  report in `CODEX_REPORT.md`): Strict OOXML, fragmented hidden runs, off-page
  frames and floating tables, hidden numbering labels, unreferenced custom XML,
  nesting beyond depth, symlink and folder-name tricks against the hook.

A case passes only if the verdict matches and no hostile payload appears in the
`--emit-visible` output. Deliberate departures from a reviewer's expected
verdict are listed with reasons in `OVERRIDES` in `tests/run_attacks.py`.

**False positives.** On the author's 31 real case documents (judgments, police
and Home Office bundles, opponents' notices, own letters; not distributed), the
result is 29 CLEAN and 2 REVIEW. Both REVIEWs are bundles carrying white form
labels, which is hidden text that a reader cannot see. Run your own sample before
relying on the gate.
