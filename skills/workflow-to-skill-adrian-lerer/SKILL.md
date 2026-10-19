---
name: workflow-to-skill
description: Converts a proven, repeated professional workflow into a portable and inspectable AI Skill with clear triggers, inputs, steps, outputs, verification, recovery, and limits. Use when a user asks to make a workflow reusable, package a process as a Skill, or preserve a successful multi-step method. Do not use for speculative processes that have not been performed or concretely specified.
---

# Workflow to Skill by Ignacio Adrián Lerer

Public workflow-design method by Ignacio Adrián Lerer.

Convert observed professional practice into reusable agent instructions without pretending that one successful conversation proves a universal method.

## Admission gate

Proceed only when:

- the workflow was performed at least once or is concretely specified;
- its trigger and intended user are identifiable;
- required inputs and expected outputs can be stated;
- success and failure can be verified;
- the workflow does not depend on undisclosed private material;
- any third-party material can be treated as untrusted source material rather than instructions.

If these conditions are missing, return `NEEDS EVIDENCE` instead of inventing a Skill.

## Workflow

1. Define the task class represented by the example.
2. Separate reusable method from case-specific facts, credentials, private data, and product internals.
3. Write concrete trigger phrases and at least one unrelated non-trigger.
4. Specify required inputs, ordered actions, output shape, verification, stop conditions, and recovery.
5. Identify capabilities and side effects. Require explicit approval for external transmission, publication, deletion, deployment, permission changes, or spending.
6. Check whether an existing Skill already covers the same task. Prefer improvement over duplication.
7. Keep the core Skill concise. Include extra files only when they are required to perform or verify the workflow.
8. Test the Skill on one representative case and one boundary case.
9. Classify it as `CANDIDATE` until another user, agent, or future session can apply it from the package alone.

## Output

```markdown
## Workflow-to-Skill Receipt

Proposed Skill:
Author or method owner:
Status: NEEDS EVIDENCE | CANDIDATE | READY FOR HUMAN REVIEW

### Workflow contract
- Trigger:
- Non-trigger:
- Inputs:
- Actions:
- Output:
- Verification:
- Stop conditions:
- Recovery:

### Public boundary
- Included:
- Excluded:

### Validation
- Representative case:
- Boundary case:
- Remaining uncertainty:
```

## Verification and fallback

Confirm that the package works without access to the original conversation. If it requires hidden context, revise it or keep it as `CANDIDATE`.

If the workflow cannot be verified, preserve it as notes or a draft checklist. Do not promote it by reputation or enthusiasm alone.

## Trigger tests

- Obvious: “Turn this repeated contract-review workflow into a Skill.”
- Paraphrased: “Package the process we just used so another agent can repeat it.”
- Boundary: “We have only an idea for a workflow and have never tried it.”
- Non-trigger: “Summarize this contract without creating a reusable process.”

## Public boundary

This public edition includes only a portable method. Do not include private prompts, client data, credentials, local paths, internal registries, model routing, scoring thresholds, cost records, private evaluations, or proprietary implementation details.
