# Policy on using the report in proceedings (`exhibit` profile) — working version 1

> **Working text until Q12 is decided.** Translated from the normative text of PRD v1.0 ("Polityka użycia raportu w postępowaniu"). It does not confirm the legal status of the report, is not legal advice and is not consent to publication; assessing legal status and professional-ethics rules is for a human (Q12). The Polish text is the source; this translation is a working aid.

Policy version identifier: `exhibit-use/1-working`.

**A report in the `exhibit` profile may be attached to a procedural pleading as party material — not as an expert opinion, a finding of fact or a measure of probability.** The policy binds the user; the skill enforces its technical part (R17).

## Status of the report (working assessment, to be confirmed — Q12)

- **Civil proceedings.** A report signed by counsel is a private document (art. 245 Code of Civil Procedure): it proves that the signatory made the statement it contains. The court assesses it freely (art. 233 § 1). It is not an expert opinion (art. 278), and the ordering of hypotheses is not a factual presumption (art. 231).
- **Duty of truth.** Art. 3 requires explanations to be truthful and without concealment. Hence the ban on a silent excerpt: any omission of hypotheses or assessments must be explicit.
- **Criminal proceedings.** Defence counsel or an attorney may file the report as a document with an evidentiary motion; the authority assesses it freely (art. 7 Code of Criminal Procedure). A report produced for a prosecuting authority falls under the high-risk mode (R12); a report for a court is excluded in v1.

## Rules

1. **Source.** Only the output of `la.py report --profile exhibit` may be attached. The report hash goes into the reproduction package; a manual edit of the substantive content after rendering removes its `exhibit` status.
2. **Responsibility.** The report contains a statement of the responsible lawyer: they reviewed the bases of the conclusions, know the limits of the method and present the report as the party's position. The skill leaves the field empty; a human fills it.
3. **Method disclosure.** The header gives the name and version of the skill, the model, the host level, the date, the share of each evidence class and a sentence that the report contains no findings of fact or probabilities.
4. **Completeness.** The report covers the full set of hypotheses and the matrix for the question. An excerpt is allowed only if explicit: the number of omitted records, the `approved_set_hash` of the full analysis and the reason for omission (e.g. secrecy, third-party data).
5. **Statuses first.** `unstable` or `underdetermined` stands in the first paragraph. The ordering of hypotheses is not presented as a chance, credibility or degree of proof.
6. **Oversight.** The bases of the report have the class `human_file`, `human_signed` or (P1) `human_role`. A report with `human_via_agent` is not an attachment.
7. **Data and secrecy.** Before filing, the lawyer assesses whether quoted passages disclose third-party data or privileged information beyond need. The tool is the explicit excerpt of rule 4.
8. **Reproducibility.** A hash manifest is attached to the report, with a statement that the reproduction package (`.lacase` without originals + code version) will be made available at the request of the court or the opposing party. Originals — according to the procedural rules.
9. **Prohibitions.** The report is not presented as an expert opinion or a "private opinion"; it is not used as a tool of a court or arbitral tribunal; it is not combined with assessments of natural persons from outside the report.
10. **Versioning.** A change of policy = a new version of the `exhibit` template; the report states the version under which it was produced.

Obligations arising from the professional ethics rules of advocates and legal advisers on disclosing the use of AI tools in pleadings — Q12 (undecided).
