# Supreme Court Oral Argument Analyzer

## Overview

Supreme Court Oral Argument Analyzer helps lawyers, legal educators, and researchers understand an argument without first reading its entire transcript. It produces a structured report explaining the case, each advocate's requested rule and concessions, the authorities discussed, and the issues that occupied the bench. It is designed for a legal reader who may be unfamiliar with the subject area.

The workflow reads the complete available transcript, attaches pinpoints to significant exchanges, and separates what speakers said from the analyst's inferences. It assesses each justice's apparent concerns and possible leanings while allowing an honest “unclear.” It distinguishes potential judgments from rationales and considers narrow procedural routes alongside merits outcomes. Optional research checks authorities, and an optional text-processing script counts speaking turns and approximate words by argument section.

The result is a nine-section analysis with authorities and justice tables, an assessment of possible dispositions, and concrete observations about advocacy. Document output depends on the host's file-generation capabilities; otherwise the report appears in chat. A readable transcript is sufficient for substantive analysis, with missing information identified. Judicial questions are not votes, the tally is not a prediction model, and the report requires professional review before reliance.

## Inputs and outputs

Provide an official transcript PDF, readable extracted text, or an identified unofficial transcript. A case name or docket number also works if the host can retrieve the correct transcript. Briefs and the opinion below are useful but optional. An excerpt yields a limited analysis, not a purported account of the full argument.

The report covers: summary; case background; advocates' positions; authorities; the bench's focus; individual justices; possible disposition; advocacy; and limits. It normally targets about 1,500 words plus tables, adjusted for complexity. Authorities are checked only when suitable research access exists, and verification status is disclosed.

## Example requests

- “Analyze this Supreme Court argument for a lawyer unfamiliar with the case. Include transcript pinpoints and identify uncertain judicial leanings.”
- “Prepare an argument report from this transcript alone. Flag authorities you cannot verify and distinguish each amicus's position.”
- “Assess the narrowest possible dispositions discussed at argument. Separate evidence about the judgment from evidence about the rationale.”

## Optional tally

Python 3 can run `scripts/tally.py` on UTF-8 extracted text preserving official-style proceedings and argument headings. Run with `--help` first. PDF extraction is a separate host capability. The script reads text and prints results only. It counts speaking turns and approximate words, including administrative remarks; it cannot identify votes, count substantive questions, or establish nonparticipation. Always verify its sections and speakers against the transcript. Qualitative analysis remains available without it.

## Use and distribution

Load SKILL.md and keep its bundled files accessible in a host that supports skills. Merely attaching a file in one chat does not establish persistent installation. Hosts differ in research, execution, document creation, and skill installation; confirm those capabilities before relying on them.

United States; English. Original work by Seth J. Chandler. Apache-2.0; see LICENSE and NOTICE. Research assistance, not legal advice. No sample case report or private transcript is included in this distribution.
