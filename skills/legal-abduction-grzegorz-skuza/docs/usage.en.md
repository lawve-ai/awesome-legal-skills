# legal-abduction — user guide EN, preview v1

## Purpose and advantage over a one-off prompt

The skill guides an agent through versioned frozen sources → literal,
source-located quotations → proposals → human review → competing hypotheses,
matrix, gaps and discriminating tests. Scripts enforce deterministic checks;
the model proposes content; a human assesses and approves outside the agent.

A one-off prompt can produce a useful account but does not itself provide a
validator, isolated proposal queue, quote checks, integrity chain, source-family
deduplication, review budget or delta updates. The skill supplies these
mechanisms and persistent instructions. This is a **design advantage**, not
measured proof of better quality or lower cost. Models can err, hosts can fail
to load instructions, and an agent with disk access can tamper with storage.
A [proposed, usable evaluation](evaluation/protocol.md) is included; no
skill-versus-bare-LLM experiment has yet been run.

**Realistic synthetic cases only in this preview.** Keep documents, personal
data, secrets and outputs out of the skill directory.

## Start

1. [Install](installation.en.md), check Python >=3.12 and skill activation.
2. Before opening documents, choose PL/EN, question, time window, scope,
   jurisdiction, purpose, perspectives and context. Profile and consent come
   from the human, not the corpus.
3. Missing/forbidden `model_processing` on A/B: stop case processing in this
   session. The human must run C/`none` outside the agent session; switching to
   `--model-id none` inside the agent does not meet this boundary.
4. `init`, `doctor` for an external case directory, explicit files for
   `ingest`, then `extract`, `families`. Do not install PDF/OCR. `needs_text`
   requires an explicit derived text document and review. Resume supported
   interrupted batch steps using global `--resume`, with unchanged inputs.
5. Follow the [command map](../references/workflow.md): prepare proposals,
   export review, wait for actual human decisions, then import them. The agent
   is not the reviewer. A quote remains a literal slice of Passage text.
6. Select observations, log searches, create alternatives, matrix and test plan.
   Comparison consumes approved records only.

## Interpret outputs

- `partial` / incomplete: missing assessments or material; a missing pair is
  `not_assessed`, never neutral.
- `underdetermined`: evidence/rules do not identify one explanation; never
  resolve a tie by ID.
- `unstable`: removing a source family changes the leader.
- Profile ordering is not a sum of scores, probability or evaluation of a person.
- SHA-256 binds bytes, not authenticity, authorship or date. Integrity is
  tamper-evident, not tamper-proof.
- Default local host A uses `human_via_agent`; a stronger class requires a real
  evidence channel and observed `doctor` permission boundary, not a declaration.
- Budget and triage protect oversight: class I individually, class II with a
  sample; a correction escalates the batch. Do not bypass budget refusals.

`working` reports support internal analysis. `exhibit` has stricter technical
gates but its legal/ethical status is **unresolved**:
[working policy](policy/exhibit-use.en.md). It is party material, not a
court/ADR tool, finding of fact or expert opinion. Only a human fills the
responsible lawyer's statement. This preview does not authorize filing reports.

## Updates and continuity

`update run` addresses new/affected material; old approvals remain and stale
records require reassessment. Its `revisit` list (and `update revisit`) names each
earlier judgment to revisit, what it said, and which change put it back under review.
When you tell the agent that a claim or observation is withdrawn, corrected or back in
force, it records that with `update withdraw|change|reinstate` and your reason. Only the
explanations whose assessment of that fact was supports/conflicts are flagged; the cells
on a withdrawn fact stop counting; a corrected fact's replacement must be assessed.
You decide each flagged judgment in the reassessment file; the agent never fills it.
To see the effect before you decide, ask for a preview: `--dry-run` lists what would be flagged,
voided and left to assess, and writes nothing.
These changes are `human_via_agent` and block the `exhibit` profile.
Never edit SQLite or triggers directly.
On host B, run `status --session-end`, `case export`, download the `.lacase`
before ending the session, then import into a fresh directory in a later
session. A case bundle may contain sensitive text even without originals.
It is not the skill installation ZIP. No G2 promise is made for B.

## Limitations and gates

Read [deployer documentation](ai-act/en.md), [legal profile](../references/legal-profile.md)
and [distribution gates](distribution.md): Q10/Q11/Q12, missing Report,
LEGAL_VERIFICATION and later tests/measurements remain open. Predictions and
material coverage are partly undefined. PostgreSQL, API, solver, scoring,
signed review, MCP/DMS are future P1/P2, not preview features.
Report actual errors/refusals instead of presenting them as success.

## Documents and rejection history (0.3.0)

Test plans identify an uncertainty, a document or candidate document type, its
identification basis and the next human action. Present, referenced-but-missing
and existence-unconfirmed documents are distinguished. Legacy details remain
missing; tests incompatible with the current scope require reassessment. New
packets use `task_tests/v2`; see [workflow](../references/workflow.md) for fields.

Review exports contain separate rejection history with the exact reviewed
version, sources and human reason. Do not enter decisions in history. Reports
include approved action tables and a case-wide audit appendix. Rejected content
never contributes to analysis. Import time is not decision time; historical
gaps remain visible.
