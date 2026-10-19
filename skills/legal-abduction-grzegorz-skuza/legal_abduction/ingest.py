"""Corpus freeze (R3): explicit files only, streaming SHA-256, signature-based type,
frozen copies, sorted manifest and `corpus_hash`, staged atomic publication and
resumable batches.

Rejected inputs (whole import, nothing published): missing/non-regular files,
symlinks or Windows reparse points anywhere in the given path, a path given twice
(or two spellings of one file), an encrypted PDF/OOXML/ZIP, a file that changes
while being read, an empty corpus, and configured limits. Originals are only
read. Ancestor links are rejected too (strict by design). Encryption detection is
heuristic and documented, not a guarantee.
"""
from __future__ import annotations

import hashlib
import csv
import io
import json
import os
import re
import shutil
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

from .repository import Repository
from .runtime import (EXIT_INTERRUPTED, EXIT_IO, EXIT_PATH, EXIT_USAGE, DEFAULT_STEP_BUDGET_S, Interrupted, LaError,
                      _is_link_or_reparse, atomic_write, canonical_json, safe_path, sha256_hex, sha256_obj)

CHUNK = 1024 * 1024
_EML_RE = re.compile(rb"^(Received|From|Return-Path|Message-ID|Date|MIME-Version|Subject|To):", re.I | re.M)
OLE_ENCRYPTED = "EncryptedPackage".encode("utf-16-le")

# Test seam: called after every chunk read so tests can change a file deterministically.
_after_chunk: Callable[[Path], None] | None = None


def _err(code: str, en: str, pl: str, exit_code: int = EXIT_USAGE, **ids: str) -> LaError:
    return LaError(code, en, pl, exit_code, ids or None)


# --- input validation ---------------------------------------------------------

def _identity(p: Path, st: os.stat_result) -> Any:
    return (st.st_dev, st.st_ino) if st.st_ino else os.path.normcase(str(p))


def validate_inputs(paths: list[str], max_files: int | None = None, max_file_bytes: int | None = None
                    ) -> list[dict[str, Any]]:
    """Return sorted, validated input descriptors or raise for the whole import."""
    if not paths:
        raise _err("E_CORPUS_EMPTY", "No input files were given.", "Nie podano plików wejściowych.")
    if max_files is not None and len(paths) > max_files:
        raise _err("E_LIMIT_EXCEEDED", "Too many input files.", "Zbyt wiele plików wejściowych.", limit="max_files")
    seen: set[Any] = set()
    out = []
    for raw in paths:
        p = Path(os.path.abspath(raw))
        cur = Path(p.anchor)
        for part in p.parts[1:]:
            cur = cur / part
            if _is_link_or_reparse(cur):
                raise _err("E_INPUT_LINK", "Symlinks and reparse points are rejected.",
                           "Dowiązania symboliczne i punkty reparse są odrzucane.", EXIT_PATH, name=p.name)
        try:
            st = os.lstat(p)
        except OSError as e:
            raise _err("E_INPUT_NOT_FILE", "Input is missing or unreadable.", "Plik wejściowy nie istnieje lub jest "
                       "nieczytelny.", EXIT_PATH, name=p.name) from e
        if not (st.st_mode & 0o170000 == 0o100000):
            raise _err("E_INPUT_NOT_FILE", "Only regular files are accepted (no directories).",
                       "Akceptowane są tylko zwykłe pliki (bez katalogów).", EXIT_PATH, name=p.name)
        key = _identity(p, st)
        if key in seen:
            raise _err("E_INPUT_DUPLICATE_PATH", "The same file was given more than once.",
                       "Ten sam plik podano więcej niż raz.", EXIT_PATH, name=p.name)
        seen.add(key)
        if max_file_bytes is not None and st.st_size > max_file_bytes:
            raise _err("E_LIMIT_EXCEEDED", "File exceeds the configured size limit.",
                       "Plik przekracza skonfigurowany limit rozmiaru.", limit="max_file_bytes", name=p.name)
        out.append({"path": str(p), "name": p.name, "size": st.st_size, "mtime_ns": st.st_mtime_ns})
    return sorted(out, key=lambda d: os.path.normcase(d["path"]))


