import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardMeta, CardTitle } from "@/components/ui/card";
import { ERROR_NODES, INTAKE_NODES, SYNC_NODES } from "@/lib/invoiceflow/engine";
import { formatDateTime } from "@/lib/invoiceflow/format";
import { useInvoiceStore } from "@/lib/invoiceflow/store";
import { showResult } from "@/lib/invoiceflow/toast";
import type { WorkflowName } from "@/lib/invoiceflow/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/automations")({ component: AutomationsPage });

const DEFS: {
  id: WorkflowName;
  title: string;
  version: string;
  file: string;
  nodes: string[];
  description: string;
}[] = [
  {
    id: "invoice-intake",
    title: "Invoice intake",
    version: "1.4.0",
    file: "n8n/workflows/invoice-intake.json",
    nodes: INTAKE_NODES,
    description: "Webhook → validate → idempotency → FastAPI ingest → extract → validate → branch → record.",
  },
  {
    id: "accounting-sync",
    title: "Accounting sync",
    version: "1.2.1",
    file: "n8n/workflows/accounting-sync.json",
    nodes: SYNC_NODES,
    description: "Approved ID → read invoice → sandbox bill → store ID → record attempt → retry / dead-letter.",
  },
  {
    id: "error-handler",
    title: "Error handler",
    version: "1.1.0",
    file: "n8n/workflows/error-handler.json",
    nodes: ERROR_NODES,
    description: "Capture workflow, execution, failed node, category, retryability, redacted message.",
  },
];

function AutomationsPage() {
  const executions = useInvoiceStore((s) => s.workflowExecutions);
  const invoices = useInvoiceStore((s) => s.invoices);
  const simulate = useInvoiceStore((s) => s.simulateWorkflow);
  const [active, setActive] = useState<WorkflowName>("invoice-intake");
  const [step, setStep] = useState(-1);
  const def = DEFS.find((d) => d.id === active)!;

  useEffect(() => {
    if (step < 0) return;
    if (step >= def.nodes.length) return;
    const timer = window.setTimeout(() => setStep((s) => s + 1), 280);
    return () => window.clearTimeout(timer);
  }, [step, def.nodes.length]);

  const stats = useMemo(() => {
    return DEFS.map((item) => {
      const runs = executions.filter((e) => e.workflow === item.id);
      const ok = runs.filter((e) => e.status === "succeeded" || e.status === "waiting_review").length;
      const failed = runs.filter((e) => e.status === "failed").length;
      const avg = runs.length ? Math.round(runs.reduce((s, r) => s + r.durationMs, 0) / runs.length) : 0;
      const last = runs[0];
      return {
        ...item,
        last: last?.startedAt ?? null,
        successRate: runs.length ? Math.round((ok / runs.length) * 100) : 0,
        avg,
        processed: runs.length,
        failed,
        active: true,
      };
    });
  }, [executions]);

  function runSim() {
    setStep(0);
    const invoice = invoices.find((i) => i.status === "NEEDS_REVIEW") ?? invoices[0];
    window.setTimeout(() => {
      showResult(simulate(active, invoice?.publicId ?? null));
    }, def.nodes.length * 280 + 40);
  }

  return (
    <div>
      <PageHeader
        title="Automations"
        description="Importable n8n workflow JSON lives in the repository. This page simulates the same stages in-process so the preview never needs n8n credentials."
      />
      <div className="grid gap-3 lg:grid-cols-3">
        {stats.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              setActive(item.id);
              setStep(-1);
            }}
            className={cn(
              "rounded-lg bg-surface p-4 text-left shadow-[var(--shadow-card)]",
              active === item.id && "ring-2 ring-accent/30",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium">{item.title}</div>
              <Badge tone="accent">active</Badge>
            </div>
            <p className="mt-2 text-xs text-muted">{item.description}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-subtle">Last execution</dt>
                <dd className="font-mono">{item.last ? formatDateTime(item.last).slice(0, 16) : "—"}</dd>
              </div>
              <div>
                <dt className="text-subtle">Success rate</dt>
                <dd className="font-mono tabular-nums">{item.successRate}%</dd>
              </div>
              <div>
                <dt className="text-subtle">Avg duration</dt>
                <dd className="font-mono tabular-nums">{item.avg} ms</dd>
              </div>
              <div>
                <dt className="text-subtle">Runs / failed</dt>
                <dd className="font-mono tabular-nums">
                  {item.processed} / {item.failed}
                </dd>
              </div>
              <div>
                <dt className="text-subtle">Version</dt>
                <dd className="font-mono">{item.version}</dd>
              </div>
              <div>
                <dt className="text-subtle">Export</dt>
                <dd className="font-mono text-[10px]">{item.file}</dd>
              </div>
            </dl>
          </button>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader>
          <div>
            <CardTitle>Simulate {def.title}</CardTitle>
            <CardMeta>
              Walks the nodes locally. The importable workflow is {def.file} — n8n is not called from this browser.
            </CardMeta>
          </div>
          <Button id="simulate-execution" onClick={runSim}>Simulate execution</Button>
        </CardHeader>
        <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {def.nodes.map((name, index) => {
            const done = step > index;
            const current = step === index;
            return (
              <li
                key={name}
                className={cn(
                  "rounded-md border px-3 py-2 text-sm",
                  done ? "border-accent bg-accent-soft text-accent" : current ? "border-amber bg-amber-soft text-amber" : "border-line text-muted",
                )}
              >
                <div className="font-mono text-[11px]">{String(index + 1).padStart(2, "0")}</div>
                {name}
              </li>
            );
          })}
        </ol>
      </Card>

      <Card className="mt-4 p-0">
        <div className="px-4 pt-4">
          <CardTitle>Workflow executions</CardTitle>
        </div>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[800px] text-sm">
            <thead className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Execution</th>
                <th className="px-3 py-2 text-left font-medium">Workflow</th>
                <th className="px-3 py-2 text-left font-medium">Invoice</th>
                <th className="px-3 py-2 text-left font-medium">Started</th>
                <th className="px-3 py-2 text-left font-medium">Duration</th>
                <th className="px-3 py-2 text-left font-medium">Status</th>
                <th className="px-3 py-2 text-left font-medium">Failed node</th>
                <th className="px-3 py-2 text-left font-medium">Retry</th>
              </tr>
            </thead>
            <tbody>
              {executions.map((run) => (
                <tr key={run.id} className="border-b border-line last:border-0">
                  <td className="px-3 py-2 font-mono text-xs">{run.publicId}</td>
                  <td className="px-3 py-2">{run.workflow}</td>
                  <td className="px-3 py-2">
                    {run.invoicePublicId ? (
                      <Link
                        to="/invoices/$invoiceId"
                        params={{ invoiceId: run.invoicePublicId }}
                        className="font-mono text-xs text-accent hover:underline"
                      >
                        {run.invoicePublicId}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px]">{formatDateTime(run.startedAt)}</td>
                  <td className="px-3 py-2 font-mono tabular-nums">{run.durationMs} ms</td>
                  <td className="px-3 py-2">{run.status.replaceAll("_", " ")}</td>
                  <td className="px-3 py-2">{run.failedNode ?? "—"}</td>
                  <td className="px-3 py-2">{run.retryState}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
