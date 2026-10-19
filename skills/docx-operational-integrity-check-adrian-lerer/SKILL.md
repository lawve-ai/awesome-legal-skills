---
name: docx-operational-integrity-check
description: Reviews whether an AI-assisted Word or DOCX workflow preserves the original, tracked changes, comments, numbering, sections, edit identity, document structure, save/verify cycles, and professional review. Use before relying on a DOCX that an AI tool read, edited, redlined, reformatted, or generated. Do not use as a legal review of the document's substance or as proof that every rendering defect was detected.
---

# DOCX Operational Integrity Check by Ignacio Adrián Lerer

Public document-safety method by Ignacio Adrián Lerer.

Treat legal Word work as controlled document mutation, not text generation alone. Preserve the original, make substantive changes reviewable, and verify the resulting file before professional use.

## Review workflow

1. Record the document, task, tool, intended output, and responsible reviewer.
2. Preserve an untouched original and write changes to a separate output unless overwrite was explicitly approved.
3. Keep user, counterparty, and AI/editor identities distinguishable in tracked changes and comments.
4. Use tracked changes, comments, or a pending review queue for substantive edits.
5. Inspect the structural surfaces below before and after mutation.
6. Reopen or parse the output, sample unchanged sections, and perform visual review when layout matters.
7. Return `PASS`, `REVIEW`, or `BLOCK`. Final acceptance remains a human professional decision.

## Structural surfaces

- tracked changes and comments;
- headers, footers, footnotes, and endnotes;
- tables, numbering, lists, and styles;
- hyperlinks, bookmarks, and cross-references;
- citations, tables of authorities, and tables of contents;
- sections, page setup, signature blocks, and embedded objects.

## Decision states

- `PASS`: the original is preserved, edits remain reviewable, material structure was checked, the output reopens correctly, and the responsible human can review it.
- `REVIEW`: evidence is incomplete, layout was not checked, or a structural surface may have changed. Do not treat the file as final.
- `BLOCK`: the original was overwritten without approval, review history was lost, bulk acceptance occurred without instruction, the output is unreadable, or material changes cannot be reconstructed.

## Output

```markdown
## DOCX Operational Integrity Receipt

Document and task:
Tool or workflow:
Decision: PASS | REVIEW | BLOCK

### Original and rollback
- Original preserved:
- Separate output:
- Rollback path:

### Reviewability
- Edit identity:
- Tracked changes/comments:
- Bulk actions:

### Structure checked
- [surface and result]

### Verification
- Reopen or parse result:
- Visual review:
- Unchanged-section sample:

### Required controls
- [control]

### Human acceptance
- Responsible reviewer:
- Current state: draft | reviewed | final
```

## Verification and fallback

When the available tool cannot preserve or inspect a structural surface, leave that surface unchanged or return `REVIEW`. Never silently flatten tracked changes, comments, fields, or document structure to make processing easier.

If visual rendering cannot be checked, say so explicitly. Structural parsing alone does not prove visual fidelity.

## Trigger tests

- Obvious: “Check whether this AI-edited Word document preserved tracked changes.”
- Paraphrased: “Can we safely rely on the DOCX produced by this redlining tool?”
- Boundary: “The text is correct, but nobody checked numbering or comments.”
- Non-trigger: “Advise whether the contract clause is enforceable under local law.”

## Public boundary

This public edition contains generic DOCX integrity controls only. Do not include client documents, private prompts, credentials, internal workflows, provider routing, scoring thresholds, cost records, or proprietary verifier logic.
