"""PL/EN guards for claim proposals (R10).

Guards always use the UNION of the Polish and English lexicons, whatever
`source_lang` says. Detection is lexical and conservative: it flags, it never
repairs. A flagged item goes to individual (class I) review; the guard does not
establish truth, intent or that an OCR-lost negation was recovered. Lexicons are
versioned files under references/lexicons and are unreviewed (Q6).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

LEXICON_DIR = Path(__file__).resolve().parents[1] / "references" / "lexicons"
_TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_QUOTED = [re.compile(p) for p in (r"„([^”“\"]+)[”“\"]", r"“([^”]+)”", r"\"([^\"]+)\"", r"«([^»]+)»")]
LEXICON_VERSION = "1"


@lru_cache(maxsize=1)
def lexicons() -> dict[str, Any]:
    pl = json.loads((LEXICON_DIR / "pl.json").read_text(encoding="utf-8"))
    en = json.loads((LEXICON_DIR / "en.json").read_text(encoding="utf-8"))
    status = json.loads((LEXICON_DIR / "claim_status.json").read_text(encoding="utf-8"))
    return {"pl": pl, "en": en, "status": status,
            "version": f"pl{pl['version']}+en{en['version']}+status{status['version']}"}


def tokens(text: str) -> list[str]:
    return [t.lower().replace("’", "'") for t in _TOKEN.findall(text)]


def find_negation(text: str) -> list[str]:
    lx = lexicons()
    words = set(lx["pl"]["negation"]["words"]) | set(lx["en"]["negation"]["words"])
    nie = lx["pl"]["negation"]["nie_prefix"]
    suffix = lx["en"]["negation"]["contraction_suffix"]
    hits = []
    for t in tokens(text):
        if t in words or t.endswith(suffix):
            hits.append(t)
        elif t.startswith("nie") and len(t) >= nie["min_length"] and t not in set(nie["exceptions"]):
            hits.append(t)  # nie- prefix (e.g. niewykonanie, nieobecny), minus listed exceptions
    return hits


def find_modality(text: str) -> list[str]:
    lx = lexicons()
    words = set(lx["pl"]["modality"]["words"]) | set(lx["en"]["modality"]["words"])
    return [t for t in tokens(text) if t in words]


def _quoted_spans(prose: str, passage_text: str | None) -> list[tuple[int, int]]:
    """Spans of `prose` that are quotations of real Passage text; bare quote marks do not count."""
    spans = []
    for rx in _QUOTED:
        for m in rx.finditer(prose):
            inner = m.group(1)
            if passage_text is not None and len(inner.strip()) >= 3 and inner in passage_text:
                spans.append(m.span())
    return spans


def find_boosters(prose: str, passage_text: str | None = None) -> list[str]:
    lx = lexicons()
    prefixes = tuple(lx["pl"]["forbidden_boosters"]["prefixes"])
    words = set(lx["en"]["forbidden_boosters"]["words"])
    spans = _quoted_spans(prose, passage_text)
    hits = []
    for m in _TOKEN.finditer(prose):
        if any(a <= m.start() < b for a, b in spans):
            continue
        t = m.group(0).lower()
        if t.startswith(prefixes) or t in words:
            hits.append(t)
    return hits


def is_lang_mixed(text: str) -> bool:
    lx = lexicons()
    toks = set(tokens(text))
    return bool(toks & set(lx["pl"]["language_markers"])) and bool(toks & set(lx["en"]["language_markers"]))


def check_claim(item: dict[str, Any], passage_text: str | None, passage_flags: list[str]) -> list[str]:
    st = lexicons()["status"]
    quote = item["quote"]
    flags: set[str] = set()
    neg, mod = find_negation(quote), find_modality(quote)
    if neg:
        flags.add("negation_detected")
    if mod:
        flags.add("modality_detected")
    if (item["polarity"] == st["polarity"]["affirmed"] and neg) or (item["polarity"] == st["polarity"]["negated"] and not neg):
        flags.add("guard_mismatch")
    if item["modality"] == st["modality_asserted"] and mod:
        flags.add("guard_mismatch")
    if is_lang_mixed(quote):
        flags.add("lang_mixed")
    if find_boosters(item["proposition"], passage_text):
        flags.add("forbidden_booster")
    if st["ocr_flag"] in passage_flags:
        flags.add("ocr_flagged")
    return sorted(flags)


def status_violation(item: dict[str, Any]) -> bool:
    """Party/subject statements may not rank above `reported`."""
    st = lexicons()["status"]
    return item["speaker_role"] in st["party_subject_roles"] and item["epistemic_status"] not in st["party_subject_allowed_status"]


def triage_class(flags: list[str]) -> str:
    """Class I (individual decision) for any guard-raised flag that questions the claim itself."""
    return "I" if {"guard_mismatch", "forbidden_booster", "ocr_flagged"} & set(flags) else "II"


# --- gold-label evaluation ---------------------------------------------------------

def evaluate_gold(gold: list[dict[str, Any]]) -> dict[str, Any]:
    """Confusion matrix per guard type and language; sensitivity and false-positive rate."""
    fns = {"negation": lambda t: bool(find_negation(t)), "modality": lambda t: bool(find_modality(t))}
    out: dict[str, Any] = {"lexicon_version": lexicons()["version"], "n": len(gold), "cells": {}}
    for kind, fn in fns.items():
        for lang in ("pl", "en", "mixed", "all"):
            tp = fp = tn = fn_ = 0
            for g in gold:
                if lang != "all" and g["lang"] != lang:
                    continue
                pred, truth = fn(g["text"]), bool(g[kind])
                tp += pred and truth
                fp += pred and not truth
                tn += (not pred) and (not truth)
                fn_ += (not pred) and truth
            out["cells"][f"{kind}/{lang}"] = {
                "tp": tp, "fn": fn_, "fp": fp, "tn": tn,
                "sensitivity": (tp / (tp + fn_)) if tp + fn_ else None,
                "false_positive_rate": (fp / (fp + tn)) if fp + tn else None}
    return out
