---
name: jev-question-translator
description: >-
  Turns a legal question, a set of draft questions, or source material such as a statute,
  jury instruction, rubric, contract checklist, or coding manual into a battery of narrow
  questions that TypeSafe's Jev, a fast classifier that returns probabilities rather than
  prose, can answer reliably across many documents. The skill breaks
  conclusions such as negligence, felony murder, or standing into element-level questions,
  writes the governing rule into each question, and delivers the questions alone, in Jev's
  request format or in plain English. Built for legal work that asks the same questions of
  many texts: coding statutes across jurisdictions, coding opinions or case files for
  empirical research, checking contracts against a review checklist, screening intake
  narratives, and grading student work against a rubric. Use when asked to write Jev questions,
  build a classifier for legal documents, or turn a legal test into yes-or-no questions. Running the questions requires Jev access; writing
  them does not.
metadata:
  author: "Seth J. Chandler"
  author_link: "https://legaled.ai"
  license: "Apache-2.0"
  version: "2026-09-27"
  jurisdiction: "All"
  language: "English"
  category: "legal-research"
  requires: "Nothing to write the questions. Running them requires access to Jev through TypeSafe's API or a provider that offers it, such as OpenRouter."
---

# Jev Question Translator

Jev is TypeSafe's first System One model. It receives a `state` (text or JSON) and a set of named questions, and returns one typed answer per question:

- **Noul**: the probability that a yes/no proposition is true. There is no separate confidence value.
- **Choice**: one option from a set of up to 255, with a probability for every option and a confidence value.
- **Score**: a position on an ordered scale of 2 to 10 described levels, with a probability for every level and a confidence value.

Jev does not generate text or explain its answers. All questions in a request see the same state and are answered independently; no question can see another question's answer. Adding questions to a request changes response time very little, because they run in parallel.

This skill takes what the user wants to know and produces questions Jev can answer reliably. Jev makes the individual judgments; code does the arithmetic, combines the judgments, and reaches the final conclusion. The procedure below designs the questions with that division in mind, but the skill delivers only the questions.

## Why legal professionals would use this

A great deal of legal work consists of asking the same questions of many documents. A
researcher coding fifty state statutes asks, for each statute, whether it covers a given
activity, who enforces it, and what penalty it sets. A scholar studying appellate decisions
asks, for each opinion, which test the court applied and whether it found each element
satisfied. A lawyer reviewing a portfolio of leases asks, for each lease, whether it contains
an assignment clause and whether that clause matches the client's preferred position. A
professor grading eighty exams asks, for each answer, whether the student identified the
controlling statute and applied each element. The questions are fixed; only the document
changes.

Jev is built for that shape of work. It receives a document and a list of typed questions and
returns, for each question, a probability that the answer is yes, a choice among options
the user defines, or a position on a scale the user describes. It does not write prose or
explain itself. TypeSafe designs it to be fast, inexpensive per question, and consistent, so
that the same document and question produce the same answer on every run. For legal work
these properties matter in concrete ways:

- **The answers are data.** Each answer is a number or a label that goes straight into a
  spreadsheet or a statistical package. A fifty-state survey or a coded set of opinions comes
  out as a table rather than as fifty paragraphs someone must read and re-code.
- **The analysis is visible element by element.** When a conclusion is built from separate
  answers about each element, a reviewer can see which element failed, not just the
  conclusion. That is the form in which lawyers already check one another's work.
- **Uncertainty is reported.** A probability near the middle marks a document a person should
  read. The lawyer can send those documents to human review and accept the clear ones, instead
  of reviewing everything or trusting everything.
- **Consistency across documents.** Every document is judged by the same questions in the same
  words. In grading and in empirical coding, that consistency is itself a requirement.

Jev answers narrow, literal questions well. It answers broad legal conclusions poorly, and it
does not know the law of any jurisdiction. "Was the defendant negligent?" asks it to supply a
body of doctrine and apply it in several steps, which it cannot do reliably. "Does the
narrative state that the driver was looking at a phone while the car was moving?" is a
question it can answer. Turning the first kind of question into the second is the familiar
lawyer's task of breaking a doctrine into its elements, factors, and definitions, together with
rules about wording that are specific to Jev. This skill performs that translation.

### Legal uses

