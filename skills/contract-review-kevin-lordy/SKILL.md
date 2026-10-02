---
name: contract-review
description: Review legal contracts, NDAs, employment agreements, SaaS terms, and M&A documents. Identifies unfavorable terms, suggests redlines, and compares to market standards. Use for contract analysis, due diligence, or negotiation prep.
version: 3.0.0
---

# Contract Review Skill

Review legal contracts for risks, extract key terms, and suggest redlines. Built on the CUAD dataset (41 risk categories), ContractEval benchmarks, and LegalBench.

## When to Activate

- User mentions "review contract", "analyze agreement", "check this contract"
- User uploads or references a PDF/DOCX legal document
- User asks about specific clauses, risks, or terms

---

## Step 1: Pre-Review Checklist

Before analyzing content, verify document completeness:

- [ ] **Blank fields**: Flag any "$X", "TBD", "[amount]", "____" placeholders
- [ ] **Missing exhibits**: List all referenced schedules/exhibits and note which are missing
- [ ] **Signature status**: Draft or already executed?
- [ ] **All pages present**: Check for truncation or missing sections

If blank fields or missing exhibits exist, flag prominently in output header.

---

## Step 2: Identify Document Type & User Position

**Ask if unclear:** "Which party are you? (customer, vendor, buyer, seller, licensor, licensee, receiving party, disclosing party)"

This affects what's "risky":
- Customer reviewing vendor agreement → flag vendor-favorable terms
- Vendor reviewing own template → flag customer-favorable terms
- Buyer in M&A → flag seller-favorable terms
- Seller in M&A → flag buyer-favorable terms
- Receiving party in NDA → flag disclosing party-favorable terms

**Assess power dynamic:**
- Startup vs. large enterprise? (limited negotiating leverage)
- Standard form vs. negotiated? (some terms non-negotiable)
- Regulated industry? (some terms legally required)

---

## Output Format

Use **markdown** for readable, scannable output. Do NOT use XML tags.

---

### Example Output

```markdown
# Contract Review: [Document Name]

**Document Type:** SaaS Subscription Agreement
**Your Position:** Customer
**Counterparty:** Acme Software Inc.
**Risk Level:** 🟡 Medium
**Document Status:** Draft / Executed on [date]

## ⚠️ Pre-Signing Alerts

- **Blank field:** Fee amount in Section 4.1 is "$____"
- **Missing exhibit:** Exhibit B (SLA) referenced but not attached

## Executive Summary

Standard vendor agreement with some one-sided terms. The 3-month liability cap and
asymmetric termination rights need attention. Data ownership is clear.

---

## Key Terms

| Term | Value | Location |
|------|-------|----------|
| Initial Term | 12 months | Section 8.1 |
| Auto-Renewal | 12-month periods, 60-day notice | Section 8.2 |
| Liability Cap | 3 months' fees | Section 10.2 |
| Governing Law | Delaware | Section 12.1 |

---

## Red Flags (Quick Scan)

| Flag | Found | Location |
|------|-------|----------|
| Liability cap < 6 months | ⚠️ Yes | Section 10.2 |
| Uncapped indemnification | No | — |
| Unilateral amendment rights | ⚠️ Yes | Section 14.1 |
| No termination for convenience | No | — |
| Perpetual obligations | No | — |
| Offshore jurisdiction | No | — |

---

## Risk Analysis

### 🔴 Critical

**Limitation of Liability** (Section 10.2)
> "Liability shall not exceed fees paid in the preceding three (3) months"

- **Issue:** 3-month cap is below market standard (typically 12 months)
- **Risk:** For $120K annual contract, liability capped at $30K
- **Market Standard:** 12 months' fees
- **Negotiability:** Medium — most vendors accept 6-12 months
- **Redline:** Change "three (3) months" → "twelve (12) months"
- **Fallback:** Accept 6 months as compromise

---

### 🟡 Important

**Termination for Convenience** (Section 8.5)
> "Vendor may terminate for any reason upon 30 days notice"

- **Issue:** One-sided; customer lacks equivalent right
- **Market Standard:** Mutual termination rights
- **Negotiability:** High — reasonable ask
- **Redline:** Add "Either party may terminate..." or change to "90 days"

---

### 🟢 Reviewed & Acceptable

| Category | Status | Notes |
|----------|--------|-------|
| Data Ownership | ✓ | Customer owns all customer data |
| IP Rights | ✓ | Clear separation, no broad assignment |
| Confidentiality | ✓ | Mutual, 3-year term, standard exceptions |
| Governing Law | ✓ | Delaware — neutral for commercial |

---

## Missing Provisions

| Provision | Priority | Why It Matters |
|-----------|----------|----------------|
| Data Export Rights | Critical | No guaranteed way to get data out on termination |
| SLA Credits | Important | 99.9% uptime stated but no remedy for breach |
| Price Increase Cap | Important | Renewal pricing uncapped |

**Suggested language for Data Export:**
> "Upon termination, Vendor shall make Customer Data available for export in CSV or JSON format for 90 days at no additional charge."

---

## Internal Consistency Issues

- ⚠️ Section 5.2 references "Exhibit C" but no Exhibit C exists
- ⚠️ "Confidential Information" defined in Section 3.1 but used lowercase in Section 7

---

## Negotiation Priority

| # | Issue | Ask | Negotiability |
|---|-------|-----|---------------|
| 1 | Liability cap | 12 months | Medium |
| 2 | Termination rights | Mutual | High |
| 3 | Data export | Add provision | High |
| 4 | Price cap | 5% annual max | Medium |

---

*This review is for informational purposes only. Material terms should be reviewed by qualified legal counsel.*
```

