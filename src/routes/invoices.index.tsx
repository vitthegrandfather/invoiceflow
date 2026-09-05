import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { InvoiceTable } from "@/components/invoice/invoice-table";
import { PageHeader } from "@/components/layout/app-shell";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { invoicesCsv } from "@/lib/invoiceflow/seed";
import { useInvoiceStore } from "@/lib/invoiceflow/store";
import type { InvoiceSource, InvoiceStatus } from "@/lib/invoiceflow/types";
import { STATUS_LABEL } from "@/lib/invoiceflow/types";

export const Route = createFileRoute("/invoices/")({ component: InvoicesPage });

function InvoicesPage() {
  const invoices = useInvoiceStore((s) => s.invoices);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<InvoiceStatus | "all">("all");
  const [source, setSource] = useState<InvoiceSource | "all">("all");
  const [csvText, setCsvText] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return invoices
      .filter((invoice) => (status === "all" ? true : invoice.status === status))
      .filter((invoice) => (source === "all" ? true : invoice.source === source))
      .filter((invoice) =>
        query
          ? [invoice.publicId, invoice.invoiceNumber, invoice.vendorName, invoice.poNumber ?? ""]
              .join(" ")
              .toLowerCase()
              .includes(query)
          : true,
      )
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, [invoices, q, status, source]);

  async function exportCsv() {
    const csv = invoicesCsv(filtered);
    setCsvText(csv);
    try {
      await navigator.clipboard.writeText(csv);
      toast.success("CSV copied", {
        description: `${filtered.length} invoices. Preview iframe cannot save files to disk — paste into a spreadsheet or text file.`,
      });
    } catch {
      toast.message("CSV ready below", {
        description: "Select the text and copy it. File download is blocked in this preview.",
      });
    }
  }

  return (
    <div>
      <PageHeader
        title="Invoices"
        description="All invoices in the Northwind demo workspace. Formula-safe CSV prefixes =, +, -, and @ cells. In this preview, export copies the file instead of downloading it."
        actions={
          <Button variant="outline" onClick={() => void exportCsv()}>
            Export CSV
          </Button>
        }
      />
      {csvText ? (
        <Card className="mb-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <CardTitle>invoiceflow-demo.csv</CardTitle>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  void navigator.clipboard.writeText(csvText).then(
                    () => toast.success("Copied to clipboard"),
                    () => toast.error("Clipboard blocked — select the text below"),
                  );
                }}
              >
                Copy
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setCsvText(null)}>
                Hide
              </Button>
            </div>
          </div>
          <p className="mb-2 text-xs text-muted">
            Download is blocked inside the live preview. Copy this CSV, or use the file attached in chat.
          </p>
          <textarea
            readOnly
            value={csvText}
            aria-label="CSV export"
            className="h-40 w-full resize-y rounded-md border border-line bg-canvas p-2 font-mono text-xs text-ink"
            onFocus={(e) => e.currentTarget.select()}
          />
        </Card>
      ) : null}
      <Card className="p-0">
        <div className="flex flex-col gap-2 border-b border-line p-3 sm:flex-row">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search ID, vendor, invoice number"
            aria-label="Search invoices"
          />
          <select
            className="h-9 rounded-md border border-line bg-surface px-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value as InvoiceStatus | "all")}
            aria-label="Filter by status"
          >
            <option value="all">All statuses</option>
            {Object.entries(STATUS_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="h-9 rounded-md border border-line bg-surface px-2 text-sm"
            value={source}
            onChange={(e) => setSource(e.target.value as InvoiceSource | "all")}
            aria-label="Filter by source"
          >
            <option value="all">All sources</option>
            <option value="upload">Upload</option>
            <option value="email_webhook">Email webhook</option>
            <option value="api">API</option>
          </select>
        </div>
        <InvoiceTable invoices={filtered} />
      </Card>
    </div>
  );
}
