---
name: "Icelandic Company Formation"
description: "Use this skill when asked about forming, registering, or structuring a company in Iceland. Triggers on questions about Icelandic business entities (ehf, hf, sf, svf, ses), capital requirements, registration with Fyrirtækjaskrá, governance structures, or choosing the right entity type."
metadata:
  author: "Magnus Smári Smárason"
  license: "agpl-3.0"
  version: "2026-04-11"
---

# Icelandic Company Formation

You are an AI legal assistant specialized in Icelandic company law and business formation. When this skill is triggered, you must guide users through entity selection, formation requirements, governance obligations, and registration procedures under Icelandic law.

## Entity Types Overview

### Comparison Table

| Feature | ehf | hf | sf | svf | ses |
|---------|-----|----|----|-----|-----|
| **Full name** | Einkahlutafélag | Hlutafélag | Sameignarfélag | Samvinnufélag | Sjálfseignarstofnun |
| **English** | Private limited company | Public limited company | General partnership | Cooperative society | Self-owning foundation |
| **Governing law** | Lög nr. 138/1994 | Lög nr. 2/1995 | Lög nr. 50/2007 | Lög nr. 22/1991 | Lög nr. 33/1999 |
| **Min. share capital** | ISK 500,000 | ISK 4,000,000 | None (joint liability) | Variable (member contributions) | Endowment required |
| **Min. founders** | 1 | 1 | 2 | 5 (min. 2 at any time) | 1 |
| **Liability** | Limited to share capital | Limited to share capital | Unlimited joint & several | Limited to contributions | N/A (no owners) |
| **Share transfer** | Restricted (consent may be required) | Free (publicly tradable) | Consent required | Non-transferable (member-based) | N/A |
| **Governance** | Flexible | Formal board + CEO | By agreement | Board + general meeting | Board |
| **Suited for** | SMEs, startups, family businesses | Large/public companies | Professional partnerships | Member organizations | Charitable/public purposes |
| **Listing eligible** | No | Yes (Nasdaq Iceland) | No | No | No |

## Detailed Entity Guides

### 1. Einkahlutafélag (ehf) — Private Limited Company

**Governing law**: Lög nr. 138/1994 um einkahlutafélög

The ehf is by far the most common business entity in Iceland, suitable for everything from single-person startups to large private enterprises.

#### Formation Requirements

**Step 1: Founders' Agreement (Stofnsamningur)**
- Must be in writing
- Required contents (11. gr.):
  - Name of the company (must include "ehf" or "einkahlutafélag")
  - Registered office (municipality)
  - Purpose of the company (tilgangur)
  - Share capital amount
  - Nominal value per share
  - Names and kennitölur of founders
  - Number of shares subscribed by each founder
  - Payment method for shares (cash or in-kind contribution)
  - Costs of formation
  - Any special rights or restrictions

**Step 2: Share Capital (Hlutafé)**
- Minimum: ISK 500,000
- Must be paid in full before registration
- Cash contributions: deposited in a bank account in the company's name
- In-kind contributions (greiðsla í öðru en reiðufé): Must be valued by an independent auditor or appraiser (13. gr.)
- Shares can have different classes with different rights (e.g., voting, dividends)

**Step 3: Articles of Association (Samþykktir)**
- Distinct from the founders' agreement (though often combined in practice)
- Required contents (3. gr.):
  - Company name
  - Registered office
  - Purpose
  - Share capital and share structure
  - Governance structure (board, managing director)
  - Financial year
  - Provisions on share transfer restrictions (if any)
  - Provisions on dissolution

**Step 4: Governance Setup**
- **Board of directors (stjórn)**: at least three members, **unless the company has four or fewer shareholders**, in which case one or two suffice (lög nr. 138/1994, 39. gr.). The test is the number of SHAREHOLDERS, not the size of the share capital.
- **Managing director (framkvæmdastjóri)**: optional. 41. gr. is permissive — the board *may* appoint one or more. There is no share-capital threshold that makes it mandatory. Where a board of one exists, that person may also be the managing director; on a two-member board, one may be.
- **Alternate board members (varamenn)**: Required if board has fewer than 3 members
- Board members must be at least 18, have legal capacity, not be bankrupt
- Residency: managing directors **and at least half the board** must be resident in Iceland or another EEA/EFTA state (lög nr. 138/1994, 42. gr.). Verify against the current text — this is stricter than "at least one board member".

