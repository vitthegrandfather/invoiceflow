import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/app-shell";
import { Card, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/architecture")({ component: ArchitecturePage });

const LAYERS = [
  {
    title: "Browser walkthrough",
    body: "This preview runs the intake, validation, review, and sandbox-sync stages in-process. State lives in the workspace store so the demo is fully interactive without API keys.",
  },
  {
    title: "FastAPI backend artifact",
    body: "backend/ is a standalone Python service: ingestion, extraction, validation, approvals, deliveries, audit, CSV export, and demo reset. Business rules sit in services, not route handlers.",
  },
  {
    title: "n8n workflow definitions",
    body: "n8n/workflows contains importable JSON for invoice-intake, accounting-sync, and error-handler. They call the Docker API service with n8n-managed credentials. This browser never starts n8n.",
  },
  {
    title: "Simulated provider delivery",
    body: "Accounting, OCR, notifications, and object storage use sandbox providers. A configured production adapter without credentials fails closed — it does not silently fall back.",
  },
];

function ArchitecturePage() {
  return (
    <div>
      <PageHeader
        title="Architecture"
        description="InvoiceFlow separates the interactive demo from the deployable automation stack. The same validation rules apply in both."
      />

      <div className="grid gap-3 md:grid-cols-2">
        {LAYERS.map((layer) => (
          <Card key={layer.title}>
            <CardTitle>{layer.title}</CardTitle>
            <p className="mt-2 text-sm text-muted">{layer.body}</p>
          </Card>
        ))}
      </div>

      <Card className="mt-4 overflow-x-auto">
        <CardTitle>System flow</CardTitle>
        <div className="mt-4 min-w-[640px] font-mono text-[11px] leading-6 text-ink">
          <div className="grid grid-cols-6 gap-2 text-center">
            {["Upload / email webhook / API", "n8n intake", "FastAPI ingest", "Extract + validate", "Human review", "Sandbox ledger"].map(
              (label, i) => (
                <div key={label} className="rounded-md bg-canvas px-2 py-3">
                  <div className="text-[10px] text-subtle">{String(i + 1).padStart(2, "0")}</div>
                  {label}
                </div>
              ),
            )}
          </div>
          <p className="mt-3 text-center text-muted">↓ failures → error-handler → retry / dead-letter → ops notice (simulated)</p>
        </div>
      </Card>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Card>
          <CardTitle>Status machine</CardTitle>
          <pre className="mt-3 overflow-auto font-mono text-xs text-muted">{`RECEIVED → EXTRACTING
EXTRACTING → NEEDS_REVIEW | VALIDATED | DUPLICATE | FAILED
NEEDS_REVIEW → VALIDATED | APPROVED | REJECTED | DUPLICATE
VALIDATED → APPROVED | REJECTED | NEEDS_REVIEW
APPROVED → SYNCING | REJECTED
SYNCING → SYNCED | FAILED
FAILED → SYNCING
DUPLICATE → NEEDS_REVIEW | REJECTED
No auto-approval. Human action required.`}</pre>
        </Card>
        <Card>
          <CardTitle>Deterministic rules</CardTitle>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
            <li>Subtotal + tax = total (integer cents)</li>
            <li>Currencies: USD, EUR, GBP</li>
            <li>Due date not before issue date</li>
            <li>Duplicate fingerprint: vendor, number, amount, currency, date</li>
            <li>PO variance: expected, received, absolute, percent</li>
            <li>Field confidence threshold 0.85</li>
            <li>Prompt-injection phrases flagged, never executed</li>
            <li>Idempotency keys on ingest and sync</li>
            <li>Bank values masked to last four</li>
          </ul>
        </Card>
        <Card>
          <CardTitle>Repository layout</CardTitle>
          <pre className="mt-3 overflow-auto font-mono text-xs text-muted">{`src/                 interactive workspace
backend/            FastAPI + Alembic + pytest
n8n/workflows/      importable JSON
docker-compose.yml  Postgres, Redis, API, n8n, frontend
.env.example        fictional placeholders only`}</pre>
        </Card>
        <Card>
          <CardTitle>What this preview does not do</CardTitle>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
            <li>Does not contact QuickBooks, Xero, banks, or SMTP</li>
            <li>Does not run the Python process or n8n runtime</li>
            <li>Does not execute instructions found in invoice notes</li>
            <li>Does not persist real payment instruments</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
