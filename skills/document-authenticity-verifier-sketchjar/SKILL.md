---
name: "document-authenticity-verifier"
description: "Forensic document authenticity check for legal professionals. Detects tampering signals (amount/words mismatch, font discontinuity, date anomalies, identifier checksums) in PDFs and images before you rely on a document. Use when reviewing contracts, payslips, invoices, statutory filings, exhibits, or any document where authenticity matters. Returns a risk band with per-signal evidence — not a fraud verdict."
metadata:
  author: "Sketchjar"
  license: "Apache-2.0"
  version: "2026-08-31"
---

# Document Authenticity Verifier

Check whether a document shows forensic signs of tampering before relying on it in a matter. Returns a `risk_band` (low / medium / high), an `inspection_quality` score, and the per-signal evidence behind both. This is a **signal with evidence**, not a fraud verdict — the goal is telling you *which* documents deserve closer scrutiny, not making the determination for you.

## When to Use This Skill

- Reviewing documents received from an opposing party
- Verifying client-provided financial records (payslips, bank statements, invoices) before filing
- Checking statutory documents, certificates, or lodgement confirmations
- Due diligence where document provenance matters
- Assessing exhibits or evidence before relying on them

## What This Skill Does

1. **Forensic inspection**: Analyzes the document for tampering signals — amount/words mismatch, font discontinuity in values, date anomalies, document label integrity, identifier checksums (ABN/ACN/TFN), table arithmetic
2. **Two-axis assessment**: Returns `risk_band` (does anything look tampered?) and `inspection_quality` (could the engine see enough to judge?) — low coverage is explicitly NOT risk
3. **Evidence transparency**: Every signal carries its status (pass / warning / fail / skipped) and an explanation
4. **Content-addressable**: Identical files are cached by hash — re-checking the same document is free

## How to Use

### Basic Usage

```bash
curl -X POST https://www.stipple.sh/v1/warrants \
  -F "file=@contract.pdf"
```

No API key needed — the anonymous free tier works immediately. For your own metering, get a free key at [stipple.sh](https://www.stipple.sh).

### Advanced Usage

```bash
# Deep inspection (more thorough, more credits)
curl -X POST "https://www.stipple.sh/v1/warrants?deep=true" -F "file=@contract.pdf"

# Force re-inspection of a previously cached document
curl -X POST "https://www.stipple.sh/v1/warrants?fresh=true" -F "file=@contract.pdf"
```

## Example

**User**: "Verify this payslip before I rely on it in the matter."

**Output**:
```
risk_band:           LOW — Nothing looks tampered.
inspection_quality:  limited
recommended action:  review_before_action

evidence (signals):
  [pass] Amount words/figure mismatch: Spelled-out amounts agree with figures.
  [pass] Font discontinuity in value: Numeric values share the font of surrounding text.
  [pass] Date anomaly: Dates present are calendar-valid and consistently ordered.
  [skip] Identifier checksum: No checksummable identifier (ABN/ACN/TFN) present.
```

## Reading Results Correctly

| Axis | Question it answers |
|---|---|
| `risk_band` | Does anything look tampered? |
| `inspection_quality` | Could the engine actually see enough to judge? |

A clean phone photo of a real payslip is commonly `low` + `limited` — "nothing looks tampered, but we couldn't read everything." **Low coverage is not risk.** Conversely, a high-quality scan of a well-forged document may return `low` + `thorough` — the engine saw everything and found nothing wrong, but sophisticated forgeries can still evade automated checks.

## Tips

- Run this **before** extraction or summarization — a tampered document yields confidently wrong extracted values
- Pair with `source-locked-verification` (in this collection) for evidential fidelity across your document set
- Document types the engine recognizes (payslips, invoices, bank statements) get type-specific checks; unrecognized types get generic checks only
- Re-checking the same document is free (cached by content hash)

## Common Use Cases

- Pre-filing verification of client-provided financial records
- Reviewing documents received in discovery or from opposing parties
- Due diligence document integrity checks
- Verifying statutory lodgements, certificates, or registrations before relying on them
- Screening invoices or payment requests for alterations before approval
