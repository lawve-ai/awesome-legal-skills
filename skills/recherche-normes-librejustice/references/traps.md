# Traps: observed failure cases

Every trap below was hit for real while probing the tools on live questions (bilateral accords, ECHR, CESEDA history, Senegalese family law). The mechanics are general; the examples are the actual probes.

## 1. The full-referential drowning

« accord franco-algérien certificat de résidence », no filter: 111 917 hits, top results = military circulaires about « départ volontaire » allowances. « certificat de résidence algérien dix ans » : 93 555 hits, top result a school contest (« Dis-moi dix mots »). The accord was in the corpus all along, with all 33 articles, reachable instantly with `code: "Accord franco-algérien du 27 décembre 1968"` (23 on-target hits) or `jurisdiction: "INTL"`.

Rule: a filterless descriptive search over 2 million articles ranks circulaires and arrêtés above everything; its `total` counts OR matches and means nothing. Name the text (`code`) or the legal order (`jurisdiction`) before reading any result, and treat a result list that changes topic as an unfiltered query, not as absence.

## 2. Usual names that the `code` filter cannot resolve

`code: "Convention européenne des droits de l'homme"` errors, and the closest-match suggestion is an unrelated circulaire. The text exists under its official name: « Convention de sauvegarde des droits de l'homme et des libertés fondamentales ». `ceseda` errors with no usable suggestion; the full name « code de l'entrée et du séjour des étrangers et du droit d'asile » works.

Rule: filters resolve slugs and official names only. Acronyms and usual names belong in the query text (alias expansion covers them there), never in `code`. To pin the slug: read `facets.code` on a query that must hit the text, or reuse an inline `/norm/` link from a decision that cites it.

## 3. Foreign texts served in a single unversioned state

`code-de-la-famille-sen/40` returns `etat: VIGUEUR` with an empty `dateDebut` and no timeline: the corpus holds one curated version of each foreign text. Nothing warns you when the country amended the code after curation.

Rule: for foreign law, date the text yourself (enactment references are usually in the text or the title, « loi n° 61-55 du 23 juin 1961 »), check the `source` (official publisher vs aggregator), and for a contested point say explicitly which version and source you relied on. French and EU texts, by contrast, carry their full timeline: trust `date` there.

## 4. « Not found » read as « never existed »

Fetching a treaty article at a date before its avenant introduced it returns « law article or code not found ». The same error shape covers a wrong slug, a wrong key, and a date outside every version's window.

Rule: on not-found, re-fetch without `date` (full timeline), then consider a renumbering (rule below) or a wrong key, before concluding anything about the law's history.

## 5. The renumbering blind spot

CESEDA 2021: L. 313-11 (versions up to abrogation) and L. 423-23 (in force since 2021-08-26) are two different keys with two different timelines, both served. A search or fetch on the current number only misses every version, and every decision, that lived under the old number, and vice versa.

Rule: across a recodification (CESEDA 2021, code du travail 2008, code de commerce 2000…), work both numbers systematically: fetch both timelines, and run case-law searches (`legal_article`) under both keys.

## 6. One article, several hits

Ranked results can list the same article once per version (article 7 bis of the accord franco-algérien appeared twice). Counting hits overstates the corpus; presenting both looks like two provisions.

Rule: deduplicate by URL before counting or presenting.
