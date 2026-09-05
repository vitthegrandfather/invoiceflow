import { Link } from "@tanstack/react-router";
import { StatusBadge } from "@/components/invoice/status-badge";
import { confidencePct, formatAmount, formatDate, sourceLabel } from "@/lib/invoiceflow/format";
import type { Invoice } from "@/lib/invoiceflow/types";

export function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  if (invoices.length === 0) {
    return <p className="px-3 py-8 text-center text-sm text-muted">No invoices match the current filters.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-line text-[11px] font-medium uppercase tracking-wide text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Invoice</th>
            <th className="px-3 py-2 font-medium">Vendor</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Total</th>
            <th className="px-3 py-2 font-medium">Issued</th>
            <th className="px-3 py-2 font-medium">Source</th>
            <th className="px-3 py-2 font-medium">Conf.</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id} className="border-b border-line last:border-0 hover:bg-canvas/80">
              <td className="px-3 py-2.5">
                <Link
                  to="/invoices/$invoiceId"
                  params={{ invoiceId: invoice.publicId }}
                  className="font-mono text-[13px] text-accent hover:underline"
                >
                  {invoice.publicId}
                </Link>
                <div className="font-mono text-[11px] text-subtle">{invoice.invoiceNumber}</div>
              </td>
              <td className="px-3 py-2.5">{invoice.vendorName}</td>
              <td className="px-3 py-2.5">
                <StatusBadge status={invoice.status} />
              </td>
              <td className="px-3 py-2.5 font-mono tabular-nums">
                {formatAmount(invoice.totalCents, invoice.currency)}
              </td>
              <td className="px-3 py-2.5 font-mono text-[13px]">{formatDate(invoice.issueDate)}</td>
              <td className="px-3 py-2.5 text-muted">{sourceLabel(invoice.source)}</td>
              <td className="px-3 py-2.5 font-mono tabular-nums text-[13px]">
                {invoice.extractionConfidence ? confidencePct(invoice.extractionConfidence) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
