# Legal profile / Profil prawny — working reference v1

**Not legal advice; no official legal verification performed for this preview.**
Jurisdiction, display language and source language are independent. PL labels
must not automatically apply Polish law to a non-PL case. The human selects
`jurisdiction` in the profile; legal reviewers determine applicable law.

PL: dokument roboczy, nie opinia prawna. `jurisdiction` wybiera człowiek.
Język PL nie przesądza jurysdykcji; tłumaczenie raportu nie zmienia prawa.

| Jurisdiction/context | Working references from PRD; verify before release/use | Gate |
| --- | --- | --- |
| PL civil / cywilne | k.p.c. art. 3, 231, 233 §1, 245, 278: truth, evaluation of evidence, private documents vs expert opinions | Q12, LEGAL_VERIFICATION |
| PL criminal / karne | k.p.k. art. 4 and 7: circumstances favorable/unfavorable and evidence evaluation; mapping to alternatives needs legal validation | Q12, Q13, LEGAL_VERIFICATION |
| EU personal data / dane | GDPR/RODO art. 5(1)(c), 22 where applicable; deployer assesses basis, secrecy, processor/controller role | D1; deployment-specific legal assessment |
| EU employee/law-enforcement | AI Act Annex III points 4 and 6; intended high-risk safeguards, no individual credibility/guilt/intent findings | Q10, human deployer_ack, LEGAL_VERIFICATION |
| Judicial, arbitration, ADR | Unsupported intended use in v1; a party's report is not a court decision tool | E_CONTEXT_UNSUPPORTED |
| Other jurisdiction | No automatic k.p.c./k.p.k. mapping; obtain qualified local review | unresolved local legal review |

Official verification queue: check current consolidated texts on EUR-Lex
(https://eur-lex.europa.eu/) and Poland's official legislation database
(https://eli.gov.pl/). Record official identifier, version/date, exact provision,
reviewer and scope outside this preview. These links are starting points,
**not evidence that verification occurred**.

The PRD's claimed amendment number and shifted AI Act dates have not been
officially verified. This preview deliberately does not restate them as fact.
Neither the absence of an alarm nor a successful `deployer_ack` establishes
lawful deployment. Licensing Q11 is unresolved; no license grant is invented.
