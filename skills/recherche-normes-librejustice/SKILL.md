---
name: recherche-normes
description: Find and quote legal texts and administrative guidance with the LibreJustice MCP tools, covering French codes at any date, EU law, treaties and bilateral accords, foreign codes (59 countries), collective agreements, BOFiP and circulaires. Use whenever the user asks what a text says or said at a given date, which version or which text applies to a situation, needs the exact wording of a provision for a brief, or works with foreign or international law in French litigation, even if they never mention LibreJustice.
---

# Statutory research (LibreJustice)

The user needs the exact provision, in the version in force at the legally relevant date, linked and quoted verbatim. A paraphrase from memory is not a deliverable: models misremember article numbers and miss amendments; every quoted provision comes from `get_norm`.

The referential goes far beyond French codes: EU law, international treaties (including bilateral accords), the codes of 59 foreign countries, collective agreements, BOFiP. Map and counts: [references/corpus.md](references/corpus.md). Observed failure modes: [references/traps.md](references/traps.md). Foreign and international law: [references/foreign-law.md](references/foreign-law.md).

The tools come from the LibreJustice MCP server; if `get_norm` is missing from your session, connect it first: [references/install-mcp.md](references/install-mcp.md).

## Iron rules

1. **Never quote a provision from memory.** Fetch it with `get_norm`, quote verbatim, link the article (`[Article 7 bis de l'Accord franco-algérien du 27 décembre 1968](https://librejustice.fr/norm/…)`, the `url` verbatim).
2. **Date before text.** Identify the legally relevant date first (the attacked decision, the facts, the contract), pass it as `date` (both `get_norm` and `search_norms` take it; the search then matches the versions valid at that date), and say which version you quote (its validity window is in the response). The version in force today is the wrong one for most litigation.
3. **Name texts by their official name.** The `code` filter resolves slugs and exact official names, not usual names: « CEDH » and « Convention européenne des droits de l'homme » fail where « Convention de sauvegarde des droits de l'homme et des libertés fondamentales » works. When unsure, recover the slug from `facets.code` or from an inline `/norm/` link in a decision.

A `get_norm` response may also carry `commentaires`, doctrine anchored on the article, served inline (`body`) or as outbound links (`url`). Context, never the norm: only the article text quotes as the provision.

## Three access paths, cheapest first

1. **Text and article known**: compose the URL directly, `https://librejustice.fr/norm/{juris}/{code-slug}/{article-key}` (`fr/code-civil`/`47`, `sn/code-de-la-famille`/`40`, `intl/accord-franco-algerien-du-27-decembre-1968`/`7-bis`; `{juris}` is the enacting jurisdiction in lowercase, `fr`, `eu`, `intl` or an ISO country code; keys are lowercase, `l761-1` for L. 761-1). A wrong slug errors back with the closest ones: guessing then correcting is one call, a search is two. The root `/norm/{juris}/{code-slug}`, with no key, always answers and never carries `num`: a text with no articles (circulaire, publication decree) comes back whole, one with articles comes back as its table of contents in `articles`, bodies joined when the text is short. On a text you do not know, read the root first. **To read a chapter, fetch the division, not its articles.** Table of contents entries with `kind: "section"` carry the url of the division, the path of its segments (`/norm/fr/code-civil/livre-i/titre-v`), that `get_norm` takes: it returns every article of that division with its body, where walking them one by one costs one call each. Past the inline reading budget the bodies drop out, `omitted` says how many, and each entry `url` still fetches its own article. An article carries its `section` too, the division enclosing it: its `url` reads the neighbouring articles in one call. A Légifrance id or permalink (LEGIARTI, LEGITEXT, LEGISCTA, JORFARTI…) goes in `textId` as is.
2. **Text known, article unknown**: `search_norms` with the `code` filter (slug or exact name) and a descriptive French query on the subject. Within one named text, ranking is reliable. When the relevant date is known, pass `date` here too: hits are the versions valid at that date, not today's.
3. **Text unknown**: descriptive query plus the `jurisdiction` filter (`FR`, `UE`, `INTL`, or an ISO country code `SN`, `DZ`, `BE`…), then read `facets.code` to see which texts concentrate the matches and re-query with the winner. Ranking is domestic-first: a bare descriptive query ranks French, EU and treaty law above the 59 foreign corpora, and naming the country in the query (« divorce au sénégal ») scopes it to that country's law instead. A query that IS a text's name, official or usual (« code civil du sénégal »), returns the text itself as a num-less first hit whose `url` is the `/norm/{juris}/{slug}` entry point: the cheapest way to recover a slug. Still **don't trust a bare descriptive search beyond its top hits**: the corpus is ~2 million articles dominated by circulaires and arrêtés, the `total` is OR-matched noise, and body-text sources keep crowding treaty searches: the `jurisdiction` and `code` filters remain the robust path.

## Versions, renumbering, silence

- The response carries the full version timeline. When a text was recodified or an article renumbered (CESEDA 2021: L. 313-11 → L. 423-23; code du travail 2008), **query both numbers**: each key has its own timeline and the decisive one depends on your date.
- « Not found » with a `date` means no version in force at that date under that key, not that the rule did not exist. Re-fetch without `date` to see the timeline, then chase the earlier numbering.
- Abrogated texts stay served: the code de la nationalité française or an old CESEDA article at its date is one `date` away.
- Hits may repeat one article once per version: deduplicate by URL.

## Legal orders and hierarchy

State which legal order a provision belongs to, and flag the hierarchy when orders collide: a bilateral accord is lex specialis (the accord franco-algérien governs Algerian residence permits and derogates from the CESEDA), EU law primes national law in its field, the Convention de sauvegarde primes statute. When the question spans orders, fetch the provisions on each side.

## Chain with case law

Both directions, and always both in a dispute:

- Text → decisions: `search_decisions` with `legal_instrument` (any slug: a French code, a treaty, a foreign code) or `legal_article` (`accord-franco-algerien-du-27-decembre-1968|7-bis`) finds the decisions applying the provision, then the recherche-jurisprudence skill takes over.
- Decision → texts: decision full texts carry inline `/norm/` links on every cited provision; open them with `get_norm` rather than searching again.

## Present each provision

Things to say, not wording to reproduce: say them in the language the user writes in, under whatever headings that language calls for.

- Cite the provision with the official text name and article number, linking it on the `url` verbatim.
- Say which version you quote, its validity dates, and why that version governs the case (rule 2).
- Quote it verbatim, never truncating a sentence in a way that drops a condition or a negation.
- For foreign and aggregated sources, say where the text comes from when reliability matters: each hit carries a `source` field (official publishers like legifrance, eur-lex, fedlex, dri.gouv.sn vs aggregators like jafbase or archive.org, see corpus.md).

## Don't waste calls

- Known article → compose the URL, skip the search.
- The version timeline arrives with every fetch: no second call to ask « since when ».
- One search with the right filter beats five filterless reformulations; after two queries with no new candidate, change the filter (code, jurisdiction), not the synonyms.
