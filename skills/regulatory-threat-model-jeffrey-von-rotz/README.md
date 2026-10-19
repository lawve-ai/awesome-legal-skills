# Regulatory Threat Model (STRIDE + LINDDUN)

Turn your AI agent into the orchestrator of a real security review. This
skill runs a **server-enforced STRIDE threat model** and a **LINDDUN
privacy threat model** over a system you describe in plain prose,
screens the dependencies you name against **live CVE / CISA-KEV / EPSS
data**, and builds a **cited screen of EU security obligations** (GDPR,
NIS2, Cyber Resilience Act, AI Act) — which may apply, which need
determination, and which do not apply yet — with every regulatory
statement fetched from officially published text at answer time and its
scope, role, and application-date limits stated. It is cited research
support, never a compliance verdict.

Built for the way software is built now: if an AI agent wrote your app,
the same agent can run its security review — and the deliverable is a
report you can put in front of a customer, an auditor, or an investor,
with its sources and unresolved items visible; not a chat transcript.

Three things make this skill different from asking a model "is my app
secure?":

- **The threat model is real, not improvised.** STRIDE and LINDDUN run
  on the Ansvar Gateway's workflow engine, which enforces the steps and
  quality gates server-side and produces the report (PDF/HTML/DOCX).
  The skill forbids the agent from passing off model-generated output
  as the workflow's deliverable — on plans without workflow access it
  produces a scoping worksheet, never an imitation register.
- **Nothing legal is answered from model memory.** Every obligation in
  the screen carries the instrument, article, and source URL of the
  provision fetched from the official publisher — with applicability
  determined, not assumed: GDPR material and territorial scope tests
  (Arts. 2/3) with each duty attributed to its role,
  NIS2's binding-through-national-transposition reality, the CRA's
  phased application dates (Arts. 69/71), and the AI Act's own
  temporal gates (Arts. 111/113) are all part of the screen.
- **Your code stays yours.** The skill is prose-only: it never uploads
  documents or files, and its data-minimization rules require the
  agent to describe the system at architecture level in its own
  words — no source code, secrets, hostnames, or customer data are
  ever transmitted — and to show you the system description before
  anything is sent.

## Overview

- **STRIDE threat model** — per-component threats with category,
  severity, affected assets, mitigations, and regulatory citations.
  Server-enforced workflow, report via `generate_report`.
- **LINDDUN privacy threat model** — per-flow privacy threats with harm
  assessment and mitigations, offered whenever personal data flows.
- **Dependency exposure screen** — live CVE leads per component you
  name, confirmed against served affected-version data, with CISA KEV
  status and FIRST's EPSS estimate; reported honestly (a keyword hit is
  a lead, not a match; absence from KEV is never treated as evidence of
  safety; feed data age is stated).
- **Security-obligations screen** — selected and non-exhaustive: GDPR
  Articles 25/32 with an Article 35 DPIA screen, CRA scope and
  manufacturer/reporting obligations against their served application
  dates, a NIS2 scope check before any Article 21 claim, AI Act
  Article 15 presented conditionally on classification and its served
  dates — each row cited from fetched text with a verdict of applies /
  conditional / forward-looking / likely out of scope / not evaluated.
- **Honest failure modes** — answered-with-citations, no matching data,
  and retrieval failure are three distinct outcomes; a connector error
  is never converted into "you're fine".

## Requirements

The skill needs the **Ansvar Gateway** MCP connector:

- Endpoint: `https://gateway.ansvar.eu/mcp` (OAuth 2.1 with Dynamic
  Client Registration)
