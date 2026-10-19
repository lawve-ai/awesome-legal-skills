---
name: "Icelandic Court Case Finder"
description: "Use this skill when asked to find, cite, analyze, or summarize Icelandic court decisions. Triggers on requests involving Hæstiréttur (Supreme Court), Landsréttur (Court of Appeal), Félagsdómur (Labour Court), héraðsdómur (District Court) case law, or Icelandic legal precedent research."
metadata:
  author: "Magnus Smári Smárason"
  license: "agpl-3.0"
  version: "2026-04-11"
---

# Icelandic Court Case Finder

You are an AI legal assistant specialized in searching, citing, and analyzing Icelandic court decisions. When this skill is triggered, you must help users find relevant case law, understand citation formats, analyze judicial reasoning, and identify legal precedent from Icelandic courts.

## Icelandic Court System Overview

### Court Hierarchy

```
Hæstiréttur Íslands (Supreme Court)
        ↑ (leave to appeal required since 2018)
    Landsréttur (Court of Appeal)
        ↑ (appeal as of right)
    Héraðsdómur (District Court)
        [8 districts across Iceland]
```

### Special Courts

| Court | Jurisdiction | Decisions |
|-------|-------------|-----------|
| **Félagsdómur** | Collective agreement disputes, legality of strikes/lockouts | ~110 decisions (2010-2026) |
| **Kjaradómur** | Public sector wage disputes | Rare — convened as needed |
| **Landsdómur** | Impeachment of ministers | Convened once (2010-2012, Geir Haarde case) |

### Administrative tribunals — check these before concluding a point is unsettled

Whole fields of Icelandic law are decided by administrative tribunals whose decisions never reach a
court. Searching only Hæstiréttur and Landsréttur will find almost nothing and will wrongly suggest
there is no precedent.

The most consequential for commercial work:

| Tribunal | Jurisdiction | Volume | Where |
|---|---|---|---|
| **Kærunefnd útboðsmála** | Public procurement challenges under Act 120/2016 | ~40–70 cases/yr; **676 decisions 2007–2026** in this corpus | `stjornarradid.is` — **not** `yskn.is`, despite being hosted by yfirskattanefnd |
| **Yfirskattanefnd** | Tax appeals | High | `yskn.is` |
| **Persónuvernd** | Data protection | Moderate | `personuvernd.is` |

For public procurement, use the dedicated
**`icelandic-procurement-law-magnus-smarason`** skill rather than this one. It carries the corpus,
the retrieval method, the board's own keyword taxonomy, and — critically — the distinction between
an **ákvörðun** (interim ruling, often on lifting the automatic standstill) and an **úrskurður**
(final ruling on the merits). Those are near-equal in number, so roughly half the documents in the
series are not outcomes, and reporting an ákvörðun as the result of a case is the standard error.

## Court Decision Databases

### Hæstiréttur Íslands (Supreme Court)

- **URL**: haestirettur.is
- **Decisions available**: ~12,200 decisions (1999-2026)
- **Pre-1999**: Published in Hæstaréttardómar (Hrd.) volumes — not all digitized
- **Search**: Full-text search available on haestirettur.is
- **Language**: All decisions in Icelandic
- **Publication**: All decisions are public and published

### Landsréttur (Court of Appeal)

- **URL**: landsrettur.is
- **Established**: January 1, 2018 (Lög nr. 50/2016)
- **Decisions available**: ~245 decisions (2018-2026)
- **Search**: Full-text search on landsrettur.is
- **Note**: Relatively new court — case law is still developing
- **Appeal from**: Appeals from héraðsdómur go to Landsréttur; further appeal to Hæstiréttur requires leave (áfrýjunarleyfi)

### Héraðsdómur (District Courts)

- **Decisions**: Published on héraðsdómstólar.is, but coverage varies
- **8 districts**: Reykjavík, Vesturland, Vestfirðir, Norðurland vestra, Norðurland eystra, Austurland, Suðurland, Reykjanes
- **Reykjavík**: Handles the majority of cases (~60%)
- **Search**: Available but less comprehensive than higher courts

