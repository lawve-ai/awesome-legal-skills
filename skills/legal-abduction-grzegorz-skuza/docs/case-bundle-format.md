# `.lacase` bundle format (version 1)

Status: implemented in `legal_abduction/bundles.py` (LA-019). Interpretation recorded in `docs/decisions.md`.

## Members (ZIP, fixed timestamps, sorted, deflate level 6)

| Member | Content |
|---|---|
| `manifest.json` | format `lacase`, `format_version` 1, `schema_version`, `code_version`, `case_id`, `approved_set_hash`, `chain_head`, `with_originals`, `documents` (id, sha256, size, kind, file), per-table row counts, `files` (sha256 + size of every other member), `report_hook`, `created_at` (the only ephemeral field) |
| `case.json` | the case profile |
| `db.jsonl` | canonical row dump: one `{"table", "row"}` object per line, tables in dependency order, rows in insertion order |
| `extraction.json` | optional extraction summary |
| `review/export-*.json` | optional review export files |
| `corpus/<file>` | frozen originals and derived files, **only with `--with-originals`** |

No `capabilities.json`, no packets/outputs, no checkpoints, no host-local state. The manifest holds no report hash:
`reproduction_manifest(bundle, report_sha256=...)` binds report hash, bundle hash and code version in a separate file,
so there is no circular hash (exhibit reproduction package, LA-020).

## Import is verification first

```text
read archive (allow-listed member names, size/ratio/count limits, no links, no encryption, no duplicates)
  -> manifest checks (format, schema_version <= supported, member hashes, exact file list)
  -> staging dir  <parent>/.import-<target>-<id>/
        fresh DDL from this code -> rows inserted with bound parameters (column names checked, scalar values only)
        schemas of every record, passage text hashes, corpus_hash, foreign keys, table counts
        hash chain verified (E_CHAIN_BROKEN with first_broken_id), approved_set_hash and chain_head == manifest
  -> case.json, manifest.json (corpus), import.json, review/, corpus/ written into staging
  -> os.rename(staging, target)       # single atomic publication; target must not exist
failure at any point: staging removed, target untouched, nothing partial
```

The SQL dump of the PRD/task wording is realised as this canonical row dump: a bundle is never executed or fed to
`executescript`; unknown columns, tables, types or values are rejected as `E_BUNDLE_INVALID`.

## Errors

| Code | When |
|---|---|
| `E_BUNDLE_INVALID` (`detail`) | not a ZIP/lacase, newer `schema_version` or `format_version`, bad member name/link/encryption/duplicate/limits, hash or count mismatch, dump shape, schema/foreign-key/passage/corpus checks |
| `E_CHAIN_BROKEN` (`first_broken_id`, `reason`) | the recomputed hash chain differs from the dump |
| `E_CASE_EXISTS` | the target directory exists: bundles are never merged or overwritten |
| `E_ORIGINAL_HASH_MISMATCH` | a re-supplied file matches no frozen document's SHA-256; nothing is attached |

## Originals

Default export has no originals; the imported case lists `originals_pending` (also in `status`). `case originals --files ...`
matches each file to its Document by SHA-256 and attaches all or none. Evidence classes of imported reviews are copied
verbatim (`import.json` records the counts and states they are not verified or raised by the import).

## Host continuity (level B)

`case export` writes `export_marker.json` (`reviews_exported`), which clears the `status` export reminder until a new
review import or session end.
