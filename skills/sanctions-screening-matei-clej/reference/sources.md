# Sources — what each list is, and how it misbehaves

Verified live 01.09.2026. Every URL here was fetched and parsed on that date;
the record counts are designation *groups*, not rows (a designation with eleven
name variants is one record, with ten aliases).

## UK Sanctions List — `uk-sanctions-list`

<https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv> · OGL v3.0 ·
6,334 designations · ~50 MB

The legal list, published by the FCDO under the Sanctions and Anti-Money
Laundering Act 2018. It is the only one of these sources that records **which
measures** were imposed — asset freeze, travel ban, arms embargo, trust services,
director disqualification, transport — rather than assuming an asset freeze.
Carries ship and aircraft designations with IMO numbers and flag history.

* **The file opens with `Report Date: …` before the header row.** A parser that
  hands the first line to `DictReader` gets a single-column table and finds
  nothing, silently. Handled by sniffing for the row containing `Name 1`.
* Names arrive across `Name 1`…`Name 6`, where `Name 6` is the family name. Both
  reading orders are indexed, because the published display order differs
  between individuals and entities.
* `Name non-latin script` is a separate column and must never be concatenated
  into the Latin name.
* Rows are grouped by `Unique ID`; one designation spans many rows.

## OFSI consolidated list — `ofsi`

<https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.csv> ·
OGL v3.0 · 5,135 designations · ~17 MB

HM Treasury's list of financial sanctions targets: everyone subject to a UK
asset freeze, UK-implemented UN designations included. Narrower than the FCDO
list in what it covers, richer in asset-freeze detail, and it carries the UK
Sanctions List reference in the `Other Information` field, which is what lets a
hit be tied to the same designation across both lists.

* **The endpoint 404s on `HEAD` and serves on `GET`.** A monitoring check that
  uses `HEAD` will report the source dead when it is not.
* Preamble line `Last Updated,dd/mm/yyyy` before the header, as above.
* `Name Non-Latin Script` — same trap, same handling.
* Grouped by `Group ID`.

## UN Security Council Consolidated List — `un`

<https://scsanctions.un.org/resources/xml/en/consolidated.xml> · free to
reproduce · 1,011 designations · ~2 MB

Individuals and entities designated by the Security Council committees. Clean
XML, `INDIVIDUALS` and `ENTITIES` blocks, aliases and dates of birth nested.
Dates of birth appear as an exact date, a bare year, or a from/to range, and all
three shapes are indexed. Note that UK implementation of a UN designation also
appears on the OFSI list, so a UN hit usually has a UK counterpart.

## EU consolidated financial sanctions list — `eu`

<https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw>
· Commission reuse policy · 6,234 designations · ~26 MB

The `token` in that URL is the Commission's published public token, not a
credential.

* **Every name is published in every official language**, so one designation
  carries a Bulgarian, Greek, Polish and Slovenian rendering of the same person
  alongside the Latin one. The display name is chosen as the first
  predominantly-Latin variant; the rest are searchable as aliases.
* **Cyrillic homoglyphs appear inside otherwise-Latin names** — `ROMASHKІN`
  carries a Cyrillic `І`. A script test that asks "does this contain a Latin
  letter" classifies a Cyrillic name as Latin, and stripping the homoglyph
  instead of folding it splits the surname in two. The matcher folds Cyrillic
  and Greek homoglyphs to Latin before comparison.

## OFAC SDN and non-SDN consolidated — `ofac-sdn`, `ofac-cons`

<https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV>
(+ `ALT.CSV`) and `CONS_PRIM.CSV` (+ `CONS_ALT.CSV`) · US Government work, public
domain · 19,321 and 481 designations

* **Headerless CSVs.** Column order is fixed by OFAC's published file spec and
  hard-coded here; a change in that spec would corrupt every field silently, so
  the tests assert that every parsed designation has a name.
* Aliases live in a **separate file** keyed on `ent_num`; without `ALT.CSV`
  roughly half the searchable names are missing.
* Null is the literal string `-0-`.
* Dates of birth, nationalities and identifiers are embedded in free-text
  `remarks` (`DOB 07 Oct 1952; POB …`) and are extracted by pattern, so treat
  them as indicative and read the remarks.
* `ofac-cons` is the sectoral list: SSI, FSE, NS-PLC, CAPTA. Those programmes
  restrict particular dealings rather than blocking the person outright, which is
  why the measures field does not say "blocked".

## Canada — `canada` (not default)

<https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml>
· OGL Canada · 5,690 designations

Designations under the Special Economic Measures Act and the Justice for Victims
of Corrupt Foreign Officials Act. Bilingual field names (`Country-Pays`), no
generation date in the file, so the retrieval date is recorded instead. Aliases
arrive as one delimited string.

## Switzerland — `swiss` (not default)

<https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml?lang=en&action=downloadXmlGesamtlisteAction>
· free reuse · 8,667 targets, of which **1,559 are de-listed**

Richest name data of any source here: names decomposed into family name, given
name and patronymic, each with spelling variants by language and script.

* **The whole-list file ships de-listed targets alongside live ones**, marked by
  a `modification` element with `modification-type="de-listed"`. Parsed as
  `status: delisted` and excluded unless `--include-delisted` is passed. A
  parser that ignores this reports people as sanctioned who were removed years
  ago — the most damaging error this tool could make.

## OpenSanctions — `opensanctions-sanctions`, `opensanctions-peps` (not default)

<https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv>
(~68 MB) and `…/peps/targets.simple.csv` (~180 MB) · **CC BY-NC 4.0**

An aggregator, not an authority: roughly ninety sources deduplicated into one
schema, including national lists this skill does not fetch directly, plus the
only PEP data available here. Useful as a wider net and as a cross-check.

* **Licence-gated.** Non-commercial only. Using it to screen fee-earning client
  work is commercial use and needs a licence from OpenSanctions. Both sources
  refuse to refresh unless `SANCTIONS_OPENSANCTIONS_LICENCE` is set.
* A hit here is a pointer to the underlying listing, and the underlying listing
  is what gets cited. Do not put an aggregator's summary in a screening record
  where the authority's own entry can be quoted.
* PEP status is an EDD trigger under MLR 2017 reg 33(1)(d) and reg 35 where the
  MLR apply at all. It is not a prohibition and must never be written up as one.

## Not covered here

* **Interpol Red Notices.** The public API at `ws-public.interpol.int` returned
  403 from this machine on 01.09.2026, with and without a browser user-agent, so
  it is not wired in. Search the public notices site by hand where it matters.
* **Companies House disqualified directors and PSC data.** Needs an API key.
* **UK Home Office immigration and travel-ban data** beyond what the FCDO list
  carries.
* **Adverse media, litigation and insolvency searches.** Different exercise.
* **Ownership and control.** No list holds it. See reg 7 SI 2019/855 and the
  SKILL.md note.
