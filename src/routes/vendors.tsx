import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/invoiceflow/format";
import { useInvoiceStore } from "@/lib/invoiceflow/store";

export const Route = createFileRoute("/vendors")({ component: VendorsPage });

function VendorsPage() {
  const vendors = useInvoiceStore((s) => s.vendors);
  const invoices = useInvoiceStore((s) => s.invoices);

  return (
    <div>
      <PageHeader
        title="Vendors"
        description="Eight fictional suppliers in the Northwind workspace. Bank accounts are stored as a four-digit suffix only."
      />
      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Vendor</th>
                <th className="px-3 py-2 text-left font-medium">Domain</th>
                <th className="px-3 py-2 text-left font-medium">Currency</th>
                <th className="px-3 py-2 text-left font-medium">Terms</th>
                <th className="px-3 py-2 text-left font-medium">Bank</th>
                <th className="px-3 py-2 text-left font-medium">Invoices</th>
                <th className="px-3 py-2 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((vendor) => {
                const related = invoices.filter((i) => i.vendorId === vendor.id);
                return (
                  <tr key={vendor.id} className="border-b border-line last:border-0">
                    <td className="px-3 py-2.5">
                      <div>{vendor.name}</div>
                      <div className="font-mono text-[11px] text-subtle">{vendor.publicId}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-mono text-xs">{vendor.domain}</div>
                      <div className="text-[11px] text-subtle">{vendor.email}</div>
                    </td>
                    <td className="px-3 py-2.5 font-mono">{vendor.currency}</td>
                    <td className="px-3 py-2.5">{vendor.paymentTerms}</td>
                    <td className="px-3 py-2.5 font-mono">{vendor.bankAccountSuffix}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {related.slice(0, 3).map((invoice) => (
                          <Link
                            key={invoice.id}
                            to="/invoices/$invoiceId"
                            params={{ invoiceId: invoice.publicId }}
                            className="font-mono text-[11px] text-accent hover:underline"
                          >
                            {invoice.publicId.slice(-5)}
                          </Link>
                        ))}
                        {related.length > 3 ? <span className="text-[11px] text-subtle">+{related.length - 3}</span> : null}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <Badge tone={vendor.status === "active" ? "accent" : "amber"}>{vendor.status.replaceAll("_", " ")}</Badge>
                      <div className="mt-1 font-mono text-[10px] text-subtle">{formatDateTime(vendor.lastInvoiceAt)}</div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
