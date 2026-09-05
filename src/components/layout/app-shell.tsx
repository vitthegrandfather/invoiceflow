import { Link, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  Building2,
  FileText,
  GitBranch,
  Inbox,
  LayoutDashboard,
  Menu,
  Settings,
  Truck,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ROLE_LABEL } from "@/lib/invoiceflow/types";
import { useCurrentUser, useInvoiceStore } from "@/lib/invoiceflow/store";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/invoices", label: "Invoices", icon: FileText },
  { to: "/review", label: "Review queue", icon: Inbox },
  { to: "/vendors", label: "Vendors", icon: Building2 },
  { to: "/automations", label: "Automations", icon: GitBranch },
  { to: "/deliveries", label: "Deliveries", icon: Truck },
  { to: "/architecture", label: "Architecture", icon: Activity },
  { to: "/settings", label: "Settings", icon: Settings },
];

function Mark() {
  return (
    <span className="flex size-8 items-center justify-center rounded-md bg-accent text-accent-fg">
      <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
        <rect x="5" y="4" width="14" height="16" rx="1.5" fill="currentColor" opacity="0.2" />
        <path
          d="M8 8h8M8 12h8M8 16h5"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const reviewCount = useInvoiceStore(
    (s) => s.invoices.filter((i) => i.status === "NEEDS_REVIEW" || i.status === "DUPLICATE").length,
  );
  const user = useCurrentUser();

  return (
    <div className="flex h-full flex-col bg-navy text-accent-fg">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <Mark />
        <div>
          <div className="text-sm font-medium tracking-tight">InvoiceFlow</div>
          <div className="text-[11px] text-accent-fg/60">AP operations</div>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 px-2">
        {NAV.map((item) => {
          const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={cn(
                "flex h-10 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors duration-150",
                active ? "bg-navy-hover text-accent-fg" : "text-accent-fg/70 hover:bg-navy-mid hover:text-accent-fg",
              )}
            >
              <Icon className="size-4 shrink-0" strokeWidth={1.75} />
              <span className="flex-1">{item.label}</span>
              {item.to === "/review" && reviewCount > 0 ? (
                <span className="rounded-sm bg-amber px-1.5 py-0.5 font-mono text-[10px] text-navy">
                  {reviewCount}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-navy-line px-4 py-3">
        <div className="text-xs font-medium">{user.name}</div>
        <div className="text-[11px] text-accent-fg/60">{ROLE_LABEL[user.role]}</div>
      </div>
      <p className="border-t border-navy-line px-4 py-3 text-[11px] leading-snug text-accent-fg/55">
        Demo workspace — all invoices, vendors, bank details, and integrations are fictional.
      </p>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const workspace = useInvoiceStore((s) => s.workspace);

  useEffect(() => {
    const finish = () => useInvoiceStore.getState().hydrateIfNeeded();
    const unsub = useInvoiceStore.persist.onFinishHydration(finish);
    if (useInvoiceStore.persist.hasHydrated()) finish();
    return unsub;
  }, []);
  useEffect(() => setOpen(false), [pathname]);

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="hidden lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>
      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-navy/40"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
          />
          <div className="relative h-full w-64 max-w-[80vw] shadow-[var(--shadow-card)]">
            <Sidebar onNavigate={() => setOpen(false)} />
          </div>
        </div>
      ) : null}
      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-3 border-b border-line bg-surface px-3 lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </Button>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{workspace.name}</div>
            <div className="hidden font-mono text-[11px] text-muted sm:block">{workspace.publicId}</div>
          </div>
          <span className="hidden rounded-sm bg-accent-soft px-2 py-1 text-[11px] font-medium text-accent sm:inline">
            Sandbox providers only
          </span>
        </header>
        <main className="min-w-0 flex-1 px-3 py-4 lg:px-6 lg:py-6">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-medium tracking-tight text-ink">{title}</h1>
        {description ? <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