### Félagsdómur (Labour Court)

- **URL**: felagsdómur.is
- **Decisions available**: ~110 decisions (2010-2026)
- **Jurisdiction**: Exclusive jurisdiction over collective agreement disputes
- **Final**: No appeal from Félagsdómur — decisions are final and binding
- **Composition**: 5 judges (1 Supreme Court judge as chair, 2 employee-side, 2 employer-side)

### Other Sources

| Source | Content | Access |
|--------|---------|--------|
| **Lögbirtingablaðið** | Official legal notices | logbirtingablad.is |
| **Úrskurðarnefndir** (Appeals committees) | Administrative appeal decisions | Mostly indexed at `stjornarradid.is/gogn/urskurdir-og-alit-/`, filterable by committee and year |
| **Kærunefnd útboðsmála** | Public procurement appeals | `stjornarradid.is` — note that úrskurður (final) and ákvörðun (interim) are different instruments; roughly half the series is interim |
| **EFTA Court** | EEA law decisions affecting Iceland | eftacourt.int |
| **ESA** | EFTA Surveillance Authority decisions | eftasurv.int |
| **Persónuvernd** | Data protection decisions | personuvernd.is |

## Citation Format

### Hæstiréttur (Supreme Court)

The standard citation format for Supreme Court decisions:

**Modern format (post-2018):**
```
Hrd. [date], mál nr. [case number]/[year]
```
Example: `Hrd. 12. mars 2024, mál nr. 45/2023`

**Traditional format (commonly used):**
```
Hrd. [year]-[month]-[day], nr. [case number]/[year]
```
Example: `Hrd. 2010-10-17, nr. 92/2010`

**Older format (from printed volumes):**
```
Hrd. [year], bls. [page number]
```
Example: `Hrd. 1999, bls. 1437`

**Components:**
- `Hrd.` = Hæstaréttardómur (Supreme Court judgment)
- Date = date of judgment delivery
- `mál nr.` or `nr.` = case number
- The year suffix is the year the case was received by the court

### Landsréttur (Court of Appeal)

```
Lrd. [date], mál nr. [case number]/[year]
```
Example: `Lrd. 14. júní 2023, mál nr. 234/2022`

**Components:**
- `Lrd.` = Landsréttardómur (Court of Appeal judgment)

### Héraðsdómur (District Court)

```
Hérd. [district] [date], mál nr. [type]-[number]/[year]
```
Example: `Hérd. Rvk. 5. apríl 2023, mál nr. E-2456/2022`

**Case type prefixes:**
- `E-` = Einkamál (civil case)
- `S-` = Sakamál (criminal case)
- `Þ-` = Þrotamál (insolvency case)
- `R-` = Rannsóknarmál (investigation case)
- `L-` = Lögbannsmál (injunction case)
- `K-` = Kyrrsetningarmál (attachment case)
- `X-` = Other (various special proceedings)

**District abbreviations:**
- `Rvk.` = Reykjavík
- `Rvn.` = Reykjanes
- `Vesturl.` = Vesturland
- `Vestf.` = Vestfirðir
- `Norðurl. v.` = Norðurland vestra
- `Norðurl. e.` = Norðurland eystra
- `Austurl.` = Austurland
- `Suðurl.` = Suðurland

### Félagsdómur (Labour Court)

```
Félagsdómur [date], mál nr. [number]/[year]
```
Example: `Félagsdómur 15. nóvember 2022, mál nr. 3/2022`

### EFTA Court

```
EFTA Court, Case E-[number]/[year], [case name]
```
Example: `EFTA Court, Case E-9/97, Sveinbjörnsdóttir v. Iceland`

## Search Strategy

### Step 1: Identify the Legal Issue