---

## Red Flags Quick Scan

Check these danger signs FIRST before deep analysis:

| Red Flag | Why It Matters |
|----------|----------------|
| Liability cap < 6 months | Inadequate protection |
| Uncapped indemnification | Unlimited exposure |
| "As-is" with no warranty | No recourse for defects |
| Unilateral suspension without notice | Service can vanish |
| Unilateral amendment rights | Terms can change |
| No termination for convenience | Locked in |
| Perpetual obligations (tails, non-competes) | Indefinite exposure |
| Offshore jurisdiction (BVI, Cayman) | Expensive to enforce |
| Pre-signed conflict waivers | No recourse for conflicts |
| "Sole discretion" language favoring counterparty | No objective standard |
| Class action waiver + mandatory arbitration | Limited remedies |
| Asymmetric assignment rights | They can assign, you can't |

---

## Document Type Checklists

### NDA Checklist

| Category | Check For |
|----------|-----------|
| Direction | One-way or mutual? |
| Definition scope | "All information" too broad? Standard exceptions? |
| Term | 2 years short, 3-5 typical, indefinite for trade secrets |
| Permitted disclosure | "Representatives" defined? Flow-down required? |
| Residuals clause | Can use general knowledge retained in memory? |
| Non-solicitation | Employees protected? |
| Standstill | Prevents hostile acquisition actions? |
| No-contact | Customers, suppliers, employees protected? |
| Return/destruction | Certification required? |
| Public announcement | Prohibits disclosure of discussions? |
| Compelled disclosure | Notice required? Time to seek protective order? |
| Injunctive relief | Pre-agreed specific performance? Bond waiver? |

### SaaS/MSA Checklist

| Category | Check For |
|----------|-----------|
| Liability cap | 12+ months = standard |
| Uptime SLA | 99.9% with credits = standard |
| Suspension rights | Unilateral? Notice required? |
| Data ownership | Customer owns customer data? |
| Data export | Format, duration, cost on termination? |
| Price increases | Capped? Notice period? |
| Auto-renewal notice | 90+ days = good, <60 = risk |
| Termination | Mutual for convenience? Cure period for cause? |
| Subprocessors | Notice of changes? Approval rights? |
| Insurance | Vendor carries E&O, cyber? |

### Payment/Merchant Agreement Checklist

| Category | Check For |
|----------|-----------|
| Reserve/holdback | Amount, duration, release conditions? |
| Chargeback liability | Capped? Fraud protection? |
| Network rules | Incorporated by reference? Access provided? |
| Auto-debit authority | Notice before debits? |
| Settlement timing | When do you receive funds? |
| Volume commitments | Realistic? Penalty for shortfall? |
| Suspension rights | Immediate or notice? |
| Termination tail | How long do obligations survive? |
| Audit rights | Frequency, notice, cost allocation? |
| PCI compliance | Who bears cost? |

### M&A Agreement Checklist

| Category | Check For |
|----------|-----------|
| Purchase price | Cash vs. stock vs. earnout mix? |
| Earnout mechanics | Measurement, discretion, audit rights, acceleration? |
| Escrow/holdback | Amount (10-15% typical), duration (12-18 mo), release? |
| Rep survival | 12-24 months general, longer for fundamental |
| Indemnification cap | 10-20% of purchase price typical |
| Basket type | True deductible vs. tipping? |
| Sandbagging | Pro-buyer or anti-sandbagging? |
| Non-compete | 2-3 years, geographic scope? |
| Working capital | Target, collar, true-up mechanism? |
| MAC definition | Carve-outs for market conditions? |
| Employment comp | Counted in purchase price or separate? |

### Finder/Broker Agreement Checklist

| Category | Check For |
|----------|-----------|
| Fee percentage | Specified or blank? |
| Fee calculation | What's included in deal value? Employment comp? |
| "Covered buyer" definition | How broad? Any prior relationship carve-out? |
| Tail period | 12-24 months typical; perpetual = red flag |
| Exclusivity | Exclusive or non-exclusive? |
| Minimum fee | Floor amount? |
| Joint representation | Consent required? Conflict waiver? |
| Escrow deduction | Auto-pay from proceeds? |
| Term/termination | Can you exit? |
| Broker status | BD registered if securities involved? |

---

## Risk Categories (CUAD 41 + Extensions)

