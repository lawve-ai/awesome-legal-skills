#!/usr/bin/env python3
"""Run scan.py over the adversarial corpus and check verdicts and --emit-visible leaks.

Expected verdicts come from tests/attacks/attacks/manifest.tsv (column 2), normalised:
  "ERROR/fail-closed" -> exit 3; "REVIEW/UNSCANNED" -> REVIEW or UNSCANNED; "HOSTILE or ERROR" -> either, etc.
Overrides for deliberate policy decisions live in OVERRIDES below.
Usage: run_attacks.py [--only SUBSTR] [--jobs N]
"""
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE.parent / "scan.py"
A = HERE / "attacks" / "attacks"
EXTRA = HERE / "attacks" / "attacks_extra"
CODEX = HERE / "attacks" / "codex"
SUITES = [A, CODEX]   # each has its own manifest.tsv

# Deliberate policy decisions that differ from the reviewer's manifest (reason in comment).
OVERRIDES = {
    # images: OCR'd and pattern-checked -> the hostile words are visible, so HOSTILE/REVIEW, not UNSCANNED
    "unsupported_hostile.png": {"HOSTILE", "REVIEW", "UNSCANNED"},
    # superseded revision is never read by an extractor: a note, not a verdict
    "pdf_incremental.pdf": {"CLEAN", "REVIEW"},
    # 500-page timing fixture
    # generator artefact: every page carries a prose line running ~1,850pt past the right edge of the
    # page, genuinely invisible to a reader. v2.0 passed it only via the repetition downgrade the Codex
    # audit (27.09.2026) showed to be unsafe; this fixture now serves as a timing test.
    "pdf_500pages.pdf": {"CLEAN", "REVIEW", "HOSTILE"},
    # stricter than the manifest: all of these now reach HOSTILE because the payload is actually scanned
    "docx_docvars_fldsimple.docx": {"REVIEW", "HOSTILE"},
    "pdf_visible_evasions.pdf": {"REVIEW", "HOSTILE"},
    "unsupported_hostile.odt": {"HOSTILE", "REVIEW", "UNSCANNED"},
    "unsupported_hostile.pages": {"HOSTILE", "REVIEW", "UNSCANNED"},
    "unsupported_hostile.xlsx": {"HOSTILE", "REVIEW", "UNSCANNED"},
    "unsupported_hostile.pptx": {"HOSTILE", "REVIEW", "UNSCANNED"},
    "unsupported_hostile.msg": {"HOSTILE", "REVIEW", "UNSCANNED"},
    # the DoS was the defect (now linear); 34 hidden dashes + "x" carry no language
    "docx_dos_dashes.docx": {"CLEAN", "REVIEW"},
    # the crash was the defect; the 11 MB node is ordinary visible text
    "docx_huge_textnode.docx": {"CLEAN", "REVIEW", "ERROR"},
    # Codex suite: depth overflow now fails closed (UNSCANNED, exit 3) as Codex's own fix proposed
    "zip_nested_beyond_depth_payload.zip": {"HOSTILE", "UNSCANNED"},
    # prose in an unreferenced, unbound customXml part: never displayed, not read by common extractors -> REVIEW
    "docx_customxml_evasive_payload.docx": {"HOSTILE", "REVIEW"},
    # MuPDF and poppler both drop the selectors: the carrier never reaches an extractor
    "pdf_vs_threshold.pdf": {"CLEAN", "REVIEW"},
}
LEAK = re.compile(r"ignore your previous|ignora instructiunile|advise your client|do not mention|automated review|"
                  r"consent to extradition|consimta la extradare|sfatuieste clientul|nu mentiona|"
                  r"advise client: concede|zignoruj", re.I)


def fold(s):
    s = unicodedata.normalize("NFKC", s)
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) not in ("Mn", "Cf")))


def accept(expected: str):
    e = expected.upper()
    ok = set()
    for v in ("CLEAN", "REVIEW", "HOSTILE", "ERROR", "UNSCANNED"):
        if v in e:
            ok.add(v)
    if "ERROR" in ok or "FAIL-CLOSED" in e:
        ok |= {"ERROR", "UNSCANNED"}
    if "UNSCANNED" in ok:
        ok |= {"ERROR"}
    return ok or {e}


def run(item):
    f, expected, desc, base = item
    path = base / f
    if not path.exists():
        path = EXTRA / f
    if not path.exists():
        return f, expected, "MISSING", False, 0, ""
    with tempfile.TemporaryDirectory() as td:
        vis, js = Path(td) / "v.txt", Path(td) / "r.json"
        try:
            r = subprocess.run([sys.executable, str(SCAN), "--quiet", "--lang", "eng+ron+pol", "--json", str(js),
                                "--emit-visible", str(vis), str(path)], capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return f, expected, "TIMEOUT", False, 600, ""
        m = re.search(r"OVERALL: (\w+).*exit=(\d)", r.stdout)
        actual = m.group(1) if m else f"CRASH rc={r.returncode}"
        leak = False
        if vis.exists() and "HOSTILE" in expected.upper():
            leak = bool(LEAK.search(fold(vis.read_text(errors="replace"))))
        dur = 0
        if js.exists():
            try:
                dur = sum(rp["duration_ms"] for rp in json.loads(js.read_text())["reports"]) / 1000
            except Exception:
                pass
        return f, expected, actual, leak, dur, (r.stderr or "")[-300:]


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
    items = []
    for base in SUITES:
        for line in (base / "manifest.tsv").read_text().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] and not parts[0].startswith("#") and only in parts[0]:
                items.append((parts[0], parts[1], parts[3] if len(parts) > 3 else "", base))
    fails = 0
    with ThreadPoolExecutor(jobs) as ex:
        for f, expected, actual, leak, dur, err in ex.map(run, items):
            ok_set = OVERRIDES.get(f, accept(expected))
            ok = actual in ok_set and not leak
            fails += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {f:48s} expected {expected:20s} got {actual:10s}"
                  f"{' LEAK' if leak else ''} ({dur:.1f}s){'  ' + err.strip().splitlines()[-1] if err.strip() and not ok else ''}",
                  flush=True)
    print(f"\n{len(items) - fails}/{len(items)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