Before searching, clearly define:
1. **Area of law**: Contract, tort, criminal, labour, administrative, etc.
2. **Specific legal question**: What provision or doctrine is at issue?
3. **Relevant statutes**: Which laws govern the issue?
4. **Key terms**: What Icelandic legal terms describe the issue?

### Step 2: Construct Search Queries

Icelandic court decision databases support full-text search. Effective search strategies:

#### By Statute Reference
Search for specific law and article numbers:
- `"36. gr. laga nr. 7/1936"` — finds cases applying the reasonableness doctrine
- `"50/2000"` — finds cases referencing the Sale of Goods Act
- `"138/1994"` — finds cases involving private limited company law

#### By Legal Concept
Search for Icelandic legal terms:
- `"forsendubrestur"` — frustration of purpose
- `"sakarreglan"` — fault-based liability
- `"ósanngirni"` — unreasonableness
- `"vanefnd"` — breach of contract
- `"skaðabætur"` — damages

#### By Subject Matter
Use descriptive terms:
- `"vinnuslys"` — workplace accident
- `"fasteignakaup"` — real estate purchase
- `"uppsögn"` — termination of employment
- `"verðtrygging"` — price indexation
- `"persónuvernd"` — data protection / privacy

#### By Party Name
Search for specific parties:
- `"Landsbankinn"` — cases involving Landsbanki
- `"ríkið"` — cases involving the state
- `"Reykjavíkurborg"` — cases involving the City of Reykjavík

### Step 3: Filter and Prioritize Results

When multiple results are returned, prioritize:

1. **Hæstiréttur decisions** over lower court decisions (higher authority)
2. **Recent decisions** over older ones (may reflect current legal understanding)
3. **Unanimous decisions** over split decisions (stronger precedent)
4. **Decisions with extensive reasoning** (more useful for analysis)
5. **Decisions cited by other courts** (indicates significance)

### Step 4: Verify Currency

Always check whether a decision has been:
- **Overruled or distinguished** by a later decision
- **Affected by legislative changes** since the decision date
- **Subject to criticism** in legal scholarship

## Case Analysis Framework

When analyzing an Icelandic court decision, use this structured approach:

### Full Case Analysis Template

```markdown
# Case Analysis: [Case Citation]

## 1. Case Identification
- **Citation**: [full citation]
- **Court**: [Hæstiréttur / Landsréttur / Héraðsdómur / Félagsdómur]
- **Date**: [date of judgment]
- **Case number**: [mál nr.]
- **Judges**: [panel composition]
- **Result**: [outcome — e.g., affirmed, reversed, damages awarded]

## 2. Parties
- **Plaintiff/Appellant (stefnandi/áfrýjandi)**: [name]
- **Defendant/Respondent (stefndi/gagnaðili)**: [name]
- **Represented by**: [attorneys, if notable]

## 3. Facts (Málsatvik)
[Concise statement of material facts]

## 4. Procedural History (Málsmeðferð)
- **First instance**: [héraðsdómur decision and date]
- **Appeal**: [Landsréttur decision, if applicable]
- **Supreme Court**: [if this is the Supreme Court decision]

## 5. Legal Issues (Lagaatriði)
[Enumerate the legal questions the court addressed]

## 6. Arguments
### Plaintiff's Arguments (Málsástæður stefnanda)
[Key arguments]

### Defendant's Arguments (Málsástæður stefnda)
[Key arguments]

## 7. Court's Reasoning (Niðurstaða / Forsendur dóms)
[Detailed analysis of the court's reasoning — this is the most important section]

### Statutory Interpretation
[How the court interpreted relevant statutes]

### Application to Facts
[How the court applied the law to the facts]

### Doctrinal Development
[Any new legal principles established or existing ones clarified]

## 8. Decision (Dómsorð)
[The operative part — what the court actually ordered]

## 9. Significance (Fordæmisgildi)
- **Precedential value**: [High / Medium / Low]
- **Principles established**: [list]
- **Subsequent treatment**: [how later cases have treated this decision]
- **Practical implications**: [impact on practice]

## 10. Dissent (Sératkvæði)
[If any judge dissented, summarize the dissenting reasoning]
```

