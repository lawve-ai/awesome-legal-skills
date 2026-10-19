"""Approved assessment matrix operations (LA-015, R13)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import facts, packets, proposals, staleness
from .profile import load_profile
from .repository import Repository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, sha256_obj

def _err(code: str, en: str, pl: str, exit_code: int = EXIT_USAGE, ids: dict[str, str] | None = None) -> LaError:
    return LaError(code, en, pl, exit_code, ids)


def _scope(repo: Repository, scope_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    sets = {s["id"]: s for s in repo.reader().approved_rows("observation_sets")}
    if scope_id not in sets:
        raise _err("E_SCOPE_UNKNOWN", "No approved ObservationSet with this id.",
                   "Brak zatwierdzonego ObservationSet o tym id.", ids={"scope_id": scope_id})
    obs_set = sets[scope_id]
    observations = {o["id"]: o for o in repo.reader().approved_rows("observations")}
    missing = sorted(set(obs_set["observation_ids"]) - observations.keys())
    if missing:
        raise _err("E_MATRIX_SCOPE_INVALID", "The ObservationSet refers to missing observations.",
                   "ObservationSet wskazuje brakujące obserwacje.", ids={"count": str(len(missing))})
    hypotheses = [h for h in repo.reader().approved_rows("hypotheses") if h["scope_id"] == scope_id]
    effective = facts.effective_observation_ids(repo.reader(), obs_set)  # withdrawn out, replacements in
    return obs_set, [observations[i] for i in effective], hypotheses


def _current(repo: Repository) -> dict[tuple[str, str], dict[str, Any]]:
    return {(a["observation_id"], a["hypothesis_id"]): a for a in repo.reader().current_assessments()}


def basis_error(repo: Repository, observation_id: str, passage_ids: list[str]) -> str | None:
    observations = {o["id"]: o for o in repo.reader().approved_rows("observations")}
    observation = observations.get(observation_id)
    if observation is None:
        return "E_UNKNOWN_ID"
    claim_ids = set(observation["claim_ids"])
    allowed = {c["passage_id"] for c in repo.reader().approved_rows("claims") if c["id"] in claim_ids}
    return "E_MATRIX_BASIS_INVALID" if any(p not in allowed for p in passage_ids) else None


def matrix_rows(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    """Return the approved full cross-product; missing cells are explicitly not_assessed."""
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        obs_set, observations, hypotheses = _scope(repo, scope_id)
        current = _current(repo)
        rows = []
        for observation in observations:
            for hypothesis in hypotheses:
                assessment = current.get((observation["id"], hypothesis["id"]))
                rows.append({"observation_id": observation["id"], "hypothesis_id": hypothesis["id"],
                             "status": "assessed" if assessment else "not_assessed", "assessment": assessment})
        return {"ok": True, "scope_id": scope_id, "observation_set_id": obs_set["id"],
            "observations": len(observations), "observation_ids": [o["id"] for o in observations],
            "hypotheses": len(hypotheses), "expected_pairs": len(rows),
                "assessed_pairs": sum(r["status"] == "assessed" for r in rows),
                "complete": bool(hypotheses) and all(r["status"] == "assessed" for r in rows), "rows": rows}
    finally:
        repo.close()


def check(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    rows = matrix_rows(case_dir, scope_id)
    missing = [{"observation_id": r["observation_id"], "hypothesis_id": r["hypothesis_id"], "status": "not_assessed"}
               for r in rows["rows"] if r["status"] == "not_assessed"]
    reasons = ["no_approved_hypotheses"] if rows["hypotheses"] == 0 else []
    return {k: v for k, v in rows.items() if k != "rows"} | {"missing": missing, "incomplete_reasons": reasons}


def prepare(case_dir: Path | str, scope_id: str, *, model_id: str = "none", prompt_version: str | None = None,
            max_chars: int | None = None, budget_hook: packets.BudgetHook | None = None,
            synthetic: bool = False) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        obs_set, observations, hypotheses = _scope(repo, scope_id)
        if not hypotheses:
            raise _err("E_HYPOTHESES_REQUIRED", "The scope has no approved hypotheses.",
                       "Zakres nie ma zatwierdzonych hipotez.", EXIT_POLICY, {"scope_id": scope_id})
        current = _current(repo)
        missing = [(o, h) for o in observations for h in hypotheses if (o["id"], h["id"]) not in current]
        if not missing:
            return {"ok": True, "needed": False, "scope_id": scope_id, "missing_pairs": 0}
        passages = {p["id"]: p for p, _ in repo.frozen_bodies("passages")}
        objects = [packets.make_object("matrix_scope", scope_id, {
            "observation_ids": sorted(o["id"] for o in observations),
            "hypothesis_ids": sorted(h["id"] for h in hypotheses),
            "assessed_pairs": sorted([[o, h, assessment["id"], sha256_obj(assessment)]
                                       for (o, h), assessment in current.items()
                                       if o in {x["id"] for x in observations}
                                       and h in {x["id"] for x in hypotheses}]),
        })]
        objects += [packets.make_object("observation", o["id"], {k: o[k] for k in ("description", "claim_ids")})
                    for o in observations]
        objects += [packets.make_object("hypothesis", h["id"], {k: h[k] for k in (
            "mechanism", "scope_id", "kind", "burdens", "attributes_intent", "concerns_natural_person")})
                    for h in hypotheses]
        marker = staleness.marker_object(repo.reader(), [x["id"] for x in observations] + [x["id"] for x in hypotheses]
                                         + [a["id"] for a in current.values()])
        if marker:  # stale inputs must change the cache key so an old proposal cannot be reused
            objects.append(marker)
        pairs = [{"observation_id": o["id"], "hypothesis_id": h["id"]} for o, h in missing]
        observation_ids = {o["id"] for o, _ in missing}
        claim_ids = {cid for o in observations if o["id"] in observation_ids for cid in o["claim_ids"]}
        basis_ids = {c["passage_id"] for c in repo.reader().approved_rows("claims") if c["id"] in claim_ids}
        objects += [packets.make_object("passage", p, {k: passages[p][k] for k in ("text", "locator", "document_id")})
                    for p in sorted(basis_ids) if p in passages]
    finally:
        repo.close()
    result = packets.prepare(root, "matrix", objects, model_id=model_id, prompt_version=prompt_version,
                             max_chars=max_chars, budget_hook=budget_hook, synthetic=synthetic)
    return {**result, "needed": True, "scope_id": scope_id, "missing_pairs": len(pairs),
            "pairs": pairs}


def ingest(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    if packet.get("task_type") != "matrix":
        raise _err("E_UNKNOWN_TASK", "This is not a matrix packet.", "To nie jest pakiet macierzy.")
    root = Path(case_dir)
    profile = load_profile(root)
    packets.verify_packet(packet)
    if packet["case_id"] != profile["case_id"]:
        raise _err("E_FOREIGN_CASE", "The packet belongs to another case.", "Pakiet należy do innej sprawy.")
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        scope_obj = next((o for o in packet.get("items", []) if o.get("type") == "matrix_scope"), None)
        if not scope_obj:
            raise _err("E_MATRIX_STALE", "The packet has no matrix scope descriptor.",
                       "Pakiet nie zawiera opisu zakresu macierzy.")
        scope_id = scope_obj["id"]
        obs_set, observations, hypotheses = _scope(repo, scope_id)
        expected_obs = sorted(o["id"] for o in observations)
        expected_hyps = sorted(h["id"] for h in hypotheses)
        content = scope_obj["content"]
        if content.get("observation_ids") != expected_obs or content.get("hypothesis_ids") != expected_hyps:
            raise _err("E_MATRIX_STALE", "The matrix scope changed after packet preparation.",
                       "Zakres macierzy zmienił się po przygotowaniu pakietu.", EXIT_POLICY)
        valid_pairs = {(o, h) for o in expected_obs for h in expected_hyps}
        current = _current(repo)
        current_scope_pairs = sorted([o, h] for o, h in current if (o, h) in valid_pairs)
        snapshot_pairs = content.get("assessed_pairs")
        current_snapshot = sorted([[o, h, assessment["id"], sha256_obj(assessment)]
                                   for (o, h), assessment in current.items() if (o, h) in valid_pairs])
        if snapshot_pairs != current_snapshot:
            raise _err("E_MATRIX_STALE", "Approved assessments changed after packet preparation.",
                       "Zatwierdzone oceny zmieniły się po przygotowaniu pakietu.", EXIT_POLICY)

        def validate_matrix(task: str, body: dict[str, Any], known: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
            pairs = [(i["observation_id"], i["hypothesis_id"]) for i in body["items"]]
            if len(set(pairs)) != len(pairs):
                return body, "E_MATRIX_DUPLICATE_PAIR"
            for item, pair in zip(body["items"], pairs):
                if pair not in valid_pairs:
                    return body, "E_UNKNOWN_ID"
                if pair in current:
                    return body, "E_MATRIX_STALE"
                invalid_basis = basis_error(repo, item["observation_id"], item["basis_passage_ids"])
                if invalid_basis:
                    return body, invalid_basis
            return body, None

        proposal = proposals.ingest_proposal(root, packet, payload, enrich=validate_matrix)
        proposal["triage"] = ["I"] * len(proposal.get("payload", {}).get("items", [])) if proposal["code"] else []
        return proposal
    finally:
        repo.close()


def matrix_gate(case_dir: Path | str, scope_id: str, *, require_complete: bool = False) -> dict[str, Any]:
    result = check(case_dir, scope_id)
    if require_complete and not result["complete"]:
        raise _err("E_MATRIX_INCOMPLETE", "The assessment matrix has unassessed pairs.",
                   "Macierz ocen zawiera nieocenione pary.", EXIT_POLICY,
                   {"missing_pairs": str(len(result["missing"]))})
    return result