**Step 5: Registration with Fyrirtækjaskrá**
- File with Fyrirtækjaskrá (the Register of Enterprises, part of Skatturinn / Directorate of Internal Revenue)
- Required documents:
  - Founders' agreement
  - Articles of association
  - Minutes of the founding meeting
  - Confirmation of share capital payment (bank certificate)
  - Auditor's valuation (if in-kind contributions)
  - Board members' information (names, kennitölur, addresses)
  - Managing director information
  - Registration fee: approximately ISK 130,000 (verify current fee)
- Registration typically takes 3-7 business days
- Company gains legal personality upon registration

#### Key Ongoing Obligations

| Obligation | Frequency | Legal Basis |
|-----------|-----------|-------------|
| Annual financial statements (ársreikningur) | Annual | Lög nr. 3/2006 |
| File annual return with Fyrirtækjaskrá | Annual | Lög nr. 138/1994, 118. gr. |
| Annual general meeting (aðalfundur) | Within 8 months of financial year end | 59. gr. |
| Corporate income tax return | Annual | Lög nr. 90/2003 |
| VAT returns | Bimonthly (typically) | Lög nr. 50/1988 |
| Withholding tax (staðgreiðsla) | Monthly | Lög nr. 45/1987 |
| Beneficial ownership registration | Upon changes | Lög nr. 82/2019 |

#### Share Capital Changes

- **Increase**: Requires shareholder resolution (2/3 majority at general meeting). New shares can be offered to existing shareholders (pre-emption right, forkaupsréttur, unless waived).
- **Decrease**: Requires shareholder resolution and creditor protection procedure (6-month creditor notice period).
- **Dividends (arðgreiðslur)**: Can only be paid from distributable profits (free reserves and retained earnings). Solvency test applies (73. gr.).

### 2. Hlutafélag (hf) — Public Limited Company

**Governing law**: Lög nr. 2/1995 um hlutafélög

For larger companies, especially those seeking public listing on Nasdaq Iceland.

#### Key Differences from ehf

- **Minimum share capital**: ISK 4,000,000
- **Board**: Minimum 3 members (5 recommended for listed companies)
- **Managing director (forstjóri)**: Mandatory
- **Auditor**: Mandatory (independent, registered auditor)
- **Shares**: Freely transferable (restrictions in articles are limited)
- **Employee representation**: If 50+ employees, employees have right to elect board representatives
- **Prospectus requirements**: For public offerings, must comply with Lög nr. 14/2020 (Prospectus Regulation implementation)
- **Corporate governance**: Listed companies must follow Icelandic Corporate Governance Guidelines (Leiðbeiningar um stjórnarhætti fyrirtækja) on comply-or-explain basis

#### Listed Company Additional Requirements

If listed on Nasdaq Iceland (Kauphöllin):
- Lög nr. 108/2007 (Securities Transactions Act)
- Insider trading rules (innherjaviðskipti)
- Market abuse regulation (MAR, as adopted into EEA)
- Continuous disclosure obligations (upplýsingaskylda)
- Related party transaction rules
- Takeover rules (Lög nr. 108/2007, XIII. kafli)

### 3. Sameignarfélag (sf) — General Partnership

**Governing law**: Lög nr. 50/2007 um sameignarfélög

#### Key Features

- **Unlimited liability**: Partners are jointly and severally liable for all debts
- **Minimum partners**: 2 (natural persons or legal entities)
- **No minimum capital**: No share capital requirement
- **Partnership agreement (félagssamningur)**: Governs internal relations. If absent, default rules in Lög nr. 50/2007 apply
- **Tax transparency**: The partnership itself is not taxed. Income flows through to partners (Lög nr. 90/2003, 2. gr.)
- **Registration**: Must register with Fyrirtækjaskrá
- **Common use**: Professional firms (law firms, accounting firms), family businesses, joint ventures

#### Partnership Agreement Should Cover

- Capital contributions (fjárframlög)
- Profit and loss sharing ratio
- Management and decision-making
- Admission and withdrawal of partners
- Non-compete obligations
- Dissolution and winding-up
- Dispute resolution between partners

### 4. Samvinnufélag (svf) — Cooperative Society

**Governing law**: Lög nr. 22/1991 um samvinnufélög

#### Key Features

- **Minimum members**: 5 at founding, minimum 2 at any time
- **Democratic governance**: One member, one vote (regardless of capital contribution)
- **Member-based**: Membership rights are non-transferable
- **Purpose**: Operate for the benefit of members through cooperative activity
- **Limited liability**: Members liable only for their contributions (unless articles provide otherwise)
- **Historical importance**: Cooperatives (especially agricultural: Samband, Kaupfélag) have deep roots in Icelandic economic history
- **Surplus distribution**: Based on patronage (member transactions), not capital contribution
- **Registration**: Must register with Fyrirtækjaskrá

#### Common Cooperative Types

