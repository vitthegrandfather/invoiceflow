import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/app-shell";
import { Card, CardHeader, CardMeta, CardTitle } from "@/components/ui/card";
import { DurationChart, ExceptionChart, OutcomesChart, VolumeChart } from "@/components/overview/charts";
import { InvoiceTable } from "@/components/invoice/invoice-table";
import { formatMoney } from "@/lib/invoiceflow/domain";
import { formatTotals, metrics } from "@/lib/invoiceflow/engine";
import { useInvoiceStore } from "@/lib/invoiceflow/store";
import type { Currency } from "@/lib/invoiceflow/types";

export const Route = createFileRoute("/")({ component: OverviewPage });

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 font-mono text-xl tabular-nums text-ink">{value}</div>
      {hint ? <div className="mt-1 text-[11px] text-subtle">{hint}</div> : null}
    </Card>
  );
}

function OverviewPage() {
  const invoices = useInvoiceStore((s) => s.invoices);
  const dailyVolume = useInvoiceStore((s) => s.dailyVolume);
  const snapshot = useInvoiceStore();
  const stats = metrics(snapshot);
  const recent = [...invoices].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 6);
  const duration = dailyVolume.map((d, i) => ({ date: d.date, hours: Number((4.2 + ((i * 13) % 7) / 3).toFixed(1)) }));

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Operational snapshot of the Northwind demo workspace. Figures are computed from seeded fictional invoices."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Metric label="Received" value={String(stats.received)} />
        <Metric label="Awaiting review" value={String(stats.awaiting)} hint="Needs review + duplicates" />
        <Metric label="Approved" value={String(stats.approved)} />
        <Metric label="Synchronized" value={String(stats.synchronized)} />
        <Metric label="Failed deliveries" value={String(stats.failedDeliveries)} />
        <Metric label="Duplicate rate" value={`${stats.duplicateRate}%`} />
        <Metric label="Exception rate" value={`${stats.exceptionRate}%`} />
        <Metric label="Extraction accuracy" value={`${stats.extractionAccuracy}%`} hint="Mean field confidence" />
        <Metric label="Avg processing" value={`${stats.avgProcessingHours} h`} />
        <Metric
          label="Invoice value"
          value={formatTotals(stats.byCurrency)}
          hint="USD / EUR / GBP totals from seeded invoices"
        />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Invoice volume · 14 days</CardTitle>
              <CardMeta>Received, reviewed, and sandbox-synced</CardMeta>
            </div>
          </CardHeader>
          <VolumeChart data={dailyVolume} />
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Processing outcomes</CardTitle>
              <CardMeta>Current status distribution</CardMeta>
            </div>
          </CardHeader>
          <OutcomesChart invoices={invoices} />
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Exception categories</CardTitle>
              <CardMeta>Open validation and security findings</CardMeta>
            </div>
          </CardHeader>
          <ExceptionChart invoices={invoices} />
        </Card>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Average processing duration</CardTitle>
              <CardMeta>Hours from ingest to decision (demo series)</CardMeta>
            </div>
          </CardHeader>
          <DurationChart data={duration} />
        </Card>
      </div>

      <Card className="mt-4 p-0">
        <div className="flex items-center justify-between px-4 pt-4">
          <CardTitle>Recent invoices</CardTitle>
          <Link to="/invoices" className="text-sm text-accent hover:underline">
            View all
          </Link>
        </div>
        <div className="mt-2">
          <InvoiceTable invoices={recent} />
        </div>
      </Card>

      <p className="mt-4 text-xs text-subtle">
        Totals by currency:{" "}
        {Object.entries(stats.byCurrency)
          .map(([ccy, centsValue]) => formatMoney(centsValue, ccy as Currency))
          .join(" · ")}
        . No live accounting, email, or banking connections are used in this workspace.
      </p>
    </div>
  );
}