- **Legal epidemiology and policy surveillance.** Code the same features across statutes or
  regulations from many jurisdictions. Each feature becomes a question, with a "not addressed"
  option because many statutes are silent on a given point. The coded results can be compared
  across jurisdictions and over time.
- **Empirical legal research.** Code judicial opinions, dockets, or case files: the procedural
  posture, the test applied, whether each element was found, the outcome. Hand-code a sample
  to measure Jev's agreement with human coders before relying on the rest.
- **Contract and document review against a checklist.** Each checklist item becomes a
  question; a playbook position can be written into the question so that Jev compares the
  clause with it. Portfolios of leases, NDAs, or vendor agreements can be screened for
  missing or non-standard provisions, with uncertain documents routed to a lawyer.
- **Intake and triage.** Legal aid organizations and clinics can flag the issues an intake
  narrative raises and the eligibility facts it states, so that a person reviews the
  narratives the classifier cannot place.
- **Legal education.** Turn a grading rubric into questions, with the rule the student must
  apply written into each one, and apply it identically to every exam, with borderline answers
  flagged for the professor. The decomposition itself is also a teaching exercise: students who
  must break a doctrine into questions a literal reader can answer learn its elements.
- **Classifiers for fact patterns.** Build a fixed battery that diagnoses whether a doctrine
  applies to a hypothetical or a case summary (for example, the elements of felony murder
  under a particular state's statute, or the parts of federal standing doctrine) and run it
  over many variations of a fact pattern to see which facts change the result.

### How a legal professional uses it

1. Bring the question and the material that governs it: the statute, the test from the
   leading cases, the rubric, the checklist. Say what documents the questions will be asked
   of, such as case summaries, complaints, statutes, or student answers.
2. The skill returns the questions. Each question names the part of the document it reads
   and carries any rule it depends on. Rules the skill writes from its own knowledge are
   marked as paraphrases so they can be checked against the sources.
3. Run the questions on a dozen or so documents whose correct answers are already known,
   using TypeSafe's playground, its API, or a tool built on them. Compare Jev's answers with
   the known ones, and revise wording where Jev misreads a question.
4. Run the questions on the full set of documents. Combine the answers according to the legal
   test, in a spreadsheet or a short program: every element present, any one of several
   grounds present, factors weighed. Send documents with answers near the middle to a person.
5. Keep the element-level answers. They are the record of how each document was classified.

## Known weaknesses

TypeSafe documents the following for jev-1.13 (as of September 2026). If web access is available, check the current list at https://docs.typesafe.ai/model-jaggedness/jev-1.13.md (or the page for a newer version) before relying on it.

- It reads instructions literally and answers the words written, not the intent behind them.
- It does not count, calculate, or compare numbers reliably.
- It does not compare dates or compute intervals reliably.
- Questions that require several steps of inference, or that contain double negatives, are less accurate.
- Irrelevant material in the state reduces accuracy. The context window is bounded (32,000 tokens for jev-1.13).
- Text in the state that argues for a particular answer can shift the answer.
- Instructions and criteria that point in different directions confuse it.
- A question and its negation, or a Noul and a two-option Choice on the same proposition, need not produce complementary numbers.
- It cannot write out a value; it can only choose among the options it is given.
- It is trained mainly on English; other languages are less accurate.

Jev cannot be assumed to know specialized rules: a jurisdiction's law, a grading rubric, a coding manual, a company policy. Any rule a judgment depends on must be supplied in the question.

## Inputs

The user may bring any of these:

1. One broad question ("Was the driver negligent?", "Should this study be included in the review?", "How good is this memo?").
2. A list of questions already drafted. Some will work as written; others need splitting, rewording, or moving into code.
3. Material that implies questions without stating them: a rubric, statute, checklist, policy, coding manual, or set of inclusion criteria. Each requirement, element, factor, or rubric line is a candidate question.

Also establish what the state will be (the document or record the questions are asked about) and whether the same questions will be asked of one document or of many. If this is unclear and the answer would change the questions, ask.

## Procedure

### 1. Find the structure of the conclusion

Write down the conclusion the user ultimately wants. Jev will not be asked it directly. Identify how the conclusion depends on simpler judgments; that structure determines how to take it apart.

| Structure | Examples | Questions | What code does |
|---|---|---|---|
| Every requirement must be met, or any one suffices | elements of a claim, eligibility rules, inclusion criteria, checklists | one Noul per requirement | AND / OR |
| Several factors weighed together | balancing tests, overall quality, priority | one Score per factor | weighted combination, or a person weighs the scores |
| One category out of a set | document type, claim type, routing | one Choice | branch on the answer |
| Several labels that can all apply | issues a document raises, defects present | one Noul per label | collect the labels whose values are high enough |
| Degree | severity, thoroughness, clarity | one Score | threshold or rank |
| A specific value | a date, an amount, a party's name, a citation | a Choice among candidates found by code, or Choices over the value's parts (month, day, year) | assemble and validate the value |
| A count or total | number of errors, number of qualifying items | one Noul per item | add |
| A numeric or time threshold | more than ten thousand dollars, within 30 days | extract the value as above | compare |
| A relation between two parts of the state | does the reply answer the question; does the source support the claim | one question naming both parts | use directly |
| A deep taxonomy | subject-matter classification | one Choice per level, in successive requests | the answer at each level determines the options offered at the next |

Most real conclusions combine several of these structures. Apply the table again to each piece: an element of a claim may itself be a weighing test, and a factor may depend on a value that must first be extracted.

**The unit of analysis.** Identify what the rule is applied to: each plaintiff, each defendant, each claim, each form of relief, each rubric line, each statutory provision, each paragraph. A single document often contains several such units: a complaint with three plaintiffs and three forms of relief, a vignette with two defendants, an essay with ten paragraphs. A question asked about several units at once has no single correct answer, and Jev returns a middling value that reflects the mixture rather than uncertainty about any one unit. When a document can contain more than one of a unit, do one of the following:

- Make the unit its own state field, with a name that says the questions are asked about one unit at a time (`plaintiff`, `defendant`, `paragraph`), so that the user runs the questions once per unit.
- Write one question per unit, naming the unit in the question ("If `plaintiff` asks for an injunction, would that injunction...").

Do not write a question about "the relief," "the plaintiffs," or "the claims" when the rule applies to each separately.

### 2. Split until each question meets these conditions

- **It asks about one proposition or one dimension.** "Was the defendant speeding and distracted?" is two questions. A Score whose levels mix punctuality and skill is two Scores.
- **It can be answered from the state plus whatever the question itself supplies.** If a knowledgeable person would need a rule or definition the request does not contain, add it (step 4).
- **A person who knows the field could answer it almost immediately** after reading the relevant part of the state. If answering requires first working out an intermediate result, that result is a separate question or a computation in code.
- **It does not depend on another question's answer** (step 3).
- **It contains no counting, arithmetic, or comparison of dates or amounts.**
- **Its possible answers can be listed in advance.** If they cannot, the task needs a generative model.

Stop splitting once a question meets these conditions. A relational question such as "Does `source.passage` support the proposition in `brief.sentence`?" is one judgment. Splitting it into "Does the passage mention X?" and "Does the brief mention X?" discards the relation that was being judged. Each question should contain one judgment, and a single judgment may require reading two parts of the state together.

**Conclusion words.** Terms such as negligent, reasonable, material, adequate, valid, compliant, or well-organized stand for a body of rules. Either replace the term with the observable conditions it stands for, or keep it and supply its definition in the question.

**Persuasive text in the state.** When the state is a brief, a complaint, a sales pitch, or anything else written to persuade, ask what the document asserts or what support it offers ("Does `complaint` allege that the defendant was using a phone?"), not whether its conclusions are correct. Persuasive text can move Jev's answer toward the writer's position.

### 3. Handle dependencies between questions

A question cannot say "if the answer to the previous question was yes." Use one of these instead, in this order of preference:

1. **Put the premise in the question.** "If the customer is asking to return an item, what reason do they give?" Code uses the answer only when the premise holds. Answers that go unused cost little.
2. **Ask once for each possible value of the earlier answer.** If the applicable standard could be any of three, ask whether the conduct met each standard, each defined in its own question, and let code use the one that matches the answer to the question about which standard applies.
3. **Plan a second set of questions** only when the later question cannot be written until the earlier answer is known: the earlier answer decides what goes into the state, which document to retrieve, or which options to offer.

### 4. Place the context

- Questions refer to parts of the state by backticked field name or path, such as `facts` or `answer.paragraphs[2]`. Use field names that make plain what each field must contain, because those names are how the user learns what state to supply.
- A rule or definition that a question depends on goes in that question's `instructions` as an object, such as `{"question": "...", "rule": "..."}`.
- Begin each supplied rule with its source, such as a statute section. When you write a rule from your own knowledge rather than from material the user provided, say in the rule text that it is a paraphrase, so the user can check it.
- Refer only to the parts of the state a question needs. For long sources, the relevant passages should be selected before the substantive questions are asked, either in code or with one relevance Noul per passage.

### 5. Write each question

For every type:

- Put the complete question in `instructions`. Question IDs are not sent to the model.
- Read the finished question literally, as a stranger would. If the literal meaning differs from the intended meaning, rewrite it.
- Keep `instructions` and `criteria` consistent with each other.
- When the same questions will be asked of many documents, word them so they make sense for every document, and allow for documents that do not address the matter at all.

Noul:

- Phrase it so that yes is the condition of interest. Ask "Does the message contain personal data?", not "Is the message free of personal data?"
- Make the line between yes and no sharp. Words such as "any," "explicitly," and "states that" help. When the line is subtle, add `criteria` with `true` and `false` descriptions.
- Do not use a Noul to measure degree. A value near 0.5 means yes and no are about equally likely, not that the quality is present to a medium extent.

Choice:

- Write descriptions that distinguish each option from the others; the option names and descriptions are both sent to the model. Use `null` for a description when the option name is self-explanatory.
- Include a no-match option (`other`, `none`, `not addressed`, `not stated`) whenever the list might not cover every input.
- Give the full list of options rather than a shortlist.
- When two options are easily confused, write each description as an object with the same fields, such as `what`, `not_for`, and `examples`.
- Use a Choice only when exactly one option applies. When several can apply, use one Noul per option.

Score:

- Each level describes a situation that could be recognized in the state ("frustrated but civil"), not a degree ("somewhat frustrated").
- The model judges each level on its own and does not see level numbers or neighbouring levels, so descriptions such as "worse than the previous level" or bare numbers do not work.
- One dimension per Score. If code must treat a rare extreme case differently, give it its own level.
- Use as many levels as can be described distinctly, from 2 to 10.

### 6. Keep only questions whose answers will be used

For each question, know which conclusion its answer feeds and how it combines with other answers. Drop any question whose answer no one will use: code, a reviewer, or a study that records the answers as data. The number of questions is whatever the decomposition produces.

### 7. Leave out what Jev should not handle

Parts of the user's original question that belong to code (arithmetic, dates, counts, lookups, the rule that combines the answers), to a generative model (writing text, extracting free-form values), or to a person (judgments whose governing rule is unavailable or disputed) get no question. Where one of those parts depends on a judgment Jev can make, such as selecting which of several candidate amounts is the price, write the question for that judgment.

## Output

Deliver the questions and nothing else. Do not add an introduction, a description of the state, a plan for combining the answers, a list of what was left out, threshold values, or commentary. The analysis in the procedure shapes the questions but is not reported.

By default, give the questions as one JSON object in the form of the `questions` field of a System One request: each key is a question ID, and each value is the question. For example:

```json
{
  "phone_in_use": {
    "type": "noul",
    "instructions": "Does `facts` state that the driver was holding or looking at a phone while the car was moving?",
    "criteria": {
      "true": "The facts say the driver held, looked at, or operated a phone while driving",
      "false": "The facts do not mention phone use while driving, or say the phone was not in use"
    }
  },
  "harm_type": {
    "type": "choice",
    "instructions": "What kind of harm to the plaintiff does `facts` describe?",
    "criteria": {
      "bodily_injury": "Physical injury to the plaintiff's body",
      "property_damage": "Damage to the plaintiff's property, with no bodily injury",
      "economic_loss_only": "Financial loss with no bodily injury or property damage",
      "none_described": "No harm to the plaintiff is described"
    }
  },
  "injury_severity": {
    "type": "score",
    "instructions": "How serious is the plaintiff's physical injury as described in `facts`?",
    "criteria": [
      "No physical injury is described",
      "Minor injury needing no more than first aid",
      "Injury requiring medical treatment but not hospital admission",
      "Injury requiring hospital admission or causing lasting impairment"
    ]
  }
}
```

When the user asks for plain English (for example, to feed a separate converter), give a numbered list of the questions, with answer options shown only for Choice and Score items, and no type labels, section introductions, or commentary.

## Checks before delivering

- Does any question join two propositions with "and," "or," or "but"?
- Does any question depend on another question's answer?
- Does any question ask about several units that the rule treats separately, such as several plaintiffs or several forms of relief?
- Does any question require counting, arithmetic, or comparing dates or amounts?
- Does any question use a conclusion word without supplying its definition?
- Is any Noul phrased so that yes means something is absent?
- Do any Choice options overlap, and is a no-match option present where one is needed?
- Does any Score mix dimensions or describe degrees rather than situations?
- Do the questions refer only to state fields the user's documents will supply, with names that make their contents plain?
- Will every answer be used?
- Does the output contain anything besides the questions?

## Examples of decomposition

These sketches show the procedure applied to different kinds of input. They illustrate the reasoning and should not be copied as templates.

**Negligence (requirements plus a dependency).** "Was the driver negligent?" becomes separate questions for each element. Whether there was a breach depends on which standard applies, so ask a Choice for the applicable standard, with each candidate standard defined in the question, and a Noul for whether the described conduct met each candidate standard; code uses the Noul that matches the Choice. Causation and harm get their own questions, the harm question as a Choice with a "none described" option.

**Multi-factor test (weighing).** A four-factor fair use analysis becomes four Scores, one per factor, each with levels written as recognizable situations. For the first factor, the levels might run from "reproduces the work for the same purpose with nothing added" to "uses the work as the object of commentary or criticism."

**Grading against a rubric (many documents, many questions).** Each rubric line becomes a question with the rule the student must apply written into it, because Jev does not know the rule. "Identifies the controlling statute" is a Noul naming the statute. "Quality of analysis" is split into Scores for separate dimensions. "Number of paragraphs that state a conclusion without supporting reasons" is one Noul per paragraph, which code adds up. A detailed rubric can produce dozens of questions.

**Coding statutes across jurisdictions.** The same set of questions is asked of each statute, with the statute text as the state. Choices include a "not addressed" option, because many statutes say nothing on a given point. Penalty amounts and deadlines are found as candidates in code and selected by Choice.

**Screening studies for a systematic review.** Each inclusion criterion (population, intervention, comparison, outcome, study design) becomes a Noul with its definition supplied.

## Jurisdiction

The method is not tied to any jurisdiction. The law each question relies on is whatever rule
the user supplies or the skill writes into the question, and the examples in this file draw
on United States law. A battery written for one jurisdiction's statute should not be used for
another's without rewriting the rules in its questions.

## Limitations and risks

**This is not legal advice.** The skill produces questions, and Jev's answers are inputs to a
lawyer's analysis, not conclusions. A classification that a doctrine applies or does not apply
to a document must be checked by someone qualified to make that judgment before anyone relies
on it.

**Rules written into the questions must be verified.** When the user supplies the statute,
test, or rubric, the questions carry it. When the skill writes a rule from its own knowledge,
it marks the rule as a paraphrase; those paraphrases can be wrong, incomplete, or out of date,
and must be checked against current authority in the relevant jurisdiction.

**Jev makes errors even on well-written questions.** In testing, Jev occasionally answered a
clearly worded question contrary to the document, answered questions that began "if..." as
though the condition were true when it was false, and returned middling values when a
question covered several parties or forms of relief at once. The skill's design reduces these
errors but cannot eliminate them. Test every battery on documents with known answers before
relying on it, and have code use a conditional question's answer only when its condition
holds.

**Client confidentiality.** Running the questions sends each document to TypeSafe, and
possibly to an intermediary such as OpenRouter. Before sending client documents, confidential
information, or privileged material, check the provider's data-handling terms, the client's
instructions, and the applicable professional-conduct rules; ABA Model Rule 1.6(c) requires
reasonable efforts to prevent unauthorized disclosure of client information. Remove
identifying details where the task allows it.

**The description of Jev is a snapshot.** The list of known weaknesses summarizes TypeSafe's
published documentation for jev-1.13 as of September 2026. Later versions may behave
differently; the skill directs the model to check the current list when web access is
available.

**The skill writes questions only.** It does not set thresholds, combine the answers, or
compute a final conclusion. Thresholds should come from testing on the user's own documents,
and the rule that combines the answers belongs in the user's spreadsheet or code.

**English.** Jev is trained mainly on English, and the skill's guidance assumes English
documents.

This skill contains no executable code.
