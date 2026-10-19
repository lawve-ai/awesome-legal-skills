"""Uncovered-observation profiles based only on approved assessments (LA-015)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import matrix


def classify(grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-observation classification of a matrix grid ({observation_ids, hypotheses, rows}); pure."""
    by_observation: dict[str, list[dict[str, Any]]] = {}
    for row in grid["rows"]:
        by_observation.setdefault(row["observation_id"], []).append(row)
    results = []
    no_hypotheses = grid["hypotheses"] == 0
    for observation_id in grid["observation_ids"]:
        rows = by_observation.get(observation_id, [])
        missing = [r["hypothesis_id"] for r in rows if r["status"] == "not_assessed"]
        relations = [r["assessment"]["relation"] for r in rows if r["assessment"] is not None]
        categories: list[str] = []
        if not missing and rows:
            if all(r == "conflicts" for r in relations):
                categories.append("conflicts_with_all")
            elif all(r == "supports" for r in relations):
                categories.append("supports_all")
            elif not any(r == "supports" for r in relations):
                categories.append("without_support")
        reasons = ["no_approved_hypotheses"] if no_hypotheses else []
        results.append({"observation_id": observation_id,
                "status": "incomplete" if missing or no_hypotheses else "complete",
                "missing_hypothesis_ids": missing, "incomplete_reasons": reasons, "categories": categories})
    return results


def report(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    grid = matrix.matrix_rows(case_dir, scope_id)
    results = classify(grid)
    return {"ok": True, "scope_id": scope_id, "complete": grid["complete"],
            "incomplete_observations": sum(r["status"] == "incomplete" for r in results),
            "observations": results}