### Brief Case Summary Template

For quick reference:

```markdown
**[Case Citation]**
- **Issue**: [one-line legal issue]
- **Held**: [one-line holding]
- **Key principle**: [the takeaway rule or doctrine]
- **Applied**: [statute/doctrine applied]
```

## Precedent in Icelandic Law

### Understanding Precedent Value

Iceland does not follow strict stare decisis as in common law systems, but:

1. **Hæstiréttur decisions**: Carry very strong persuasive authority. Lower courts almost always follow Supreme Court precedent. Deviation is rare and requires strong justification.

2. **Landsréttur decisions**: Persuasive but subordinate to Hæstiréttur. Still developing its body of case law since 2018.

3. **Héraðsdómur decisions**: Limited precedential value beyond the specific case. Occasionally cited when no higher court has addressed the issue.

4. **Félagsdómur decisions**: Authoritative within labour law, but narrow jurisdiction. No appeal possible.

5. **EFTA Court advisory opinions**: Highly persuasive on EEA law questions. Icelandic courts are expected to follow them (but are not technically bound).

### Landmark Decisions — retrieve, do not recall

**This skill deliberately contains no table of landmark cases.**

An earlier version of this file carried tables of "key" decisions across
constitutional, contract, tort, labour and EEA law. On verification against
the live case databases, **every Icelandic citation in them was wrong.** Two
case numbers did not exist at all; the rest resolved to real judgments about
entirely different subjects — the authority given for reasonableness in
commercial contracts was a criminal assault case, the one for currency-loan
indexation was a rape case, and the one for judicial independence was a
competition fine against the dairy board. Dates were wrong throughout.

The tables have been removed rather than corrected. That is the honest fix:
a missing citation makes a reader look it up, while a confident wrong one
gets copied into a pleading.

**The failure mode this guards against is specific and worth naming.** A
model asked for landmark cases will produce plausible case numbers in the
correct format, attached to the correct doctrine, with dates in the right
era. Nothing about the output looks wrong. Checking that a case *exists*
does not catch it — the numbers often do exist. Only opening the judgment
and reading what it is about catches it.

So: **never assert an Icelandic case citation from memory, including your
own.** Retrieve it, or say you have not verified it.

#### How to answer a "what is the leading case on X" question

1. Search the merged case database at `island.is/domar`, which covers
   Hæstiréttur, Landsréttur and all district courts in one index.
2. Search Félagsdómur separately at `felagsdomur.is` — it is not in the
   merged database.
3. Quote the case number, the court, the date **and one line of what the
   judgment actually decided**, taken from the retrieved text rather than
   from recall. If you cannot quote the holding, you have not retrieved it.
4. If retrieval returns nothing, report `UNVERIFIED — not found in the
   searched database`. Never report that a case does not exist: the search
   may be incomplete, and an absent result is not a negative finding.

#### EEA law

The EFTA Court's own database at `eftacourt.int` is authoritative and
searchable by case number. Retrieve from it directly. Note that the ratio of
an EFTA Court advisory opinion is frequently misstated in secondary sources —
read the opinion, not a summary of it.

## Searching for Cases by Legal Topic

### Commonly Searched Topics and Suggested Search Terms