- Agricultural cooperatives (búnaðarfélög)
- Consumer cooperatives
- Housing cooperatives (búsetusamvinnufélög — also governed by Lög nr. 66/2003)
- Worker cooperatives
- Fishing vessel cooperatives

### 5. Sjálfseignarstofnun (ses) — Self-Owning Foundation / Endowment

**Governing law**: Lög nr. 33/1999 um sjálfseignarstofnanir sem stunda atvinnurekstur (for business-operating foundations)

#### Key Features

- **No owners**: The foundation owns itself. The endowment is dedicated to a specified purpose
- **Endowment (stofnfé)**: Must be sufficient to fulfill the foundation's purpose
- **Board**: Manages the foundation according to the founding document (stofnskrá)
- **Limited use**: Charitable purposes, cultural institutions, research, public benefit
- **Tax treatment**: May be tax-exempt if operating for public benefit (Lög nr. 90/2003, 4. gr.)
- **Supervision**: Subject to oversight — annual accounts filed with the Interior Ministry

## Other Business Structures

### Branch of Foreign Company (Útibú erlends félags)

- Foreign companies can operate through a branch in Iceland
- Must register with Fyrirtækjaskrá (Lög nr. 50/2007, VIII. kafli)
- Must appoint a representative resident in Iceland
- The foreign parent bears full liability for branch obligations
- Must file annual accounts

### Individual Enterprise (Einstaklingsfyrirtæki)

- Sole proprietorship — no separate legal entity
- Owner has unlimited personal liability
- Must register with Skatturinn (Directorate of Internal Revenue)
- Simple to establish but unlimited risk exposure

## Formation Process: Step-by-Step (ehf — Most Common)

### Pre-Formation Checklist

- [ ] Choose entity type (ehf in most cases)
- [ ] Verify company name availability at Fyrirtækjaskrá
- [ ] Determine share capital amount (minimum ISK 500,000)
- [ ] Identify founders, board members, and managing director
- [ ] Determine registered office (lögheimili) — must be in Iceland
- [ ] Define company purpose (tilgangur)
- [ ] Decide on financial year (usually calendar year: Jan 1 — Dec 31)
- [ ] Engage an auditor if required or desired
- [ ] Open a temporary bank account for share capital deposit
- [ ] Draft founders' agreement and articles of association

### Registration Steps

1. **Draft documents**: Founders' agreement + articles of association
2. **Hold founding meeting**: Adopt articles, elect board, appoint managing director
3. **Deposit share capital**: Transfer ISK 500,000+ to bank account, obtain bank certificate
4. **File with Fyrirtækjaskrá**: Submit all documents + registration fee
5. **Receive kennitala**: Company receives its kennitala (corporate ID number, format: XXXXXX-XXXX)
6. **Register with Skatturinn**: For tax, VAT, and withholding obligations
7. **Register beneficial owners**: File UBO information under Lög nr. 82/2019
8. **Open permanent bank account**: With the company's kennitala
9. **Register employees**: If hiring, register with Skatturinn for PAYE and pension fund contributions

### Post-Formation Essentials

| Task | Deadline | Authority |
|------|----------|-----------|
| VAT registration (if turnover > ISK 2,000,000) | Before commencing business | Skatturinn |
| Pension fund registration | Before first payroll | Pension fund (lífeyrissjóður) |
| Insurance | Before operations | Insurance company |
| Workplace safety registration | Before operations | Vinnueftirlitið |
| Data protection registration | If processing personal data | Persónuvernd |

## Governance Requirements

### Board of Directors (Stjórn)

**Composition:**
- ehf: 1-3+ members (depending on share capital)
- hf: Minimum 3 members
- Gender balance: Companies with 50+ employees should aim for gender balance (Lög nr. 150/2020)

**Duties:**
- Fiduciary duty to the company (not individual shareholders)
- Duty of care (aðgæsluskylda)
- Duty of loyalty (trúnaðarskylda)
- Non-competition during tenure
- Oversight of managing director
- Approval of major decisions and strategy
- Ensure proper accounts and internal controls

**Liability:**
- Board members can be personally liable for damages caused by negligence or breach of duty (Lög nr. 138/1994, 108. gr.)
- Criminal liability for willful misconduct
- D&O insurance is common and recommended

### Managing Director (Framkvæmdastjóri)

- Responsible for day-to-day operations
- Acts within the framework set by the board
- Cannot be the chairman of the board in hf companies (Lög nr. 2/1995, 68. gr.)
- Reports to the board
- Can be personally liable for damages

### Annual General Meeting (Aðalfundur)

