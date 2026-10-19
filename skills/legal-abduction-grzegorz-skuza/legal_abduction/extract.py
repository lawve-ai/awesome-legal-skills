"""Text extraction (R4): native DOCX/EML/TXT/CSV, optional PDF via detected tools.

Reads only the frozen copies under `corpus/`, never the originals. Passage
locator v1 (T-LOCATOR): {"locator_version": 1, "paragraph"|"message"|"row": n
(1-based), "page_index": n (0-based), "printed_page": str}. Claim/quote offsets
count Unicode code points into `Passage.text`, exactly as extracted.

A document that cannot be read (no PDF tool, corrupt or over-limit archive)
gets a placeholder Passage flagged `needs_text` and an entry in `limitations`;
it is never an empty, correctly analysed document. OCR text is always flagged
`ocr_unverified`; OCR itself is not integrated here (no OCR backend is bundled).
"""
from __future__ import annotations

import csv
import email
import email.policy
import hashlib
import html.parser
import io
import re
import shutil
import statistics
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET

from .ingest import _doc_filename, _finish
from .repository import Repository
from .runtime import (DEFAULT_STEP_BUDGET_S, EXIT_INTEGRITY, EXIT_INTERRUPTED, EXIT_USAGE, Interrupted, LaError,
                      atomic_write, canonical_json, run_subprocess, sha256_hex, sha256_obj)

EXTRACTION_VERSION = "native-1"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DEFAULT_LIMITS = {"max_pages": None, "max_chars": 50_000_000, "max_zip_members": 5000,
                  "max_uncompressed_bytes": 100 * 1024 * 1024, "max_zip_ratio": 200}
_ODD_DATE = re.compile(r"\b(?=[\dOolI|./-]*\d)(?=[\dOolI|./-]*[OolI|])[\dOolI|]{1,2}[./-][\dOolI|]{1,2}[./-][\dOolI|]{2,4}\b")


class ExtractionFailed(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# --- native extractors: each returns [(locator_fields, text, flags)] ---------------

def _paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))


def extract_txt(data: bytes, limits: dict[str, Any]) -> list[tuple[dict[str, Any], str, list[str]]]:
    flags: list[str] = []
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("utf-8-sig", errors="replace")
        flags.append("encoding_replaced")
    return [({"paragraph": i}, p.strip("\n"), list(flags)) for i, p in enumerate(_paragraphs(text), 1) if p.strip()]


def extract_csv(data: bytes, limits: dict[str, Any]) -> list[tuple[dict[str, Any], str, list[str]]]:
    flags: list[str] = []
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("utf-8-sig", errors="replace")
        flags.append("encoding_replaced")
    sample = text[:4096]
    delim = max((",", ";", "\t"), key=sample.count)
    out = []
    for i, row in enumerate(csv.reader(io.StringIO(text, newline=""), delimiter=delim), 1):
        if any(c.strip() for c in row):
            out.append(({"row": i}, " | ".join(row), list(flags)))
    return out


class _Strip(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, d: str) -> None:
        self.parts.append(d)


def extract_eml(data: bytes, limits: dict[str, Any]) -> list[tuple[dict[str, Any], str, list[str]]]:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    flags: list[str] = []
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        try:
            body = body_part.get_content()
        except (LookupError, ValueError):
            raw = body_part.get_payload(decode=True) or b""
            body = raw.decode("utf-8", errors="replace")
            flags.append("encoding_replaced")
        if body_part.get_content_type() == "text/html":
            p = _Strip()
            p.feed(body)
            body = "".join(p.parts)
            flags.append("html_converted")
    if any(True for _ in msg.iter_attachments()):
        flags.append("attachment_skipped")
    head = "".join(f"{h}: {msg[h]}\n" for h in ("From", "To", "Cc", "Date", "Subject") if msg[h] is not None)
    return [({"message": 1}, f"{head}\n{body}".rstrip("\n"), sorted(set(flags)))]


