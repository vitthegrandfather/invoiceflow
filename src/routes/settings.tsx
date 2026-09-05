import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { canResetDemo } from "@/lib/invoiceflow/domain";
import { DEMO_PASSWORD } from "@/lib/invoiceflow/seed";
import { ROLE_LABEL } from "@/lib/invoiceflow/types";
import { useCurrentUser, useInvoiceStore } from "@/lib/invoiceflow/store";
import { showResult } from "@/lib/invoiceflow/toast";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/settings")({ component: SettingsPage });

function SettingsPage() {
  const users = useInvoiceStore((s) => s.users);
  const current = useCurrentUser();
  const switchUser = useInvoiceStore((s) => s.switchUser);
  const reset = useInvoiceStore((s) => s.resetDemo);

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Demo operators only. Password is a documented placeholder and is not a real credential."
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardTitle>Demo operators</CardTitle>
          <p className="mt-2 text-sm text-muted">
            Shared password <span className="font-mono">{DEMO_PASSWORD}</span>. Switching roles here only changes the in-browser session.
          </p>
          <ul className="mt-3 space-y-2">
            {users.map((user) => (
              <li key={user.id}>
                <button
                  type="button"
                  onClick={() => showResult(switchUser(user.id))}
                  className={cn(
                    "flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm",
                    user.id === current.id ? "border-accent bg-accent-soft" : "border-line hover:bg-canvas",
                  )}
                >
                  <span>
                    <span className="font-medium">{user.name}</span>
                    <span className="mt-0.5 block font-mono text-[11px] text-muted">{user.email}</span>
                  </span>
                  <Badge tone={user.id === current.id ? "accent" : "neutral"}>{ROLE_LABEL[user.role]}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle>Role capabilities</CardTitle>
          <table className="mt-3 w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="py-1 text-left font-medium">Action</th>
                <th className="py-1 text-left font-medium">Roles</th>
              </tr>
            </thead>
            <tbody className="text-muted">
              <tr className="border-t border-line">
                <td className="py-2">Approve / reject / correct / acknowledge</td>
                <td className="py-2">Admin, AP Manager, Reviewer</td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-2">Retry delivery / edit vendor</td>
                <td className="py-2">Admin, AP Manager</td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-2">Reset demo data</td>
                <td className="py-2">Admin only</td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-2">View invoices, vendors, architecture</td>
                <td className="py-2">All roles including Viewer</td>
              </tr>
            </tbody>
          </table>
        </Card>

        <Card>
          <CardTitle>Reset demo data</CardTitle>
          <p className="mt-2 text-sm text-muted">
            Restores the eighteen seeded invoices, vendors, deliveries, and audit events. Requires the Admin operator (Jordan Hale).
          </p>
          <Button
            id="reset-demo"
            className="mt-3"
            variant="outline"
            disabled={!canResetDemo(current.role)}
            onClick={() => showResult(reset())}
          >
            Reset demo data
          </Button>
          {!canResetDemo(current.role) ? (
            <p className="mt-2 text-xs text-amber">Switch to Jordan Hale (Admin) to enable reset.</p>
          ) : null}
        </Card>

        <Card>
          <CardTitle>Runtime notes</CardTitle>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
            <li>Browser walkthrough uses the in-process engine</li>
            <li>FastAPI lives in backend/ for Docker and CI</li>
            <li>n8n JSON is importable but not executed here</li>
            <li>Sandbox QuickBooks IDs are fictional (QBO-SB-*)</li>
            <li>No .env with real secrets is committed</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
