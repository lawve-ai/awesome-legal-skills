"""Single stdlib JSON Schema validator for a documented Draft 2020-12 subset.

Supported keywords (anything else is a SchemaError, never silently accepted):
  structure/annotation: $schema, $id, $defs, $ref, $comment, title, description
  any:      type, enum, const, anyOf, oneOf, allOf, not
  object:   properties, required, additionalProperties
  array:    items (single schema), minItems, maxItems, uniqueItems
  string:   minLength, maxLength, pattern (Python `re`, search semantics)
  number:   minimum, maximum
$ref resolves only to local JSON Pointers ("#", "#/...") or to a $id present in
the supplied registry. No network access, no format assertions. Errors carry a
JSON-pointer path and a stable code, never instance text.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .runtime import EXIT_USAGE, LaError

DIALECT = "https://json-schema.org/draft/2020-12/schema"
ANNOTATIONS = frozenset({"$schema", "$id", "$comment", "title", "description"})
KEYWORDS = ANNOTATIONS | frozenset({
    "$defs", "$ref", "type", "enum", "const", "anyOf", "oneOf", "allOf", "not",
    "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
    "uniqueItems", "minLength", "maxLength", "pattern", "minimum", "maximum",
})
TYPES = frozenset({"null", "boolean", "object", "array", "number", "integer", "string"})
MAX_DEPTH = 64


class SchemaError(Exception):
    pass


@dataclass(frozen=True, order=True)
class Error:
    path: str
    code: str


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _type_ok(v: Any, t: str) -> bool:
    if t == "null":
        return v is None
    if t == "boolean":
        return isinstance(v, bool)
    if t == "object":
        return isinstance(v, dict)
    if t == "array":
        return isinstance(v, list)
    if t == "string":
        return isinstance(v, str)
    if t == "number":
        return _is_num(v)
    return _is_num(v) and (isinstance(v, int) or float(v).is_integer())


def json_equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_num(a) and _is_num(b):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


# --- references ---------------------------------------------------------------

def _pointer(root: Any, ptr: str) -> Any:
    cur = root
    if ptr in ("", "/"):
        return cur if ptr == "" else cur
    for raw in unquote(ptr).lstrip("/").split("/"):
        tok = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and tok in cur:
            cur = cur[tok]
        elif isinstance(cur, list) and tok.isdigit() and int(tok) < len(cur):
            cur = cur[int(tok)]
        else:
            raise SchemaError("unresolved $ref")
    return cur


def _resolve(ref: str, root: Any, registry: dict[str, Any]) -> tuple[Any, Any]:
    base, _, frag = ref.partition("#")
    if base == "":
        return _pointer(root, frag), root
    if base in registry:
        doc = registry[base]
        return _pointer(doc, frag), doc
    raise SchemaError("unresolved $ref")


# --- schema checking ----------------------------------------------------------

def check_schema(schema: Any, registry: dict[str, Any] | None = None, _root: Any = None,
                 _depth: int = 0) -> None:
    """Raise SchemaError for unsupported keywords or malformed keyword values."""
    registry = registry or {}
    root = schema if _root is None else _root
    if _depth > MAX_DEPTH:
        raise SchemaError("schema too deep")
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise SchemaError("schema must be object or boolean")
    unknown = sorted(set(schema) - KEYWORDS)
    if unknown:
        raise SchemaError(f"unsupported keyword: {unknown[0]}")
    if "$schema" in schema and schema["$schema"] != DIALECT:
        raise SchemaError("unsupported $schema")
    for k in ("$id", "$comment", "title", "description", "pattern"):
        if k in schema and not isinstance(schema[k], str):
            raise SchemaError(f"{k} must be string")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except re.error as e:
            raise SchemaError("invalid pattern") from e
    if "type" in schema:
        t = schema["type"]
        ts = [t] if isinstance(t, str) else t
        if not isinstance(ts, list) or not ts or any(x not in TYPES for x in ts if isinstance(x, str)) \
                or any(not isinstance(x, str) for x in ts):
            raise SchemaError("invalid type")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise SchemaError("enum must be array")
    if "required" in schema and (not isinstance(schema["required"], list)
                                 or any(not isinstance(x, str) for x in schema["required"])):
        raise SchemaError("required must be array of strings")
    for k in ("minItems", "maxItems", "minLength", "maxLength"):
        if k in schema and (not isinstance(schema[k], int) or isinstance(schema[k], bool) or schema[k] < 0):
            raise SchemaError(f"{k} must be non-negative integer")
    for k in ("minimum", "maximum"):
        if k in schema and not _is_num(schema[k]):
            raise SchemaError(f"{k} must be number")
    if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
        raise SchemaError("uniqueItems must be boolean")
    if "$ref" in schema:
        if not isinstance(schema["$ref"], str):
            raise SchemaError("$ref must be string")
        _resolve(schema["$ref"], root, registry)
    subs: list[Any] = []
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise SchemaError("properties must be object")
        subs += list(schema["properties"].values())
    if "$defs" in schema:
        if not isinstance(schema["$defs"], dict):
            raise SchemaError("$defs must be object")
        subs += list(schema["$defs"].values())
    for k in ("additionalProperties", "items", "not"):
        if k in schema:
            subs.append(schema[k])
    for k in ("anyOf", "oneOf", "allOf"):
        if k in schema:
            if not isinstance(schema[k], list) or not schema[k]:
                raise SchemaError(f"{k} must be non-empty array")
            subs += schema[k]
    for s in subs:
        check_schema(s, registry, root, _depth + 1)


# --- validation ---------------------------------------------------------------

def _validate(inst: Any, schema: Any, root: Any, reg: dict[str, Any], path: str,
              errs: list[Error], depth: int) -> None:
    if depth > MAX_DEPTH:
        errs.append(Error(path, "DEPTH_EXCEEDED"))
        return
    if schema is True:
        return
    if schema is False:
        errs.append(Error(path, "FALSE_SCHEMA"))
        return

    def sub(i: Any, s: Any, p: str, r: Any = None) -> list[Error]:
        out: list[Error] = []
        _validate(i, s, root if r is None else r, reg, p, out, depth + 1)
        return out

    if "$ref" in schema:
        target, new_root = _resolve(schema["$ref"], root, reg)
        errs += sub(inst, target, path, new_root)
    if "type" in schema:
        t = schema["type"]
        ts = [t] if isinstance(t, str) else t
        if not any(_type_ok(inst, x) for x in ts):
            errs.append(Error(path, "TYPE"))
    if "enum" in schema and not any(json_equal(inst, e) for e in schema["enum"]):
        errs.append(Error(path, "ENUM"))
    if "const" in schema and not json_equal(inst, schema["const"]):
        errs.append(Error(path, "CONST"))
    for k, ok in (("allOf", None), ("anyOf", None), ("oneOf", None)):
        if k in schema:
            results = [not sub(inst, s, path) for s in schema[k]]
            if k == "allOf" and not all(results):
                errs.append(Error(path, "ALL_OF"))
            if k == "anyOf" and not any(results):
                errs.append(Error(path, "ANY_OF"))
            if k == "oneOf" and sum(results) != 1:
                errs.append(Error(path, "ONE_OF"))
    if "not" in schema and not sub(inst, schema["not"], path):
        errs.append(Error(path, "NOT"))
    if isinstance(inst, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in inst:
                errs.append(Error(f"{path}/{_esc(name)}", "REQUIRED"))
        for name, val in inst.items():
            p = f"{path}/{_esc(name)}"
            if name in props:
                errs += sub(val, props[name], p)
            elif "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                # Instance keys are data, so errors name the parent, not the key.
                if ap is False:
                    errs.append(Error(path, "ADDITIONAL_PROPERTY"))
                elif ap is not True:
                    errs += sub(val, ap, f"{path}/*")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errs.append(Error(path, "MIN_ITEMS"))
        if "maxItems" in schema and len(inst) > schema["maxItems"]:
            errs.append(Error(path, "MAX_ITEMS"))
        if schema.get("uniqueItems") and any(
                json_equal(inst[i], inst[j]) for i in range(len(inst)) for j in range(i)):
            errs.append(Error(path, "UNIQUE_ITEMS"))
        if "items" in schema:
            for i, v in enumerate(inst):
                errs += sub(v, schema["items"], f"{path}/{i}")
    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errs.append(Error(path, "MIN_LENGTH"))
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append(Error(path, "MAX_LENGTH"))
        if "pattern" in schema and re.search(schema["pattern"], inst) is None:
            errs.append(Error(path, "PATTERN"))
    if _is_num(inst):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append(Error(path, "MINIMUM"))
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append(Error(path, "MAXIMUM"))


def _esc(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def validate(instance: Any, schema: Any, registry: dict[str, Any] | None = None) -> list[Error]:
    reg = registry or {}
    check_schema(schema, reg)  # fail closed on unsupported keywords at run time too
    errs: list[Error] = []
    _validate(instance, schema, schema, reg, "", errs, 0)
    return sorted(set(errs))


# --- project schema registry --------------------------------------------------

SCHEMA_ID_RE = re.compile(r"^la:schema/[a-z_]+/v[0-9]+$")


def load_registry(schema_dir: Path | str) -> dict[str, Any]:
    reg: dict[str, Any] = {}
    for f in sorted(Path(schema_dir).glob("*.schema.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        sid = doc.get("$id", "")
        if not SCHEMA_ID_RE.match(sid):
            raise SchemaError(f"{f.name}: $id must match {SCHEMA_ID_RE.pattern}")
        if sid in reg:
            raise SchemaError(f"{f.name}: duplicate $id")
        reg[sid] = doc
    for doc in reg.values():
        check_schema(doc, reg)
    return reg


def admit(instance: Any, schema_id: str, registry: dict[str, Any]) -> None:
    """Gate: raise before bad data can reach any approved-record writer."""
    errs = validate(instance, registry[schema_id], registry)
    if errs:
        raise LaError("SCHEMA_INVALID", f"Instance invalid against {schema_id}.",
                      f"Instancja niezgodna ze schematem {schema_id}.", EXIT_USAGE,
                      {"schema": schema_id, "first_path": errs[0].path,
                       "first_code": errs[0].code, "count": str(len(errs))})
