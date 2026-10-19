"""Stdlib-only, exact-allowlist preview packaging; never packages a case tree."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

PREFIX = "legal-abduction/"
MIN_PYTHON = (3, 12)
MAX_BYTES = 16 * 1024 * 1024
MODULES = """__init__ altcause bundles claims cli compare doctor extract facts families guards
hypotheses ingest integrity matrix observations packets profile proposals report repository
review_budget review review_history revisit runtime search staleness status test_plan uncovered update validation""".split()
SCHEMAS = """assessment assumption claim document event_time_assessment family_membership
hypothesis metrics observation_set observation packet passage perspective profile proposal
review_decision review run search_record status step task_altcause task_claims task_event_time
task_hypotheses task_matrix task_tests test""".split()
FILES = tuple(sorted(
    ["SKILL.md", "README.md", "la.py", "scripts/package_preview.py", "schemas/README.md",
     "schemas/sql/001_core.sql", "references/legal-profile.md",
     "references/workflow.md", "references/lexicons/claim_status.json",
     "references/lexicons/person_evaluation.json", "references/lexicons/en.json",
     "references/lexicons/pl.json", "docs/host-degradation.md",
     "docs/case-bundle-format.md", "docs/distribution.md",
     "docs/evaluation/protocol.md", "docs/evaluation/preregistration.example.json",
     "docs/evaluation/results.example.json", "scripts/evaluate_quality.py",
     "tests/test_document_actions_history.py"]
    + [f"legal_abduction/{name}.py" for name in MODULES]
    + [f"schemas/{name}.schema.json" for name in SCHEMAS]
    + [f"locales/{lang}.json" for lang in ("pl", "en")]
    + [f"docs/{name}.{lang}.md" for lang in ("pl", "en") for name in ("usage", "installation")]
    + [f"docs/ai-act/{lang}.md" for lang in ("pl", "en")]
    + [f"docs/policy/exhibit-use.{lang}.md" for lang in ("pl", "en")]
    + [f"assets/templates/{lang}/{name}" for lang in ("pl", "en")
       for name in ("working.md", "exhibit.md", "strings.json")]
))
GATES = ["Q10", "Q11", "Q12", "REPORT_SOURCE", "LEGAL_VERIFICATION",
         "LA-022", "LA-023", "LA-024", "LA-025"]
SECRET = re.compile(
    rb"-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|"
    rb"\bAKIA[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}\b|"
    rb"\bsk-ant-[A-Za-z0-9_-]{20,}\b")


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_version(files: dict[str, bytes]) -> str:
    tree = ast.parse(files["legal_abduction/__init__.py"].decode("utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__"
                                                for t in node.targets)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            return node.value.value
    raise ValueError("Runtime code version must be a literal string")


def regular(path: Path) -> None:
    """Check every ancestor as well as leaf, including Windows junctions."""
    for p in (path, *path.parents):
        s = p.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Link/reparse path: {p}")
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")


def check_skill(data: bytes) -> None:
    """Validate our deliberately simple YAML subset, not arbitrary host YAML."""
    text = data.decode("utf-8").replace("\r\n", "\n")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.+)", text, re.S)
    if not match:
        raise ValueError("SKILL.md needs frontmatter and a nonempty body")
    fields = {}
    for line in match[1].splitlines():
        key, sep, value = line.partition(": ")
        if not sep or key in fields or key not in {"name", "description", "compatibility"}:
            raise ValueError("Unsupported or duplicate SKILL frontmatter")
        fields[key] = value
    if fields.get("name") != "legal-abduction":
        raise ValueError("Skill name must match parent directory legal-abduction")
    for key, limit in (("description", 1024), ("compatibility", 500)):
        if key == "compatibility" and key not in fields:
            continue  # current Skill Creator keeps compatibility in the body
        value = fields.get(key, "")
        if not 1 <= len(value) <= limit or any(c in value for c in "\n{}[]"):
            raise ValueError(f"Invalid {key}")
    if "Python >=3.12" not in fields.get("compatibility", "") + match[2]:
        raise ValueError("Python minimum must be declared")


def check_payload(files: dict[str, bytes]) -> None:
    if set(files) != set(FILES):
        raise ValueError("Payload differs from exact distribution allowlist")
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError("Preview exceeds size limit")
    for name, data in files.items():
        if SECRET.search(data):
            raise ValueError(f"Possible credential in {name}; manual review required")
        if name.endswith((".py", ".md", ".json", ".sql")):
            data.decode("utf-8")
    check_skill(files["SKILL.md"])
    # Local links are checked against the ZIP payload, not the developer workspace.
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        for link in re.findall(r"\]\(([^)]+)\)", data.decode("utf-8")):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#")[0]
            parts = list(PurePosixPath(name).parent.parts)
            for part in PurePosixPath(target).parts:
                if part == "..":
                    if not parts:
                        raise ValueError(f"Escaping link in {name}: {link}")
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            path = "/".join(parts)
            if path not in files and not any(f.startswith(path.rstrip("/") + "/") for f in files):
                raise ValueError(f"Broken local link in {name}: {link}")


def collect(root: Path) -> dict[str, bytes]:
    files = {}
    for name in FILES:
        p = root / name
        regular(p)
        before = p.stat()
        data = p.read_bytes()
        regular(p)
        after = p.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError(f"File changed while reading: {name}")
        files[name] = data
    check_payload(files)
    return files


def archive(files: dict[str, bytes]) -> bytes:
    check_payload(files)
    hashes = {p: digest(b) for p, b in sorted(files.items())}
    manifest = {"format": "la:preview-bundle/v1", "status": "evaluation-preview",
                "code_version": code_version(files),
                "python_min": "3.12", "license": "unresolved-Q11",
                "release_gates": GATES, "files": hashes, "payload_digest": digest(canonical(hashes))}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as z:
        for name, data in sorted({**files, "BUNDLE-MANIFEST.json": canonical(manifest)}.items()):
            info = zipfile.ZipInfo(PREFIX + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(info, data)
    return output.getvalue()


def verify(data: bytes, *, smoke: bool = False) -> dict:
    if len(data) > MAX_BYTES + 1024 * 1024:
        raise ValueError("Archive too large")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        expected = {PREFIX + p for p in (*FILES, "BUNDLE-MANIFEST.json")}
        if len(infos) != len(expected) or {i.filename for i in infos} != expected:
            raise ValueError("Duplicate, forbidden, missing or unsafe archive entry")
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError("Unpacked archive too large")
        for i in infos:
            mode = i.external_attr >> 16
            if stat.S_IFMT(mode) != stat.S_IFREG or i.flag_bits & 1:
                raise ValueError("Nonregular or encrypted ZIP entry")
        contents = {i.filename[len(PREFIX):]: z.read(i) for i in infos}
    manifest = json.loads(contents.pop("BUNDLE-MANIFEST.json"))
    check_payload(contents)
    hashes = {p: digest(b) for p, b in sorted(contents.items())}
    if manifest != {"format": "la:preview-bundle/v1", "status": "evaluation-preview",
                    "code_version": code_version(contents),
                    "python_min": "3.12", "license": "unresolved-Q11",
                    "release_gates": GATES, "files": hashes,
                    "payload_digest": digest(canonical(hashes))}:
        raise ValueError("Manifest or file hash mismatch")
    result = {"ok": True, "status": "evaluation-preview", "files": len(contents),
              "zip_sha256": digest(data), "payload_digest": manifest["payload_digest"],
              "secret_scan": "known-patterns-only; not a confidentiality guarantee",
              "smoke": "not-run"}
    if smoke:
        with tempfile.TemporaryDirectory(prefix="la-preview-") as temp:
            root = Path(temp) / "legal-abduction"
            for name, content in contents.items():
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
            initial = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
                   "PYTHONHASHSEED": "0"}
            # Do not let an inherited module path select the developer runtime.
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            commands = [
                [sys.executable, "-B", "-X", "utf8", "la.py", "--json", "version"],
                [sys.executable, "-B", "-X", "utf8", "la.py", "--help"],
                [sys.executable, "-B", "-X", "utf8", "-c",
                 "from legal_abduction.validation import load_registry; "
                 "from legal_abduction.report import load_templates,policy_files; "
                 "from pathlib import Path; import legal_abduction; "
                 "assert Path(legal_abduction.__file__).resolve().parent == Path.cwd() / 'legal_abduction'; "
                 "load_registry('schemas'); load_templates('pl'); load_templates('en'); policy_files(); "
                 "print('schemas/templates/policy: OK')"],
            ]
            for cmd in commands:
                run = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True,
                                     encoding="utf-8", timeout=60, shell=False)
                if run.returncode:
                    raise ValueError(f"Extraction smoke failed: {cmd}: {run.stderr}")
            final = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
            if final != initial or any((root / p).read_bytes() != b for p, b in contents.items()):
                raise ValueError("Smoke modified the skill tree")
        result["smoke"] = "3 subprocesses passed; no case data or skill-tree changes"
    return result


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit("Python >=3.12 required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--check", type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        data = args.check.read_bytes() if args.check else archive(collect(args.root))
        result = verify(data, smoke=args.smoke)
        if args.out:
            # Exclusive creation: never overwrite someone else's archive.
            parent = args.out.absolute().parent
            for p in (parent, *parent.parents):
                s = p.lstat()
                if stat.S_ISLNK(s.st_mode) or getattr(s, "st_file_attributes", 0) & 0x400:
                    raise ValueError("Output parent is a link/reparse point")
            with args.out.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            result["artifact"] = str(args.out.absolute())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
