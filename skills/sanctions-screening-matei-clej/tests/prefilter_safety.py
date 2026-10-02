#!/usr/bin/env python3
"""
How much margin the bigram prefilter leaves on known-true pairs.

This is a MEASUREMENT ON A SAMPLE, not a proof. It draws a sample of real
designations, deforms each one's own name, and asks the prefilter directly
whether it would have let that designation through. Zero blocked across the
pairs drawn is evidence that the filter is not costing recall on names of this
shape; it is not a guarantee about the names it did not draw, nor about any
matching path the filter does not sit in front of.

Read the reported margin, not just the pass line: a tightest margin of +0 means
some true pair only just survived, and the next name of that shape may not.

    python3 tests/prefilter_safety.py [--sample 2000]
"""

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import matching as M  # noqa: E402
import sources as S  # noqa: E402
from benchmark import SEED, deform  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--sample", type=int, default=2000)
a = ap.parse_args()

rng = random.Random(SEED)
pool = [r for s in S.SOURCES if s.default
        for r in S.load_records(s.id)
        if r.get("name") and len(r["name"].split()) >= 2]
sample = rng.sample(pool, min(a.sample, len(pool)))

checked = blocked = 0
worst = []
examples = []
for rec in sample:
    rmask = 0
    for cand in [rec["name"]] + list(rec.get("aliases", [])):
        if cand:
            rmask |= M.bigram_mask(M.normalise(cand))
    for label, variant in deform(rec["name"], rng).items():
        qmask = M.bigram_mask(M.normalise(variant))
        if not qmask:
            continue
        need = M.prefilter_threshold(qmask)
        shared = M._popcount(qmask & rmask)
        checked += 1
        margin = shared - need
        worst.append(margin)
        if shared < need:
            blocked += 1
            if len(examples) < 5:
                examples.append((rec["name"], label, variant, shared, need))

worst.sort()
print(f"true pairs checked        : {checked:,} ({len(sample):,} designations x deformations)")
print(f"blocked by the prefilter  : {blocked}")
print(f"tightest margin observed  : {worst[0]:+d} shared bigrams above what is required")
print(f"1st percentile margin     : {worst[int(0.01 * len(worst))]:+d}")
print(f"median margin             : {worst[len(worst) // 2]:+d}")
for e in examples:
    print(f"  BLOCKED {e[0]!r} as {e[2]!r} ({e[1]}): shared {e[3]}, needed {e[4]}")
print(f"\nPASS — nothing blocked in the {checked:,} true pairs drawn. That is evidence "
      "on this sample,\n       not a proof about the pairs it did not draw."
      if not blocked else "\nFAIL — the prefilter blocks true matches")
sys.exit(1 if blocked else 0)