# --- hashing / sniffing -------------------------------------------------------

def hash_and_stage(src: Path, dest: Path) -> dict[str, Any]:
    """One streaming pass: SHA-256, copy to `dest`, head/tail for sniffing; detects change during read."""
    before = os.stat(src)
    h = hashlib.sha256()
    head, tail, total = b"", b"", 0
    try:
        with open(src, "rb") as f, open(dest, "wb") as out:
            while True:
                chunk = f.read(CHUNK)
                if _after_chunk is not None:
                    _after_chunk(src)
                if not chunk:
                    break
                if not head:
                    head = chunk[:65536]
                tail = (tail + chunk)[-4096:]
                h.update(chunk)
                out.write(chunk)
                total += len(chunk)
                if total > before.st_size:  # growing while read: stop instead of chasing the writer
                    raise _err("E_INPUT_CHANGED", "The file changed while it was being read.",
                               "Plik zmienił się podczas odczytu.", EXIT_PATH, name=src.name)
            out.flush()
            os.fsync(out.fileno())
    except OSError as e:
        raise _err("IO_WRITE_FAILED", "Reading or staging failed; nothing was published.",
                   "Odczyt lub staging nie powiódł się; nic nie opublikowano.", EXIT_IO, errno=str(e.errno)) from e
    after = os.stat(src)
    if total != before.st_size or (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
        raise _err("E_INPUT_CHANGED", "The file changed while it was being read.",
                   "Plik zmienił się podczas odczytu.", EXIT_PATH, name=src.name)
    return {"sha256": h.hexdigest(), "size": total, "mtime_ns": before.st_mtime_ns, "head": head, "tail": tail}


def sniff(head: bytes, tail: bytes, name: str, staged: Path) -> str:
    """MIME from content signature; raises for encrypted inputs."""
    if head.startswith(b"%PDF-"):
        if b"/Encrypt" in head or b"/Encrypt" in tail:
            raise _encrypted(name)
        return "application/pdf"
    if head.startswith(b"PK\x03\x04"):
        if len(head) > 7 and head[6] & 1:
            raise _encrypted(name)
        try:
            with zipfile.ZipFile(staged) as z:
                names = set(z.namelist())
        except zipfile.BadZipFile:
            return "application/octet-stream"
        if "[Content_Types].xml" in names and "word/document.xml" in names:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/zip"
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        if OLE_ENCRYPTED in head or OLE_ENCRYPTED in tail:
            raise _encrypted(name)
        return "application/x-ole-storage"
    if b"\x00" in head:
        return "application/octet-stream"
    try:
        text = head.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "application/octet-stream"
    if _EML_RE.match(head.lstrip(b"\xef\xbb\xbf")):
        return "message/rfc822"
    if name.lower().endswith(".csv"):
        for d in (",", ";", "\t"):
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=d))
            if len(head) >= 65536:
                rows = rows[:-1]  # the last record may be cut by the sniff window
            if len(rows) >= 2 and len({len(r) for r in rows}) == 1 and len(rows[0]) > 1:
                return "text/csv"
    return "text/plain"


def _encrypted(name: str) -> LaError:
    return _err("E_INPUT_ENCRYPTED", "Encrypted input is not supported; supply a decrypted copy.",
                "Zaszyfrowane pliki nie są obsługiwane; podaj kopię odszyfrowaną.", EXIT_USAGE, name=name)


# --- freeze -------------------------------------------------------------------

def _doc_filename(doc_id: str) -> str:
    return doc_id.replace(":", "_") + ".bin"


