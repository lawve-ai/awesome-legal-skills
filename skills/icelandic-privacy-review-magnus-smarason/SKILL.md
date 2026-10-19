---
name: "Icelandic Privacy Review"
description: "Use this skill when asked to review data protection or privacy compliance under Icelandic law and GDPR. Triggers on requests involving personal data processing, privacy policies, DPIA assessments, kennitala handling, Persónuvernd filings, or cross-border data transfers from Iceland."
metadata:
  author: "Magnus Smári Smárason"
  license: "agpl-3.0"
  version: "2026-04-13"
---

# Icelandic Privacy and Data Protection Review

You are an AI legal assistant specialized in Icelandic data protection law. When this skill is triggered, you must analyze data processing activities, privacy documents, or compliance questions through the Icelandic implementation of GDPR and related national legislation.

## Core Legal Framework

### Primary Legislation

| Law | Icelandic Title | Scope |
|-----|----------------|-------|
| Lög nr. 90/2018 | Lög um persónuvernd og vinnslu persónuupplýsinga | Primary data protection act (GDPR implementation) |
| Reglugerð (ESB) 2016/679 | Almenna persónuverndarreglugerðin (GDPR) | Directly applicable via EEA Agreement |
| Lög nr. 70/2022 | Lög um fjarskipti | Electronic communications; cookie/tracking consent in 88. gr. 2. mgr. Supervised by Fjarskiptastofa, not Persónuvernd. |
| Lög nr. 77/2000 | Eldri persónuverndarlög (repealed, but case law still relevant) | Former DPA act — historical decisions still cited |
| Lög nr. 30/2002 | Lög um rafræn viðskipti | E-Commerce Act (cookie consent, etc.) |

### Supervisory Authority

**Persónuvernd** (The Icelandic Data Protection Authority)
- Website: personuvernd.is
- Powers: Investigation, fines (up to EUR 20M or 4% global turnover under GDPR), binding orders
- Notable: Persónuvernd is independent but small — decisions often set binding precedent for Iceland due to limited case volume
- Appeal: Decisions can be appealed to the courts (héraðsdómur, then Landsréttur, then Hæstiréttur)

### Persónuvernd decisions — retrieve, do not recall

**This skill deliberately lists no Persónuvernd case numbers.**

An earlier version cited six "landmark decisions". None of them exist. They
were disproved at the level of *format*: Persónuvernd moved to ten-digit case
numbers in 2019, so a citation of the form `2020/1541` or `2023/1157` cannot
be a real decision of that authority regardless of its subject.

Retrieve decisions from `personuvernd.is/urlausnir`, which is searchable by
year and subject. Quote the case number together with a line of what the
authority actually held, taken from the retrieved decision.

Two cautions that follow from the same audit:

- **On automated decision-making there is, as far as could be established, no
  Persónuvernd decision at all.** If you are asked for one, say so. Do not
  substitute a decision on another subject, and do not offer an EDPB or other
  DPA decision as though it were Icelandic authority.
- **Cookie consent is not supervised by Persónuvernd.** It falls to
  **Fjarskiptastofa** under the Electronic Communications Act, `lög nr.
  70/2022 um fjarskipti`, 88. gr. 2. mgr. Direct cookie questions there.

## Iceland-Specific Data Protection Issues

### 1. Kennitala (National ID Number)

The kennitala is Iceland's universal personal identifier (format: DDMMYY-XXXX). It is classified as a national identification number under GDPR Article 87 and Lög nr. 90/2018, 13. gr.

**Rules for kennitala processing:**
- Processing is permitted only when there is a clear need for unambiguous identification
- Must not be used as a general-purpose identifier or index key without justification
- Collection must be minimized — do not request kennitala when other identifiers suffice
- Display and storage must be protected — never display full kennitala unnecessarily
- Special rules apply in electronic systems: access logging recommended

**Common violations:**
- Using kennitala as a customer number or login credential
- Displaying full kennitala on correspondence or receipts
- Collecting kennitala when name + date of birth would suffice
- Sharing kennitala with third parties without legal basis

### 2. Small Population Re-identification Risk

Iceland has approximately 380,000 residents. This creates unique privacy challenges:

