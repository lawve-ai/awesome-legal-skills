#!/usr/bin/env python3
"""
Recall and precision benchmark.

Recall is measured against the lists themselves: take real designations, deform
the name the way a client, a passport office or a transliterator would, and see
whether the designation still comes back. Precision is measured against ordinary
names that have no business matching anything.

    python3 tests/benchmark.py [--sample 300] [--threshold 85]
"""

import argparse
import random
import re
import statistics
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import screen as SC
import sources as S

SEED = 20260901
PREFILTER = True


class Args:
    """Stands in for the argparse namespace screen.screen() expects."""
    def __init__(self, threshold, kind="individual", dob="", nationality=""):
        self.threshold = threshold
        self.type = kind
        self.dob = dob
        self.nationality = nationality
        self.limit = 25
        self.max_age_hours = 24.0
        self.client = self.matter = ""
        self.include_delisted = False


# ---------------------------------------------------------------- deformations

TRANSLIT = [("PH", "F"), ("Y", "I"), ("KS", "X"), ("OV", "OW"), ("IE", "I"),
            ("SH", "S"), ("TS", "C"), ("KH", "H"), ("DZH", "J"), ("EI", "EY")]
PATRONYMICS = ["Sergeyevich", "Ivanovich", "Petrovich", "Alexandrovich", "Nikolaevich"]