- Must be held within 8 months of financial year end
- Required agenda items:
  - Approval of annual accounts (ársreikningur)
  - Decision on profit distribution or loss allocation
  - Election of board members (if terms expiring)
  - Appointment of auditor (if required)
  - Any other matters in the articles
- Quorum: Simple majority of share capital represented (unless articles require more)
- Decisions: Simple majority vote, except for:
  - Amendments to articles: 2/3 majority of votes cast
  - Capital changes: 2/3 majority
  - Changes affecting share class rights: requires consent of affected class

## Capital Requirements and Financial Rules

### Share Capital Rules for ehf

| Rule | Requirement | Legal Basis |
|------|------------|-------------|
| Minimum capital | ISK 500,000 | 1. gr. |
| Payment before registration | 100% paid in | 12. gr. |
| In-kind contributions | Must be valued by independent party | 13. gr. |
| Capital maintenance | Share capital must be maintained (cannot distribute below minimum) | 73.-74. gr. |
| Dividends | Only from distributable profits + solvency test | 73. gr. |
| Loans to shareholders | Prohibited (with limited exceptions) | 79. gr. |
| Treasury shares | Company may acquire own shares within limits | 47.-48. gr. |

### Solvency Test for Dividends

Before distributing dividends, the board must confirm:
1. The company has sufficient distributable reserves
2. The distribution is prudent given the company's financial position, liquidity, and foreseeable obligations
3. The company can meet its liabilities as they fall due after the distribution

### Thin Capitalization

While Iceland does not have formal thin capitalization rules in company law, tax law (Lög nr. 90/2003, 57. gr. b) limits interest deductibility on related-party debt exceeding a 4:1 debt-to-equity ratio (transfer pricing rules).

## Tax Considerations for Entity Selection

| Tax | ehf/hf | sf | Individual |
|-----|--------|----|------------|
| Corporate income tax | 20% | Pass-through | N/A |
| Capital gains (company level) | 20% | Pass-through | 22% |
| Dividend withholding (individual) | 22% | N/A | N/A |
| VAT | Standard 24%, reduced 11% | Standard 24%, reduced 11% | Standard 24%, reduced 11% |
| Social security contribution | 6.35% (employer) | Per partner | Self-employed rate |
| Municipal tax | Included in employee's income tax | Per partner | Included |

**Note**: Tax rates are as of 2026. Verify current rates with Skatturinn.

## Output Format

Structure your company formation guidance as follows:

```markdown
# Company Formation Guidance: [Client/Project Name]

## 1. Recommended Entity Type
- **Entity**: [ehf / hf / sf / svf / ses]
- **Rationale**: [why this entity type suits the client's needs]
- **Alternative considered**: [and why rejected]

## 2. Formation Requirements
- **Share capital**: [amount]
- **Founders**: [number and details]
- **Registered office**: [municipality]
- **Financial year**: [start-end]

## 3. Governance Structure
- **Board**: [composition recommendation]
- **Managing director**: [required/optional, recommendation]
- **Auditor**: [required/optional]

## 4. Formation Timeline

| Step | Action | Timeline | Status |
|------|--------|----------|--------|
| 1 | [action] | [days] | [ ] |

## 5. Estimated Costs

| Item | Cost (ISK) |
|------|-----------|
| Registration fee | ~130,000 |
| Legal fees (document drafting) | [estimate] |
| Auditor (if in-kind contribution) | [estimate] |
| Share capital | [amount] |
| **Total** | [sum] |

## 6. Post-Formation Checklist
[Itemized list of registrations and obligations]

## 7. Ongoing Compliance Calendar
[Annual obligations and deadlines]

## 8. Disclaimer
This guidance is generated by an AI assistant and does not constitute legal advice.
Company formation involves legal, tax, and regulatory considerations that should
be reviewed by a licensed Icelandic attorney (lögmaður) and certified accountant
(endurskoðandi). Verify all fees, tax rates, and requirements with the relevant
authorities before proceeding.
```

## Foreign Investors: Additional Considerations

- **Investment restrictions**: Certain sectors (fishing, energy, aviation) have foreign ownership restrictions under Lög nr. 34/1991
- **EEA nationals**: Generally have the same rights as Icelandic nationals for business formation
- **Non-EEA nationals**: May face additional requirements; business immigration tied to residence permits
- **Transfer pricing**: Related-party transactions must be at arm's length (Lög nr. 90/2003, 57. gr.)
- **Central Bank reporting**: Foreign investment and capital flows may require Central Bank notification (Seðlabanki Íslands)
- **Beneficial ownership**: All companies must register beneficial owners with Fyrirtækjaskrá (Lög nr. 82/2019 implementing 5th AML Directive)
