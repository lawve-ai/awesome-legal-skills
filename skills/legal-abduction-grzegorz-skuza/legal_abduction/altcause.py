"""Alternative-cause checks (LA-014): an intent hypothesis needs a non-intent alternative in the same scope."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import hypotheses


def check(case_dir: Path | str) -> dict[str, Any]:
    r = hypotheses.check_set(case_dir)
    return {"ok": True, "blocked": bool(r["intent"]), "intent": r["intent"]}


def prepare(case_dir: Path | str, **kw: Any) -> dict[str, Any]:
    return hypotheses.prepare_altcause(case_dir, **kw)


def ingest(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    return hypotheses.ingest_altcause(case_dir, packet, payload)
