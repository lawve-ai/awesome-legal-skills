"""SQLite repository: one database per case, `case_id` in every table, typed IDs,
CHECK-constrained enums, trigger-protected append-only records and a hash chain.
Integrity is *detectable*, not guaranteed against a party with disk access.

`Prediction` is intentionally not stored: its contract is open (T-PREDICTION).
Review `decision` and `evidence_class` are stored verbatim (T-ENUM); `approve`
admits a record only for a decision in `admitting_decisions` (interim default
{"approved"} until T-ENUM supplies the real value set).

Dialect: SQLite. Tables, keys, FKs and CHECKs are plain SQL; `GLOB`, `json_valid`,
`RAISE(ABORT)` triggers and `rowid` ordering are SQLite-specific and need a
PostgreSQL port (tracked in LA-022/LA-030).
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from .integrity import GENESIS, Verdict, canonical_row, merkle_root, row_hash, verify_chain
from .runtime import EXIT_INTEGRITY, EXIT_USAGE, LaError, canonical_json, sha256_obj
from .validation import admit, load_registry

SCHEMA_VERSION = 1
SQL_FILE = Path(__file__).resolve().parents[1] / "schemas" / "sql" / "001_core.sql"
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
# value_records has no schema yet (P1 contract, LA-026) and is not validated.
SCHEMA_OF = {
    "documents": "document", "passages": "passage", "family_memberships": "family_membership",
    "event_time_assessments": "event_time_assessment", "search_records": "search_record",
    "claims": "claim", "observation_sets": "observation_set", "observations": "observation",
    "perspectives": "perspective", "hypotheses": "hypothesis", "assumptions": "assumption",
    "assessments": "assessment", "tests": "test", "reviews": "review",
}
DENIED_READ = frozenset({"proposals", "checkpoints"})
PROV_PREDICATES = ("wasGeneratedBy", "wasDerivedFrom", "wasAttributedTo", "wasInformedBy", "used", "wasInvalidatedBy")


def _enum(col: str, *vals: str) -> str:
    return f"{col} TEXT NOT NULL CHECK ({col} IN ({', '.join(repr(v) for v in vals)}))"


NN = "TEXT NOT NULL CHECK (length({c}) > 0)"
HEX = "TEXT NOT NULL CHECK (length({c}) = 64)"
NOT_ESTABLISHED = "TEXT NOT NULL CHECK ({c} <> 'established' AND length({c}) > 0)"


def _c(tmpl: str, col: str) -> str:
    return f"{col} " + tmpl.format(c=col)


# kind: frozen (immutable, unchained) | approved (chained, in approved set) | review (chained)
# kind: frozen (immutable, unchained) | log (immutable, in the hash chain, not in the approved set)
# | approved (chained, in approved set) | review (chained)
WRITABLE_KINDS = ("frozen", "log")
TABLES: dict[str, dict[str, Any]] = {
    "documents": {"kind": "frozen", "prefix": "doc", "cols": [
        _c(HEX, "sha256"), _enum("kind", "original", "derived"), "derived_from TEXT"],
        "checks": ["CHECK (kind = 'original' OR derived_from IS NOT NULL)"], "fks": []},
    "passages": {"kind": "frozen", "prefix": "psg", "cols": ["document_id TEXT NOT NULL", _c(HEX, "text_sha256")],
                 "checks": [], "fks": [("document_id", "documents")]},
    "family_memberships": {"kind": "log", "prefix": None, "cols": [
        "document_id TEXT NOT NULL", _c(NN, "family_id"), _enum("basis", "bytes", "email_headers", "human")],
        "checks": [], "fks": [("document_id", "documents")]},
    "event_time_assessments": {"kind": "log", "prefix": None, "cols": ["observation_id TEXT NOT NULL"],
                               "checks": [], "fks": []},
    "search_records": {"kind": "log", "prefix": None, "cols": [_c(HEX, "corpus_hash")], "checks": [], "fks": []},
    "value_records": {"kind": "log", "prefix": None, "cols": [], "checks": [], "fks": []},
    "claims": {"kind": "approved", "prefix": "clm", "cols": [
        _enum("speaker_role", "party", "subject", "witness", "third", "system"),
        _c(NOT_ESTABLISHED, "epistemic_status")], "checks": [], "fks": []},
    "observation_sets": {"kind": "approved", "prefix": "set", "cols": [], "checks": [], "fks": []},
    "observations": {"kind": "approved", "prefix": "obs", "cols": [], "checks": [], "fks": []},
    "perspectives": {"kind": "approved", "prefix": "per", "cols": [
        _enum("role", "party", "subject", "organization", "third_party")], "checks": [], "fks": []},
    "hypotheses": {"kind": "approved", "prefix": "hyp", "cols": [
        _enum("kind", "substantive", "process", "data_error", "mixed", "other_unrecognized"),
        _enum("status", "hypothesis")], "checks": [], "fks": []},
    "assumptions": {"kind": "approved", "prefix": "asm", "cols": [
        _enum("kind", "bridge_rule", "background", "model_assumed")], "checks": [], "fks": []},
    "assessments": {"kind": "approved", "prefix": "ass", "cols": [
        "observation_id TEXT NOT NULL", "hypothesis_id TEXT NOT NULL",
        _enum("relation", "supports", "conflicts", "neutral"), "supersedes TEXT"],
        "checks": [], "fks": [("observation_id", "observations"), ("hypothesis_id", "hypotheses"),
                              ("supersedes", "assessments")]},
    "tests": {"kind": "approved", "prefix": "tst", "cols": [], "checks": [], "fks": []},
    "reviews": {"kind": "review", "prefix": "rev", "cols": [
        _c(NN, "item_id"), _c(NN, "decision"), _c(NN, "reviewer"), _c(NN, "evidence_class")],
        "checks": [], "fks": []},
}
CHAINED = {t: [c.split()[0] for c in s["cols"]] for t, s in TABLES.items() if s["kind"] != "frozen"}
APPROVED = [t for t, s in TABLES.items() if s["kind"] == "approved"]
PROMOTED = {t: [c.split()[0] for c in s["cols"]] for t, s in TABLES.items()}


def _protect(t: str, pk: tuple[str, ...], unique: tuple[str, ...] = ()) -> str:
    def same(cols: tuple[str, ...]) -> str:
        return "EXISTS (SELECT 1 FROM {} WHERE {})".format(t, " AND ".join(f"{c} = NEW.{c}" for c in cols))
    cond = " OR ".join([same(pk), *([same(unique)] if unique else [])])
    ins = (f"CREATE TRIGGER {t}_no_replace BEFORE INSERT ON {t} WHEN {cond}"
           " BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;\n")  # blocks INSERT OR REPLACE on any key
    return ins + "".join(
        f"CREATE TRIGGER {t}_no_{op.lower()} BEFORE {op} ON {t} "
        f"BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;\n" for op in ("UPDATE", "DELETE"))


PROTECTED_PK: dict[str, tuple[str, ...]] = {
    "meta": ("case_id",), "runs": ("case_id", "id"), "steps": ("case_id", "id"),
    **{t: ("case_id", "id") for t in TABLES}, "prov_edges": ("case_id", "id"),
    "proposals": ("case_id", "id"), "chain": ("case_id", "seq"),
    "run_heads": ("case_id", "run_id", "seq"),
}
PROTECTED_UNIQUE = {"chain": ("case_id", "table_name", "row_id")}


def render_ddl() -> str:
    out = [
        "-- Generated from legal_abduction/repository.py TABLES; keep in sync (tested).",
        "-- SQLite dialect (GLOB, json_valid, RAISE triggers); PostgreSQL port: LA-022/LA-030.",
        "CREATE TABLE meta (case_id TEXT NOT NULL PRIMARY KEY, schema_version INTEGER NOT NULL);",
        "CREATE TABLE runs (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (id GLOB 'run:?*'),"
        " corpus_hash TEXT NOT NULL, analysis_hash TEXT NOT NULL, render_hash TEXT NOT NULL,"
        " approved_set_hash TEXT NOT NULL, code_version TEXT NOT NULL, model_id TEXT NOT NULL,"
        " runtime TEXT NOT NULL, parent_run_id TEXT, PRIMARY KEY (case_id, id),"
        " FOREIGN KEY (case_id, parent_run_id) REFERENCES runs (case_id, id));",
        "CREATE TABLE steps (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (length(id) > 0),"
        " run_id TEXT NOT NULL, name TEXT NOT NULL CHECK (length(name) > 0),"
        " agent TEXT NOT NULL CHECK (agent GLOB 'software:?*' OR agent GLOB 'model:?*'"
        " OR agent GLOB 'human:?*' OR agent = 'none'), PRIMARY KEY (case_id, id),"
        " FOREIGN KEY (case_id, run_id) REFERENCES runs (case_id, id));",
    ]
    for t, s in TABLES.items():
        idck = "length(id) BETWEEN 1 AND 140" + (f" AND id GLOB '{s['prefix']}:?*'" if s["prefix"] else "")
        lines = ["case_id TEXT NOT NULL", f"id TEXT NOT NULL CHECK ({idck})",
                 "body_json TEXT NOT NULL CHECK (json_valid(body_json))", *s["cols"],
                 "created_step_id TEXT NOT NULL", "PRIMARY KEY (case_id, id)",
                 "FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)"]
        lines += [f"FOREIGN KEY (case_id, {c}) REFERENCES {r} (case_id, id)" for c, r in s["fks"]]
        lines += s["checks"]
        out.append(f"CREATE TABLE {t} (\n  " + ",\n  ".join(lines) + "\n);")
    preds = ", ".join(repr(p) for p in PROV_PREDICATES)
    out += [
        "CREATE TABLE prov_edges (case_id TEXT NOT NULL, id TEXT NOT NULL, subject_id TEXT NOT NULL"
        " CHECK (subject_id GLOB '?*:?*'), predicate TEXT NOT NULL CHECK (predicate IN (" + preds + ")),"
        " object_id TEXT NOT NULL CHECK (object_id GLOB '?*:?*'), step_id TEXT NOT NULL,"
        " PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, step_id) REFERENCES steps (case_id, id));",
        "CREATE TABLE proposals (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (length(id) > 0),"
        " task_type TEXT NOT NULL CHECK (length(task_type) > 0), cache_key TEXT NOT NULL,"
        " payload_json TEXT NOT NULL CHECK (json_valid(payload_json)), created_step_id TEXT NOT NULL,"
        " PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id));",
        "CREATE TABLE chain (case_id TEXT NOT NULL, seq INTEGER NOT NULL CHECK (seq >= 1),"
        " table_name TEXT NOT NULL, row_id TEXT NOT NULL, row_hash TEXT NOT NULL CHECK (length(row_hash) = 64),"
        " prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64), PRIMARY KEY (case_id, seq),"
        " UNIQUE (case_id, table_name, row_id));",
        "CREATE TABLE run_heads (case_id TEXT NOT NULL, run_id TEXT NOT NULL, seq INTEGER NOT NULL CHECK (seq >= 0),"
        " chain_head TEXT NOT NULL CHECK (length(chain_head) = 64), PRIMARY KEY (case_id, run_id, seq),"
        " FOREIGN KEY (case_id, run_id) REFERENCES runs (case_id, id));",
        "CREATE TABLE checkpoints (case_id TEXT NOT NULL, step_id TEXT NOT NULL, batch_no INTEGER NOT NULL,"
        " record_json TEXT NOT NULL CHECK (json_valid(record_json)), PRIMARY KEY (case_id, step_id, batch_no));",
        "CREATE VIEW current_assessments AS SELECT a.* FROM assessments a WHERE NOT EXISTS"
        " (SELECT 1 FROM assessments b WHERE b.case_id = a.case_id AND b.supersedes = a.id);",
        "CREATE VIEW proposal_state AS SELECT p.case_id, p.id, COALESCE((SELECT r.decision FROM reviews r"
        " WHERE r.case_id = p.case_id AND r.item_id = p.id ORDER BY r.rowid DESC LIMIT 1),"
        " CASE WHEN n.k = 0 THEN 'pending' WHEN n.k >= COALESCE(json_array_length(json_extract(p.payload_json,"
        " '$.items')), 0) THEN 'reviewed' ELSE 'partially_reviewed' END) AS state FROM proposals p"
        " JOIN (SELECT p2.case_id AS cid, p2.id AS pid, (SELECT count(DISTINCT r2.item_id) FROM reviews r2"
        " WHERE r2.case_id = p2.case_id AND substr(r2.item_id, 1, length(p2.id) + 1) = p2.id || '#') AS k"
        " FROM proposals p2) n ON n.cid = p.case_id AND n.pid = p.id;",
        "CREATE VIEW runs_current AS SELECT r.*, (SELECT h.chain_head FROM run_heads h WHERE h.case_id = r.case_id"
        " AND h.run_id = r.id ORDER BY h.rowid DESC LIMIT 1) AS chain_head FROM runs r;",
    ]
    out += [_protect(t, pk, PROTECTED_UNIQUE.get(t, ())).rstrip("\n") for t, pk in PROTECTED_PK.items()]
    return "\n".join(out) + "\n"


def _connect(path: str, *, readonly: bool) -> sqlite3.Connection:
    if readonly:
        conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _deny_proposals(action: int, arg1: Any, *_: Any) -> int:
    return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and arg1 in DENIED_READ else sqlite3.SQLITE_OK


class ReadRepository:
    """Read-only interface for comparison/report code; the authorizer denies reads of proposals."""

    def __init__(self, path: str | Path, case_id: str):
        self.case_id = case_id
        self.conn = _connect(str(path), readonly=True)
        self.conn.set_authorizer(_deny_proposals)

    def close(self) -> None:
        self.conn.close()

    def current_assessments(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT body_json FROM current_assessments WHERE case_id = ? ORDER BY id",
                                 (self.case_id,))
        return [json.loads(r[0]) for r in rows]

    def approved_rows(self, table: str) -> list[dict[str, Any]]:
        if table not in APPROVED:
            raise LaError("E_UNKNOWN_TABLE", "Table is not an approved-set table.",
                          "Tabela nie należy do zbioru zatwierdzonego.", EXIT_USAGE)
        rows = self.conn.execute(
            f"SELECT body_json FROM {table} t WHERE case_id = ? AND NOT EXISTS "  # noqa: S608 whitelisted
            + (f"(SELECT 1 FROM {table} b WHERE b.case_id = t.case_id AND b.supersedes = t.id)"
               if "supersedes" in PROMOTED[table] else "(SELECT 1 WHERE 0)") + " ORDER BY id",
            (self.case_id,))
        return [json.loads(r[0]) for r in rows]

    def frozen_rows(self, table: str) -> list[dict[str, Any]]:
        """Bodies of an immutable (frozen or log) table; the authorizer still denies proposals."""
        if TABLES.get(table, {}).get("kind") not in ("frozen", "log"):
            raise LaError("E_UNKNOWN_TABLE", "Not a frozen-record table.", "To nie tabela rekordów zamrożonych.",
                          EXIT_USAGE)
        rows = self.conn.execute(f"SELECT body_json FROM {table} WHERE case_id = ? ORDER BY id",  # noqa: S608 whitelisted
                                 (self.case_id,))
        return [json.loads(r[0]) for r in rows]

    def review_rows(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT body_json FROM reviews WHERE case_id = ? ORDER BY rowid", (self.case_id,))
        return [json.loads(r[0]) for r in rows]

    def superseded_ids(self, table: str) -> set[str]:
        """Ids of rows of `table` that a newer row supersedes (history, not current)."""
        if table not in APPROVED or "supersedes" not in PROMOTED[table]:
            raise LaError("E_UNKNOWN_TABLE", "Table has no supersedes chain.", "Tabela nie ma łańcucha supersedes.",
                          EXIT_USAGE)
        rows = self.conn.execute(f"SELECT supersedes FROM {table} WHERE case_id = ? AND supersedes IS NOT NULL",  # noqa: S608
                                 (self.case_id,))
        return {r[0] for r in rows}

    def prov_edges(self, predicate: str | None = None) -> list[tuple[str, str, str]]:
        sql = "SELECT subject_id, predicate, object_id FROM prov_edges WHERE case_id = ?"
        args: list[Any] = [self.case_id]
        if predicate is not None:
            sql += " AND predicate = ?"
            args.append(predicate)
        return [(a, b, c) for a, b, c in self.conn.execute(sql + " ORDER BY id", args)]

    def runs(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM runs_current WHERE case_id = ? ORDER BY id", (self.case_id,))
        names = [c[0] for c in cur.description]
        return [dict(zip(names, r)) for r in cur]

    def chain_head(self) -> str:
        r = self.conn.execute("SELECT row_hash FROM chain WHERE case_id = ? ORDER BY seq DESC LIMIT 1",
                              (self.case_id,)).fetchone()
        return r[0] if r else GENESIS

    def approved_set_hash(self) -> str:
        hashes: list[str] = []
        for t in APPROVED:
            sup = (f"AND NOT EXISTS (SELECT 1 FROM {t} b WHERE b.case_id = t.case_id AND b.supersedes = t.id)"
                   if "supersedes" in PROMOTED[t] else "")
            hashes += [r[0] for r in self.conn.execute(
                f"SELECT c.row_hash FROM {t} t JOIN chain c ON c.case_id = t.case_id AND "  # noqa: S608
                f"c.table_name = '{t}' AND c.row_id = t.id WHERE t.case_id = ? {sup}", (self.case_id,))]
        return merkle_root(hashes)

    def verify(self) -> Verdict:
        return verify_chain(self.conn, self.case_id, CHAINED)

    def assert_chain_ok(self) -> None:
        v = self.verify()
        if not v.ok:
            raise LaError("E_CHAIN_BROKEN", "Hash chain verification failed.",
                          "Weryfikacja łańcucha haszy nie powiodła się.", EXIT_INTEGRITY,
                          {"first_broken_id": v.first_broken_id or "", "reason": v.reason or ""})


class Repository:
    """Write interface (ingest, proposals, review transactions, checkpoints)."""

    def __init__(self, path: str | Path, case_id: str,
                 admitting_decisions: frozenset[str] = frozenset({"approved"})):
        self.case_id = case_id
        self.path = str(path)
        self.admitting_decisions = admitting_decisions
        self.registry = load_registry(SCHEMA_DIR)
        self.conn = _connect(self.path, readonly=False)
        if self.conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'meta'").fetchone() is None:
            self.conn.executescript(SQL_FILE.read_text(encoding="utf-8"))
        self._once("meta", ["case_id", "schema_version"], [case_id, SCHEMA_VERSION], ["case_id"])
        self._readers: list[ReadRepository] = []
        self._depth = 0

    def _once(self, table: str, cols: list[str], vals: list[Any], pk: list[str]) -> None:
        """Insert unless the key exists; an existing row with different content is a conflict."""
        where = " AND ".join(f"{c} = ?" for c in pk)
        keyvals = [vals[cols.index(c)] for c in pk]
        cur = self.conn.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) SELECT {', '.join('?' * len(cols))} "  # noqa: S608
            f"WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE {where})", [*vals, *keyvals])
        if cur.rowcount == 0:
            row = self.conn.execute(f"SELECT {', '.join(cols)} FROM {table} WHERE {where}", keyvals).fetchone()  # noqa: S608
            if tuple(row) != tuple(vals):
                raise LaError("E_CONFLICT", "Row exists with different content.",
                              "Wiersz istnieje z inną treścią.", EXIT_USAGE, {"table": table})

    def proposal_ids_for_cache_key(self, cache_key: str) -> list[tuple[str, str]]:
        """(proposal id, derived state) for this case only; the cache never crosses cases."""
        rows = self.conn.execute(
            "SELECT p.id, s.state FROM proposals p JOIN proposal_state s ON s.case_id = p.case_id AND s.id = p.id"
            " WHERE p.case_id = ? AND p.cache_key = ? ORDER BY p.id", (self.case_id, cache_key))
        return [(r[0], r[1]) for r in rows]

    def list_steps(self) -> list[dict[str, str]]:
        rows = self.conn.execute("SELECT id, run_id, name, agent FROM steps WHERE case_id = ? ORDER BY rowid",
                                 (self.case_id,))
        return [dict(zip(("id", "run_id", "name", "agent"), r)) for r in rows]

    def review_count(self) -> int:
        return self.conn.execute("SELECT count(*) FROM reviews WHERE case_id = ?", (self.case_id,)).fetchone()[0]

    def proposal_state(self) -> dict[str, str]:
        """Review-side view: state derived from reviews, never stored on the proposal."""
        return dict(self.conn.execute("SELECT id, state FROM proposal_state WHERE case_id = ? ORDER BY id",
                                      (self.case_id,)))

    def close(self) -> None:
        for r in self._readers:
            r.close()
        self.conn.close()

    def reader(self) -> ReadRepository:
        r = ReadRepository(self.path, self.case_id)
        self._readers.append(r)
        return r

    @contextlib.contextmanager
    def _tx(self) -> Iterator[None]:
        if self._depth > 0:  # join the outer transaction
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        self.conn.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield
        except sqlite3.IntegrityError as e:
            self._depth = 0
            self.conn.execute("ROLLBACK")
            raise LaError("E_CONSTRAINT", "A database constraint rejected the write.",
                          "Ograniczenie bazy danych odrzuciło zapis.", EXIT_USAGE,
                          {"detail": str(e)[:200]}) from e
        except BaseException:
            self._depth = 0
            self.conn.execute("ROLLBACK")
            raise
        self._depth = 0
        self.conn.execute("COMMIT")

    def transaction(self) -> contextlib.AbstractContextManager[None]:
        """All writes inside one all-or-nothing transaction (inner calls join it)."""
        return self._tx()

    def proposals_rows(self) -> list[tuple[str, str, dict[str, Any]]]:
        rows = self.conn.execute("SELECT id, task_type, payload_json FROM proposals WHERE case_id = ? ORDER BY id",
                                 (self.case_id,))
        return [(i, t, json.loads(p)) for i, t, p in rows]

    def review_rows(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT body_json FROM reviews WHERE case_id = ? ORDER BY rowid", (self.case_id,))
        return [json.loads(r[0]) for r in rows]

    # --- structure -------------------------------------------------------------
    def begin_run(self, run: dict[str, Any]) -> None:
        with self._tx():
            self._once("runs", ["case_id", "id", "corpus_hash", "analysis_hash", "render_hash",
                                "approved_set_hash", "code_version", "model_id", "runtime", "parent_run_id"],
                       [self.case_id, run["id"], run["corpus_hash"], run["analysis_hash"], run["render_hash"],
                        run["approved_set_hash"], run["code_version"], run["model_id"], run["runtime"],
                        run.get("parent_run_id")], ["case_id", "id"])

    def add_step(self, step_id: str, run_id: str, name: str, agent: str) -> None:
        step = {"case_id": self.case_id, "id": step_id, "run_id": run_id, "name": name, "agent": agent}
        admit(step, "la:schema/step/v1", self.registry)
        with self._tx():
            self._once("steps", list(step), list(step.values()), ["case_id", "id"])

    def finish_run(self, run_id: str) -> str:
        """Record the current chain head for the run (append-only)."""
        with self._tx():
            r = self.conn.execute("SELECT seq, row_hash FROM chain WHERE case_id = ? ORDER BY seq DESC LIMIT 1",
                                  (self.case_id,)).fetchone()
            seq, head = (r[0], r[1]) if r else (0, GENESIS)
            self._once("run_heads", ["case_id", "run_id", "seq", "chain_head"],
                       [self.case_id, run_id, seq, head], ["case_id", "run_id", "seq"])
        return head

    # --- records ---------------------------------------------------------------
    def _link(self, table: str, row_id: str, body: Any) -> None:
        r = self.conn.execute("SELECT seq, row_hash FROM chain WHERE case_id = ? ORDER BY seq DESC LIMIT 1",
                              (self.case_id,)).fetchone()
        seq, prev = (r[0] + 1, r[1]) if r else (1, GENESIS)
        h = row_hash(canonical_row(table, self.case_id, row_id, body), prev)
        self.conn.execute("INSERT INTO chain (case_id, seq, table_name, row_id, row_hash, prev_hash)"
                          " VALUES (?,?,?,?,?,?)", (self.case_id, seq, table, row_id, h, prev))

    def _put(self, table: str, body: dict[str, Any], step_id: str) -> bool:
        """Insert once; identical repeat is a no-op, different content is a conflict."""
        spec = TABLES[table]
        row_id = body["id"] if "id" in body else sha256_obj(body)[:32]  # id-less records: content-derived
        existing = self.conn.execute(f"SELECT body_json FROM {table} WHERE case_id = ? AND id = ?",  # noqa: S608
                                     (self.case_id, row_id)).fetchone()
        if existing is not None:
            if canonical_json(json.loads(existing[0])) != canonical_json(body):
                raise LaError("E_CONFLICT", "Record id exists with different content.",
                              "Identyfikator istnieje z inną treścią.", EXIT_USAGE, {"id": row_id})
            return False
        sid = SCHEMA_OF.get(table)
        if sid is not None:
            if body.get("case_id") != self.case_id:
                raise LaError("E_CASE_MISMATCH", "Record case_id differs from the repository case.",
                              "case_id rekordu różni się od sprawy repozytorium.", EXIT_USAGE, {"id": row_id})
            admit(body, f"la:schema/{sid}/v1", self.registry)
        if table == "assessments":
            self._check_supersedes(body)
        cols = PROMOTED[table]
        self.conn.execute(
            f"INSERT INTO {table} (case_id, id, body_json, created_step_id{''.join(', ' + c for c in cols)})"  # noqa: S608
            f" VALUES (?,?,?,?{',?' * len(cols)})",
            (self.case_id, row_id, canonical_json(body).decode("utf-8"), step_id, *[body.get(c) for c in cols]))
        if spec["kind"] != "frozen":
            self._link(table, row_id, body)
        return True

    def _check_supersedes(self, body: dict[str, Any]) -> None:
        head = self.conn.execute(
            "SELECT a.id FROM assessments a WHERE a.case_id = ? AND a.observation_id = ? AND a.hypothesis_id = ?"
            " AND NOT EXISTS (SELECT 1 FROM assessments b WHERE b.case_id = a.case_id AND b.supersedes = a.id)",
            (self.case_id, body["observation_id"], body["hypothesis_id"])).fetchone()
        if (head[0] if head else None) != body.get("supersedes"):
            raise LaError("E_SUPERSEDES_REQUIRED", "A new assessment must supersede the current one for the pair.",
                          "Nowa ocena musi zastąpić bieżącą ocenę pary.", EXIT_USAGE, {"id": body["id"]})

    def add_frozen(self, table: str, body: dict[str, Any], step_id: str) -> bool:
        if TABLES.get(table, {}).get("kind") not in WRITABLE_KINDS:
            raise LaError("E_UNKNOWN_TABLE", "Not a frozen-record table.", "To nie tabela rekordów zamrożonych.",
                          EXIT_USAGE)
        with self._tx():
            return self._put(table, body, step_id)

    def add_frozen_many(self, table: str, bodies: list[dict[str, Any]], step_id: str) -> int:
        """All-or-nothing insert of frozen records; returns how many were new."""
        if TABLES.get(table, {}).get("kind") not in WRITABLE_KINDS:
            raise LaError("E_UNKNOWN_TABLE", "Not a frozen-record table.", "To nie tabela rekordów zamrożonych.",
                          EXIT_USAGE)
        with self._tx():
            return sum(self._put(table, b, step_id) for b in bodies)

    def add_prov_edges(self, edges: list[tuple[str, str, str]], step_id: str) -> None:
        with self._tx():
            for subject, predicate, obj in edges:
                self._edge(subject, predicate, obj, step_id)

    def frozen_bodies(self, table: str) -> list[tuple[dict[str, Any], str]]:
        if TABLES.get(table, {}).get("kind") not in WRITABLE_KINDS:
            raise LaError("E_UNKNOWN_TABLE", "Not a frozen-record table.", "To nie tabela rekordów zamrożonych.",
                          EXIT_USAGE)
        rows = self.conn.execute(f"SELECT body_json, created_step_id FROM {table} WHERE case_id = ? ORDER BY id",  # noqa: S608
                                 (self.case_id,))
        return [(json.loads(b), s) for b, s in rows]

    def add_proposal(self, proposal: dict[str, Any], step_id: str) -> None:
        admit({**proposal, "case_id": self.case_id, "created_step_id": step_id},
              "la:schema/proposal/v1", self.registry)
        with self._tx():
            self._once("proposals", ["case_id", "id", "task_type", "cache_key", "payload_json", "created_step_id"],
                       [self.case_id, proposal["id"], proposal["task_type"], proposal["cache_key"],
                        canonical_json(proposal["payload_json"]).decode("utf-8"), step_id], ["case_id", "id"])

    def _edge(self, subject: str, predicate: str, obj: str, step_id: str) -> None:
        eid = f"{subject}|{predicate}|{obj}"
        self._once("prov_edges", ["case_id", "id", "subject_id", "predicate", "object_id", "step_id"],
                   [self.case_id, eid, subject, predicate, obj, step_id], ["case_id", "id"])

    def _admits(self, review: dict[str, Any]) -> bool:
        d = review.get("decision")
        return isinstance(d, str) and d in self.admitting_decisions

    def record_review(self, review: dict[str, Any], step_id: str) -> bool:
        """Store a review that admits nothing (e.g. rejection)."""
        if self._admits(review):
            raise LaError("E_DECISION_ADMITTING", "Admitting decisions must go through approve().",
                          "Decyzje dopuszczające muszą przejść przez approve().", EXIT_USAGE)
        with self._tx():
            if self.conn.execute("SELECT 1 FROM proposals WHERE case_id = ? AND id = ?",
                                 (self.case_id, str(review.get("item_id", "")).split("#", 1)[0])).fetchone() is None:
                raise LaError("E_NO_PROPOSAL", "Unknown proposal.", "Nieznana propozycja.", EXIT_USAGE)
            return self._put("reviews", review, step_id)

    def approve(self, proposal_id: str, review: dict[str, Any], table: str, record: dict[str, Any],
                step_id: str) -> bool:
        """One transaction: Review + approved record + provenance + chain links."""
        if table not in APPROVED:
            raise LaError("E_UNKNOWN_TABLE", "Not an approved-set table.", "To nie tabela zbioru zatwierdzonego.",
                          EXIT_USAGE)
        item = review.get("item_id")
        if item != proposal_id and not (isinstance(item, str) and item.startswith(proposal_id + "#")):
            raise LaError("E_REVIEW_ITEM", "Review does not refer to the proposal.",
                          "Recenzja nie dotyczy tej propozycji.", EXIT_USAGE)
        if not self._admits(review):
            raise LaError("E_DECISION_NOT_ADMITTING", "Review decision does not admit a record.",
                          "Decyzja recenzji nie dopuszcza rekordu.", EXIT_USAGE)
        with self._tx():
            if self.conn.execute("SELECT 1 FROM proposals WHERE case_id = ? AND id = ?",
                                 (self.case_id, proposal_id)).fetchone() is None:
                raise LaError("E_NO_PROPOSAL", "Unknown proposal.", "Nieznana propozycja.", EXIT_USAGE)
            new_review = self._put("reviews", review, step_id)
            new_record = self._put(table, record, step_id)
            self._edge(record["id"], "wasGeneratedBy", f"step:{step_id}", step_id)
            self._edge(record["id"], "wasAttributedTo", f"human:{review['reviewer']}", step_id)
            self._edge(record["id"], "wasDerivedFrom", f"proposal:{proposal_id}", step_id)
            return new_review or new_record

    # --- CheckpointStore protocol (LA-002) -------------------------------------
    def load(self, step_id: str, batch_no: int) -> dict[str, Any] | None:
        r = self.conn.execute("SELECT record_json FROM checkpoints WHERE case_id = ? AND step_id = ? AND batch_no = ?",
                              (self.case_id, step_id, batch_no)).fetchone()
        return json.loads(r[0]) if r else None

    def save(self, step_id: str, batch_no: int, record: dict[str, Any]) -> None:
        self.conn.execute("INSERT OR REPLACE INTO checkpoints (case_id, step_id, batch_no, record_json)"
                          " VALUES (?,?,?,?)", (self.case_id, step_id, batch_no, canonical_json(record).decode("utf-8")))