def extract_docx(data: bytes, limits: dict[str, Any]) -> list[tuple[dict[str, Any], str, list[str]]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ExtractionFailed("E_EXTRACT_CORRUPT") from e
    with z:
        infos = z.infolist()
        total = sum(i.file_size for i in infos)
        if len(infos) > limits["max_zip_members"] or total > limits["max_uncompressed_bytes"] \
                or total > limits["max_zip_ratio"] * max(len(data), 1):
            raise ExtractionFailed("E_EXTRACT_LIMIT")
        try:
            xml = z.read("word/document.xml")  # in memory only; nothing is written to disk
        except (KeyError, zipfile.BadZipFile, RuntimeError) as e:
            raise ExtractionFailed("E_EXTRACT_CORRUPT") from e
    if b"\x00" in xml or b"<!doctype" in xml.lower() or b"<!entity" in xml.lower():  # also UTF-16 payloads
        raise ExtractionFailed("E_EXTRACT_CORRUPT")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ExtractionFailed("E_EXTRACT_CORRUPT") from e
    out = []
    for i, p in enumerate(root.iter(f"{W}p"), 1):
        parts = []
        for el in p.iter():
            if el.tag == f"{W}t" and el.text:
                parts.append(el.text)
            elif el.tag == f"{W}tab":
                parts.append("\t")
            elif el.tag in (f"{W}br", f"{W}cr"):
                parts.append("\n")
        text = "".join(parts)
        if text.strip():
            out.append(({"paragraph": i}, text, []))
    return out


# --- PDF via detected tools (no installation) ----------------------------------

def _pypdf_pages(path: Path, limits: dict[str, Any]) -> list[dict[str, Any]]:
    from pypdf import PdfReader  # type: ignore[import-not-found]
    r = PdfReader(str(path))
    labels = list(getattr(r, "page_labels", []) or [])
    pages = []
    for i, pg in enumerate(r.pages):
        pages.append({"page_index": i, "printed_page": labels[i] if i < len(labels) and labels[i] != str(i + 1) else None,
                      "text": pg.extract_text() or "", "ocr": False})
    return pages


def _pdftotext_pages(path: Path, limits: dict[str, Any]) -> list[dict[str, Any]]:
    r = run_subprocess(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise ExtractionFailed("E_EXTRACT_TOOL")
    texts = r.stdout.decode("utf-8", errors="replace").split("\f")
    if texts and texts[-1] == "":
        texts.pop()
    return [{"page_index": i, "printed_page": None, "text": t, "ocr": False} for i, t in enumerate(texts)]


def _has_pypdf() -> bool:
    import importlib.util
    return importlib.util.find_spec("pypdf") is not None


# name, availability probe, extractor (replaceable in tests)
PDF_BACKENDS: list[tuple[str, Callable[[], bool], Callable[[Path, dict[str, Any]], list[dict[str, Any]]]]] = [
    ("pypdf", _has_pypdf, _pypdf_pages),
    ("pdftotext", lambda: shutil.which("pdftotext") is not None, _pdftotext_pages),
]


def extract_pdf(path: Path, limits: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    for name, available, run in PDF_BACKENDS:
        if available():
            pages = run(path, limits)
            if limits["max_pages"] is not None and len(pages) > limits["max_pages"]:
                raise ExtractionFailed("E_EXTRACT_LIMIT")
            if not any(p["text"].strip() for p in pages):
                raise ExtractionFailed("E_EXTRACT_NO_TEXT")  # e.g. a scan without a text layer
            return name, pages
    raise ExtractionFailed("E_EXTRACT_NO_TOOL")


# --- quality flags ----------------------------------------------------------------

def page_flags(pages: list[dict[str, Any]]) -> list[list[str]]:
    sizes = [len(p["text"].strip()) for p in pages]
    med = statistics.median(sizes) if len(sizes) >= 3 else 0
    out = []
    for p, n in zip(pages, sizes):
        fl = []
        if n == 0:
            fl.append("empty_page")
        elif med and n < 0.5 * med:
            fl.append("char_drop")
        if _ODD_DATE.search(p["text"]):
            fl.append("odd_date_chars")
        if p.get("ocr"):
            fl.append("ocr_unverified")
        out.append(fl)
    return out


# --- run ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _psg_id(doc_id: str, version: str, n: int) -> str:
    return f"psg:{doc_id.split(':', 1)[1]}.{version}.{n:05d}"


def _passage(case_id: str, doc_id: str, version: str, n: int, loc: dict[str, Any], text: str,
             flags: list[str]) -> dict[str, Any]:
    return {"case_id": case_id, "id": _psg_id(doc_id, version, n), "document_id": doc_id,
            "locator": {"locator_version": 1, **loc}, "text": text, "text_sha256": sha256_hex(text.encode("utf-8")),
            "extraction_version": version, "quality_flags": sorted(set(flags))}


def _placeholder(case_id: str, doc_id: str, version: str, code: str) -> dict[str, Any]:
    return _passage(case_id, doc_id, version, 0, {}, "", ["needs_text", f"extraction_failed:{code}"])


def extract_document(case_id: str, doc: dict[str, Any], path: Path, limits: dict[str, Any]) -> dict[str, Any]:
    """Pure per-document step: {passages, derived (doc, text) | None, limitation | None}."""
    mime, did = doc["mime"], doc["id"]
    if _sha256_file(path) != doc["sha256"]:
        raise LaError("E_CORPUS_TAMPERED", "A frozen copy no longer matches its SHA-256; extraction refused.",
                      "Zamrożona kopia nie zgadza się już z SHA-256; ekstrakcja odrzucona.", EXIT_INTEGRITY,
                      {"document_id": did})
    version, derived = EXTRACTION_VERSION, None
    try:
        if mime == "application/pdf":
            backend, pages = extract_pdf(path, limits)
            version = f"{backend}-1"
            flags = page_flags(pages)
            text_all = "\f".join(p["text"] for p in pages)
            if len(text_all) > limits["max_chars"]:
                raise ExtractionFailed("E_EXTRACT_LIMIT")
            tb = text_all.encode("utf-8")
            dsha = sha256_hex(tb)
            derived_doc = {"case_id": case_id, "id": f"doc:{did.split(':', 1)[1]}.{version}", "sha256": dsha,
                           "kind": "derived", "derived_from": did, "mime": "text/plain", "size_bytes": len(tb),
                           "origin": f"extracted:{backend}"}
            derived = (derived_doc, tb)
            psgs = []
            for p, fl in zip(pages, flags):
                loc = {"page_index": p["page_index"]}
                if p.get("printed_page") is not None:
                    loc["printed_page"] = str(p["printed_page"])
                psgs.append(_passage(case_id, derived_doc["id"], version, p["page_index"], loc, p["text"], fl))
            return {"passages": psgs, "derived": derived, "limitation": None, "version": version}
        data = path.read_bytes()
        fn = {"text/plain": extract_txt, "text/csv": extract_csv, "message/rfc822": extract_eml,
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx}.get(mime)
        if fn is None:
            raise ExtractionFailed("E_EXTRACT_UNSUPPORTED")
        items = fn(data, limits)
        if sum(len(t) for _, t, _ in items) > limits["max_chars"]:
            raise ExtractionFailed("E_EXTRACT_LIMIT")
        if not items:
            raise ExtractionFailed("E_EXTRACT_EMPTY")
        return {"passages": [_passage(case_id, did, version, i, loc, t, fl) for i, (loc, t, fl) in enumerate(items, 1)],
                "derived": None, "limitation": None, "version": version}
    except ExtractionFailed as e:
        return {"passages": [_placeholder(case_id, did, version, e.code)], "derived": None,
                "limitation": {"document_id": did, "code": e.code}, "version": version}


def extract_all(case_dir: Path | str, case_id: str, *, batch_size: int = 10, resume: bool = False,
                budget_s: float = DEFAULT_STEP_BUDGET_S, cancel: threading.Event | None = None,
                limits: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    repo = Repository(root / "case.db", case_id)
    started = time.monotonic()
    try:
        docs = [b for b, _ in repo.frozen_bodies("documents") if b["kind"] == "original"]
        if not docs:
            raise LaError("E_NO_CORPUS", "No frozen documents; run ingest first.", "Brak zamrożonych dokumentów; "
                          "najpierw uruchom ingest.", EXIT_USAGE)
        ckpt = f"extract:{sha256_obj([d['sha256'] + d['id'] for d in docs])[:16]}/b{batch_size}/{EXTRACTION_VERSION}"
        results: list[dict[str, Any]] = []
        for n, start in enumerate(range(0, len(docs), batch_size)):
            batch = docs[start:start + batch_size]
            if cancel is not None and cancel.is_set():
                raise Interrupted("CANCELLED", "Cancelled; nothing was published.", "Anulowano; nic nie opublikowano.",
                                  EXIT_INTERRUPTED, {"step_id": ckpt})
            if time.monotonic() - started > budget_s:
                raise Interrupted("STEP_BUDGET_EXCEEDED", "Step budget exceeded; resume with --resume.",
                                  "Przekroczono budżet kroku; wznów z --resume.", EXIT_INTERRUPTED, {"step_id": ckpt})
            sig = [d["sha256"] for d in batch]
            rec = repo.load(ckpt, n) if resume else None
            if rec is not None and rec["sig"] == sig:
                out = rec["output"]
            else:
                out = []
                for d in batch:
                    r = extract_document(case_id, d, root / "corpus" / _doc_filename(d["id"]), lim)
                    if r["derived"] is not None:
                        r["derived"] = [r["derived"][0], r["derived"][1].decode("utf-8")]
                    out.append(r)
                repo.save(ckpt, n, {"sig": sig, "output": out})
            results.extend(out)
        return _publish(repo, root, case_id, ckpt, results)
    finally:
        repo.close()


def _publish(repo: Repository, root: Path, case_id: str, ckpt: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    run = repo.reader().runs()[-1]
    step_id = f"{ckpt.split('/')[0]}:{run['id']}:{EXTRACTION_VERSION}"  # bound to Run and version: re-runnable in a later Run
    repo.add_step(step_id, run["id"], "extract", "software:la.py")
    derived_docs = [r["derived"][0] for r in results if r["derived"]]
    if derived_docs:  # database first (one transaction); files afterwards are idempotent
        repo.add_frozen_many("documents", derived_docs, step_id)
        repo.add_prov_edges([(d["id"], "wasDerivedFrom", d["derived_from"]) for d in derived_docs], step_id)
        (root / "corpus").mkdir(exist_ok=True)
        for r in results:
            if r["derived"]:
                atomic_write(root, f"corpus/{_doc_filename(r['derived'][0]['id'])}", r["derived"][1].encode("utf-8"))
        # corpus_hash covers originals and derived documents: refresh manifest and Run
        docs_all = sorted([b for b, _ in repo.frozen_bodies("documents")], key=lambda d: d["id"])
        _finish(repo, root, docs_all, sha256_obj(docs_all))
    passages = [p for r in results for p in r["passages"]]
    new = repo.add_frozen_many("passages", passages, step_id)
    limitations = [r["limitation"] for r in results if r["limitation"]]
    review = [{"passage_id": p["id"], "flags": p["quality_flags"]} for p in passages if p["quality_flags"]]
    summary = {"extraction_versions": sorted({r["version"] for r in results}), "passages": len(passages),
               "limitations": limitations, "review": review}
    atomic_write(root, "extraction.json", canonical_json(summary) + b"\n")
    return {"ok": True, "complete": not limitations, "new_passages": new, **summary,
            "needs_text": sum(1 for p in passages if "needs_text" in p["quality_flags"])}
