"""`doctor`: detect (never install) host capabilities without reading case files.

Every value is tagged `declared`, `observed` or `unverifiable`; nothing unmeasured
is presented as verified, and persistence between sessions is never claimed.
`human_file` eligibility requires an *observed* permission denial when probing
the review directory; a declaration, a read-only file flag or any other write
error does not qualify.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .runtime import atomic_write, canonical_json

MIN_PYTHON = (3, 12)
DEFAULT_STEP_BUDGET_S = 90
LEVELS = ("A", "B", "C")
TOOLS = {"pdftotext": "pdftotext", "tesseract": "tesseract", "jq": "jq", "clingo": "clingo"}

# capability, condition, behaviour, code, blocking
MATRIX: list[dict[str, Any]] = [
    {"capability": "python", "condition": "version below 3.12", "behavior": "every step except doctor refuses to run",
     "code": "E_PYTHON_TOO_OLD", "blocking": True},
    {"capability": "sqlite_json", "condition": "SQLite lacks JSON functions", "behavior": "case database cannot be created",
     "code": "E_SQLITE_JSON_MISSING", "blocking": True},
    {"capability": "pdf_extractor", "condition": "neither pypdf nor pdftotext found",
     "behavior": "PDF passages are flagged needs_text", "code": "W_PDF_EXTRACTOR_MISSING", "blocking": False},
    {"capability": "ocr", "condition": "tesseract not found", "behavior": "scanned pages are flagged needs_text",
     "code": "W_OCR_MISSING", "blocking": False},
    {"capability": "jq", "condition": "jq not found", "behavior": "P1 shell wrappers unavailable; P0 unaffected",
     "code": "W_JQ_MISSING", "blocking": False},
    {"capability": "clingo", "condition": "clingo not found", "behavior": "P1 constraint backend unavailable; P0 unaffected",
     "code": "W_CLINGO_MISSING", "blocking": False},
    {"capability": "review_dir", "condition": "directory missing or not given",
     "behavior": "human_file unavailable; strongest class human_via_agent", "code": "W_REVIEW_DIR_MISSING", "blocking": False},
    {"capability": "review_dir", "condition": "agent process can write to it",
     "behavior": "human_file unavailable; strongest class human_via_agent", "code": "W_REVIEW_DIR_WRITABLE",
     "blocking": False},
    {"capability": "review_dir", "condition": "write failed for a reason other than permission denial",
     "behavior": "read-only not proven; strongest class human_via_agent", "code": "W_REVIEW_DIR_UNVERIFIED",
     "blocking": False},
    {"capability": "disk", "condition": "free space not measurable", "behavior": "limit reported as unmeasured",
     "code": "W_DISK_UNMEASURED", "blocking": False},
    {"capability": "disk", "condition": "free space below the caller-supplied minimum",
     "behavior": "ingest and extract refuse to start", "code": "E_DISK_LOW", "blocking": True},
    {"capability": "memory", "condition": "available memory not measurable", "behavior": "limit reported as unmeasured",
     "code": "W_MEMORY_UNMEASURED", "blocking": False},
    {"capability": "persistence", "condition": "level B (or undeclared level): persistence cannot be verified from inside",
     "behavior": "continuity only via case export; reminder after every review import",
     "code": "W_PERSISTENCE_UNVERIFIED", "blocking": False},
    {"capability": "level", "condition": "no host level declared", "behavior": "treated as A; no promise about G2",
     "code": "W_LEVEL_UNDECLARED", "blocking": False},
]


def _tag(status: str, **kw: Any) -> dict[str, Any]:
    return {"status": status, **kw}


def _tool(name: str) -> dict[str, Any]:
    path = shutil.which(TOOLS[name])
    return _tag("observed", present=path is not None, **({"path": path} if path else {}))


def probe_review_dir(review_dir: Path | str | None) -> dict[str, Any]:
    """Controlled write probe: exclusive create of an own, uniquely named file; never overwrites."""
    if review_dir is None:
        return _tag("unverifiable", result="not_given")
    d = Path(review_dir)
    shown = str(d.resolve())  # bind the verdict to the directory actually probed
    if not d.is_dir():
        return _tag("observed", result="missing", path=shown)
    probe = d / f".la-probe-{uuid.uuid4().hex}.tmp"
    try:
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except PermissionError:
        return _tag("observed", result="read_only_confirmed", path=shown)
    except OSError as e:
        return _tag("unverifiable", result="write_failed_other", errno=e.errno, path=shown)
    left = False
    try:
        os.close(fd)
    finally:
        try:
            os.unlink(probe)  # only the exact probe file created above
        except OSError:
            left = True
    return _tag("observed", result="writable", path=shown, **({"probe_left_behind": probe.name} if left else {}))


def _memory_available() -> dict[str, Any]:
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):  # type: ignore[attr-defined]
                return _tag("observed", bytes=int(ms.ullAvailPhys))
        else:
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    return _tag("observed", bytes=int(line.split()[1]) * 1024)
    except (OSError, ValueError, AttributeError):
        pass
    return _tag("unverifiable")


def _disk_free(path: Path | str | None) -> dict[str, Any]:
    p = Path(path) if path else Path(tempfile.gettempdir())
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return _tag("observed", bytes=shutil.disk_usage(p).free)
    except OSError:
        return _tag("unverifiable")


def _sqlite_json() -> bool:
    try:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("SELECT json_valid('{}')").fetchone()
        finally:
            conn.close()
        return True
    except sqlite3.Error:
        return False


def collect(*, declared_level: str | None = None, review_dir: Path | str | None = None,
            disk_path: Path | str | None = None, step_budget_s: int = DEFAULT_STEP_BUDGET_S) -> dict[str, Any]:
    """Gather capabilities. Reads no case files and needs no profile."""
    return {
        "schema_version": 1,
        "level": {"declared": _tag("declared", value=declared_level if declared_level in LEVELS else None),
                  "verified": _tag("unverifiable", note="level cannot be verified from inside the session")},
        "python": _tag("observed", version=".".join(map(str, sys.version_info[:3])),
                       meets_minimum=sys.version_info >= MIN_PYTHON),
        "db_engine": _tag("observed", engine="sqlite", version=sqlite3.sqlite_version, json_functions=_sqlite_json()),
        "extractors": {"pypdf": _tag("observed", present=importlib.util.find_spec("pypdf") is not None),
                       "pdftotext": _tool("pdftotext"), "tesseract": _tool("tesseract")},
        "tools": {"jq": _tool("jq"), "clingo": _tool("clingo")},
        "review_dir": probe_review_dir(review_dir),
        "disk_free": _disk_free(disk_path),
        "memory_available": _memory_available(),
        "step_budget_s": _tag("declared", value=step_budget_s, measured=False),
        "persistence": _tag("unverifiable", note="persistence between sessions is never assumed"),
    }


def evaluate(caps: dict[str, Any], min_free_bytes: int | None = None) -> list[dict[str, Any]]:
    """Map capabilities to degradation findings (code, blocking)."""
    codes: list[str] = []
    if not caps["python"]["meets_minimum"]:
        codes.append("E_PYTHON_TOO_OLD")
    if not caps["db_engine"]["json_functions"]:
        codes.append("E_SQLITE_JSON_MISSING")
    if not (caps["extractors"]["pypdf"]["present"] or caps["extractors"]["pdftotext"]["present"]):
        codes.append("W_PDF_EXTRACTOR_MISSING")
    if not caps["extractors"]["tesseract"]["present"]:
        codes.append("W_OCR_MISSING")
    if not caps["tools"]["jq"]["present"]:
        codes.append("W_JQ_MISSING")
    if not caps["tools"]["clingo"]["present"]:
        codes.append("W_CLINGO_MISSING")
    rd = caps["review_dir"].get("result")
    codes += {"not_given": ["W_REVIEW_DIR_MISSING"], "missing": ["W_REVIEW_DIR_MISSING"],
              "writable": ["W_REVIEW_DIR_WRITABLE"], "write_failed_other": ["W_REVIEW_DIR_UNVERIFIED"]}.get(rd, [])
    disk = caps["disk_free"]
    if disk["status"] != "observed":
        codes.append("W_DISK_UNMEASURED")
    elif min_free_bytes is not None and disk["bytes"] < min_free_bytes:
        codes.append("E_DISK_LOW")
    if caps["memory_available"]["status"] != "observed":
        codes.append("W_MEMORY_UNMEASURED")
    level = caps["level"]["declared"]["value"]
    if level is None:
        codes.append("W_LEVEL_UNDECLARED")
    if level in (None, "B"):
        codes.append("W_PERSISTENCE_UNVERIFIED")
    by_code = {r["code"]: r for r in MATRIX}
    return [{"code": c, "blocking": by_code[c]["blocking"], "behavior": by_code[c]["behavior"]} for c in codes]


def strongest_review_class(caps: dict[str, Any]) -> str:
    """`human_file` only after an observed permission denial on the review directory."""
    rd = caps["review_dir"]
    return "human_file" if rd.get("status") == "observed" and rd.get("result") == "read_only_confirmed" \
        else "human_via_agent"


def run_doctor(case_dir: Path | str | None, *, declared_level: str | None = None,
               review_dir: Path | str | None = None, step_budget_s: int = DEFAULT_STEP_BUDGET_S,
               min_free_bytes: int | None = None) -> dict[str, Any]:
    caps = collect(declared_level=declared_level, review_dir=review_dir, disk_path=case_dir,
                   step_budget_s=step_budget_s)
    caps["findings"] = evaluate(caps, min_free_bytes)
    caps["strongest_review_class"] = strongest_review_class(caps)
    if case_dir is not None:
        Path(case_dir).mkdir(parents=True, exist_ok=True)
        atomic_write(case_dir, "capabilities.json", canonical_json(caps) + b"\n")
    return caps


def render_matrix_markdown() -> str:
    rows = ["| Capability | Condition | Behaviour | Code | Blocking |", "| --- | --- | --- | --- | --- |"]
    rows += [f"| {r['capability']} | {r['condition']} | {r['behavior']} | `{r['code']}` | "
             f"{'yes' if r['blocking'] else 'no'} |" for r in MATRIX]
    return "\n".join(rows) + "\n"