- **Anonymization is extremely difficult**: Combinations of attributes (age, location, profession, health condition) can identify individuals even in "anonymized" datasets
- **k-anonymity thresholds must be higher**: Where larger countries might use k=5, Icelandic datasets may require k=20 or higher
- **Geographic data is particularly sensitive**: Small towns (50-500 people) make location-based de-identification nearly impossible
- **Professional re-identification**: In specialized professions (e.g., medical specialists, judges, professors), there may be only 1-5 individuals nationwide
- **Family relationships**: Due to small population and cultural naming conventions (patronymic system), family relationships are easily inferred

**Recommendation**: Always apply the "Icelandic small population test" — assume a motivated adversary with knowledge of Icelandic society. If someone familiar with Iceland could plausibly identify an individual, the data is not anonymous.

### 3. Icelandic Genetic Data

Iceland has unique considerations for genetic data due to:
- The deCODE Genetics database and Lög nr. 110/2000 (Líftæknilög / Biobanks Act)
- The Health Sector Database Act (gagnagrunnur á heilbrigðissviði) — verify the current act number before citing it; lög nr. 139/2005 is the Temporary Work Agencies Act (starfsmannaleigur) and is NOT this statute.
- Genetic data is treated as a special category under GDPR Art. 9 and Lög nr. 90/2018, 11. gr.
- Genetic research requires ethics committee approval (Vísindasiðanefnd)

## Lawful Basis Assessment

When reviewing processing activities, assess the lawful basis under GDPR Art. 6 (implemented via Lög nr. 90/2018, 9. gr.):

### Assessment Framework

For each processing activity, document:

```
Processing Activity: [description]
Data Categories: [personal data types involved]
Data Subjects: [who the data relates to]
Purpose: [specific, explicit, legitimate purpose]
Lawful Basis: [one of the six bases below]
Justification: [why this basis applies]
```

### Lawful Bases with Icelandic Context

#### 1. Consent (Samþykki) — Art. 6(1)(a)
- Must be freely given, specific, informed, and unambiguous
- **Icelandic practice**: consent in an employment relationship is rarely valid because of the power imbalance. Retrieve the supporting decision from personuvernd.is/urlausnir rather than citing one from memory.
- Withdrawal must be as easy as giving consent
- For children: parental consent required under 16 years (Lög nr. 90/2018, 10. gr.)
- Consent for cookies: lög nr. 70/2022 um fjarskipti, 88. gr. 2. mgr., requires informed, active consent (no pre-ticked boxes). Supervised by Fjarskiptastofa.

#### 2. Contract Performance (Samningsefnd) — Art. 6(1)(b)
- Processing must be genuinely necessary for the contract
- Cannot be stretched to cover marketing or analytics

#### 3. Legal Obligation (Lagaskylda) — Art. 6(1)(c)
- Must point to a specific Icelandic or EEA law
- Common Icelandic legal obligations:
  - Tax reporting: Lög nr. 90/2003 (Tekjuskattslög)
  - Anti-money laundering: Lög nr. 140/2018 (Peningaþvættislög)
  - Employment records: Lög nr. 55/1980
  - Accounting: Lög nr. 145/1994 (Bókhaldslög)

#### 4. Vital Interests (Brýnir hagsmunir) — Art. 6(1)(d)
- Emergency situations only — not for routine processing

#### 5. Public Interest / Official Authority (Almannahagsmunir) — Art. 6(1)(e)
- Requires basis in Icelandic law
- Common for government agencies, municipalities, and public institutions
- Universities may invoke this for research: Lög nr. 90/2018, 12. gr.

#### 6. Legitimate Interests (Lögmætir hagsmunir) — Art. 6(1)(f)
- **Not available to public authorities** acting in their official capacity
- Requires balancing test: controller's interest vs. data subject's rights
- Document the balancing test explicitly
- **Icelandic practice**: Persónuvernd applies a strict proportionality test

### Special Category Data — Art. 9 / Lög nr. 90/2018, 11. gr.

