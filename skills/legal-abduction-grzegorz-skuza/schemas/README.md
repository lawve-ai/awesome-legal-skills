# Schemas

Versioned (`la:schema/<name>/vN`) Draft 2020-12 subset schemas, checked by the
single validator `legal_abduction/validation.py` (supported keywords are listed
in its docstring; any other keyword fails `load_registry`). Objects set
`additionalProperties: false`.

Deliberately open (decisions T-ENUM, T-LOCATOR, T-PREDICTION; no guessed values):

- Claim `epistemic_status` and Review `decision`/`evidence_class`, plus Claim
  `polarity`/`modality`, remain open pending the referenced Report. LA-015
  explicitly defines Assessment `relation` as `supports`, `conflicts`, or
  `neutral`; this is scoped to that field and does not resolve other T-ENUMs.
- `Passage.locator` carries `locator_version: 1` and the PRD components; the
  offset unit is not frozen.
- No `Prediction` schema; `Hypothesis` has no predictions field.
- Review `decision`/`evidence_class` and Claim `polarity`/`modality` are free
  non-empty strings until their enums are sourced.

Test proposals use `task_tests/v2` and require the document/action fields described
in [workflow](../references/workflow.md). Approved `test/v1` records retain a
legacy branch with no action fields; partial mixtures are rejected. Existing
approved records are never rewritten.
