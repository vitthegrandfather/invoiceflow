import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { canRetryDelivery } from "@/lib/invoiceflow/domain";
import { formatDateTime } from "@/lib/invoiceflow/format";
import { useCurrentUser, useInvoiceStore } from "@/lib/invoiceflow/store";
import { showResult } from "@/lib/invoiceflow/toast";

export const Route = createFileRoute("/deliveries")({ component: DeliveriesPage });

function tone(status: string): "accent" | "amber" | "danger" | "neutral" | "info" {
  if (status === "succeeded") return "accent";
  if (status === "pending" || status === "retrying") return "info";
  if (status === "failed_dead_letter") return "danger";
  if (status.startsWith("failed")) return "amber";
  return "neutral";
}

function DeliveriesPage() {
  const deliveries = useInvoiceStore((s) => s.deliveries);
  const user = useCurrentUser();
  const retry = useInvoiceStore((s) => s.retryDelivery);
  const allowed = canRetryDelivery(user.role);

  return (
    <div>
      <PageHeader
        title="Deliveries"
        description="Sandbox accounting attempts only. Retry is idempotent and never calls a live QuickBooks or Xero tenant."
      />
      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] text-sm">
            <thead className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Delivery</th>
                <th className="px-3 py-2 text-left font-medium">Invoice</th>
                <th className="px-3 py-2 text-left font-medium">Provider</th>
                <th className="px-3 py-2 text-left font-medium">Attempt</th>
                <th className="px-3 py-2 text-left font-medium">Status</th>
                <th className="px-3 py-2 text-left font-medium">HTTP</th>
                <th className="px-3 py-2 text-left font-medium">Duration</th>
                <th className="px-3 py-2 text-left font-medium">Next retry</th>
                <th className="px-3 py-2 text-left font-medium">Bill ID</th>
                <th className="px-3 py-2 text-left font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((d) => (
                <tr key={d.id} className="border-b border-line align-top last:border-0">
                  <td className="px-3 py-2 font-mono text-xs">{d.publicId}</td>
                  <td className="px-3 py-2">
                    <Link to="/invoices/$invoiceId" params={{ invoiceId: d.invoicePublicId }} className="font-mono text-xs text-accent hover:underline">
                      {d.invoicePublicId}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{d.provider}</td>
                  <td className="px-3 py-2 font-mono">{d.attemptNumber}</td>
                  <td className="px-3 py-2">
                    <Badge tone={tone(d.status)}>{d.status.replaceAll("_", " ")}</Badge>
                  </td>
                  <td className="px-3 py-2 font-mono">{d.responseCode || "—"}</td>
                  <td className="px-3 py-2 font-mono tabular-nums">{d.durationMs ? `${d.durationMs} ms` : "—"}</td>
                  <td className="px-3 py-2 font-mono text-[11px]">{d.nextRetryAt ? formatDateTime(d.nextRetryAt) : "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{d.providerBillId ?? "—"}</td>
                  <td className="px-3 py-2">
                    {d.status !== "succeeded" && d.status !== "pending" ? (
                      <Button size="sm" variant="outline" disabled={!allowed} onClick={() => showResult(retry(d.id))}>
                        Retry
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="space-y-3 border-t border-line p-4">
          {deliveries
            .filter((d) => d.redactedError)
            .slice(0, 4)
            .map((d) => (
              <div key={d.id}>
                <div className="text-xs font-medium text-ink">
                  {d.publicId} · redacted error
                </div>
                <p className="text-xs text-muted">{d.redactedError}</p>
                <pre className="mt-1 max-h-32 overflow-auto rounded-md bg-canvas p-2 font-mono text-[11px]">{d.redactedRequest}</pre>
              </div>
            ))}
        </div>
      </Card>
    </div>
  );
}
