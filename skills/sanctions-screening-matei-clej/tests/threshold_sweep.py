#!/usr/bin/env python3
"""
Where to set the default match threshold.

Screens once at a low threshold and evaluates the same scores at several
cut-offs, so recall and the false-positive rate can be read off the same run.
Recall is measured on real designations searched under deformed spellings;
false positives on ordinary names that have no business matching anything.

    python3 tests/threshold_sweep.py
"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import screen as SC  # noqa: E402
import sources as S  # noqa: E402
from benchmark import FORENAMES, SEED, SURNAMES, deform  # noqa: E402

CUTOFFS = [82, 85, 86, 88, 90, 92]
FLOOR = 78.0


class Args:
    threshold = FLOOR
    type = "individual"
    dob = nationality = ""
    limit = 400
    include_delisted = False
    max_age_hours = 24.0
    client = matter = ""


meta = S.load_meta()
srcs = [s for s in S.SOURCES if s.default and meta.get(s.id, {}).get("ok")]
rng = random.Random(SEED)

pool = [r for r in S.load_records("uk-sanctions-list")
        if r["type"] == "individual" and r["name"] and len(r["name"].split()) >= 2]
sample = rng.sample(pool, 60)

true_scores = []          # score at which the correct designation was found
for rec in sample:
    for label, variant in deform(rec["name"], rng).items():
        hits = SC.screen(variant, Args, srcs, meta).hits
        s = next((h["score"] for h in hits
                  if h["record"]["uid"] == rec["uid"] and h["record"]["source"] == rec["source"]), 0.0)
        true_scores.append((label, s))

names = set()
while len(names) < 150:
    names.add(f"{rng.choice(FORENAMES)} {rng.choice(SURNAMES)}")
fp_scores = []
for nm in sorted(names):
    hits = SC.screen(nm, Args, srcs, meta).hits
    fp_scores.append(max([h["score"] for h in hits], default=0.0))

print(f"{len(true_scores)} true searches, {len(fp_scores)} ordinary names\n")
print(f"{'cut-off':>8} {'recall':>9} {'false positives':>17}   {'missed at this cut-off'}")
for c in CUTOFFS:
    found = sum(1 for _, s in true_scores if s >= c)
    fps = sum(1 for s in fp_scores if s >= c)
    missed = {}
    for label, s in true_scores:
        if s < c:
            missed[label] = missed.get(label, 0) + 1
    detail = ", ".join(f"{k} x{v}" for k, v in sorted(missed.items(), key=lambda kv: -kv[1])[:3])
    print(f"{c:>8} {100*found/len(true_scores):>8.1f}% {100*fps/len(fp_scores):>16.1f}%   {detail or '—'}")