### Document Basics
- Document Name and Type
- Parties (legal names, roles)
- Agreement Date / Effective Date
- Expiration Date
- Renewal Terms
- **Document Status** (draft/executed)
- **Blank Fields / Placeholders**

### Term & Termination
- Contract Term / Duration
- Termination for Convenience
- Termination for Cause
- Post-Termination Services
- Survival Clauses
- **Suspension Rights** (immediate vs. with notice)
- **Cure Periods**

### Assignment & Control
- Anti-Assignment Clause
- Change of Control
- Consent Requirements
- **Asymmetric Assignment** (they can, you can't)

### Financial Terms
- Payment Terms
- Price Restrictions / Adjustments
- Most Favored Nation (MFN)
- Minimum Commitment
- Volume Restrictions
- Audit Rights
- **Price Escalation Caps**
- **Reserve/Holdback Requirements**
- **Auto-Debit Authority**

### Liability & Risk
- Limitation of Liability
- Cap on Liability
- Uncapped Liability Carve-outs
- Indemnification
- Insurance Requirements
- Warranty Duration
- **Warranty Disclaimer (As-Is)**
- **Exclusive Remedy Clauses**
- **Chargeback/Return Liability**

### IP & Confidentiality
- IP Ownership Assignment
- License Grant
- Affiliate License - Licensor/Licensee
- Covenant Not To Sue
- Non-Compete
- Non-Solicitation (Employees/Customers)
- Competitive Restriction Exception
- Exclusivity
- Non-Disparagement
- Confidentiality Duration
- Third Party Beneficiary
- **Residuals Clause**
- **Feedback Ownership**

### Dispute Resolution
- Governing Law
- Jurisdiction / Venue
- Arbitration vs Litigation
- Jury Trial Waiver
- **Class Action Waiver**
- **Offshore Jurisdiction Flags**

### Special Provisions
- ROFR / ROFO / ROFN
- Revenue/Profit Sharing
- Joint IP Ownership
- Source Code Escrow
- Irrevocable or Perpetual License
- **Data Export Rights**
- **Uptime/Availability SLA**
- **Sublicensing Rights**
- **Unilateral Amendment Rights**

---

## Market Standard Benchmarks

| Provision | Standard | Yellow Flag | Red Flag |
|-----------|----------|-------------|----------|
| **Liability cap** | 12 months' fees | 6-11 months | <6 months |
| **Non-compete duration** | 1-2 years | 3-4 years | 5+ years |
| **Non-compete geography** | Where business operates | State-wide | Nationwide |
| **Auto-renewal notice** | 90+ days | 60-89 days | <60 days |
| **Termination notice** | Mutual, 60-90 days | One-sided, 30 days | Immediate |
| **Indemnification** | Mutual, capped | Asymmetric | Uncapped |
| **Rep survival (M&A)** | 12-18 months general | 24-30 months | 36+ months |
| **Escrow (M&A)** | 10-15% for 12-18 mo | 15-20% for 18-24 mo | >20% or >24 mo |
| **Confidentiality (NDA)** | 3 years general | 2 years | 5+ years |
| **Fee tail (broker)** | 12-18 months | 24 months | Perpetual |
| **SLA uptime** | 99.9% with credits | 99.5% | No SLA |
| **Data export** | 90 days, standard format | 30 days | None |
| **Price increase cap** | CPI or 5% annual | 10% annual | Uncapped |
| **Cure period** | 30 days | 15 days | None |

---

## Negotiability Guide

| Rating | Meaning | Examples |
|--------|---------|----------|
| **High** | Usually accepted | Mutual termination, cure periods, data export |
| **Medium** | Depends on leverage | Liability cap increase, price caps |
| **Low** | Rarely changed | Network rules (payments), regulatory requirements |
| **None** | Non-negotiable | Card network mandates, banking regulations |

**Power dynamic factors:**
- Large customer + small vendor = more leverage
- Startup + enterprise vendor = less leverage
- Competitive market = more leverage
- Sole-source vendor = less leverage
- Regulated terms = no leverage (legally required)

---

## Jurisdiction Notes

**Non-Competes:**
- California, North Dakota, Oklahoma, Minnesota: Generally void
- Other states: Reasonableness test applies

**Choice of Law:**
- Delaware: Corp-friendly, predictable
- New York: Financial agreements, sophisticated courts
- California: Employee-friendly, tech industry
- BVI/Cayman: Offshore, expensive to litigate, potential red flag

**Arbitration Venues:**
- AAA, JAMS: Standard US commercial
- SIAC (Singapore), LCIA (London): International, expensive
- Mandatory + class waiver: Limits remedies significantly

---

## Guardrails

- **Not legal advice**: Recommend attorney review for material terms
- **Not tax advice**: Flag but don't opine
- **Jurisdiction matters**: Note when enforceability varies
- **Express uncertainty**: Say when interpretation is unclear
- **No hallucination**: Only reference text actually in document
- **Show what's acceptable**: Always include "Reviewed & Acceptable" section
- **Document status matters**: Note if already executed (review is informational)

