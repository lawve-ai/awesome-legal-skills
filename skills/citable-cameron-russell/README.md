# citable

Citable helps make your cite-checking more efficient and accurate. It transforms US court filings and drafts into structured tables that link every citation to pinpoint locations in the record, case law (CourtListener), statutes (Cornell LII), or treaties in a single click. Citable flags when a pincite cannot be located, potentially catching incorrect cites before your check begins. You can record your cite-checking progress by updating the status flag and adding notes, and save your edits. When a draft filing is revised, citable rebuilds the table, flags citations that changed, and carries forward your saved statuses and notes.

Citable locates and links sources; the cite-checking judgment stays with the user.

**Version:** 1.0.0 (2026-10-07) · **Owner:** Cameron Russell (ccrnyc) · Report issues to the owner; review before each release.

## How to install in Claude
1. **Download the skill.** Download the packaged ZIP file here: https://github.com/ccrnyc/citable/releases/latest/download/citable.zip (alternatively, download from this repo's [Releases page](../../releases)). The skill is also listed on [Lawve](https://lawve.ai/@cameron-russell).
2. **Ensure skills can run.** On Free/Pro/Max plans: go to Settings > Capabilities and make sure "Cloud code execution and file creation" is turned on. On Team/Enterprise plans: your organization Owner enables Skills under Organization settings > Skills.
3. **Upload the skill.** Go to Customize > Skills, click "+" or "Add" → "Upload a skill", and select the ZIP. Select the skill and toggle it on.

citable reads the filing and its exhibits in a folder on your computer and writes the table beside them, so use it where Claude can work in that folder: the Claude desktop app (Cowork, with the case folder connected) or Claude Code. To use it, just ask, e.g. *"Build a citation table for the memorandum in this folder"* or *"Cite-check this brief"*.

## Requirements
Runs on the user's computer: `python3` (3.10 or later; tested on 3.10, although the bundled nupunkt declares 3.11+, and a simpler sentence splitter takes over if it fails) with `pdfplumber` and `Pillow`; poppler (`pdftotext`, `pdftoppm`); `tesseract` (optional: needed only for exhibits whose paragraph numbers are images). The CourtListener connector is used to look up cases while drafting the map.

## Before you start
- citable v1.0 is designed to work with PDFs. If your draft is in Word, make a copy, accept all tracked changes, delete all comments, and save the copy as a PDF (File → Save As → PDF), and then run citable on that copy.
- Put the filing and every cited document in one folder. PDFs need a text layer. OCR'd PDFs are fine. Image-only scans must be OCR'd first. OCR errors in the filing itself can cause missed citations.
- Documents cited by name (exhibits not yet lettered, other filings, authorities saved in the folder) are matched to files by name. Name files the way the filing cites them (e.g. a brief citing "2026-09-10 medical report" → `2026-09-10 Medical Report.pdf`). You confirm every mapping before the table is built.
- Statuses and notes are kept only in the open page until you click Save, so save frequently. For a revised draft, click Save in the old table first; only saved review work carries forward when the table for the revised draft is built.
- Each rebuild keeps the earlier table and its CSV in a `citable-backups/` folder beside it; delete old copies when no longer needed.

## Limits
Case citations link to CourtListener; Westlaw/Lexis cites link (approximately) to the court's copy on CourtListener where one exists, or to the CourtListener docket where only the docket is there; otherwise they are listed for checking. Case pinpoints jump only where CourtListener's copy marks the cited reporter's pages. State statutes, local rules, another case's docket entries and citations the map marks "do not link" are listed for checking but not linked. *supra* is listed but not linked. Bates numbers and transcript page numbers must be legible in the text layer; OCR misreads make those links approximate. Uncited factual sentences are not flagged.

## Contents
- `SKILL.md`: the workflow.
- `CHANGELOG.md`: release history.
- `references/map-format.md`: the per-case link map.
- `scripts/inventory.py`: case-folder inventory.
- `scripts/build_table.py` and `scripts/template.html`: the table builder.
- `scripts/vendor/nupunkt/`, `scripts/data/reporters.json`: bundled third-party code and data (see below).

## License
Copyright (C) 2026 Cameron Russell (ccrnyc). Licensed under the **GNU Affero General Public License v3.0** (`AGPL-3.0-only`); see [LICENSE](LICENSE). This program comes with no warranty. The bundle as a whole is `AGPL-3.0-only AND MIT AND BSD-2-Clause` (see Third-party components). Generated tables carry the notice "citable © 2026 ccrnyc" and the licence name. The license covers the skill's code and documentation only. Linked sources (CourtListener, Cornell LII, UN Treaty Series) are governed by their own terms; the tool only links to them and stores no copies.

## Third-party components
- **nupunkt** 0.8.0, ALEA Institute — legal-text sentence splitter, bundled in `scripts/vendor/nupunkt/` under the MIT License (`scripts/vendor/nupunkt/LICENSE`).
- **reporters-db** 3.2.66, Free Law Project — reporter abbreviations and their variants, bundled as a derived subset in `scripts/data/reporters.json` under the BSD 2-Clause License (`scripts/data/LICENSE-reporters-db`).