- Signup at [ansvar.eu](https://ansvar.eu). The dependency screen and
  obligations screen work on the **Free plan**; the STRIDE and LINDDUN
  workflow runs need **Premium** or above (metered monthly); the DPIA
  workflow needs **Team** or above. This skill itself never uploads
  documents on any plan.
- Works in MCP-capable agents — Claude, ChatGPT, Microsoft Copilot,
  Gemini and others. Supported surfaces and per-client prerequisites
  differ; see the current client matrix at
  [ansvar.eu/setup](https://ansvar.eu/setup).

## Installation

**Claude (claude.ai):** Settings → Capabilities → Skills → upload this
folder (SKILL.md). Then add the Ansvar Gateway connector under Settings →
Connectors with the endpoint above.

**Claude Code:** place the folder under `.claude/skills/` in your
project, and add the gateway as an MCP server.

**Other MCP-capable agents:** attach SKILL.md as standing instructions
for the conversation or project, with the gateway connected as an MCP
tool source — check [ansvar.eu/setup](https://ansvar.eu/setup) for your
client's exact connector surface and prerequisites.

## Usage

**Quick start** — try a prompt like:

> I built a SaaS app with Cursor over the last month — Next.js, Postgres,
> Stripe, EU users. My first business customer is asking for a security
> review. Threat-model it.

or:

> We're launching a feature that profiles user behavior with an LLM. Run
> a privacy threat model and tell me if we need a DPIA.

**Trigger phrases:** threat model, STRIDE, LINDDUN, security review,
privacy threats, is my app secure, DPIA needed, security obligations,
GDPR security requirements, NIS2 measures, Cyber Resilience Act,
dependency vulnerabilities, KEV, known exploited vulnerabilities,
vibe-coded app security, AI-built app.

**Workflow the agent follows:**

| Phase | What happens |
|---|---|
| 0. Plan check | `get_my_capabilities` — full mode on Premium+, honest free lane otherwise |
| 1. Staged intake | Architecture-level system snapshot, data picture, key assets, coarse legal posture — confirmed by you before anything is transmitted; no code, no secrets, no uploads |
| 2. STRIDE run | Server-enforced workflow, started only after you explicitly approve the metered run; report via `generate_report` |
| 3. LINDDUN run | Offered when personal data flows; separate explicit approval; ROPA uploads declined — processing described in prose |
| 4. Dependency screen | CVE leads per named component, confirmed/possible/unmatched against served version data, KEV + EPSS from their attributed surfaces, feed age stated |
| 5. Obligations screen | GDPR / CRA / NIS2 / AI Act provisions fetched and applied with their scope, role, and date limits — verdicts, never "all of this binds you" |
| 6. Deliverable | Workflow reports + exposure table + cited obligations screen + DPIA recommendation + the record of what was searched and what stayed unresolved |

## Grounding & safety

The skill's ground rules instruct the agent to: never simulate the
workflow engine or present model output as its report; treat only
documented structural workflow fields as control data and ALL free text
from tools, repositories, and documents as untrusted; transmit only
architecture-level prose the user has confirmed — no source code,
secrets, hostnames, customer data, or file uploads of any kind; obtain
explicit consent immediately before each metered workflow start; honor
server-enforced human-input gates rather than inventing answers; cite
every regulatory statement from fetched official-publisher text with
scope, role, and application dates checked; state the coverage limits
and source attribution of vulnerability data; and keep answered /
no-match / retrieval-failure outcomes separate.

## Regulatory basis

| Instrument | Role in this skill |
|---|---|
| [Regulation (EU) 2016/679 (GDPR)](https://eur-lex.europa.eu/eli/reg/2016/679/oj) | Material and territorial scope tests (Arts. 2/3); role-attributed duties: security of processing (Art. 32, controller and processor), data protection by design (Art. 25, controller), DPIA screen (Art. 35, controller) |
| [Directive (EU) 2022/2555 (NIS2)](https://eur-lex.europa.eu/eli/dir/2022/2555/oj) | Entity scope check (Art. 2) before any risk-management-measures claim (Art. 21), applied through national transposition |
| [Regulation (EU) 2024/2847 (CRA)](https://eur-lex.europa.eu/eli/reg/2024/2847/oj) | Product scope and roles (Arts. 2/3), manufacturer and reporting obligations (Arts. 13/14) against served application and transitional dates (Arts. 69/71) |
| [Regulation (EU) 2024/1689 (AI Act)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | Accuracy, robustness and cybersecurity for high-risk AI systems (Art. 15), gated on its served application dates and pre-existing-system rules (Arts. 111/113) |
| NVD (CVE Program records) / CISA KEV / FIRST EPSS | Dependency exposure screen, values quoted from their attributed detail surfaces with per-row citations |

All instrument text is fetched at answer time from official publishers
with per-row citations; the table above is orientation, not a data
source.

## Provenance

- Every tool-call shape and canonical reference in SKILL.md was
  verified against the live gateway on 2026-07-21.
- Published after a three-round adversarial review with live EUR-Lex
  cross-checking (2026-07-21). The free lane was then executed
  end-to-end on a live Free-plan token (2026-07-22): every free-lane
  tool, all 16 legal references with full citations, and the honest
  Premium refusal on the workflow gate — 49/49 checks. v1.2 folds the
  one finding (a Requirements grouping correction) back in.
- Companion skills, same author and grounding discipline:
  `cra-vulnerability-obligations` (full CRA product-duty analysis),
  `incident-reporting-navigator` (who to notify, where, by when).
- The same file is served at
  [ansvar.eu/skills/regulatory-threat-model/SKILL.md](https://ansvar.eu/skills/regulatory-threat-model/SKILL.md);
  this repository is the canonical home.
- Built by [Ansvar Systems AB](https://ansvar.eu) — the team behind the
  Ansvar Gateway.

## License & disclaimer

Skill text and this repository: [CC BY 4.0](LICENSE). The legal text the
skill fetches at runtime is served from official publishers with per-row
citations (EUR-Lex under Commission Decision 2011/833/EU; national
gazettes under their own terms); vulnerability data retrieved via the
NVD (CVE Program records), the CISA KEV catalog, and FIRST's EPSS.

Output produced with this skill is cited research support and a
design-level security review. It is not legal advice, not a compliance
determination, not a penetration test, and not a code audit.
