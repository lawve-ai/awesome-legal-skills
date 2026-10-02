#!/usr/bin/env python3
"""pleading-injection-guard: scan documents from the other side for prompt injection
before any AI reads them.

Usage:
    scan.py PATH [PATH ...] [--json OUT.json] [--emit-visible OUT.txt] [--lang eng+ron]
            [--no-ocr] [--ocr-workers N] [--ocr-dpi DPI] [--time-budget SECONDS]
            [--password PW] [--max-pages N] [--quiet]
    scan.py --check        verify dependencies and tesseract languages
    scan.py --version

Exit codes (worst across all files and their attachments):
    0 CLEAN · 1 REVIEW · 2 HOSTILE · 3 ERROR or UNSCANNED (nothing was verified)
Consumers must treat 2 and 3 as "do not let a model read the raw file".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from pig.core import SCANNER_VERSION, Report, exit_code, overall  # noqa: E402
    from pig.containers import JUNK, soffice_path  # noqa: E402
    from pig.engine import envelope, render, scan_bytes, visible_dump  # noqa: E402
except ImportError as _e:   # fail closed: a missing dependency is never "REVIEW"
    print(f"OVERALL: ERROR (missing dependency: {_e}; run with /opt/homebrew/bin/python3) exit=3")
    sys.exit(3)

DEFAULT_CACHE = os.path.expanduser("~/.cache/pleading-injection-guard")


def tesseract_langs():
    try:
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=30)
        return {l.strip() for l in r.stdout.splitlines()[1:] if l.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def tool_versions():
    v = {"python": sys.version.split()[0]}
    try:
        import fitz
        v["pymupdf"] = fitz.VersionBind
    except Exception:
        v["pymupdf"] = None
    try:
        from lxml import etree
        v["lxml"] = ".".join(map(str, etree.LXML_VERSION))
    except Exception:
        v["lxml"] = None
    try:
        v["numpy"] = __import__("numpy").__version__
    except Exception:
        v["numpy"] = None
    try:
        r = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=30)
        v["tesseract"] = (r.stdout or r.stderr).split("\n")[0]
    except Exception:
        v["tesseract"] = None
    v["libreoffice"] = soffice_path()
    return v


def iter_files(paths):
    """Yield (path, error). Directories are walked without following symlinks."""
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for root, dirs, files in os.walk(p, followlinks=False):
                dirs.sort()
                for f in sorted(files):
                    if f in JUNK or f.startswith("~$"):
                        continue
                    fp = Path(root) / f
                    if fp.is_symlink() and not fp.exists():
                        yield fp, "broken symlink"
                        continue
                    yield fp, None
        elif p.exists():
            yield p, None
        else:
            yield p, "file not found"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--emit-visible", type=Path, help="write visible text only (withheld for unscanned files)")
    ap.add_argument("--no-ocr", dest="ocr", action="store_false", default=True,
                    help="skip the OCR backstop (per-word render check still runs)")
    ap.add_argument("--lang", default="eng", help="tesseract languages, e.g. eng+ron+pol")
    ap.add_argument("--ocr-workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--ocr-dpi", type=int, default=0, help="0 = auto (200, or 300 for small print)")
    ap.add_argument("--time-budget", type=float, default=900, help="seconds per file for OCR")
    ap.add_argument("--password")
    ap.add_argument("--max-pages", type=int, default=0)
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--quiet", action="store_true", help="print only the OVERALL line")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--version", action="store_true")
    opts = ap.parse_args()

    if opts.version:
        print(f"pleading-injection-guard {SCANNER_VERSION}")
        return 0
    tv = tool_versions()
    if opts.check:
        print(json.dumps(tv, indent=2))
        langs = tesseract_langs()
        print("tesseract languages:", "MISSING" if langs is None else f"{len(langs)} installed")
        print("LibreOffice (legacy .doc/.odt/.pages/.xls/.ppt):",
              tv["libreoffice"] or "MISSING (those types will be UNSCANNED)")
        ok = all(tv.get(k) for k in ("pymupdf", "lxml", "numpy", "tesseract"))
        print("OK" if ok else "MISSING DEPENDENCIES")
        return 0 if ok else 3
    if not opts.paths:
        ap.error("no paths given")
    os.makedirs(opts.cache_dir, exist_ok=True)
    if opts.ocr:
        langs = tesseract_langs()
        if langs is None:
            print("OVERALL: ERROR (tesseract not installed; install it or pass --no-ocr) exit=3")
            return 3
        missing = [l for l in opts.lang.split("+") if l not in langs]
        if missing:
            print(f"OVERALL: ERROR (tesseract language(s) not installed: {', '.join(missing)}) exit=3")
            return 3

    reports = []
    for path, err in iter_files(opts.paths):
        if err:
            rep = Report(file=str(path), display_name=path.name, status="error", verdict="ERROR",
                         notes=[f"ERROR: {err}"])
        else:
            try:
                data = path.read_bytes()
            except OSError as e:
                rep = Report(file=str(path), display_name=path.name, status="error", verdict="ERROR",
                             notes=[f"ERROR: cannot read file: {e}"])
            else:
                rep = scan_bytes(data, str(path), opts)
                rep.display_name = path.name
        reports.append(rep)
        if not opts.quiet:
            print(render(rep), end="\n\n", flush=True)

    worst = max((exit_code(r) for r in reports), default=3)
    verdicts = [overall(r) for r in reports]
    label = next((v for v in ("HOSTILE", "ERROR", "UNSCANNED", "REVIEW") if v in verdicts), "CLEAN")
    if opts.json:
        opts.json.parent.mkdir(parents=True, exist_ok=True)
        opts.json.write_text(json.dumps(envelope(reports, opts, tv), indent=2, ensure_ascii=False))
    if opts.emit_visible:
        opts.emit_visible.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for r in reports:
            lines += visible_dump(r)
        opts.emit_visible.write_text("\n".join(lines))
    print(f"OVERALL: {label} ({len(reports)} file(s)) exit={worst}")
    return worst


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(3)
    except Exception as e:   # last-resort fail-closed
        print(f"OVERALL: ERROR (scanner failure: {type(e).__name__}: {e}) exit=3")
        sys.exit(3)