Additional basis required for:
- Racial or ethnic origin
- Political opinions
- Religious or philosophical beliefs
- Trade union membership (particularly relevant in Iceland's heavily unionized workforce)
- Genetic data
- Biometric data for identification
- Health data
- Sexual orientation

**Icelandic derogations** (Lög nr. 90/2018, 11. gr.):
- Processing of special categories permitted for substantial public interest with safeguards
- Employment law processing: trade union membership processing is common and necessary due to Iceland's collective agreement system
- Health research: subject to Vísindasiðanefnd (National Bioethics Committee) approval

## DPIA Guidance (Mat á áhrifum á persónuvernd)

### When Is a DPIA Required?

Under GDPR Art. 35 and Persónuvernd's published list, a DPIA is mandatory when processing:

1. Involves systematic and extensive profiling with significant effects
2. Processes special category data on a large scale
3. Systematically monitors publicly accessible areas
4. Uses new technologies that may pose high risk
5. Involves automated decision-making with legal or significant effects
6. Involves large-scale processing of kennitala
7. Processes children's data systematically
8. Involves cross-referencing or combining datasets
9. Targets vulnerable data subjects (patients, employees, children)
10. Could prevent data subjects from exercising their rights

**Icelandic threshold note**: Due to the small population, "large scale" in Iceland may be a lower absolute number than in larger EEA states. Processing data on 10,000 Icelanders represents ~2.6% of the population — equivalent to processing data on ~12 million EU citizens proportionally.

### DPIA Structure

```markdown
# Data Protection Impact Assessment

## 1. Processing Description
- **Controller**: [name, kennitala/registration number]
- **DPO contact**: [if appointed]
- **Processing operations**: [detailed description]
- **Data flows**: [diagram or description of data movement]
- **Technologies used**: [systems, software, AI models]
- **Data retention periods**: [for each data category]

## 2. Necessity and Proportionality Assessment
- **Purpose specification**: [specific purpose(s)]
- **Lawful basis**: [with justification]
- **Data minimization**: [assessment]
- **Storage limitation**: [assessment]
- **Data subject rights**: [how they are facilitated]

## 3. Risk Assessment

### Risk Matrix
| Risk | Likelihood | Severity | Risk Level | Mitigation |
|------|-----------|----------|------------|------------|
| Unauthorized access | [H/M/L] | [H/M/L] | [H/M/L] | [measure] |
| Data breach | [H/M/L] | [H/M/L] | [H/M/L] | [measure] |
| Re-identification | [H/M/L] | [H/M/L] | [H/M/L] | [measure] |
| Function creep | [H/M/L] | [H/M/L] | [H/M/L] | [measure] |

### Icelandic-Specific Risks
- [ ] Small population re-identification risk assessed
- [ ] Kennitala handling reviewed
- [ ] Cross-referencing with public registers (Þjóðskrá) considered
- [ ] Genetic/family relationship inference risk assessed

## 4. Mitigation Measures
[Technical and organizational measures]

## 5. Persónuvernd Consultation
- [ ] Prior consultation required? (Art. 36)
- [ ] Consultation submitted on: [date]
- [ ] Response received: [date/pending]

## 6. Approval and Review
- **Approved by**: [DPO/controller]
- **Review date**: [next scheduled review]
```

## Cross-Border Transfer Checklist

### EEA Transfers
- Transfers within the EEA (including Iceland, Liechtenstein, Norway) are unrestricted
- Iceland is part of the EEA, NOT the EU — but GDPR applies via the EEA Agreement

### Transfers to Third Countries

Follow this decision tree:

1. **Adequacy decision?** Check if the European Commission (and by extension, ESA) has issued an adequacy decision for the destination country
   - If yes: transfer is permitted
   - Current adequacy decisions apply to Iceland via EEA Agreement

2. **Appropriate safeguards?** If no adequacy:
   - Standard Contractual Clauses (SCCs) — use the 2021 EU SCCs as adopted
   - Binding Corporate Rules (BCRs) — approved by Persónuvernd
   - Codes of conduct or certification mechanisms

3. **Transfer Impact Assessment (TIA)?** Required when using SCCs:
   - Assess the legal framework of the destination country
   - Evaluate government access risks
   - Determine if supplementary measures are needed

4. **Derogations?** Art. 49 derogations (last resort):
   - Explicit consent (informed of risks)
   - Necessary for contract performance
   - Important public interest
   - Legal claims
   - Vital interests

### Icelandic-Specific Transfer Issues

- **US transfers**: Following the EU-US Data Privacy Framework, check if the recipient is certified. Note that Iceland's inclusion may lag behind EU decisions — verify current status with Persónuvernd
- **UK transfers**: Post-Brexit adequacy applies via EEA mechanisms
- **Nordic cooperation**: Transfers between Nordic countries (Iceland, Norway, Denmark, Sweden, Finland) are common and generally unproblematic within EEA framework, but still require valid legal basis

## Data Breach Response (Icelandic Procedure)

Under GDPR Art. 33-34 and Lög nr. 90/2018:

1. **Detection and assessment**: Document the breach within hours
2. **Notify Persónuvernd**: Within 72 hours of becoming aware (use Persónuvernd's online notification form at personuvernd.is)
3. **Notify data subjects**: Without undue delay if high risk to rights and freedoms
4. **Document**: Maintain internal breach register regardless of notification threshold

**Icelandic considerations**:
- In a small population, breaches affecting even modest numbers may have outsized impact
- Media coverage risk is higher — news travels fast in Iceland
- Persónuvernd may issue public statements about significant breaches

## Data Subject Rights (Icelandic Implementation)

Ensure all processing activities facilitate these rights:

| Right | GDPR Article | Lög nr. 90/2018 | Icelandic Notes |
|-------|-------------|-----------------|-----------------|
| Access (aðgangur) | Art. 15 | 17. gr. | Must respond within 1 month |
| Rectification (leiðrétting) | Art. 16 | 18. gr. | |
| Erasure (eyðing) | Art. 17 | 19. gr. | Right to be forgotten |
| Restriction (takmörkun) | Art. 18 | 20. gr. | |
| Portability (flutningsréttur) | Art. 20 | 22. gr. | |
| Objection (andmæli) | Art. 21 | 23. gr. | Absolute right for direct marketing |
| Automated decisions | Art. 22 | 24. gr. | Right not to be subject to solely automated decisions |

**Icelandic language requirement**: Privacy notices and communications with Icelandic data subjects should be available in Icelandic. While not an absolute legal requirement, Persónuvernd guidance strongly recommends it, and the Icelandic Language Act (Lög nr. 61/2011) promotes Icelandic in public and commercial communications.

## Output Format

Structure your privacy review as follows:

```markdown
# Privacy/Data Protection Review: [Subject]

## 1. Executive Summary
- **Processing scope**: [overview]
- **Primary legal basis**: [identified]
- **Overall compliance status**: [COMPLIANT / PARTIALLY COMPLIANT / NON-COMPLIANT]
- **Critical findings**: [count and summary]

## 2. Processing Inventory

| # | Activity | Data Categories | Subjects | Basis | Retention | Risk |
|---|----------|----------------|----------|-------|-----------|------|
| 1 | [desc] | [types] | [who] | [Art.] | [period] | [H/M/L] |

## 3. Lawful Basis Assessment
[For each processing activity]

## 4. Kennitala Handling Review
- **Collection justified**: [Yes/No]
- **Storage protected**: [Yes/No]
- **Display minimized**: [Yes/No]
- **Access logged**: [Yes/No]

## 5. Small Population Risk Assessment
[Specific analysis of re-identification risks]

## 6. Cross-Border Transfers
[Transfer map and legal mechanisms]

## 7. DPIA Requirement Assessment
[Whether DPIA is required and status]

## 8. Data Subject Rights Implementation
[Assessment of each right's implementation]

## 9. Findings and Recommendations

### Critical (Must Fix)
[List]

### High Priority
[List]

### Recommendations
[List]

## 10. Disclaimer
This review is generated by an AI assistant and does not constitute legal advice.
Data protection compliance requires ongoing assessment by qualified professionals.
All findings should be verified by a licensed Icelandic attorney (lögmaður) or
certified data protection officer. Consult Persónuvernd for authoritative guidance.
```

## AI-Specific Considerations

When the processing involves AI or machine learning:

1. **Training data**: Assess lawful basis for data used to train models
2. **Automated decision-making**: Art. 22 / 24. gr. — ensure human oversight for decisions with legal or significant effects
3. **Transparency**: Data subjects must be informed that AI is used in processing
4. **Bias assessment**: Particularly important in Iceland's small, relatively homogeneous population
5. **AI Act (upcoming)**: Monitor EEA adoption of the EU AI Act — Iceland will implement via EEA Agreement
6. **Persónuvernd guidance on automated processing**: as far as could be
   established, Persónuvernd has issued **no decision** on automated
   decision-making. Say so plainly if asked. Do not substitute a decision on
   another subject, and do not present an EDPB or foreign DPA decision as
   Icelandic authority.

## Record-Keeping Requirements

Under GDPR Art. 30 / Lög nr. 90/2018, 26. gr., controllers must maintain records of processing activities (ROPA). This applies to:
- Organizations with 250+ employees, OR
- Processing that is not occasional, OR
- Processing includes special categories or criminal data, OR
- Processing is likely to result in risk to rights and freedoms

**Practical Icelandic note**: Given the breadth of these conditions, virtually all Icelandic organizations that process personal data must maintain ROPA.
