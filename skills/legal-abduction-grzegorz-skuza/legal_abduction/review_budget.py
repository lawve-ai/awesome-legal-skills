"""Review budget (R8): predicted load before any H packet for hypotheses/matrix is emitted.

load = (class I items + class II samples) x seconds_per_item; the default budget is
120 minutes at 45 s per item (an uncalibrated hypothesis, Q9). Exceeding it raises
`E_REVIEW_BUDGET` with three concrete options before packets go to a model; an
override needs a written justification that is stored against the Run. When content
does not exist yet, the forecast uses the declared counts and counts every unknown
cell as class I; an undeclared count is an error, never zero.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from .repository import Repository
from .runtime import EXIT_POLICY, LaError, sha256_obj

DEFAULT_BUDGET_MINUTES = 120
DEFAULT_SECONDS_PER_ITEM = 45
SUGGESTIONS = ["Select fewer observations (step 6).", "Reduce hypotheses after mechanism de-duplication.",
               "Split the question into narrower ones."]


def sample_size(n: int) -> int:
    """min(n, max(5, ceil(10% of n)))."""
    return min(n, max(5, math.ceil(0.1 * n)))


def predicted_minutes(class_i: int, class_ii_batches: list[int], seconds_per_item: float = DEFAULT_SECONDS_PER_ITEM) -> float:
    items = class_i + sum(sample_size(n) for n in class_ii_batches)
    return items * seconds_per_item / 60.0


def forecast_hypotheses(declared_hypotheses: int | None) -> tuple[int, list[int]]:
    """Every hypothesis is class I, plus one conservative bridge-rule assumption each."""
    if declared_hypotheses is None or declared_hypotheses < 0:
        raise _missing("declared hypotheses")
    return declared_hypotheses * 2, []


def forecast_matrix(observations: int | None, hypotheses: int | None) -> tuple[int, list[int]]:
    """Unknown distinguishing status: every cell is conservatively class I."""
    if observations is None or hypotheses is None or observations < 0 or hypotheses < 0:
        raise _missing("observation and hypothesis counts")
    return observations * hypotheses, []


def _missing(what: str) -> LaError:
    return LaError("E_BUDGET_FORECAST_MISSING", f"Review-load forecast needs the {what}; unknown is not zero.",
                   f"Prognoza obciążenia recenzji wymaga: {what}; nieznane nie jest zerem.", EXIT_POLICY)


def check_budget(class_i: int, class_ii_batches: list[int], *, budget_minutes: float = DEFAULT_BUDGET_MINUTES,
                 seconds_per_item: float = DEFAULT_SECONDS_PER_ITEM) -> dict[str, Any]:
    minutes = predicted_minutes(class_i, class_ii_batches, seconds_per_item)
    if minutes > budget_minutes:
        raise LaError("E_REVIEW_BUDGET", f"Predicted review load {minutes:.1f} min exceeds the {budget_minutes} min "
                      "budget. Options: " + " ".join(SUGGESTIONS),
                      f"Przewidywane obciążenie recenzji {minutes:.1f} min przekracza budżet {budget_minutes} min.",
                      EXIT_POLICY, {"predicted_minutes": f"{minutes:.1f}", "budget_minutes": str(budget_minutes)})
    return {"predicted_minutes": minutes, "budget_minutes": budget_minutes, "within": True}


def make_budget_hook(case_dir: Path | str, *, declared_hypotheses: int | None = None,
                     observations: int | None = None, override_reason: str | None = None,
                     budget_minutes: float = DEFAULT_BUDGET_MINUTES,
                     seconds_per_item: float = DEFAULT_SECONDS_PER_ITEM) -> Callable[[str, int, int], bool]:
    """Hook for packets.prepare. Re-evaluated on every call, so a changed forecast is re-checked."""
    from .profile import load_profile

    def hook(task_type: str, chars: int, n_items: int) -> bool:
        if task_type == "hypotheses":
            class_i, batches = forecast_hypotheses(declared_hypotheses)
        elif task_type == "matrix":
            class_i, batches = forecast_matrix(observations, declared_hypotheses)
        else:
            return True
        try:
            check_budget(class_i, batches, budget_minutes=budget_minutes, seconds_per_item=seconds_per_item)
        except LaError as e:
            if e.code != "E_REVIEW_BUDGET" or not (override_reason and override_reason.strip()):
                raise
            _record_override(case_dir, load_profile(case_dir)["case_id"], task_type, override_reason.strip(),
                             predicted_minutes(class_i, batches, seconds_per_item), budget_minutes)
        return True
    return hook


def _record_override(case_dir: Path | str, case_id: str, task_type: str, reason: str, predicted: float,
                     budget: float) -> None:
    repo = Repository(Path(case_dir) / "case.db", case_id)
    try:
        run = repo.reader().runs()[-1]
        step = f"budget-override:{sha256_obj([task_type, reason, round(predicted, 3), budget])[:16]}"
        repo.add_step(step, run["id"], "budget-override", "none")
        repo.add_frozen_many("value_records", [{
            "id": step, "kind": "budget_override", "run_id": run["id"], "task_type": task_type, "reason": reason,
            "predicted_minutes": round(predicted, 3), "budget_minutes": budget}], step)
    finally:
        repo.close()


def overrides(case_dir: Path | str, case_id: str) -> list[dict[str, Any]]:
    """Recorded overrides, for the report header."""
    repo = Repository(Path(case_dir) / "case.db", case_id)
    try:
        return [b for b, _ in repo.frozen_bodies("value_records") if b.get("kind") == "budget_override"]
    finally:
        repo.close()
