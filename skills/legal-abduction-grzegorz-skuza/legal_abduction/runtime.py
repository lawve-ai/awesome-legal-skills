"""Shared deterministic runtime: canonical JSON, hashing, safe paths, atomic
publication, batch execution with checkpoints/resume. Standard library only."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, Sequence

DEFAULT_STEP_BUDGET_S = 90.0

# T-CLI-ERROR: stable exit-code mapping.
EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_USAGE = 2
EXIT_NOT_IMPLEMENTED = 3
EXIT_PATH = 4
EXIT_IO = 5
EXIT_INTERRUPTED = 6
EXIT_INTEGRITY = 7
EXIT_POLICY = 8

EPHEMERAL_KEYS = frozenset({"run_id", "step_id"})  # plus *_at and *_path


class LaError(Exception):
    """Error with a stable English code and PL/EN display text."""

    def __init__(self, code: str, en: str, pl: str, exit_code: int = EXIT_INTERNAL,
                 ids: dict[str, str] | None = None):
        super().__init__(en)
        self.code, self.en, self.pl = code, en, pl
        self.exit_code = exit_code
        self.ids = ids or {}

    def envelope(self, lang: str = "en") -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "ids": dict(self.ids),
                "message": self.pl if lang == "pl" else self.en,
                "message_en": self.en,
                "message_pl": self.pl,
            },
        }


class Interrupted(LaError):
    pass


# --- canonical JSON / hashing -------------------------------------------------

def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


def _is_ephemeral(key: str) -> bool:
    return key in EPHEMERAL_KEYS or key.endswith("_at") or key.endswith("_path")


def strip_ephemeral(obj: Any) -> Any:
    """Drop volatile fields for determinism comparison only; never for audit."""
    if isinstance(obj, dict):
        return {k: strip_ephemeral(v) for k, v in obj.items() if not _is_ephemeral(k)}
    if isinstance(obj, list):
        return [strip_ephemeral(v) for v in obj]
    return obj


def stable_sorted(items: Iterable[Any], key: Callable[[Any], Any] | None = None) -> list[Any]:
    """Sort by code point (locale independent)."""
    return sorted(items, key=key)


# --- safe paths / atomic publication -----------------------------------------

def _is_link_or_reparse(p: Path) -> bool:
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


_BAD_NAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_DEVICE_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                          *(f"LPT{i}" for i in range(1, 10))})


def _bad_name() -> LaError:
    return LaError("PATH_NAME_REJECTED", "Path component is not portable or is reserved.",
                   "Składnik ścieżki jest niedozwolony lub zastrzeżony.", EXIT_PATH)


def safe_path(case_dir: Path | str, rel: str) -> Path:
    """Resolve rel inside case_dir; reject traversal, absolute paths, links."""
    root = Path(case_dir).resolve()
    if os.path.isabs(rel) or Path(rel).drive or rel.startswith(("/", "\\")):
        raise LaError("PATH_OUTSIDE_CASE", "Path must be relative to the case directory.",
                      "Ścieżka musi być względna wobec katalogu sprawy.", EXIT_PATH)
    candidate = root.joinpath(rel)
    if not Path(rel).parts:
        raise _bad_name()
    # Check each existing component for links before resolving.
    cur = root
    for part in Path(rel).parts:
        if part == "..":
            raise LaError("PATH_OUTSIDE_CASE", "Path escapes the case directory.",
                          "Ścieżka wychodzi poza katalog sprawy.", EXIT_PATH)
        if part == "." or _BAD_NAME_CHARS.search(part) or part.endswith((".", " ")) \
                or part.split(".")[0].upper() in _DEVICE_NAMES:
            raise _bad_name()
        cur = cur / part
        if _is_link_or_reparse(cur):
            raise LaError("PATH_LINK_REJECTED", "Symlink or reparse point rejected.",
                          "Odrzucono dowiązanie symboliczne lub punkt ponownej analizy.", EXIT_PATH)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise LaError("PATH_OUTSIDE_CASE", "Path escapes the case directory.",
                      "Ścieżka wychodzi poza katalog sprawy.", EXIT_PATH) from None
    return resolved


def atomic_write(case_dir: Path | str, rel: str, data: bytes) -> Path:
    """Stage in the target directory, fsync, then atomically rename."""
    target = safe_path(case_dir, rel)
    tmp = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".stage-", suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except OSError as e:
        raise LaError("IO_WRITE_FAILED", "Write failed; no artifact published.",
                      "Zapis nie powiódł się; nie opublikowano artefaktu.", EXIT_IO,
                      {"errno": str(e.errno)}) from e
    finally:
        if tmp is not None and os.path.exists(tmp):
            os.unlink(tmp)
    return target


def run_subprocess(args: Sequence[str], **kw: Any) -> subprocess.CompletedProcess:
    if isinstance(args, (str, bytes)) or not all(isinstance(a, str) for a in args):
        raise LaError("SUBPROCESS_ARGV_REQUIRED", "Subprocess requires an argument list.",
                      "Podproces wymaga listy argumentów.", EXIT_USAGE)
    kw.pop("shell", None)
    return subprocess.run(list(args), shell=False, **kw)


# --- checkpoints (T-RESUME) ---------------------------------------------------

class CheckpointStore(Protocol):
    def load(self, step_id: str, batch_no: int) -> dict[str, Any] | None: ...
    def save(self, step_id: str, batch_no: int, record: dict[str, Any]) -> None: ...


class MemoryCheckpointStore:
    """Test adapter; the production store arrives with LA-004."""

    def __init__(self) -> None:
        self.data: dict[tuple[str, int], dict[str, Any]] = {}

    def load(self, step_id: str, batch_no: int) -> dict[str, Any] | None:
        return self.data.get((step_id, batch_no))

    def save(self, step_id: str, batch_no: int, record: dict[str, Any]) -> None:
        self.data[(step_id, batch_no)] = record


def step_identity(name: str, inputs: Any) -> str:
    return f"{name}:{sha256_obj(inputs)[:16]}"


def run_step(
    name: str,
    items: Sequence[Any],
    batch_fn: Callable[[Sequence[Any]], list[Any]],
    store: CheckpointStore,
    publish: Callable[[list[Any]], None],
    *,
    batch_size: int = 10,
    resume: bool = False,
    budget_s: float = DEFAULT_STEP_BUDGET_S,
    cancel: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Any]:
    """Run batches; checkpoints are working state, publish() is called only
    after every batch is complete. Resume reuses verified batches only."""
    step_id = step_identity(name, items)
    batches = [list(items[i:i + batch_size]) for i in range(0, len(items), batch_size)]
    start = time.monotonic()
    results: list[Any] = []
    for n, batch in enumerate(batches):
        if cancel is not None and cancel.is_set():
            raise Interrupted("CANCELLED", "Cancelled; no final artifact published.",
                              "Anulowano; nie opublikowano wyniku końcowego.", EXIT_INTERRUPTED,
                              {"step_id": step_id})
        if time.monotonic() - start > budget_s:
            raise Interrupted("STEP_BUDGET_EXCEEDED", "Step budget exceeded; resume with --resume.",
                              "Przekroczono budżet kroku; wznów z --resume.", EXIT_INTERRUPTED,
                              {"step_id": step_id})
        in_hash = sha256_obj(batch)
        rec = store.load(step_id, n) if resume else None
        if rec is not None and rec.get("input_sha256") == in_hash \
                and rec.get("output_sha256") == sha256_obj(rec.get("output")):
            out = rec["output"]
        else:
            out = batch_fn(batch)
            store.save(step_id, n, {"input_sha256": in_hash, "output": out,
                                    "output_sha256": sha256_obj(out)})
        results.extend(out)
        if on_progress is not None:
            on_progress(n + 1, len(batches))
    publish(results)
    return results
