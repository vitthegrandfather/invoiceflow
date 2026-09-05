import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState, type ReactNode } from "react";
import { StatusBadge } from "@/components/invoice/status-badge";
import { PageHeader } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardMeta, CardTitle } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { approvalBlockedReason, canApprove, canCorrectFields, canRetryDelivery, formatMoney, lowConfidenceFields } from "@/lib/invoiceflow/domain";
import { confidencePct, fieldLabel, formatAmount, formatDate, formatDateTime, sourceLabel } from "@/lib/invoiceflow/format";
import { useCurrentUser, useInvoiceStore } from "@/lib/invoiceflow/store";
import { showResult } from "@/lib/invoiceflow/toast";
import type { FieldName } from "@/lib/invoiceflow/types";
import { CONFIDENCE_THRESHOLD } from "@/lib/invoiceflow/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/invoices/$invoiceId")({ component: InvoiceDetailPage });

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 text-sm text-ink">{children}</div>
    </div>
  );
}

function InvoiceDetailPage() {
  const { invoiceId } = Route.useParams();
  const invoices = useInvoiceStore((s) => s.invoices);
  const pos = useInvoiceStore((s) => s.purchaseOrders);
  const allDeliveries = useInvoiceStore((s) => s.deliveries);
  const allAudit = useInvoiceStore((s) => s.auditEvents);
  const invoice = invoices.find((i) => i.publicId === invoiceId || i.id === invoiceId);
  const original = invoice?.duplicateMatch
    ? invoices.find((i) => i.publicId === invoice.duplicateMatch?.matchedPublicId)
    : undefined;
  const po = pos.find((p) => p.id === invoice?.poId || p.publicId === invoice?.poNumber);
  const deliveries = allDeliveries.filter((d) => d.invoicePublicId === invoiceId || d.invoiceId === invoice?.id);
  const audit = allAudit.filter((e) => e.entityId === invoiceId || e.entityId === invoice?.id);
  const user = useCurrentUser();
  const store = useInvoiceStore();
  const [reason, setReason] = useState("");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [rejectReason, setRejectReason] = useState("");
  const [uniqueReason, setUniqueReason] = useState("Different document batch");

  const blocked = invoice ? approvalBlockedReason(invoice) : null;
  const low = invoice ? lowConfidenceFields(invoice) : [];
  const jsonPayload = useMemo(() => {
    if (!invoice) return "";
    return JSON.stringify(
      {
        public_id: invoice.publicId,
        vendor: invoice.vendorName,
        invoice_number: invoice.invoiceNumber,
        currency: invoice.currency,
        subtotal: (invoice.subtotalCents / 100).toFixed(2),
        tax: (invoice.taxCents / 100).toFixed(2),
        total: (invoice.totalCents / 100).toFixed(2),
        issue_date: invoice.issueDate,
        due_date: invoice.dueDate,
        po_number: invoice.poNumber,
        bank_account_suffix: invoice.bankAccountSuffix,
        line_items: invoice.lineItems.map((l) => ({
          description: l.description,
          quantity: l.quantity,
          amount: (l.amountCents / 100).toFixed(2),
        })),
        fingerprint: invoice.fingerprint,
      },
      null,
      2,
    );
  }, [invoice]);

  if (!invoice) {
    return (
      <div>
        <PageHeader title="Invoice not found" />
        <p className="text-sm text-muted">
          No invoice with ID {invoiceId}. <Link to="/invoices" className="text-accent hover:underline">Back to invoices</Link>
        </p>
      </div>
    );
  }

  const canAct = canCorrectFields(user.role);
  const canAppr = canApprove(user.role);
  const canSync = canRetryDelivery(user.role) || canAppr;

  return (
    <div>
      <PageHeader
        title={invoice.publicId}
        description={`${invoice.vendorName} · ${sourceLabel(invoice.source)}`}
        actions={
          <>
            <StatusBadge status={invoice.status} />
            {invoice.status === "APPROVED" || invoice.status === "FAILED" ? (
              <Button
                disabled={!canSync}
                id="sync-invoice"
                onClick={() => showResult(store.syncAccounting(invoice.publicId))}
              >
                Run sandbox sync
              </Button>
            ) : null}
            {["NEEDS_REVIEW", "VALIDATED"].includes(invoice.status) ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    className="h-9 w-44"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Rejection reason"
                    aria-label="Rejection reason"
                  />
                  <Button
                    variant="outline"
                    disabled={!canAppr || !rejectReason.trim()}
                    onClick={() => showResult(store.rejectInvoice(invoice.publicId, rejectReason))}
                  >
                    Reject
                  </Button>
                </div>
                <Button
                  id="approve-invoice"
                  disabled={!canAppr || Boolean(blocked)}
                  title={blocked ?? undefined}
                  onClick={() => showResult(store.approveInvoice(invoice.publicId))}
                >
                  Approve
                </Button>
              </>
            ) : null}
          </>
        }
      />

      {blocked && ["NEEDS_REVIEW", "VALIDATED", "DUPLICATE"].includes(invoice.status) ? (
        <div className="mb-4 rounded-md bg-amber-soft px-3 py-2 text-sm text-amber">{blocked}</div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-4">
        <Card className="lg:col-span-3">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Meta label="Vendor">{invoice.vendorName}</Meta>
            <Meta label="Invoice number">
              <span className="font-mono">{invoice.invoiceNumber}</span>
            </Meta>
            <Meta label="Amount">
              <span className="font-mono tabular-nums">{formatAmount(invoice.totalCents, invoice.currency)}</span>
            </Meta>
            <Meta label="Subtotal">
              <span className="font-mono tabular-nums">{formatAmount(invoice.subtotalCents, invoice.currency)}</span>
            </Meta>
            <Meta label="Tax">
              <span className="font-mono tabular-nums">{formatAmount(invoice.taxCents, invoice.currency)}</span>
            </Meta>
            <Meta label="Currency">
              <span className="font-mono">{invoice.currency}</span>
            </Meta>
            <Meta label="Issue date">
              <span className="font-mono">{formatDate(invoice.issueDate)}</span>
            </Meta>
            <Meta label="Due date">
              <span className="font-mono">{formatDate(invoice.dueDate)}</span>
            </Meta>
            <Meta label="Payment terms">{invoice.paymentTerms}</Meta>
            <Meta label="PO reference">
              <span className="font-mono">{invoice.poNumber ?? "—"}</span>
            </Meta>
            <Meta label="Source">{sourceLabel(invoice.source)}</Meta>
            <Meta label="Bank (masked)">
              <span className="font-mono">{invoice.bankAccountSuffix}</span>
            </Meta>
            <Meta label="Extraction confidence">
              <span className="font-mono tabular-nums">{confidencePct(invoice.extractionConfidence)}</span>
            </Meta>
            <Meta label="Duplicate score">
              <span className="font-mono tabular-nums">{invoice.duplicateScore.toFixed(2)}</span>
            </Meta>
            <Meta label="Reviewer">{invoice.assignedReviewer ?? "Unassigned"}</Meta>
            <Meta label="Created">
              <span className="font-mono text-xs">{formatDateTime(invoice.createdAt)}</span>
            </Meta>
            <Meta label="Updated">
              <span className="font-mono text-xs">{formatDateTime(invoice.updatedAt)}</span>
            </Meta>
            <Meta label="Provider bill">
              <span className="font-mono">{invoice.providerBillId ?? "—"}</span>
            </Meta>
          </div>
        </Card>
        <Card>
          <CardTitle>Policy</CardTitle>
          <ul className="mt-2 space-y-1 text-xs text-muted">
            <li>No automatic approval</li>
            <li>Integer-cent arithmetic</li>
            <li>Untrusted document text</li>
            <li>Sandbox providers only</li>
          </ul>
          {invoice.approval ? (
            <p className="mt-3 text-xs text-muted">
              {invoice.approval.action} by {invoice.approval.actorName} · {formatDateTime(invoice.approval.at)}
            </p>
          ) : null}
        </Card>
      </div>

      <Card className="mt-3">
        <CardHeader>
          <div>
            <CardTitle>Field-level confidence</CardTitle>
            <CardMeta>Threshold {CONFIDENCE_THRESHOLD * 100}% · uncertain fields are highlighted</CardMeta>
          </div>
          {canAct ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => showResult(store.rerunValidation(invoice.publicId))}
            >
              Rerun validation
            </Button>
          ) : null}
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="py-1 text-left font-medium">Field</th>
                <th className="py-1 text-left font-medium">Value</th>
                <th className="py-1 text-left font-medium">Confidence</th>
                <th className="py-1 text-left font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {invoice.fields.map((field) => {
                const uncertain = field.confidence < CONFIDENCE_THRESHOLD && !field.corrected;
                return (
                  <tr key={field.name} className={cn("border-t border-line", uncertain && "bg-amber-soft/60")}>
                    <td className="py-2 capitalize">{fieldLabel(field.name)}</td>
                    <td className="py-2">
                      {canAct ? (
                        <Input
                          className="h-8 font-mono text-xs"
                          defaultValue={edits[field.name] ?? field.value}
                          onChange={(e) => setEdits((m) => ({ ...m, [field.name]: e.target.value }))}
                          aria-label={fieldLabel(field.name)}
                        />
                      ) : (
                        <span className="font-mono text-xs">{field.value || "—"}</span>
                      )}
                    </td>
                    <td className="py-2 font-mono tabular-nums text-xs">
                      {confidencePct(field.confidence)}
                      {field.corrected ? <Badge className="ml-2" tone="accent">corrected</Badge> : null}
                    </td>
                    <td className="py-2">
                      {canAct ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            showResult(
                              store.correctField(
                                invoice.publicId,
                                field.name as FieldName,
                                edits[field.name] ?? field.value,
                              ),
                            )
                          }
                        >
                          Save
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {low.length > 0 ? (
          <p className="mt-2 text-xs text-amber">
            {low.length} field{low.length === 1 ? "" : "s"} below threshold
            {invoice.publicId === "INV-2026-00104" ? " — correct a value, save, then rerun validation." : "."}
          </p>
        ) : null}
      </Card>

      <Card className="mt-3 p-0">
        <div className="px-4 pt-4">
          <CardTitle>Line items</CardTitle>
        </div>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Description</th>
                <th className="px-4 py-2 text-left font-medium">Qty</th>
                <th className="px-4 py-2 text-left font-medium">Unit</th>
                <th className="px-4 py-2 text-left font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lineItems.map((line) => (
                <tr key={line.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-2">{line.description}</td>
                  <td className="px-4 py-2 font-mono">{line.quantity}</td>
                  <td className="px-4 py-2 font-mono tabular-nums">{formatMoney(line.unitPriceCents, invoice.currency)}</td>
                  <td className="px-4 py-2 font-mono tabular-nums">{formatMoney(line.amountCents, invoice.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="mt-3">
        <CardTitle>Validation issues</CardTitle>
        {invoice.issues.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No validation issues. Calculations and vendor details match.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {invoice.issues.map((issue) => (
              <li
                key={issue.id}
                className={cn(
                  "rounded-md px-3 py-2 text-sm",
                  issue.severity === "security"
                    ? "bg-danger-soft text-danger"
                    : issue.severity === "error"
                      ? "bg-danger-soft/70 text-danger"
                      : "bg-amber-soft text-amber",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={issue.severity === "warning" ? "amber" : "danger"}>{issue.code}</Badge>
                  {issue.blocking && !issue.acknowledged ? <span className="text-[11px] uppercase">blocking</span> : null}
                  {issue.acknowledged ? <span className="text-[11px] uppercase">acknowledged</span> : null}
                </div>
                <p className="mt-1">{issue.message}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {invoice.duplicateMatch ? (
        <Card className="mt-3">
          <CardTitle>Duplicate match</CardTitle>
          <p className="mt-2 text-sm text-muted">
            Probable original{" "}
            <Link
              to="/invoices/$invoiceId"
              params={{ invoiceId: invoice.duplicateMatch.matchedPublicId }}
              className="font-mono text-accent hover:underline"
            >
              {invoice.duplicateMatch.matchedPublicId}
            </Link>{" "}
            · score {invoice.duplicateMatch.score.toFixed(2)} · decision {invoice.duplicateMatch.decision.replaceAll("_", " ")}
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm text-ink">
            {invoice.duplicateMatch.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          {original ? (
            <p className="mt-2 text-xs text-muted">
              Original {original.publicId} is {original.status.toLowerCase()} with sandbox bill {original.providerBillId ?? "—"}.
            </p>
          ) : null}
          {canAct && invoice.duplicateMatch.decision === "pending" ? (
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
              <Button variant="outline" onClick={() => showResult(store.confirmDuplicate(invoice.publicId))}>
                Confirm duplicate
              </Button>
              <Input
                className="sm:max-w-xs"
                value={uniqueReason}
                onChange={(e) => setUniqueReason(e.target.value)}
                aria-label="Unique reason"
              />
              <Button
                variant="secondary"
                onClick={() => showResult(store.markUnique(invoice.publicId, uniqueReason))}
              >
                Mark as unique
              </Button>
            </div>
          ) : null}
        </Card>
      ) : null}

      {po && invoice.issues.some((i) => i.code === "PO_VARIANCE") ? (
        <Card className="mt-3">
          <CardTitle>Purchase-order variance</CardTitle>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <Meta label="PO">{po.publicId}</Meta>
            <Meta label="Expected">
              <span className="font-mono">{formatMoney(po.amountCents, po.currency)}</span>
            </Meta>
            <Meta label="Received">
              <span className="font-mono">{formatMoney(invoice.totalCents, invoice.currency)}</span>
            </Meta>
            <Meta label="Difference">
              <span className="font-mono">
                {formatMoney(Math.abs(invoice.totalCents - po.amountCents), invoice.currency)} (
                {((Math.abs(invoice.totalCents - po.amountCents) / po.amountCents) * 100).toFixed(2)}%)
              </span>
            </Meta>
          </div>
          {invoice.varianceAcknowledged ? (
            <p className="mt-3 text-sm text-muted">Acknowledged: {invoice.varianceReason}</p>
          ) : canAct ? (
            <div className="mt-3 space-y-2">
              <Label htmlFor="var-reason">Internal reason</Label>
              <Textarea id="var-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this variance accepted?" />
              <Button
                id="acknowledge-variance"
                onClick={() => showResult(store.acknowledgeVariance(invoice.publicId, reason))}
              >
                Acknowledge variance
              </Button>
            </div>
          ) : null}
        </Card>
      ) : null}

      {invoice.issues.some((i) => i.code === "PROMPT_INJECTION") ? (
        <Card className="mt-3">
          <CardTitle>Security event</CardTitle>
          <p className="mt-2 text-sm text-ink">
            Document notes contain an instruction-like phrase asking the extractor to ignore validation and approve payment.
            InvoiceFlow treats document contents as untrusted data. The instruction was ignored and this invoice remains in review.
          </p>
          {canAct && invoice.issues.some((i) => i.code === "PROMPT_INJECTION" && !i.acknowledged) ? (
            <Button
              className="mt-3"
              variant="outline"
              onClick={() => showResult(store.acknowledgeSecurity(invoice.publicId, "Reviewed hostile instruction; document treated as data."))}
            >
              Acknowledge security event
            </Button>
          ) : null}
        </Card>
      ) : null}

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <Card>
          <CardTitle>Original extracted text</CardTitle>
          <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-canvas p-3 font-mono text-xs whitespace-pre-wrap">
            {invoice.extraction.rawText}
          </pre>
        </Card>
        <Card>
          <CardTitle>Normalized JSON payload</CardTitle>
          <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-canvas p-3 font-mono text-xs">{jsonPayload}</pre>
        </Card>
      </div>

      <Card className="mt-3">
        <CardTitle>Audit timeline</CardTitle>
        <ol className="mt-3 space-y-2">
          {audit.length === 0 ? <p className="text-sm text-muted">No events yet.</p> : null}
          {audit.map((event) => (
            <li key={event.id} className="border-l-2 border-line pl-3 text-sm">
              <div className="font-mono text-[11px] text-subtle">{formatDateTime(event.at)}</div>
              <div>
                <span className="font-medium">{event.action.replaceAll("_", " ")}</span>
                <span className="text-muted"> · {event.actor}</span>
              </div>
              <p className="text-muted">{event.summary}</p>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="mt-3">
        <CardTitle>Delivery history</CardTitle>
        {deliveries.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No accounting deliveries yet.</p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  <th className="py-1 text-left font-medium">Delivery</th>
                  <th className="py-1 text-left font-medium">Attempt</th>
                  <th className="py-1 text-left font-medium">Status</th>
                  <th className="py-1 text-left font-medium">HTTP</th>
                  <th className="py-1 text-left font-medium">Bill ID</th>
                </tr>
              </thead>
              <tbody>
                {deliveries.map((d) => (
                  <tr key={d.id} className="border-t border-line">
                    <td className="py-2 font-mono text-xs">{d.publicId}</td>
                    <td className="py-2 font-mono">{d.attemptNumber}</td>
                    <td className="py-2">{d.status.replaceAll("_", " ")}</td>
                    <td className="py-2 font-mono">{d.responseCode || "—"}</td>
                    <td className="py-2 font-mono text-xs">{d.providerBillId ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
