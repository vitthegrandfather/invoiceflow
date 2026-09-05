import { createFileRoute, Link } from "@tanstack/react-router";
import { InvoiceTable } from "@/components/invoice/invoice-table";
import { PageHeader } from "@/components/layout/app-shell";
import { Card, CardTitle } from "@/components/ui/card";
import { useInvoiceStore } from "@/lib/invoiceflow/store";

export const Route = createFileRoute("/review")({ component: ReviewPage });

const FEATURED = [
  { id: "INV-2026-00101", reason: "Clean match — approve" },
  { id: "INV-2026-00102", reason: "Probable duplicate" },
  { id: "INV-2026-00103", reason: "PO variance" },
  { id: "INV-2026-00104", reason: "Low-confidence fields" },
  { id: "INV-2026-00106", reason: "Hostile instruction" },
] as const;

function ReviewPage() {
  const invoices = useInvoiceStore((s) => s.invoices);
  const queue = invoices.filter(
    (i) => i.status === "NEEDS_REVIEW" || i.status === "DUPLICATE" || i.status === "VALIDATED",
  );

  return (
    <div>
      <PageHeader
        title="Review queue"
        description="Human approval is required. Nothing posts to a sandbox ledger until an authorized operator approves it."
      />
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {FEATURED.map((item) => {
          const invoice = invoices.find((i) => i.publicId === item.id);
          if (!invoice) return null;
          return (
            <Link key={item.id} to="/invoices/$invoiceId" params={{ invoiceId: item.id }}>
              <Card className="h-full hover:bg-canvas">
                <div className="font-mono text-xs text-accent">{item.id}</div>
                <div className="mt-1 text-sm">{invoice.vendorName}</div>
                <div className="mt-2 text-xs text-muted">{item.reason}</div>
              </Card>
            </Link>
          );
        })}
      </div>
      <Card className="p-0">
        <div className="px-4 pt-4">
          <CardTitle>Open items</CardTitle>
        </div>
        <InvoiceTable invoices={queue} />
      </Card>
    </div>
  );
}
