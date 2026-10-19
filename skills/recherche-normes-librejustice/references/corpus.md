# The referential: what is actually inside

Orders of magnitude (October 2026): ~1.5 million texts, ~2.1 million articles in force, ~3.9 million article versions in all. Knowing the map prevents both false confidence (« it must be there ») and false absence (« only French codes »).

## France (`jurisdiction: FR`: ~1.3 million texts)

- **99 codes**, fully versioned article by article (every version with its validity window, back through recodifications).
- Lois and ordonnances (~17 500), décrets (~234 000), arrêtés (~732 000), décrets-lois, Constitution and lois organiques, each Journal officiel publication linked to what it amends or repeals; ~281 000 other official publications.
- **Circulaires and instructions** (~44 000): the administration's own reading; never confuse with the norm itself.
- **BOFiP** (6 288): the tax administration's doctrine, opposable under LPF art. L. 80 A; slugs like `bic-provisions-sort-et-surveillance-des-provisions`.
- **Conventions collectives** (~1 400, ~242 000 articles, source `kali`): filter with the exact convention name in `code`.

## European Union (`jurisdiction: UE`: ~149 000 texts)

Regulations and directives, article by article (`directive-2008-115-ce-retour-des-ressortissants-en-sejour-irregulier`).

## International (`jurisdiction: INTL`: ~6 300 texts)

Multilateral conventions (Convention de sauvegarde des droits de l'homme et des libertés fondamentales and its protocols, under their **official** names) and bilateral accords, some under their usual name (`accord-franco-algerien-du-27-decembre-1968`, with its avenants as versions), most under the French décret that published them: « décret n° XX portant publication de l'accord… ».

## Foreign law (ISO country codes: 59 countries)

Curated codes targeting what French litigation actually needs: family, nationality, civil status, civil, procedure. Largest volumes (article versions): BE 10 035, DJ 7 815, GN 5 660, MA 4 486, DE 4 324, SN 4 321, CM 4 176, CH 3 988, TG 3 965, BJ 3 661, plus DZ, TN, ML, CI, CD, CG, BF, KM, MR, NE, EG… Slugs carry a country suffix: `code-de-la-famille-sen`, `code-etat-civil-sen`.

Foreign texts are **not versioned**: one curated version, `dateDebut` empty. Check the enactment date stated in the text against the date of the facts yourself.

## Provenance: the `source` field

Every article carries its source. Official publishers: `legifrance`, `jorf`, `kali`, `bofip`, `eu-law`, `official-fr`, `gesetze-im-internet.de` (DE), `fedlex` (CH), `legilux` (LU). Government sites that are official but not always current: `dri.gouv.sn` (SN, documentation site, not the JO), `sgg-mali.ml` (ML). Aggregators and secondary sources: `jafbase` (33 700 foreign family-law articles), `africa-laws.org`, `natlex.ilo.org`, `archive.org`. For a contested point of foreign law, say which source the text comes from; an aggregator or stale government copy may lag a reform ([external-sources.md](external-sources.md)).

## URL and key shapes

`https://librejustice.fr/norm/{juris}/{slug}/{article-key}`, keys lowercase: `1240`, `l761-1`, `r421-1`, `7-bis`. Texts without numbered articles (circulaires, instructions, many BOFiP pages) are served as a single pseudo-article whose URL ends with `/`.