def strip_marks(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def deform(name, rng, kind="individual"):
    """Return {variant label: deformed name} for one published name.

    The deformation has to make sense for the KIND of thing designated. Giving a
    North Korean cargo ship a Russian patronymic and then counting the miss as
    lost recall measures nothing about the tool: "Rye Song Gang 1" is not
    someone's name with a middle name to drop. Applying the individual
    deformations to every record type pushed the headline figure down by a third
    on artefacts of the harness."""
    toks = name.split()
    out = {"exact": name}
    if len(toks) >= 2:
        out["lowercased"] = name.lower()
    if strip_marks(name) != name:
        out["diacritics stripped"] = strip_marks(name)
    up = name.upper()
    for a, b in TRANSLIT:
        if a in up:
            i = up.index(a)
            out["transliterated"] = name[:i] + b.lower() + name[i + len(a):]
            break
    if kind != "individual":
        # How a ship, an aeroplane or a company is actually mistyped: spacing and
        # punctuation, not a reordered forename.
        if "-" in name or "." in name:
            out["punctuation dropped"] = name.replace("-", " ").replace(".", "")
        if len(toks) >= 2:
            out["run together"] = "".join(toks)
        return out
    if len(toks) >= 2:
        out["reordered"] = " ".join(reversed(toks))
        out["initial"] = toks[0][0] + " " + " ".join(toks[1:])
    if len(toks) >= 3:
        out["dropped middle name"] = " ".join([toks[0], toks[-1]])
    if len(toks) == 2:
        out["extra patronymic"] = f"{toks[0]} {rng.choice(PATRONYMICS)} {toks[1]}"
    return out


# ---------------------------------------------------------------------- recall

def recall(args, srcs, sample_n, threshold):
    """Measured on individuals, vessels, aircraft AND native-script names.

    Every deformation below is built from the publisher's own Latin primary
    name, so a harness drawing only on Latin individuals reports high recall
    while the CLI misses an exact ship, an exact aeroplane, and a Cyrillic name
    the publisher spells in Latin. Those are the cohorts, so they are measured."""
    rng = random.Random(SEED)
    # Drawn from every source being screened, not from the UK list alone. The UK
    # normalised list holds no aircraft at all, so an aircraft cohort taken from
    # it was empty and the harness reported a cohort it had never tested.
    everything = [r for s in srcs for r in S.load_records(s.id) if r.get("name")]
    pool = [r for r in everything
            if r["type"] == "individual" and len(r["name"].split()) >= 2]
    sample = rng.sample(pool, min(sample_n, len(pool)))

    # Named cohorts, sampled separately so a thin one cannot be swamped. A cohort
    # the corpus cannot supply is reported as absent rather than passed over.
    for kind, want in (("vessel", max(20, sample_n // 10)),
                       ("aircraft", max(20, sample_n // 10)),
                       ("entity", max(20, sample_n // 10))):
        cohort = [r for r in everything if r["type"] == kind]
        if cohort:
            sample += rng.sample(cohort, min(want, len(cohort)))
        else:
            print(f"  !! no {kind} records in the selected sources — cohort NOT tested")
    native = [r for r in everything if r.get("nonlatin")]
    if native:
        sample += rng.sample(native, min(max(20, sample_n // 5), len(native)))
    else:
        print("  !! no native-script names in the selected sources — cohort NOT tested")
    got = defaultdict(lambda: [0, 0])
    misses = defaultdict(list)
    times = []
    for rec in sample:
        variants = deform(rec["name"], rng, rec.get("type") or "individual")
        # A record the publisher also gives in a native script must be findable
        # FROM that script, which is how the client's own passport reads.
        for nl in (rec.get("nonlatin") or [])[:1]:
            # Named for what it measures: the record is found FROM its own
            # publisher's native spelling, on the source that publishes it. It
            # does not measure whether the same person is found on a source that
            # holds them only in Latin — that needs an identifier shared across
            # publishers, which none of these lists provides.
            variants["native script, own source"] = nl
        if rec.get("type") in ("vessel", "aircraft"):
            variants[f"{rec['type']} searched as its own type"] = rec["name"]
        for label, variant in variants.items():
            a = Args(threshold)
            # Screen each record under ITS OWN type, which is how anyone would
            # actually search for it. Leaving every cohort on "individual" made
            # _scan skip every ship and every company before scoring — reported
            # as 0% recall on deformations the matcher in fact scores 91 to 100.
            a.type = rec.get("type") or "individual"
            t0 = time.perf_counter()
            hits = SC.screen(variant, a, srcs, prefilter=PREFILTER).hits
            times.append(time.perf_counter() - t0)
            found = any(h["record"]["uid"] == rec["uid"] and
                        h["record"]["source"] == rec["source"] for h in hits)
            got[label][1] += 1
            if found:
                got[label][0] += 1
            elif len(misses[label]) < 3:
                misses[label].append((rec["name"], variant))
    return got, misses, times


# ------------------------------------------------------------------- precision

FORENAMES = ["James", "Sarah", "David", "Emma", "Thomas", "Laura", "Daniel", "Rachel",
             "Andrei", "Ioana", "Cristian", "Elena", "Piotr", "Agnieszka", "Marek",
             "Mohammed", "Aisha", "Wei", "Priya", "Carlos"]
SURNAMES = ["Whitfield", "Brennan", "Hollis", "Marsden", "Callaghan", "Prentice",
            "Ionescu", "Dumitrescu", "Stanciu", "Munteanu", "Kowalczyk", "Zielinski",
            "Nowicki", "Okonkwo", "Nakamura", "Fernandez", "Bergstrom", "Halloran",
            "Ashworth", "Pemberton"]


def precision(args, srcs, n, threshold):
    rng = random.Random(SEED + 1)
    names = set()
    while len(names) < n:
        names.add(f"{rng.choice(FORENAMES)} {rng.choice(SURNAMES)}")
    flagged = []
    for nm in sorted(names):
        hits = SC.screen(nm, Args(threshold), srcs, prefilter=PREFILTER).hits
        if hits:
            flagged.append((nm, hits[0]["score"], hits[0]["record"]["name"],
                            hits[0]["record"]["source"]))
    return len(names), flagged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--precision-n", type=int, default=200)
    # The shipped default, so the figures describe the tool as it is actually
    # run. Pass --threshold to sweep.
    ap.add_argument("--threshold", type=float, default=SC.DEFAULT_THRESHOLD)
    ap.add_argument("--no-prefilter", action="store_true")
    a = ap.parse_args()
    global PREFILTER
    PREFILTER = not a.no_prefilter

    meta = S.load_meta()
    srcs = [s for s in S.SOURCES if s.default and meta.get(s.id, {}).get("ok")]
    if not srcs:
        sys.exit("refresh first")
    total = sum(meta[s.id]["records"] for s in srcs)
    print(f"engine: stdlib matcher, prefilter {'ON' if PREFILTER else 'OFF'} | "
          f"{len(srcs)} lists, {total:,} designations | threshold {a.threshold}\n")

    print(f"RECALL — {a.sample} real designations, deformed as a client would give them")
    got, misses, times = recall(a, srcs, a.sample, a.threshold)
    overall = [0, 0]
    for label in sorted(got, key=lambda k: -got[k][1]):
        hit, tot = got[label]
        overall[0] += hit
        overall[1] += tot
        bar = "█" * round(20 * hit / tot)
        print(f"  {label:<22} {hit:>4}/{tot:<4} {100*hit/tot:5.1f}%  {bar}")
        for orig, var in misses.get(label, [])[:2]:
            print(f"      missed: {orig!r} searched as {var!r}")
    print(f"  {'OVERALL':<22} {overall[0]:>4}/{overall[1]:<4} {100*overall[0]/overall[1]:5.1f}%")

    print(f"\nPRECISION — {a.precision_n} ordinary names that should hit nothing")
    n, flagged = precision(a, srcs, a.precision_n, a.threshold)
    print(f"  {len(flagged)}/{n} produced a candidate ({100*len(flagged)/n:.1f}% false-positive rate)")
    for nm, sc, match, src in flagged[:8]:
        print(f"      {nm!r} → {sc} {match!r} [{src}]")

    print(f"\nSPEED — {len(times)} screens")
    print(f"  median {statistics.median(times)*1000:6.0f} ms   "
          f"mean {statistics.mean(times)*1000:6.0f} ms   "
          f"max {max(times)*1000:6.0f} ms")


if __name__ == "__main__":
    main()
