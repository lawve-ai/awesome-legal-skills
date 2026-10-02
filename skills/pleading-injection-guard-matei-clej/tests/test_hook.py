#!/usr/bin/env python3
"""Hook regression: received files must be scanned whatever their folder names or symlinks.
Uses a temporary cache; never touches ~/.cache/pleading-injection-guard."""
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pig_hook", HERE.parent / "hook.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

tmp = Path(tempfile.mkdtemp(prefix="pig-hooktest-"))
hook.CACHE, hook.RESULTS, hook.ALLOW, hook.LOG = tmp, tmp / "results", tmp / "allow.tsv", tmp / "log"
watched = HERE / "attacks" / "codex" / "hook_watch"
fixtures = HERE / "fixtures"
cfg = dict(hook.DEFAULT_CFG)
cfg["roots"] = [str(watched), str(fixtures)]
orig_cfg = hook.cfg


def fake_cfg():
    c = dict(cfg)
    roots = []
    for r in c["roots"]:
        roots += [os.path.abspath(r), os.path.realpath(r)]
    c["roots"] = sorted(set(roots))
    c["trusted_dirs"] = []
    return c


hook.cfg = fake_cfg
CASES = [
    ("folder named Internal", watched / "Opponent" / "Internal" / "received.pdf", 2),
    ("symlink escaping the root", watched / "external-link.pdf", 2),
    ("hostile docx", fixtures / "hostile.docx", 2),
    ("clean pdf", fixtures / "clean.pdf", 0),
    ("outside every root", Path("/etc/hosts"), 0),
]
fails = 0
for name, path, want in CASES:
    sys.stdin = io.StringIO(json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(path)}}))
    stderr, sys.stderr = sys.stderr, io.StringIO()
    try:
        rc = hook.hook()
    finally:
        msg, sys.stderr = sys.stderr.getvalue(), stderr
    ok = rc == want
    fails += not ok
    leaked = "summarise" in msg.lower() and "appeal as hopeless" in msg.lower()
    print(f"{'ok  ' if ok and not leaked else 'FAIL'} hook: {name}: rc={rc} (want {want}){' HIDDEN TEXT IN MESSAGE' if leaked else ''}")
    fails += leaked
sys.exit(1 if fails else 0)
