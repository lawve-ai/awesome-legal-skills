# pleading-injection-guard

Scans documents from the other side for prompt injection before an AI reads them.

An opponent does not need to hack anything to attack a lawyer who uses AI. It is
enough to put words in their own skeleton, bundle or email that the lawyer will
never see but the model will read: white text, a 1pt line, text parked off the
page, a hidden Word run, a CSS-hidden paragraph, invisible Unicode. This tool
checks, word by word, that what a text extractor would hand the model was
actually drawn visibly on the page, and blocks the file if it was not.

## Install

```bash
git clone <this repo> ~/.claude/skills/pleading-injection-guard
pip install pymupdf lxml numpy
brew install tesseract tesseract-lang     # or your platform's package
# optional, for .doc/.odt/.pages/.xls/.ppt:  brew install --cask libreoffice
python3 ~/.claude/skills/pleading-injection-guard/scan.py --check
```

## Use

```bash
python3 scan.py bundle.pdf --json report.json --emit-visible visible.txt --lang eng
```

Exit code: **0 CLEAN · 1 REVIEW · 2 HOSTILE · 3 ERROR/UNSCANNED**. It fails
closed: anything it could not fully read is 3, never CLEAN. `--emit-visible`
writes a reader's-eye text with hidden material removed, for use when a HOSTILE
document still has to be worked on.

Optional Claude Code hook: a `PreToolUse` hook with matcher `Read` running
`python3 ~/.claude/skills/pleading-injection-guard/hook.py` (timeout 300) scans
each file under the roots in `hook_config.json` (default `~/Downloads`) the first
time it is opened, caches the verdict by SHA-256, and blocks anything not CLEAN.
`hook.py allow <sha256> "<reason>"` releases a file you have checked.

`SKILL.md` sets out the formats, checks, severity policy, the reading discipline
for opposing documents and the known limits. `TESTING.md` sets out the evidence.

## Privacy

Scanning is entirely local. The scanner opens no network connection; it calls
only `tesseract`, and (for legacy formats) headless LibreOffice, `textutil` or
`sips` on macOS. Nothing about the document leaves the machine.

MIT licence.

## Adversarial corpus

This package omits the 153 hostile test documents (some are deliberately
malformed archives and symlinks). Get them, with `tests/run_attacks.py`, from
https://github.com/mateiclej-wq/pleading-injection-guard.
