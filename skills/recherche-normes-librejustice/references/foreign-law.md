# Foreign and international law in French litigation

Why it matters: nationality, filiation, civil status, family and personal-status disputes are routinely governed by foreign law under French conflict-of-laws rules, and residence litigation by bilateral accords. The court applies the foreign or treaty rule: the brief that quotes it exactly, dated and sourced, wins the point.

## Working the corpus

- **Find a country's texts**: `search_norms` with `jurisdiction` set to the ISO code (`SN`, `DZ`, `MA`, `CM`, `CD`…), descriptive French query. Slugs carry a country suffix (`code-de-la-famille-sen`). 59 countries are covered, strongest on family, nationality and civil-status law of francophone Africa and the Maghreb, plus BE/CH/DE/LU codes from their official publishers.
- **Find a treaty**: `jurisdiction: "INTL"` plus a descriptive query, or the exact official name in `code`. Bilateral accords often live under the décret that published them: searching « décret portant publication accord [pays] [matière] » in the query text works. Amended accords (avenants) carry the amendments as versions: pass `date` to get the state applicable to your case.
- **From a decision**: French decisions applying foreign law usually quote or reproduce it; the decision text carries inline `/norm/` links when the cited text is in the corpus. The reverse chain finds the case law applying a foreign provision: `search_decisions` + `legal_instrument: ["code-de-la-famille-sen"]` or `legal_article: ["…|40"]`.

## When the corpus does not have the text

Do not improvise from memory. In order:

1. Search the decisions: courts ruling on the point often reproduce the foreign provision in their motifs. Quote it as « tel que cité par [decision, linked] », which is also how the court will receive it.
2. Go outside: the vetted external sources, their reflex chain and their own pitfalls are in [external-sources.md](external-sources.md). Say plainly that the text comes from outside the referential and from which source.

## How the French judge receives foreign law

Points of method the answer should reflect (and verify in current case law with the recherche-jurisprudence skill before building on a formulation):

- Since the twin arrêts of 28 June 2005, the French judge who declares a foreign law applicable must seek its content (of their own motion or at a party's request), with the parties' cooperation and personally if needed, and give the dispute a solution conforming to the foreign positive law. A claim can no longer be dismissed just because a party failed to prove the foreign law. Where the content genuinely cannot be established, French law applies subsidiarily.
- The Cour de cassation controls only dénaturation of the foreign law, not its interpretation, which makes the *documents* placed before the judge decisive.
- The **certificat de coutume** (a written consultation on the foreign rule by any qualified jurist, no authority holds a monopoly) is private evidence, weighed freely; competing certificats de complaisance are common. A dated, sourced quotation of the foreign text is often stronger, and it is exactly what this corpus or the external sources give you.
- For foreign **civil-status acts**, article 47 of the Code civil presumes their probative force, rebuttable when other documents, external data or the act itself establish irregularity, falsification or untruth. The foreign law governing the act's form (what a birth certificate must state, in which delay) is precisely what the corpus's foreign civil-status codes give you. Add the formal layer: légalisation or apostille conditions the act's effect in France, and an act drawn under a foreign judgment (jugement supplétif) is inseparable from that judgment, whose international regularity is controlled. The case law on which defects are « substantial » lives in the recherche-jurisprudence skill.

## Hierarchy and lex specialis

- A bilateral accord derogates from the general statute in its scope: the accord franco-algérien du 27 décembre 1968 governs Algerian nationals' residence, and CESEDA provisions apply to them only where the accord is silent or refers back. Check the accord first, the code second.
- EU law primes national law in its field; the Convention de sauvegarde primes statute. When quoting a national provision in a field occupied by EU law, fetch the directive or regulation too.
- Older bilateral conventions (établissement, circulation, sécurité sociale) still bite: when the person is a national of a country with a post-independence convention with France, search INTL for that country before concluding from the code alone.
