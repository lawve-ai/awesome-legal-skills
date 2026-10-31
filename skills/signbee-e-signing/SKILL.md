---
name: "signbee-e-signing"
description: "Document signing for AI agents and legal workflows — send Markdown or PDF contracts, NDAs, and agreements for two-party e-signing with tamper-evident SHA-256 cryptographic certificates, email OTP verification, and webhooks."
metadata:
  author: "Signbee"
  license: "MIT"
  version: "2026-10-31"
  repository: "https://github.com/signbee/skill"
---

# Signbee

Send contracts, NDAs, and agreements for two-party e-signing directly from Claude Code or any AI agent using Markdown or PDF files, complete with tamper-evident SHA-256 cryptographic signing certificates.

## When to Use This Skill

- Drafting and sending a Mutual NDA, freelance contract, or statement of work for signature
- Converting Markdown agreements into formatted, legally binding signed PDFs
- Checking signature status, sending reminders, or downloading SHA-256 signing certificates

## What This Skill Does

1. **Instant Document Creation & Delivery**: Converts agent-authored Markdown (or a PDF URL) into a formatted PDF and sends signing invitations to both parties.
2. **Two-Party Verification & E-Signing**: Verifies the sender via email OTP (or pre-verified API key) and routes the signed agreement to the recipient via a zero-account tokenized signing link.
3. **Cryptographic Audit Trail**: Appends a two-pass SHA-256 tamper-evident signing certificate with timestamps, IP audit trail, and digital signatures to the final PDF.
4. **Full Lifecycle Management via MCP & REST**: Supports status checks, reminders, voiding documents, and retrieving certificates via `npx -y signbee-mcp` or REST.

## How to Use

### Basic Usage

Install the skill globally:

```bash
npx skills add signbee/skill --skill signbee -g
```

Or add the MCP server to Claude Code:

```bash
claude mcp add signbee -- npx -y signbee-mcp
```

Prompt Claude:
```
Draft a Mutual NDA between Alice Chen (alice@startup.com) and Bob Smith (bob@acme.com) and send it for e-signing via Signbee.
```

### Advanced Usage

Send directly via the zero-config REST API:

```bash
curl -X POST https://signb.ee/api/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "markdown": "# Mutual NDA\n\nThis Non-Disclosure Agreement is entered into by the undersigned parties...",
    "sender_name": "Alice Chen",
    "sender_email": "alice@startup.com",
    "recipient_name": "Bob Smith",
    "recipient_email": "bob@acme.com"
  }'
```

## Example

**User**: "Send a 2-year Mutual NDA to Bob Smith (bob@acme.com) from Alice Chen (alice@startup.com) for signature."

**Output**:
```json
{
  "document_id": "doc_01J...",
  "status": "pending_sender",
  "message": "Verification email sent to alice@startup.com. Complete OTP verification to send the document to bob@acme.com."
}
```

**Inspired by:** [Signbee](https://github.com/signbee/skill) agentic legal & contract execution workflow.

## Tips

- Put the document title as the first `# Heading` in your Markdown so Signbee extracts it automatically.
- Use an optional `Authorization: Bearer <api_key>` from [signb.ee/dashboard](https://signb.ee/dashboard) to skip sender OTP verification on automated workflows.

## Common Use Cases

- Sending NDAs before sharing confidential repository access or architecture docs
- Executing consulting agreements, SOWs, and contractor onboarding paperwork from Claude Code
- Automating B2B sales order forms and vendor agreements with webhook callbacks
