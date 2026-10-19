"""`status --json`: steps, queue, gaps and the level-B export reminder.

Read-only apart from opening the case database; works without a complete profile
and reports what is missing instead of failing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .profile import check_profile, load_profile
from .repository import Repository
from .runtime import LaError


def build_status(case_dir: Path | str, *, session_end: bool = False) -> dict[str, Any]:
    root = Path(case_dir)
    missing: list[str] = []
    profile: dict[str, Any] | None = None
    try:
        profile = load_profile(root)
        check_profile(profile)
    except LaError as e:
        missing.append(e.code + (f":{e.ids['field']}" if "field" in e.ids else ""))
    if not (root / "capabilities.json").exists():
        missing.append("capabilities.json")
    steps: list[dict[str, str]] = []
    queue: dict[str, int] = {}
    reviews = 0
    db = root / "case.db"
    if profile is not None and db.exists():
        repo = Repository(db, profile["case_id"])
        try:
            steps = repo.list_steps()
            for state in repo.proposal_state().values():
                queue[state] = queue.get(state, 0) + 1
            reviews = repo.review_count()
        finally:
            repo.close()
    elif profile is not None:
        missing.append("case.db")
    level = (profile or {}).get("host_level")
    exported = 0
    marker = root / "export_marker.json"  # written by case export (LA-019); absent = nothing exported
    if marker.exists():
        try:
            exported = int(json.loads(marker.read_text(encoding="utf-8")).get("reviews_exported", 0))
        except (ValueError, TypeError, AttributeError):
            exported = 0
    reminder = None
    if level == "B":
        if reviews > exported:
            reminder = "review_import"
        elif session_end:
            reminder = "session_end"
    pending = 0
    if profile is not None and db.exists():
        from .bundles import pending_originals
        pending = len(pending_originals(root))
    return {"ok": True, "originals_pending": pending, "steps": steps, "queue": dict(sorted(queue.items())), "missing": missing,
            "reviews": reviews, "export_reminder": {"required": reminder is not None, "reason": reminder,
                                                    "action": "case export" if reminder else None}}
