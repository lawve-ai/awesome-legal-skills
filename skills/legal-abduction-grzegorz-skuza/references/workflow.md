# Runtime workflow / Procedura runtime — preview v1

All paths are relative to the installed skill. Commands below reflect the
current CLI, not a promise of complete backlog integration. Check `python -B
-X utf8 la.py --help` and each command's `--help`. Global flags precede the
command: `--json --lang pl|en --case-dir <external-dir> --resume
--step-budget-s 90`. Only resumable paths actually implement batch resume;
the existence of a global flag is not proof that every step does.

PL: poniższa mapa obejmuje polecenia PRD, ale nie potwierdza ich pełnego DoD.
ID `set:...` musi pochodzić z zatwierdzonego zbioru, nie z przykładu dokumentacji.
Nie uruchamiaj pracy z aktami na A/B przy zakazie lub braku zgody.

| PRD step | Current CLI suffix (after globals) | Work / boundary |
| --- | --- | --- |
| 0 | `init --profile-file <file>` | Human answers, external case only |
| 1 | `doctor --declared-level A|B|C [--review-dir <dir>]` | Capabilities, no installation; directory permission probing |
| 2 | `ingest <explicit-file> ... [--batch-size 10]` | Frozen originals, SHA-256 |
| 3 | `extract [--max-pages N]` | Passages/locators; absent optional tools → `needs_text` |
| 4 | `families` | Exact bytes/email families; near duplicates remain P1 |
| 5 | `claims prepare --model-id <actual-id>` then `claims ingest --packet <file> --proposal <file>` | H output queues only; `none` for manual filling |
| 6 | `observations select --file <selection>`; `observations coverage`; `observations time --observation <id> --text <date>` | Approved claims only; human selection file; ambiguous time retained |
| 7 | `search run --query <literal> --scope all [--variant <literal>]`; `search rerun`; `search verify --record <id>` | Logged scope, limits and current corpus hash |
| 8 | `hypotheses prepare --scope <set-id> --declared-hypotheses N`; `hypotheses ingest --packet <file> --proposal <file>`; `hypotheses check` | Proposals and budget; predictions blocked by T-PREDICTION |
| 9 | `altcause check`; `altcause prepare` | Non-intent alternatives; no findings about people |
| 10 | `matrix prepare --scope <set-id>`; `matrix ingest --packet <file> --proposal <file>`; `matrix check --scope <set-id>` | Missing pairs stay not_assessed |
| 11 | `uncovered run --scope <set-id>` | Gaps, conflicting-all and consistent-all observations |
| 12 | `compare --scope <set-id>` | Lexicographic profile and LOO, no sum; T-COVERAGE unresolved |
| 13 | `tests prepare --scope <set-id>`; `tests ingest --packet <file> --proposal <file>`; `tests plan --scope <set-id>` | Distinct impact vectors, document-linked uncertainty/actions (task_tests/v2), access basis, uninformative outcome |
| 14 | `review export [--out <relative-case-path>]`; `review import --file <human-file>`; `review gates --profile working|exhibit` | O repeated after H; never agent-made approvals |
| 15 | `report --profile working|exhibit --scope <set-id>`; `report verify --file <report>`; `report replay --file <report> --bundle <lacase>` | Provisional report structure; missing Report chapter 15; Q12 open |
| 16 | `update run --files <new-files>`; `update stale`; `update invalidate --id <id> --reason <reason>`; `update reassess --file <human-file>` | New/affected packets, append-only reassessment; `run` output lists `revisit` and `changed_facts` |
| 16a | `update withdraw --id <clm|obs> --reason <r>`; `update change --id <old> --replacement <new> --reason <r>`; `update reinstate --id <id> --reason <r>` (each also `--dry-run`: preview only, nothing written); `update revisit [--scope <set-id>] [--template [<file>]]` | Human-stated fact change only (agent command, `human_via_agent`, blocks exhibit); flags explanations with a supports/conflicts cell on the fact, voids its cells, puts a replacement in scope; `revisit` gives prior content, reason, impact and path; template decisions stay empty for the human |
| 17 | `case export --out <case-dir/bundle.lacase>`; `case import --bundle <file>`; `case pending`; `case originals --files <files>`; `case inspect --bundle <file>` | New external destination on import; originals optional |
| supporting | `prepare <task-type> --objects-file <file>`; `ingest-proposal --packet <file> --proposal <file>`; `metrics`; `status --session-end`; `version` | Generic packet path/diagnostics, not an API model adapter |

