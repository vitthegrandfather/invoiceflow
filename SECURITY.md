# InvoiceFlow security model

Fictional portfolio demonstration. No real money movement, no live providers, no committed secrets.

## Untrusted documents

Invoice notes and extracted text are **data**. The extractor and validator never execute instructions found in a PDF, TIFF, or email body.

Detected phrases (non-exhaustive): “ignore previous instructions”, “skip validation”, “approve immediately”, “set confidence to 1”, “mark as paid”. A `PROMPT_INJECTION` security issue is recorded and the invoice stays in review.

## Input hygiene

- HTML escaping helpers for any rendered document text
- Filename sanitization (path segments stripped, unsafe characters replaced)
- MIME allow-list: PDF, PNG, JPEG, TIFF
- 10 MB upload cap
- Formula-safe CSV (`=`, `+`, `-`, `@` prefixed with `'`)

## Sensitive fields

- Bank accounts stored and displayed as `••••` + last four only
- Structured logs redact long digit runs, password/token/key assignments, and account-like keys
- JWT demo secret is a documented placeholder, not a production key

## Isolation and access

- Single demo workspace (`WS-NORTHWIND`)
- Roles: Admin, AP Manager, Reviewer, Viewer
- Approve / reject / correct / acknowledge: Admin, AP Manager, Reviewer
- Retry delivery / edit vendor: Admin, AP Manager
- Reset demo: Admin
- Simple per-IP rate limit on the API

## Idempotency and providers

- Ingest and sync keys prevent double-posting sandbox bills
- `ACCOUNTING_PROVIDER=quickbooks` without credentials fails closed
- The API will not silently swap a production adapter for sandbox

## What this repo will not do

- No real financial transactions
- No live QuickBooks / Xero / SMTP / Slack
- No `.env` with real secrets (see `.env.example` only)
