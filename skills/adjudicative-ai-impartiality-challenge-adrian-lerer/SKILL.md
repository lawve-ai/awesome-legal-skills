---
name: adjudicative-ai-impartiality-challenge
description: Public-safe preliminary screen for challenges to the impartiality of an AI evaluator, LLM-as-a-judge, decision-support agent, or adjudicative system based on prior outputs, suspected bias, unstable reasoning, or self-reinforcing memory. Use when asked whether an AI should be recused, disqualified, replaced, audited, or escalated. Does not decide real cases or claim that human judicial-recusal doctrine automatically applies.
status: candidate
---

# Adjudicative AI Impartiality Challenge

## Purpose

Turn an allegation of “biased prior decisions” into an auditable, proportionate challenge. Treat recusal as a functional analogy unless jurisdiction-specific law establishes a legal mechanism.

## Workflow

1. Classify the role: evaluator, decision-support agent, or legally authorised adjudicator. Never infer authority from benchmark performance.
2. Identify the challenged target separately: base model; exact model version; system prompt and configuration; retrieval corpus; memory; tools; deploying institution; or a particular proceeding.
3. Freeze attribution evidence: dates, versions, prompts, record, retrieved sources, tool calls, memory state, output, and human intervention. If identity or provenance is missing, do not attribute a pattern to “the model”.
4. Test comparability of prior outputs. Compare like tasks, governing sources, language, procedural posture, and time period. Label incomparable examples.
5. Separate possible loci of distortion:
   - record construction and fact selection;
   - credibility attribution;
   - issue framing or dispute substitution;
   - source retrieval and authority ordering;
   - norm attribution and application;
   - remedy;
   - memory or precedent-like reuse.
6. Run or propose controlled counterfactuals. Hold legally relevant facts and sources constant while varying only the suspected nuisance feature. Include order permutations and a human-coded reference set where feasible.
7. Classify the evidence:
   - `INCIDENT`: isolated anomaly;
   - `SIGNAL`: repeated concern without adequate controls;
   - `REPLICATED_PATTERN`: comparable, controlled and reproducible disparity;
   - `NOT_ATTRIBUTABLE`: version, configuration or provenance is insufficient.
8. Choose the least disruptive adequate remedy: disclosure, preservation, independent audit, alternate configuration, exclusion of contaminated memory, human de novo review, quarantine, replacement, or functional disqualification.
9. Apply the legal uncertainty gate:
   - `PASS`: low-stakes research/evaluation and no material unresolved signal;
   - `ESCALATE`: material signal, unclear doctrine, or consequential decision support;
   - `BLOCK`: real rights or legal status would be affected without lawful authority, contestability, inspectable record, and effective human review.

## Required output

```yaml
status: PROPUESTO
role: evaluator | decision_support | adjudicator
challenged_target: model | configuration | memory | institution | proceeding
evidence_class: INCIDENT | SIGNAL | REPLICATED_PATTERN | NOT_ATTRIBUTABLE
bias_locus: []
comparability_limits: []
alternative_explanations: []
recommended_remedy: []
workflow_state: PASS | ESCALATE | BLOCK
human_review_required: true
```

## Guardrails

- Prior outputs are evidence, not self-proving precedents.
- One wrong result does not establish structural bias.
- Outcome parity alone cannot rule out process disparity.
- Never reuse the challenged system's own summaries as independent proof of impartiality.
- Never expose confidential matters, internal prompts, private thresholds, routing logic, or gate records.
- For a real controversy, require jurisdiction-specific counsel and a human decision-maker with power to disregard the system.

## Verification fixtures

- One anomalous output with no version record must remain `INCIDENT` or `NOT_ATTRIBUTABLE`, not “biased model”.
- Repeated controlled profile swaps that change credibility and outcome may become `REPLICATED_PATTERN` and trigger quarantine plus de novo review.
- Outputs from an obsolete model version cannot automatically disqualify a materially changed deployment; re-test the current configuration.

## Recovery

If evidence is incomplete, preserve what exists, stop reliance, label missing provenance, and request a fresh controlled evaluation. Do not manufacture certainty from narrative similarity.
