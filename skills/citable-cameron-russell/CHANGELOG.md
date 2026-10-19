# Changelog

## 1.0.0 — 2026-10-07

Initial public release.

- Builds an interactive cite-checking table for a US court filing (PDF): each passage with its citations, one sub-row per citation with links, a cite-check status (check pending / confirmed / partial support / unsupported) and a note field.
- Links record citations (exhibits, declarations, deposition transcripts, Bates numbers, docket and NYSCEF entries) to the cited page or paragraph in the case folder; cases to CourtListener at the pinpoint where CourtListener's copy marks the cited reporter's pages; federal statutes and rules to Cornell LII; treaties to the record copy or the UN Treaty Series.
- Link dots: green = exact page, amber = approximate (with the reason), red = unresolved (with the reason), grey = listed for checking but not linked.
- Every build follows a per-case link map that the user confirms first; the build never invents entries.
- Rebuilds the table for a revised draft, flags citation-related changes and carries saved statuses and notes forward; each rebuild keeps a backup of the earlier table.
- Coverage and format warnings (pages with no citations, footnote numbering problems, early stops) are reported to the user.