Propagation is typed (`staleness.py`): a content change (re-extraction, displaced
representative, manual `invalidate`) flows to derived records and the cells that judged
them; a fact change moves only *standing* — explanations relying on the fact through a
supports/conflicts cell, and observations citing a withdrawn claim. Neutral cells, other
hypotheses, tests and the rest of the matrix are not re-flagged. Events recorded by
version 0.1.0 keep the breadth they were recorded with.

Selection, packets and proposals use the installed schemas. Do not invent
enum values delegated to the missing Report. Guard flags mean human review,
not an automatic factual determination. For PL/EN templates and labels see
`assets/templates/{pl,en}/` and `locales/{pl,en}.json`. Source extraction quality,
document authenticity and assessment relation are separate.

P1 deferred PRD commands/capabilities: timeline/value normalization, Horn/clingo,
heuristic scoring/sensitivity, near-duplicates, PostgreSQL roles/RLS, API adapter,
`diff`, critic, retention/`purge`, quote translation, PROV-JSON, `run.sh`/`run.ps1`,
signed review. P2: MCP, DMS, quorum, specialized Prolog/R adapters, HTML viewer,
provider high-risk pack. No equivalent fake command is advertised here.

## Document-linked test contract (runtime 0.3.0)

New test packets use `la:schema/task_tests/v2`. Prepare a fresh packet after
upgrading; a v1 packet cannot be imported as v2. In addition to `question`,
`outcomes`, `uninformative_outcome` and `access_basis`, every proposed item requires:

| Field | Contract |
| --- | --- |
| `scope_id` | Existing approved observation-set ID. |
| `uncertainty.description` | The bounded unresolved question. |
| `uncertainty.observation_ids` | Existing effective observations within the scope; may be empty. |
| `uncertainty.hypothesis_ids` | At least two distinct approved hypotheses in the scope which this test differentiates. |
| `document.status` | `in_corpus`, `referenced_not_obtained`, or `existence_unconfirmed`; document-availability labels, not factual or credibility judgments. |
| `document.description` | A precise document/version or candidate document type. |
| `document.document_id` | Existing frozen ID for `in_corpus`; otherwise JSON `null`. |
| `document.basis` | Why this document could help; distinguish a source reference from a suggested document type. |
| `document.basis_passage_ids` | Known passage IDs. `in_corpus` requires a passage in the identified document; `referenced_not_obtained` requires a source reference; unconfirmed existence may have no source. Human review checks semantic support. |
| `document.relevant_period`, `document.custodian` | A relevant period and custodian, or an explicit statement that they are unknown. |
| `next_step` | Concrete human action; not automatic access or collection. |

Unknown fields are refused. IDs, scope and outcome contracts are checked on
specialized ingest, generic ingest-proposal and human correction/approval.
Test packets include approved scope observations/claims and their frozen source
passages/documents; packet limits still refuse oversize input rather than truncate.
Each outcome vector must cover all current hypotheses in the scope. `tests plan`
rechecks current links/contracts; invalid tests remain visible with
`requires_reassessment` and do not cover required pairs. Old approved tests remain
unchanged and show `legacy_missing_details`. A new reviewed test can cover a gap
without rewriting an older test. Missing details never acquire invented values.

## Rejection history and report boundary

`review export` adds `review_history.rejections` separately from pending `items`.
Each entry shows the exact proposal, review reason and identity, evidence class,
source text/quote/locator, document/version hashes and recorded import time.
No decision time is inferred. New rejections atomically save a chained audit
snapshot in `value_records`. Export can append missing legacy snapshots from
retained proposals; missing item hashes are labelled `legacy_unbound`.
Without a snapshot, the report lists `snapshot_missing` and the prior decision.
Technical `auto_rejected` validation results are not human rejections.

The importer ignores the history section and reads decisions only from pending
`items`; changing that section cannot alter an earlier review. The reason
requirement and evidence-channel rules are unchanged.

Both PL/EN report profiles contain the approved action table and a clearly
separated case-wide rejection appendix. The appendix reads only chained audit
snapshots and review rows via `ReadRepository`; it never reads proposals.
It is excluded from comparison, observations and assessment inputs. Full source
content in the appendix is untrusted data, displayed literally. Existing exhibit
gates and all unresolved release/legal gates still apply.

For reconsideration, submit a new proposal through the normal validated path.
The human may fill `reconsiders_review_id` on its new pending review row, naming
an earlier rejected review of the same task type, and must provide a reason.
The old decision remains unchanged; history displays `later_reviews`. Importing
a changed decision for the original item still fails with `E_REVIEW_STALE`.
The agent never fills this link or decision on the human’s behalf.
