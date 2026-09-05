# n8n workflows for InvoiceFlow

These files are importable n8n workflow JSON, not screenshots. InvoiceFlow is a fictional portfolio demonstration. The workflows call the Docker Compose service at `http://api:8000` and authenticate through n8n credentials; they contain no live accounting, messaging, or API secrets.

## Files

| File | Trigger | Purpose |
|---|---|---|
| `workflows/invoice-intake.json` | Authenticated webhook `POST /webhook/invoice-intake` | Validate payload, set idempotency key, ingest, extract, validate, branch to review, record execution |
| `workflows/accounting-sync.json` | Authenticated webhook `POST /webhook/accounting-sync` | Load an approved invoice, create a sandbox bill with bounded retries, and record delivered or dead-letter state |
| `workflows/error-handler.json` | Error Trigger | Capture workflow and execution context, classify retryability, redact sensitive numbers, and POST a simulated operations alert |

## Import and wire-up

1. Open n8n (the Docker Compose service defaults to `http://localhost:5678`).
2. Import all three JSON files from **Import from file**.
3. Create and bind these credentials in every matching node:
   - **InvoiceFlow API** — credential type **Header Auth**, header `Authorization`, value `Bearer <demo JWT from POST /auth/login>`.
   - **InvoiceFlow Webhook** — credential type **Header Auth**, using a local demo-only inbound secret.
4. If n8n and the API are not running in the supplied Docker Compose network, replace the `http://api:8000` base URL in each HTTP Request node.
5. In both business workflows, select **InvoiceFlow Error Handler** as the workflow-level error workflow. The exported files do not hard-code this link because n8n stores an instance-specific workflow ID.
6. Open every credentialed node and confirm the intended credential is selected.
7. Keep both webhooks inactive until representative local test payloads pass.

The browser walkthrough does not execute n8n. Use **Automations → Simulate execution** for the in-process portfolio demo.

## Error payload

The handler records the workflow name, execution ID, failed node, category, retryability, redacted error message, timestamp, and related invoice ID.
