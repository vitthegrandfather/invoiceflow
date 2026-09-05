import { Badge } from "@/components/ui/badge";
import { statusLabel } from "@/lib/invoiceflow/format";
import type { InvoiceStatus } from "@/lib/invoiceflow/types";

const TONE: Record<InvoiceStatus, "neutral" | "accent" | "amber" | "danger" | "info" | "navy"> = {
  RECEIVED: "neutral",
  EXTRACTING: "info",
  NEEDS_REVIEW: "amber",
  VALIDATED: "accent",
  APPROVED: "accent",
  REJECTED: "neutral",
  SYNCING: "info",
  SYNCED: "accent",
  FAILED: "danger",
  DUPLICATE: "amber",
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  return <Badge tone={TONE[status]}>{statusLabel(status)}</Badge>;
}
