"""Canonical row hashing, hash chain and Merkle root. Pure functions plus a
verifier; detects tampering, does not prevent it for a party with disk access.

row_hash = sha256(canonical_json({table, case_id, id, data}) || prev_hash_hex_ascii)
Only semantic data is hashed; historical fields (created_step_id, rowid) are not.
Merkle: leaf = sha256(0x00||row_hash_bytes), node = sha256(0x01||left||right),
an unpaired node is promoted unchanged, leaves are sorted by row_hash hex,
empty set = sha256("la:merkle:empty:v1") (T-MERKLE-EMPTY).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping

from .runtime import canonical_json, sha256_hex

GENESIS = "0" * 64
EMPTY_ROOT = sha256_hex(b"la:merkle:empty:v1")


def canonical_row(table: str, case_id: str, row_id: str, data: Any) -> bytes:
    return canonical_json({"table": table, "case_id": case_id, "id": row_id, "data": data})


def row_hash(canon: bytes, prev_hash: str) -> str:
    return sha256_hex(canon + prev_hash.encode("ascii"))


def merkle_root(row_hashes: list[str]) -> str:
    if not row_hashes:
        return EMPTY_ROOT
    level = [hashlib.sha256(b"\x00" + bytes.fromhex(h)).digest() for h in sorted(row_hashes)]
    while len(level) > 1:
        nxt = [hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest()
               for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0].hex()


@dataclass(frozen=True)
class Verdict:
    ok: bool
    first_broken_id: str | None = None
    reason: str | None = None


def verify_chain(conn: sqlite3.Connection, case_id: str, tables: Mapping[str, Any]) -> Verdict:
    """`tables` maps whitelisted chained table name -> iterable of promoted columns."""
    prev, expect = GENESIS, 1
    link_hash_at = {0: GENESIS}
    rows = conn.execute("SELECT seq, table_name, row_id, row_hash, prev_hash FROM chain "
                        "WHERE case_id = ? ORDER BY seq", (case_id,)).fetchall()
    for seq, table, rid, h, ph in rows:
        if table not in tables:
            return Verdict(False, rid, "unknown_table")
        if seq != expect or ph != prev:
            return Verdict(False, rid, "link")
        cols = list(tables[table])
        sel = ", ".join(["body_json"] + cols)
        r = conn.execute(f"SELECT {sel} FROM {table} WHERE case_id = ? AND id = ?",  # noqa: S608 whitelisted
                         (case_id, rid)).fetchone()
        if r is None:
            return Verdict(False, rid, "missing_row")
        try:
            body = json.loads(r[0])
        except ValueError:
            return Verdict(False, rid, "body_json")
        if row_hash(canonical_row(table, case_id, rid, body), prev) != h:
            return Verdict(False, rid, "hash")
        for col, val in zip(cols, r[1:]):
            if body.get(col) != val:
                return Verdict(False, rid, "column_mismatch")
        prev, expect = h, expect + 1
        link_hash_at[seq] = h
    for table in tables:
        r = conn.execute(f"SELECT id FROM {table} WHERE case_id = ? AND id NOT IN "  # noqa: S608
                         "(SELECT row_id FROM chain WHERE case_id = ? AND table_name = ?) "
                         "ORDER BY rowid LIMIT 1", (case_id, case_id, table)).fetchone()
        if r:
            return Verdict(False, r[0], "unchained_row")
    for run_id, seq, head in conn.execute(
            "SELECT run_id, seq, chain_head FROM run_heads WHERE case_id = ? ORDER BY rowid", (case_id,)):
        if link_hash_at.get(seq) != head:
            return Verdict(False, run_id, "run_head")
    return Verdict(True)
