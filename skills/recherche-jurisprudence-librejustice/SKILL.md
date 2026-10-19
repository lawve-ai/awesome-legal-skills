---
name: recherche-jurisprudence
description: Search and cite French and European case law with the LibreJustice MCP tools. Use whenever the user asks about court decisions (Cour de cassation, Conseil d'État, cours d'appel, TJ/TA, CNDA, Conseil constitutionnel, CNIL, CEDH, CJUE), needs authorities for a brief, requête, référé or consultation, wants to check how courts rule on an issue, or needs counts of decisions on a point, even if they never mention LibreJustice.
---

# French and European case-law research (LibreJustice)

The user needs decisions whose reasoning states a precise proposition, applicable to the situation at hand, with a quotable excerpt.

The tools come from the LibreJustice MCP server; if `search_decisions` is missing from your session, connect it first: [references/install-mcp.md](references/install-mcp.md).

Five rules dominate everything:

1. **No decision appears in the answer (as support, contrary authority, analogy, or lead) unless you read its full text with `get_decision`.** An `aiSummary` or a `snippet` is not reading.
2. **Quotation marks quote a text you fetched, nothing else.** A hit's `aiSummary` is a machine paraphrase, never the court's words; a `snippet` is verbatim but torn from context. Every quoted string in the answer is copied character-for-character from a `get_decision` or `get_norm` text of this session: not opened means not quotable. A quotation is **one continuous span of one single text**, cuts marked « […] » : merging passages, or decisions, into one pair of quotation marks is fabrication, one source per quote, two passages are two quotes. A sentence reporting a decision in your own voice (« la cour retient que… » followed by your summary or a parenthesized list) is prose, never a quotation.
3. **Every decision named anywhere is a markdown link** to its `url` verbatim: `[CA Paris, 10 janv. 2024, n° 21/22203](https://librejustice.fr/decision/…)`. Never reconstruct or shorten a URL.
4. **The exact object of the question is a hard filter.** The most quotable sentence in the corpus routinely concerns a near-twin object one word apart: another mention, another délai, another clause. A decision whose decisive sentence names a different object is an analogy, never an authority. When the decisive sentence leaves the object unqualified (« l'heure », « ce délai », « cette mention »), its object is the one in the moyen it answers: find the party critique above it; the sentence inherits *that* object.
5. **`caseChronology` gives the decision's fate on review.** The step right above the current one, when its `linkToNext` is `APPEL_DE` or `POURVOI_CONTRE`, reviewed it, and its `solution` is that fate. Copy it into the answer. It overrides your own docket sweep: a sweep that found nothing while the chronology names a review means the sweep missed the arrêt, never that none exists.

A `get_decision` response may also carry `commentaires`, the court's own analysis served inline (`body`) and outbound links (`url`) to the rapporteur public's conclusions or related court documents. They are context and cite as commentary, never as the ruling: only the decision text quotes as the court's words.

## Protocol: run the steps in order

### 1. Frame

Pin down (ask when the request leaves them open): the proposition in one sentence; who demands what and what winning means; the legally relevant date; the target courts; the exclusions; the proximity axes that decide transposability. **A legal assertion inside the question (« c'est bien uniquement devant telle juridiction ? », « cet acte est nul, non ? ») is a claim to research, never an input**: the complement of the assertion gets its own step-2 sweeps (its own queries and filters, including the courts or outcomes the assertion excludes), and the answer's opening sentence states your verified verdict, never an echo of the premise. Follow-ups refine, they never reset: « d'autres ? » = new decisions, same bar; « tu peux vérifier ? » = reopen the source, never restate with more confidence.

### 2. Sweep: three passes, all mandatory

1. **One `solution`-filtered sweep per side, your first two `search_decisions` calls.** Map each direction of the holding to outcomes, then run the same query twice with opposite `solution` filters, e.g. `{"query": "convention de forfait en jours privée d'effet", "seat": ["CA.VERSAILLES"], "solution": ["SATISFACTION_TOTALE", "SATISFACTION_PARTIELLE"]}` then the same with `["REJET"]`. This is the only lever that separates the two directions of a line.
2. **The consecrated formula, quoted, in each phrasing.**
3. **A plain full-sentence query** (no quotes).

Engine facts:

- **Ranking is direction-blind**: semantic matching ignores negations, and summaries surface the side that won. Never read direction or absence in an order, an `aiSummary` or a `snippet`.
- **A lexical list (quotes/operators) is a set, not a ranking**: read it whole or partition it, never skim its top.
- **A lexical query is a conjunction**, and nothing recovers a miss: a quoted formula followed by context words returns zero unless one decision carries all of it. Quote the formula alone, or ask plainly.
- **A docket number goes in bare**: `21PA01295`, `19-20.682`, matched by exact key whatever the spelling, and served alone. A number or a case name inside a question (`387763 Czabaj délai raisonnable`, `Danthony vice de procédure`) keeps the question's `hits` and surfaces the designated decision in `pinned`: open it from there, never look for it in the ranking. `pinned` exists in `auto` only; a stated `mode` is served as stated.
- **The window is `limit` (max 20), no pagination.** Read the `date_lecture_year` facet on every sweep: a year newer than the newest hit you opened, with a nonzero count, is unswept. Re-run with `date_from`/`date_to` on that year before concluding.
- **`date_from` is the filter that silently hides a line's founding arrêt**, often decades old. Bound dates only when the question itself is time-bounded or a facet year needs re-sweeping, never by default.
- **A specialised contentieux has its own axis, and no query wording replaces it**: `legal_domain` for the subject (`PUBLIC_DROIT_ETRANGERS_NATIONALITE`, `SOCIAL_DROIT_TRAVAIL`, `COMMERCIAL_DROIT_ENTREPRISES_DIFFICULTE`…), where a root covers its leaves (`CIVIL` also returns `CIVIL_DROIT_LOCATIF`, `CIVIL_DROIT_PERSONNES_FAMILLE`), `office` for the single-judge courts (`JLD`, `JAF`, `JCP`, `JEX`…), `legal_article` for the decisions citing one article (`"code-civil|1240"`). Each cuts the corpus before ranking.
- **`seat` is the court unit itself, from its type down to its room**: a dotted path, one segment per level (`"CC"`, `"CC.SOCIALE"`, `"CA.PARIS"`, `"CA.PARIS.P5.C6"`). A path matches itself and everything under it, so `"CC.SOCIALE"` also returns the sections of that chamber and `"CA"` returns every cour d'appel. Take the paths from `facets.seat`, which serves the tree of the result set in hand: search, read the facet, then filter. Crossing a path with a period is how a line of one chamber is followed across a reorganisation.
- Filter tokens (« ca_paris », « REJET ») poison the query text: filters carry constraints, the query carries only words a court would write. After two queries with no new candidate, change one real axis or start opening.

### 3. Read everything you might cite

Open every hit of the target court that touches the issue. Open first, and always, every hit whose served `solution` sits on the user's side. Fewer than eight decisions opened by the end of this step means the research has not happened: go back to step 2 and change a real axis (court level, phrasing, dates) until eight full texts are read or the target courts' relevant hits are exhausted. Five verdicts per decision:

- **Who speaks.** Court's motifs, or a party's argument (« il soutient que… ») ? Cross-check the dispositif and who succombe: the loser's phrase is contrary authority under a favorable label. In a cassation arrêt the moyen (« alors que… ») is the loser's text even when it reads like a holding; the Cour speaks in « Mais attendu » / « Réponse de la Cour », and « par les motifs reproduits au moyen » attributes those motifs to the court below. Quote each voice separately: one clause of the moyen imported into the Cour's motif turns the quote into fabrication.
- **Exact object.** Near-twins one word apart have opposite regimes (forclusion/prescription, faute grave/lourde, nullité relative/absolue), and snippets truncate, summaries smooth over, exactly the deciding word.
- **Appellate fate** (dominant rule 5). `INFIRMATION` kills the decision as support. `CONFIRMATION` = open that arrêt and cite the pair; the arrêt holds what the judgment held, never the opposite line's direction. No review in `caseChronology` = run the judgment's docket number, bare and unquoted, filtered to the appellate court: a number is matched by exact key, and quoting it drops the fallback. **A sweep hit is the same case only if its « Décision déférée » header names your judgment, same court, same date** : RG numbers collide across courts, and a hit from another ressort or another date is noise, never the fate. No review in the chronology and no sweep = « aucun recours lié dans le corpus ».
- **Legal basis.** Decision texts carry inline `/norm/` links; open them with `get_norm` at the facts' date. A failed tool call (bad URL format, unknown code) is retried with the corrected argument, never silently dropped: an article the question turns on that you never managed to read voids every claim about it.
- **The quotable sentence.** While the text is in front of you, copy the exact sentence(s) of the motifs you would quote in a brief. The writing stage may only put between quotation marks strings collected this way.

### 4. Map the line

Re-run the winning query with `sort: "date_desc"`, **once per direction, with that side's `solution` filter, per target court**, and read the most recent decisions of each. When a court ruled both ways, the deliverable is a dated timeline, never a flat « court X says P »: either side of a flip, presented alone, misleads. A hit newer than every decision the answer names, seen in *any* list this session, is either opened and cited or excluded for a stated reason, never silently dropped.

### 5. Absence claims and counts

« No decision of court X states P » is falsifiable with one citation. Before writing it: exact formula (both phrasings) + a descriptive query under the court filter; a `solution`-filtered sweep on P's outcomes; `date_from` widened; facets read. Last: re-scan the hits you did NOT open across every list of the session: one unopened hit whose `solution` sits on P's side voids the claim until opened. Counts: define the corpus; keep raw hits, deduplicated decisions and verified holdings apart. A counting table is built from the facets of **one named query per column**: never merge facets from different queries into one series. `total` and the facets count every decision matched under the current filters, not the page served: neither a count of the corpus nor a count of the hits. Two things distort that number. A multi-word query matches on ANY of its tokens, so its total counts whatever carries one word of it: it counts something only under a quoted formula, or under filters (court, dates, solution) narrow enough to define the corpus. And a decision found by meaning alone is counted only inside the window served, so the total of a purely descriptive query is a floor. A yearly series that starts or jumps abruptly usually marks the edge of source coverage, not the birth of the contentieux: say so instead of narrating the jump.

## The answer

The shape is the user's: the format they asked for, or the one their earlier answers were in. What follows is what the answer has to carry, never how it looks. None of it is wording to reproduce: these are things to say, said in the language the user writes in, under whatever headings that language and that format call for.

- **Give the verdict first**, then, per target court, the most recent decision in *each* direction, named and dated. Naming a court's latest word requires having run the `date_desc` + `solution` query of step 4 for that court and that direction.
- **Say the same five things of every authority**: cite it and link it, quote it, say what its decisive sentence was about, say how it fared on appeal, say where it stops. The quotation is one collected at read time (the quotable sentence of step 3); when none was collected for that decision, write plain prose with NO quotation marks, marked « (résumé, citation non collectée) ». A passage from the exposé of a party's moyens is that party's argument, not the court's.
- **Say how a decision fared on appeal in closed words**: the fate read in `caseChronology` (« infirmé par [arrêt lié] », « confirmé par [arrêt lié] », and the pair cites together), or, when the chronology names no review, « aucun recours lié dans le corpus ». The words « balayé » / « vérifié » may appear only when the docket-number query is in this session's searches; any other wording (« à vérifier », « définitif »…) is a failed check.
- **Say what opposing counsel will plead, per target court**: the recent contrary line, infirmations, reversals, dated. A first-instance court has its own contrary decisions, and calling its line « constante » while the opposite-`solution` sweep never ran for it is the check that fails most.
- **Leave a thin side thin**: when a court offers a single decision, present it alone and say so.
- **Give the perimeter, from two lists kept as you go.** One entry per `search_decisions` call of this session: the query, the filters (`solution`, dates, courts), the sort, the hits opened. One entry per `get_decision`, in call order: the linked citation. Append the entry when the call is sent, then paste both lists into the answer. An entry for a call that never ran, or a filter listed but never sent, is fabrication; a search that ran but is missing (including a failed one) is a hole in the audit trail. Every decision link anywhere else in the answer copies an entry of the list of opened decisions, and no other count of decisions read is ever stated. A direction of the holding with no `solution`-filtered entry is unresearched: run it now, or write « non recherché » next to the list, a sentence always available and always true.

Cite only decisions returned by the tools.

## Final check, fix rather than flag

- Every decision link in the answer has its entry in the list of opened decisions; a link without one is opened now (entry added) or deleted, along with every claim resting on it.
- Every quoted string, searched **as one continuous block** in this session's `get_decision` / `get_norm` texts. Found only in separate pieces, it is a splice: re-cut it into one quote per source, « […] » for internal cuts. Found only in a hit's `aiSummary` or `snippet`, or nowhere: rewritten from the fetched text, or unquoted. Then who speaks: the motifs of the decision it is attributed to, not a party's argument or moyen, not another decision.
- How each decision fared on appeal is verbatim one of two wordings: the fate read in `caseChronology`, or « aucun recours lié dans le corpus ». Re-read each cited decision's chronology now. « balayé » / « vérifié » survives only when this session's searches carry that docket number, and any other wording (« définitif », « à vérifier ») is rewritten to the default formula.
- Every perimeter entry pointed at the call of this session it copies: delete what you cannot point at, add the searches you ran and did not list.
- No decision whose decisive sentence names another object left standing as an authority.
- Weight adjectives (« isolé », « constant ») consistent with the decisions the answer itself lists; the answer states which way the most recent decisions of each target court go; an infirmed judgment never stands as support; every « no decision » claim earned under step 5.

## Statutes

Quick lookups only: anything deeper (treaties, EU law, versions across recodifications) is the recherche-normes skill's job. `get_norm` returns an article as it stood on a given date: pass `date` and say which version you quote.
