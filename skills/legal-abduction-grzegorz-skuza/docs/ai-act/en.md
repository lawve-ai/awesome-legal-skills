# Deployer documentation — EN, preview v1

Document version `deployer-preview/1`, bound to code and the bundle SHA-256
manifest, not a compliance assertion. **Legal assessment/classification has
not been performed.** Q10 (provider role), Q11 (license), Q12 (exhibit/ethics)
and LEGAL_VERIFICATION remain open. Amendment numbers and dates cited by the
PRD are not confirmed here.

## Intended purpose and boundaries

Support for counsel, defence and compliance in documentary analysis and
competing explanations of a bounded event. Preview: realistic synthetic cases
only. Planned `internal_employee` and `law_enforcement` contexts trigger
high-risk safeguards; the gate itself does not authorize deployment.
Courts, arbitration and ADR (`judicial`) are excluded. A party report is not
a court tool, finding or expert opinion. No evaluation of people, guilt,
credibility, propensity or future conduct is allowed.

## Instructions and consent

Follow the [guide](../usage.en.md). A human selects the profile, jurisdiction,
basis of use and `model_processing`. Missing/forbidden consent on A/B requires
stopping and using C outside the session, not merely selecting `none`.
For high-risk contexts the deployer records their own `deployer_ack` in
`case.json` after considering these documents. The agent cannot create it or
treat it as a conformity assessment. No ack → `E_HIGH_RISK_ACK`; judicial →
`E_CONTEXT_UNSUPPORTED`. No acknowledgement has been given by these docs.

## Oversight, logs and limitations

H is a proposal; O is actual human assessment outside the agent. Triage,
sampling, budget and review-pace gates cannot be bypassed. Default local A
uses `human_via_agent`; `human_file` requires observed write denial.
Signature/role classes are future P1. Reports show evidence-class shares,
hashes, code version, chain head and gaps. Logs/provenance support replay,
but full logging completeness and actual-host tests remain open (including
step timestamps in the current implementation).

A hash establishes byte agreement, not authenticity. SQLite with disk access
is not tamper-proof. Source instructions are data, but injection risks require
agent testing. OCR, interpretation, predictions, coverage and the missing
Report limit evaluation. Cost and effectiveness have not been demonstrated.

The deployer and qualified counsel assess data protection, secrecy,
classification, supervision and log retention duties under current law.
Packets/proposals contain text; `.lacase` without originals is not anonymous.
Do not send these in telemetry. Retention/purge is P1, not automatic deletion
in this preview. The [legal profile](../../references/legal-profile.md) is a
queue for official verification, not its result.