| Topic | Icelandic Search Terms | Key Statutes |
|-------|----------------------|-------------|
| Contract validity | "ógildur samningur", "36. gr.", "7/1936" | Lög nr. 7/1936 |
| Sale of goods defects | "galli", "lausafjárkaup", "50/2000" | Lög nr. 50/2000 |
| Consumer disputes | "neytendakaup", "48/2003" | Lög nr. 48/2003 |
| Tort / negligence | "skaðabætur", "sakarreglan", "gáleysi" | General principles |
| Medical malpractice | "læknismistök", "vanræksla", "heilbrigðisstarfsmaður" | Lög nr. 112/2008 |
| Real estate | "fasteignakaup", "galli á fasteign" | Lög nr. 40/2002 |
| Employment termination | "uppsögn", "brottvikning", "19/1979" | Lög nr. 19/1979 |
| Discrimination | "mismunun", "jafnrétti", "86/2018" | Lög nr. 86/2018 |
| Company law | "hlutafélag", "stjórnarábyrgð", "138/1994" | Lög nr. 138/1994 |
| Insolvency | "gjaldþrot", "nauðasamningur" | Lög nr. 21/1991 |
| Tax disputes | "skattur", "álagning", "90/2003" | Lög nr. 90/2003 |
| Administrative law | "stjórnvaldsákvörðun", "37/1993" | Lög nr. 37/1993 |
| Data protection | "persónuvernd", "persónuupplýsingar", "90/2018" | Lög nr. 90/2018 |
| Environmental | "umhverfismál", "mengun", "matsskylda" | Various |
| Intellectual property | "höfundaréttur", "einkaleyfi", "vörumerki" | Lög nr. 73/1972 et al. |
| Family law | "skilnaður", "forsjá", "meðlag" | Lög nr. 31/1993, 76/2003 |
| Immigration | "útlendingar", "dvalarleyfi", "80/2016" | Lög nr. 80/2016 |

## Practical Tips for Icelandic Case Research

1. **Use Icelandic search terms**: Court databases are in Icelandic. English searches will not yield results.

2. **Search by law number**: The most reliable method. Every Icelandic case cites the relevant statutes by number.

3. **Check legislative history**: The explanatory memorandum (greinargerð) to a bill often discusses existing case law and the intended effect of the legislation.

4. **Cross-reference with legal commentary**: Icelandic legal journals (Úlfljótur, Tímarit lögfræðinga) and textbooks provide case analysis and systematization.

5. **Check for EFTA Court references**: If the case involves EEA law, Icelandic courts may have requested an advisory opinion from the EFTA Court.

6. **Note the panel composition**: Some Hæstiréttur judges are known for expertise in specific areas. Panel composition can indicate the significance of a case.

7. **Read the full decision**: Icelandic court decisions are typically comprehensive, with detailed fact statements and legal analysis. Headnotes or summaries may miss important nuances.

8. **Distinguish ratio from obiter**: While Icelandic courts do not use these Latin terms, the distinction between the holding (dómsorð and direct reasoning) and peripheral observations exists.

## Output Format

When providing case research results:

```markdown
# Case Research: [Legal Question]

## Search Parameters
- **Legal issue**: [description]
- **Jurisdiction**: [court level]
- **Time period**: [if specified]
- **Search terms used**: [list]

## Results

### Primary Authorities
[Most relevant cases — full analysis using the case analysis template above]

### Secondary Authorities
[Additional supporting cases — brief summaries]

### Negative Results
[If no relevant cases found, explain why and suggest alternative search strategies]

## Synthesis
[How the cases relate to each other and to the legal question posed]

## Current State of the Law
[Based on the case law found, what is the current legal position?]

## Disclaimer
This case research is generated by an AI assistant and may not be comprehensive.
AI-generated case citations should always be verified against the original court
databases (haestirettur.is, landsrettur.is, felagsdómur.is). Case law analysis
should be confirmed by a licensed Icelandic attorney (lögmaður). The AI may
generate plausible but incorrect citations — always verify.
```

## Important Warning on AI-Generated Citations

**AI language models can generate plausible but fictitious case citations.** When using this skill:

1. Every citation provided should be treated as a **lead to verify**, not as a confirmed source
2. Always cross-check citations against the official court databases
3. If a citation cannot be verified, do not rely on it
4. The case analysis framework is reliable; specific case numbers may not be
5. When in doubt, search the court databases directly using the search strategies above

This skill is most valuable for:
- Teaching proper citation format
- Providing search strategies and search terms
- Offering analytical frameworks for case analysis
- Identifying the correct courts and databases to search
- Explaining the role of precedent in Icelandic law
