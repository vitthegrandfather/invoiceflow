# InvoiceFlow demo walkthrough

InvoiceFlow is a fictional portfolio demonstration. Nothing in this walkthrough contacts a live accounting, email, or banking system.

## Recommended screenshot order

1. **Overview** — operational metrics and 14-day volume. Best **cover image**.
2. **Review queue** — five featured exceptions, including the clean invoice.
3. **INV-2026-00101 detail** — field confidence, matched totals, approve + sandbox sync.
4. **INV-2026-00102** — duplicate match against INV-2026-00097.
5. **INV-2026-00103** — PO variance with expected / received / percent. Approval disabled.
6. **INV-2026-00104** — low-confidence fields highlighted, correction + rerun validation.
7. **INV-2026-00105 / Deliveries** — 422/503, retry count, dead-letter, redacted payload.
8. **INV-2026-00106** — hostile instruction ignored, security event.
9. **Automations** — node walker for invoice-intake.
10. **Architecture** — four runtime layers.

## Exact walkthrough

1. Open **Settings**. Switch to Jordan Hale (Admin) and **Reset demo data**, then switch back to Maya Chen.
2. Open **INV-2026-00101**. Confirm subtotal $1,140.00 + tax $108.60 = $1,248.60, confidence 0.96, no blockers.
3. **Approve**. Status becomes Approved.
4. **Run sandbox sync**. Toast: sandbox bill created; **no real accounting provider was contacted**.
5. Confirm fictional `QBO-SB-*` bill id and an audit event.
6. Open **INV-2026-00102**. Original is INV-2026-00097. Reasons: same vendor, number, amount, currency, date. Record is retained.
7. Open **INV-2026-00103**. Approve is disabled. Expected €4,100.00, received €4,510.00, difference €410.00 (10.00%).
8. Enter an internal reason, **Acknowledge variance**. Approve becomes available.
9. Open **INV-2026-00104**. Uncertain fields are highlighted.
10. Correct vendor name to `Harborline Facilities`, save, **Rerun validation**. Confidence and audit update.
11. Open **INV-2026-00105** (or Deliveries) and **Retry**. Idempotent sandbox retry; still no live tenant.
12. Open **INV-2026-00106**. Notes contain an ignore-instructions phrase. Status stays Needs review. Instruction is not executed.
13. Open **Automations** and **Simulate execution**. Nodes walk in order; n8n is not called.
14. Open **Architecture** and confirm the four layers.
15. Resize to ~390px. Tables scroll inside the card; the page does not overflow horizontally.
16. Footer remains: *Demo workspace — all invoices, vendors, bank details, and integrations are fictional.*

## Portfolio captions

- “Human-in-the-loop AP workspace: extraction confidence, PO variance, and sandbox delivery — no auto-approval.”
- “Duplicate fingerprinting that preserves the submitted record.”
- “Untrusted document handling: prompt-injection style notes are data, not instructions.”

## Cover image

Use **Overview** (desktop 1440×900) or the **Review queue** with INV-2026-00101 selected. Avoid decorative AI imagery.
