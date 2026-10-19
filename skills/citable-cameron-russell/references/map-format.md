# citable-map.json

One file per case folder. Confirmed by the user before any build; the build never invents entries.

```json
{
 "exhibits": {"A": "Ex A.pdf", "B": "Ex B.pdf", "12": "Exhibit 12.pdf"},
 "para_image_docs": ["A"],
 "docs": {"Friedman Decl": "Friedman decl.pdf"},
 "record_terms": {"ICSID Convention": "B", "Award": "A"},
 "authorities": [
  {"cite": "735 F.3d 72", "short": "Blue Ridge",
   "url": "https://www.courtlistener.com/opinion/1037860/blue-ridge-investments-llc-v-republic-of-argentina/", "markers": true},
  {"cite": "725 F. Supp. 52", "short": "M.B.L.", "url": "…", "cl_name": "M.B.I. International Contractors, Inc. v. …"},
  {"cite": "556 U.S. 662", "short": "Iqbal", "url": "https://www.courtlistener.com/opinion/145875/ashcroft-v-iqbal/", "markers": false, "marker_reporter": "129 S. Ct. 1937"},
  {"cite": "695 F.3d 129", "short": "Lass", "no_link": "CourtListener resolves this cite to a different case"}
 ],
 "treaties": [
  {"cite": "575 U.N.T.S. 159", "name": "ICSID Convention", "record": "B"},
  {"cite": "658 U.N.T.S. 163", "name": "Hague Service Convention",
   "url": "https://treaties.un.org/doc/Publication/UNTS/Volume%20658/volume-658-I-9432-English.pdf",
   "source": "UNTS vol. 658, No. 9432"}
 ],
 "unreported": [
  {"cite": "2014 WL 4804479", "short": "Troy", "entry": "S.D.N.Y. 13-cv-5082, Dkt. 53",
   "recap": "https://storage.courtlistener.com/recap/gov.uscourts.nysd.415078/gov.uscourts.nysd.415078.53.0.pdf",
   "pages": {"*10": {"page": 17, "how": "\"treating individuals unequally\" found on PDF p. 17"}}},
  {"cite": "2017 WL 1189747", "short": "Feliciano", "docket_url": "https://www.courtlistener.com/docket/6504370/feliciano-v-anderson/",
   "note": "the 30 Mar 2017 decision is not in RECAP"}
 ],
 "dockets": {"2:25-cv-02222": {"name": "FedEx v. My Pillow (W.D. Tenn.)", "url": "https://www.courtlistener.com/docket/69685817/…/",
                               "entries": {"18": "Clerk's entry of default, 7/8/2025"}},
             "_this": {"url": "…", "entries": {"4": "Affidavit of service"}}},
 "nyscef": {"index": "659206/2025"},
 "doc_series": {"CSMF": "Counterstatement"},
 "numbered_paragraphs": false,
 "confirmed": {"by": "J. Reviewer", "date": "2026-10-05", "sha256": "a0b0fd43306653c6"}
}
```

| Key | Meaning |
|---|---|
| `exhibits` | Exhibit label as cited (`Ex. A`, `Ex. 12`) → file in the case folder, or `{"file": "…", "pages": "20-25"}` for an exhibit that is a page range inside another file (also allowed in `docs`). |
| `para_image_docs` | Exhibits whose paragraph numbers are margin images (few ¶ numbers in the text layer and roughly one margin image per page; confirm by looking at a page). Pages are found by counting those images and confirmed by OCR. |
| `docs` | Files cited by name rather than exhibit label: other filings (`Friedman Decl., ¶ 8 n.2`), exhibits not yet lettered, authorities saved in the folder (`CL-12`). Key = the name exactly as the filing uses it. Linked by ¶ (filings' ¶s and footnotes are parsed directly; other documents use the exhibit ¶ maps), by page, or to the first page when no pinpoint is given. A name without a pinpoint counts only in citation position (after a signal, or ending the sentence or clause). |
| `record_terms` | Defined terms in the filing that refer to an exhibit, including deposition short names ("Vavra Dep.": "A" links "Vavra Dep. 124:19-21"); also used to link references such as "Article 54 of the ICSID Convention" or "paragraph 1010 of the Award". |
| `authorities` | Cases. `cite` = vol reporter first-page exactly as in the filing. `short` = the short name the filing uses. Cases not listed fall back to CourtListener's citation route, marked amber. `markers`: whether the copy CourtListener displays marks the **cited reporter's** pages (checked when drafting by searching for the page after the first page); pinpoints are green only if true. `marker_reporter`: the parallel reporter whose pages the copy marks instead (links amber, with that reporter named). `stub`: CourtListener has little or no text. `no_link`: a reason not to link the case (e.g. CourtListener resolves the cite to a different case); it is listed in grey with that reason. Use it rather than leaving such a case out: an unlisted case falls back to CourtListener's citation route, which may open the wrong case. Marker checks use CourtListener's API (about 125 requests a day, 50 an hour; each opinion in a multi-id call counts): check cases cited with a pinpoint first. Only http(s) URLs are used. |
| `unreported` | Westlaw/Lexis cites found on CourtListener. `cite` = "YYYY WL N" (or the LEXIS form) as in the filing; `recap` = the court's PDF; `entry` = court, docket and Dkt. number; `pages` = star page → PDF page where the quoted passage was found (with `how`); or `docket_url` (+ `note`) when the decision itself is not there. Always amber. |
| `dockets` | Per cited case number (`_this` = the court of the filing): CourtListener docket `url`, `entries` (short descriptions of cited entries), optional `files` (entry → file) where the stamps cannot find the copy. Copies in the folder: a `files` entry in the map first, then the filing stamps. CourtListener docket links are amber (they open the listing, not the document). |
| `nyscef` | `index` number; optional `files` (number → file). Copies are found from the NYSCEF stamps. |
| `doc_series` | A defined term that points to a second numbered series inside a filing, e.g. `"CSMF": "Counterstatement"` for a counterstatement that restarts at ¶ 1. |
| `numbered_paragraphs` | `false` when the filing being built is not organised in numbered paragraphs but quotes a numbered list. |
| `treaties` | Matched exactly on the U.N.T.S. (or U.S.T.) volume and page. `record` (exhibit) is linked first, then `url`. |
| `confirmed` | Recorded only after the user confirms the map: `by`, `date` and `sha256` = the output of `build_table.py --fingerprint <map>`. The build refuses a map without it, or one changed since. |

Everything else (statutes and federal rules → LII, CPLR → NY Senate, web addresses, footnote cross-references) needs no map entry.
