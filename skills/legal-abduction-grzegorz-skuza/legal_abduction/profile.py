"""Case profile (`case.json`), analysis/render hashes and the processing gate.

Consent (`model_processing`) and `deployer_ack` come only from the human-supplied
profile, never from corpus text: this module never reads corpus content, and the
profile schema rejects unknown keys. Legal content is a working assessment of the
PRD, not verified law.

Check precedence (T-PROFILE-MODEL, stable): language -> completeness (fixed field
order) -> validity -> `judicial` context -> high-risk ack. The model-processing
*gate* is separate: anything other than exactly `allowed` is restricted.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from . import __version__
from .integrity import EMPTY_ROOT
from .repository import SCHEMA_DIR, Repository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, atomic_write, canonical_json, safe_path, sha256_obj
from .validation import load_registry, validate

LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"
ANALYSIS_FIELDS = ("question", "time_window", "corpus_scope", "jurisdiction", "purpose", "perspectives",
                   "deployment_context")
REQUIRED_ORDER = ("lang", *ANALYSIS_FIELDS, "model_processing")
HIGH_RISK_CONTEXTS = frozenset({"internal_employee", "law_enforcement"})
UNSUPPORTED_CONTEXTS = frozenset({"judicial"})
CHANGE_AUDITED_FIELDS = ("deployer_ack", "host_level", "model_processing")
_catalogs: dict[str, dict[str, str]] = {}


def normalize_context(ctx: str) -> str:
    """Case, whitespace, dash and Unicode-compatibility variants map to one key."""
    return unicodedata.normalize("NFKC", ctx).strip().casefold().replace(" ", "_").replace("-", "_")


def catalog(lang: str) -> dict[str, str]:
    if lang not in _catalogs:
        _catalogs[lang] = json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    return _catalogs[lang]


def profile_error(code: str, exit_code: int, field: str | None = None) -> LaError:
    kw = {"field": field} if field is not None else {}
    return LaError(code, catalog("en")[code].format(**kw), catalog("pl")[code].format(**kw), exit_code,
                   {"field": field} if field is not None else None)


def _blank(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def check_profile(p: dict[str, Any]) -> None:
    """Raise the first applicable profile error in the documented precedence."""
    if _blank(p.get("lang")):
        raise profile_error("E_LANG_REQUIRED", EXIT_USAGE)
    for f in REQUIRED_ORDER:
        if _blank(p.get(f)):
            raise profile_error("E_PROFILE_INCOMPLETE", EXIT_USAGE, f)
    if _blank(p.get("case_id")):
        raise profile_error("E_PROFILE_INCOMPLETE", EXIT_USAGE, "case_id")
    persp = p["perspectives"]
    if isinstance(persp, list):
        for i, item in enumerate(persp):
            for f in ("role", "conduct_in_scope"):
                if not isinstance(item, dict) or _blank(item.get(f)):
                    raise profile_error("E_PROFILE_INCOMPLETE", EXIT_USAGE, f"perspectives[{i}].{f}")
    errs = validate(p, load_registry(SCHEMA_DIR)["la:schema/profile/v1"])
    if errs:
        raise profile_error("E_PROFILE_INVALID", EXIT_USAGE, errs[0].path or "(root)")
    ids = [x["id"] for x in persp]
    if len(set(ids)) != len(ids):
        raise profile_error("E_PROFILE_INVALID", EXIT_USAGE, "perspectives")
    ctx = normalize_context(p["deployment_context"])
    if ctx in UNSUPPORTED_CONTEXTS:
        raise profile_error("E_CONTEXT_UNSUPPORTED", EXIT_POLICY)
    if ctx in HIGH_RISK_CONTEXTS and _blank(p.get("deployer_ack")):
        raise profile_error("E_HIGH_RISK_ACK", EXIT_POLICY)


# --- hashes -------------------------------------------------------------------

def analysis_hash(p: dict[str, Any]) -> str:
    """Content-affecting fields only; perspectives are a set (sorted by id)."""
    obj = {k: p[k] for k in ANALYSIS_FIELDS}
    obj["perspectives"] = sorted(p["perspectives"], key=lambda x: x["id"])
    return sha256_obj(obj)


def render_hash(p: dict[str, Any]) -> str:
    return sha256_obj({"lang": p["lang"], "report_profile": p.get("report_profile", "working")})


# --- gate ---------------------------------------------------------------------

def load_profile(case_dir: Path | str) -> dict[str, Any]:
    f = safe_path(case_dir, "case.json")
    if not f.exists():
        raise profile_error("E_PROFILE_MISSING", EXIT_USAGE)
    try:
        p = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise profile_error("E_PROFILE_INVALID", EXIT_USAGE, "(root)") from e
    if not isinstance(p, dict):
        raise profile_error("E_PROFILE_INVALID", EXIT_USAGE, "(root)")
    return p


def declared_lang(case_dir: Path | str) -> str | None:
    """Best-effort language for error messages; never raises."""
    try:
        lang = load_profile(case_dir).get("lang")
    except (LaError, OSError, ValueError):
        return None
    return lang if lang in ("pl", "en") else None


def require_ready(case_dir: Path | str, step: str, *, touches_corpus: bool) -> dict[str, str]:
    """Common gate for every command before it reads corpus content.

    Only `doctor` (and `init`, which creates the profile) bypass it. The host
    level is the one declared in the human-edited profile (absent -> `A`, the
    most restrictive). LIMIT: level and consent live in a file the agent session
    can also edit, and level C cannot be verified from inside a session; the gate
    stops accidental and prompt-injected misuse, not a malicious agent. Changes to
    consent/level are recorded as audit steps (see `update_profile`).
    """
    if step in ("doctor", "init"):
        return {"mode": "none", "lang": "en"}
    p = load_profile(case_dir)
    check_profile(p)
    level = p.get("host_level", "A")
    if touches_corpus and p["model_processing"] != "allowed" and level in ("A", "B"):
        raise profile_error("E_LEVEL_C_REQUIRED", EXIT_POLICY)
    return {"mode": "host" if p["model_processing"] == "allowed" and level != "C" else "none", "lang": p["lang"]}


# --- init / update --------------------------------------------------------------

def _write_profile(case_dir: Path | str, p: dict[str, Any]) -> None:
    atomic_write(case_dir, "case.json", canonical_json(p) + b"\n")


def _new_run(repo: Repository, p: dict[str, Any], parent: str | None) -> str:
    runs = repo.reader().runs()
    n = len(runs) + 1
    prev = next((r for r in runs if r["id"] == parent), None)
    ah = analysis_hash(p)
    run_id = f"run:{n:04d}-{ah[:8]}"
    # A new Run keeps the corpus and approved-set state of its parent; only content hashes of the profile change.
    repo.begin_run({"id": run_id, "corpus_hash": prev["corpus_hash"] if prev else sha256_obj([]),
                    "analysis_hash": ah, "render_hash": render_hash(p),
                    "approved_set_hash": prev["approved_set_hash"] if prev else EMPTY_ROOT,
                    "code_version": __version__, "model_id": "none",
                    "runtime": "python", "parent_run_id": parent})
    repo.add_step(f"init:{n}", run_id, "init", f"software:la.py@{__version__}")
    return run_id


def init_case(case_dir: Path | str, answers: dict[str, Any], case_id: str) -> dict[str, Any]:
    p = {**answers, "case_id": case_id}
    check_profile(p)
    root = Path(case_dir)
    if (root / "case.json").exists() or (root / "case.db").exists():
        raise profile_error("E_CASE_EXISTS", EXIT_USAGE)
    root.mkdir(parents=True, exist_ok=True)
    _write_profile(root, p)
    repo = Repository(root / "case.db", case_id)
    try:
        run_id = _new_run(repo, p, None)
    finally:
        repo.close()
    return {"ok": True, "run_id": run_id, "analysis_hash": analysis_hash(p), "render_hash": render_hash(p)}


def update_profile(case_dir: Path | str, changes: dict[str, Any]) -> dict[str, Any]:
    """New Run only if analysis_hash changes; lang/report profile change render_hash only.

    Consent/level/ack changes never alter hashes but are recorded as an audit step
    (field names and enum values only) before case.json is rewritten.
    """
    old = load_profile(case_dir)
    if changes.get("case_id", old["case_id"]) != old["case_id"]:
        raise profile_error("E_PROFILE_INVALID", EXIT_USAGE, "case_id")
    new = {**old, **changes}
    check_profile(new)
    repo = Repository(Path(case_dir) / "case.db", old["case_id"])
    try:
        runs = repo.reader().runs()
        run_id, new_run = runs[-1]["id"], False
        if analysis_hash(new) != runs[-1]["analysis_hash"]:
            run_id, new_run = _new_run(repo, new, runs[-1]["id"]), True
        audited = []
        for f in CHANGE_AUDITED_FIELDS:
            if old.get(f) != new.get(f):
                audited.append(f"{f}={'set' if new.get(f) else 'unset'}" if f == "deployer_ack" else f"{f}={new.get(f)}")
        if audited:
            repo.add_step(f"upd:{len(repo.list_steps()) + 1}", run_id, "profile_change:" + ",".join(audited),
                          f"software:la.py@{__version__}")
    finally:
        repo.close()
    _write_profile(case_dir, new)
    return {"ok": True, "run_id": run_id, "new_run": new_run, "analysis_changed": analysis_hash(new) != analysis_hash(old),
            "render_changed": render_hash(new) != render_hash(old)}
