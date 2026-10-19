---
name: public-legal-ai-endpoint-protection
description: Reviews public or shared AI-backed web endpoints for abuse, excessive cost, data exposure, unsafe browser control, weak request limits, and missing human approval. Use before launching or materially changing an HTTP or API endpoint that can invoke an AI model. Do not use as a penetration test, compliance certification, or substitute for runtime monitoring and professional security review.
---

# Public Legal-AI Endpoint Protection by Ignacio Adrián Lerer

Public-light endpoint review method by Ignacio Adrián Lerer.

Review the design and configuration without probing a live third-party system. Use local code, documentation, synthetic requests, or an authorized test environment.

## Review workflow

1. Map the request path from caller to model provider and back.
2. Identify who can call the endpoint, what data they can supply, and which costly or sensitive actions they can influence.
3. Verify that authorization and abuse controls run before any paid model call.
4. Check the minimum controls below.
5. Record missing evidence separately from confirmed defects.
6. Return `PASS`, `REVIEW`, or `BLOCK` and the smallest safe remediation.

## Minimum controls

- Accept only intended HTTP methods and content types.
- Enforce authentication or a documented public-use policy.
- Restrict allowed origins when browser access is intended.
- Apply per-user or per-client rate and concurrency limits.
- Cap request size, history length, output size, duration, and retry count.
- Select models and tools on the server, not from unrestricted browser input.
- Keep secrets and provider credentials outside client-visible responses.
- Validate and normalize user-controlled fields before provider calls.
- Return sanitized errors without upstream request details or sensitive diagnostics.
- Record enough metadata to investigate abuse without logging confidential content by default.
- Define spend alerts, a kill switch, and a rollback path.
- Require explicit human approval before expanding permissions, data access, external actions, or budget.

## Decision states

- `PASS`: minimum controls are evidenced and remaining risk fits the declared public-use policy.
- `REVIEW`: evidence is incomplete or a non-critical control needs a named owner and deadline. Do not claim production readiness.
- `BLOCK`: an unauthenticated or browser-controlled request can cause uncapped spending, expose sensitive data, select unrestricted tools/models, or trigger consequential external actions.

## Output

```markdown
## Public AI Endpoint Protection Receipt

Endpoint and intended users:
Evidence reviewed:
Decision: PASS | REVIEW | BLOCK

### Request path
- Caller:
- Server controls:
- Model or tool boundary:
- Returned data:

### Findings
- Confirmed:
- Missing evidence:
- Highest plausible impact:

### Required controls
- [control, owner, verification]

### Human approval points
- [action requiring approval]

### Recheck triggers
- [code, provider, permission, model, tool, or budget change]
```

## Verification and fallback

Verify controls from source, configuration, or an explicitly authorized test environment. Do not probe external systems, bypass access controls, or run load tests merely because this Skill was invoked.

If the deployment or configuration cannot be inspected, return `REVIEW` or `BLOCK`. Do not infer safety from a framework, hosting provider, or security product name.

## Trigger tests

- Obvious: “Review this public AI API before launch.”
- Paraphrased: “Could a visitor make our chatbot spend without limit?”
- Changed system: “We added tools and a larger model to the endpoint. Recheck it.”
- Non-trigger: “Draft the marketing copy for our legal-tech homepage.”

## Public boundary

This edition contains a general educational checklist only. Do not include credentials, private configurations, internal prompts, client data, local paths, proprietary thresholds, provider routing, cost ledgers, private evaluations, or exploit instructions.