def freeze(case_dir: Path | str, case_id: str, paths: list[str], *, batch_size: int = 10, resume: bool = False,
           budget_s: float = DEFAULT_STEP_BUDGET_S, cancel: threading.Event | None = None,
           max_files: int | None = None, max_file_bytes: int | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    inputs = validate_inputs(paths, max_files, max_file_bytes)
    total = sum(i["size"] for i in inputs)
    free = shutil.disk_usage(root if root.exists() else root.parent).free
    if free < 2 * total:  # staging copy plus published copy
        raise _err("E_DISK_LOW", "Not enough free disk space for the frozen copies.",
                   "Za mało wolnego miejsca na dysku na zamrożone kopie.", EXIT_IO)
    key = sha256_obj([os.path.normcase(i["path"]) for i in inputs])[:16]
    step_key = f"ingest:{key}"
    ckpt_key = f"{step_key}/b{batch_size}"
    staging = safe_path(root, f".staging/{key}")
    staging.mkdir(parents=True, exist_ok=True)
    repo = Repository(root / "case.db", case_id)
    started = time.monotonic()
    records: list[dict[str, Any]] = []
    try:
        if resume and any(s["id"] == step_key for s in repo.list_steps()):
            docs = sorted([b for b, _ in repo.frozen_bodies("documents")], key=lambda d: d["id"])
            mf = root / "manifest.json"
            if mf.exists() and json.loads(mf.read_text(encoding="utf-8")).get("corpus_hash") == sha256_obj(docs):
                shutil.rmtree(staging, ignore_errors=True)
                return {"ok": True, "corpus_hash": sha256_obj(docs), "documents": len(docs), "added": 0,
                        "already_complete": True}
        for n, start in enumerate(range(0, len(inputs), batch_size)):
            batch = inputs[start:start + batch_size]
            if cancel is not None and cancel.is_set():
                raise Interrupted("CANCELLED", "Cancelled; nothing was published.", "Anulowano; nic nie opublikowano.",
                                  EXIT_INTERRUPTED, {"step_id": step_key})
            if time.monotonic() - started > budget_s:
                raise Interrupted("STEP_BUDGET_EXCEEDED", "Step budget exceeded; resume with --resume.",
                                  "Przekroczono budżet kroku; wznów z --resume.", EXIT_INTERRUPTED,
                                  {"step_id": step_key})
            rec = repo.load(ckpt_key, n) if resume else None
            if rec is not None:
                out = _reuse(rec, batch, staging)
            else:
                out = []
                for i, item in enumerate(batch):
                    dest = staging / f"{start + i:06d}.part"
                    info = hash_and_stage(Path(item["path"]), dest)
                    mime = sniff(info.pop("head"), info.pop("tail"), item["name"], dest)
                    out.append({**info, "mime": mime, "origin": item["name"], "staged": dest.name,
                                "path_key": os.path.normcase(item["path"])})
                repo.save(ckpt_key, n, {"sigs": [[b["size"], b["mtime_ns"]] for b in batch], "output": out})
            records.extend(out)
        result = _publish(repo, root, case_id, step_key, records)
    finally:
        repo.close()
    shutil.rmtree(staging, ignore_errors=True)
    return result


def _reuse(rec: dict[str, Any], batch: list[dict[str, Any]], staging: Path) -> list[dict[str, Any]]:
    """Reuse a completed batch only if every input is unchanged since it was hashed."""
    for item, sig, out in zip(batch, rec["sigs"], rec["output"]):
        st = os.stat(item["path"])
        staged = staging / out["staged"]
        if [st.st_size, st.st_mtime_ns] != sig or not staged.exists() or staged.stat().st_size != out["size"]:
            raise _err("E_INPUT_CHANGED", "An input changed since it was hashed; resume refused. Re-run without "
                       "--resume.", "Plik zmienił się od czasu haszowania; wznowienie odrzucone. Uruchom bez --resume.",
                       EXIT_PATH, name=item["name"])
    return rec["output"]


def _publish(repo: Repository, root: Path, case_id: str, step_key: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    # The same source path may be frozen only once; a changed file is refused, not re-registered.
    seen = {b["id"]: b for b, _ in repo.frozen_bodies("value_records") if b["id"].startswith("srcpath:")}
    fresh, markers = [], []
    for r in records:
        vid = "srcpath:" + sha256_hex(r["path_key"].encode("utf-8"))[:32]
        prev = seen.get(vid)
        if prev is None:
            fresh.append(r)
            markers.append({"id": vid, "sha256": r["sha256"]})
        elif prev["sha256"] != r["sha256"]:
            raise _err("E_INPUT_CHANGED", "This file was frozen earlier and has changed since; refused.",
                       "Ten plik zamrożono wcześniej i zmienił się; odrzucono.", EXIT_PATH, name=r["origin"])
    records = fresh
    if not records:
        docs = sorted([b for b, _ in repo.frozen_bodies("documents")], key=lambda d: d["id"])
        h = sha256_obj(docs)
        mf = root / "manifest.json"
        if not (mf.exists() and json.loads(mf.read_text(encoding="utf-8")).get("corpus_hash") == h):
            _finish(repo, root, docs, h)  # recovery after a crash between documents and manifest
        return {"ok": True, "corpus_hash": h, "documents": len(docs), "added": 0}
    existing = [b for b, step in repo.frozen_bodies("documents") if step != step_key]
    counts: dict[str, int] = {}
    for b in existing:
        counts[b["sha256"][:16]] = counts.get(b["sha256"][:16], 0) + 1
    new_docs = []
    for r in sorted(records, key=lambda r: (r["sha256"], r["origin"], r["path_key"])):
        pre = r["sha256"][:16]
        counts[pre] = counts.get(pre, 0) + 1
        new_docs.append(({"case_id": case_id, "id": f"doc:{pre}-{counts[pre]}", "sha256": r["sha256"], "kind": "original",
                          "mime": r["mime"], "size_bytes": r["size"], "origin": r["origin"]}, r["staged"]))
    corpus = root / "corpus"
    corpus.mkdir(exist_ok=True)
    for doc, staged in new_docs:  # idempotent publication of copies (staging kept until success); manifest last
        src = root / ".staging" / step_key.split(":")[1] / staged
        dst = corpus / _doc_filename(doc["id"])
        tmp = dst.with_suffix(".tmp")
        try:
            shutil.copyfile(src, tmp)
            os.replace(tmp, dst)
        except OSError as e:
            raise _err("IO_WRITE_FAILED", "Publishing the frozen copy failed; no manifest was written.",
                       "Publikacja zamrożonej kopii nie powiodła się; nie zapisano manifestu.", EXIT_IO,
                       errno=str(e.errno)) from e
    runs = repo.reader().runs()
    prior = next((s for s in repo.list_steps() if s["id"] == step_key), None)  # resume after a crash
    base = next((r for r in runs if prior and r["id"] == prior["run_id"]), runs[-1])
    repo.add_step(step_key, base["id"], "ingest", "software:la.py")
    repo.add_frozen_many("documents", [d for d, _ in new_docs], step_key)
    repo.add_frozen_many("value_records", markers, step_key)
    manifest_docs = sorted([b for b, _ in repo.frozen_bodies("documents")], key=lambda d: d["id"])
    corpus_hash = sha256_obj(manifest_docs)
    _finish(repo, root, manifest_docs, corpus_hash, base)
    return {"ok": True, "corpus_hash": corpus_hash, "documents": len(manifest_docs), "added": len(new_docs)}


def _finish(repo: Repository, root: Path, docs: list[dict[str, Any]], corpus_hash: str,
            base: dict[str, Any] | None = None) -> None:
    """Record the Run for this corpus_hash (once) and publish the manifest last."""
    runs = repo.reader().runs()
    parent = base or runs[-1]
    exists = any(r["corpus_hash"] == corpus_hash and (base is None or r["parent_run_id"] == base["id"]) for r in runs)
    if not exists:
        n = len(runs) + 1
        repo.begin_run({"id": f"run:{n:04d}-{corpus_hash[:8]}", "corpus_hash": corpus_hash,
                        "analysis_hash": parent["analysis_hash"], "render_hash": parent["render_hash"],
                        "approved_set_hash": parent["approved_set_hash"], "code_version": parent["code_version"],
                        "model_id": "none", "runtime": parent["runtime"], "parent_run_id": parent["id"]})
    atomic_write(root, "manifest.json", canonical_json({"corpus_hash": corpus_hash, "documents": docs}) + b"\n")


def verify_corpus(case_dir: Path | str, case_id: str) -> list[str]:
    """Ids of documents whose frozen copy is missing or no longer matches its SHA-256."""
    root = Path(case_dir)
    repo = Repository(root / "case.db", case_id)
    bad = []
    try:
        for body, _ in repo.frozen_bodies("documents"):
            f = root / "corpus" / _doc_filename(body["id"])
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != body["sha256"]:
                bad.append(body["id"])
    finally:
        repo.close()
    return sorted(bad)
