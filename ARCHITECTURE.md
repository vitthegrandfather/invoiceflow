# InvoiceFlow architecture

InvoiceFlow is a fictional AP automation demo. The same validation rules exist in the browser engine (`src/lib/invoiceflow`) and the Python services (`backend/app/services/domain.py`).

## Four runtimes

1. **Browser walkthrough** — React + Zustand. Seeded Northwind workspace. Fully interactive without credentials.
2. **FastAPI artifact** — `backend/`. Ingest, extract, validate, approve, sandbox sync, audit, CSV, demo reset.
3. **n8n definitions** — importable JSON. Authenticated webhooks call the Docker API service with n8n-managed credentials.
4. **Simulated providers** — sandbox extraction, accounting, notifications, object storage. A configured production name **without** credentials raises `PROVIDER_MISCONFIGURED` and does **not** fall back.

```
Upload / email webhook / API
        → n8n intake (optional)
        → FastAPI ingest (idempotent)
        → extract (sandbox parser)
        → validate (integer cents, PO, duplicates, confidence, injection)
        → human review (required)
        → sandbox ledger (QBO-SB-*)
        → retry / dead-letter
        → error-handler (simulated ops)
```

## Layers (backend)

- `app/api` — HTTP only
- `app/services` — transitions, validation, sync
- `app/repositories` — SQLAlchemy
- `app/providers` — sandbox vs fail-closed production adapters
- `app/models` — UUID internals, public IDs (`INV-2026-00101`)
- `app/seed` — deterministic, idempotent

## Status machine

```
RECEIVED → EXTRACTING → NEEDS_REVIEW | VALIDATED | DUPLICATE | FAILED
NEEDS_REVIEW → VALIDATED | APPROVED | REJECTED | DUPLICATE
VALIDATED → APPROVED | REJECTED | NEEDS_REVIEW
APPROVED → SYNCING | REJECTED
SYNCING → SYNCED | FAILED
FAILED → SYNCING
DUPLICATE → NEEDS_REVIEW | REJECTED
```

No automatic approval. Invalid transitions return HTTP 409.

## Idempotency

- Ingest keys map to invoice public IDs.
- Sync keys map to sandbox bill IDs. Replays reuse the stored bill.

## Data

Workspace-scoped rows. Money stored as integer cents. Bank values stored as `••••` + last four.
