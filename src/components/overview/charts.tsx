import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Invoice } from "@/lib/invoiceflow/types";

function useMounted() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}

const tooltipStyle = {
  background: "#ffffff",
  border: "1px solid #e4dfd6",
  borderRadius: 6,
  fontSize: 12,
  color: "#1a2433",
};

export function VolumeChart({
  data,
}: {
  data: { date: string; received: number; reviewed: number; synced: number }[];
}) {
  const mounted = useMounted();
  if (!mounted) return <div className="h-48" />;
  return (
    <ResponsiveContainer width="100%" height={192}>
      <BarChart data={data} barGap={2}>
        <CartesianGrid stroke="#e4dfd6" vertical={false} />
        <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(5)} tick={{ fontSize: 11, fill: "#5d6b7a" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#5d6b7a" }} width={28} />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="received" fill="#0e1a2b" name="Received" />
        <Bar dataKey="reviewed" fill="#0f7a5c" name="Reviewed" />
        <Bar dataKey="synced" fill="#185fa5" name="Synced" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function OutcomesChart({ invoices }: { invoices: Invoice[] }) {
  const mounted = useMounted();
  const data = [
    { name: "Needs review", value: invoices.filter((i) => i.status === "NEEDS_REVIEW").length, fill: "#9a6700" },
    { name: "Duplicate", value: invoices.filter((i) => i.status === "DUPLICATE").length, fill: "#c47b17" },
    { name: "Approved", value: invoices.filter((i) => i.status === "APPROVED").length, fill: "#0f7a5c" },
    { name: "Synced", value: invoices.filter((i) => i.status === "SYNCED").length, fill: "#0c684e" },
    { name: "Failed", value: invoices.filter((i) => i.status === "FAILED").length, fill: "#b42318" },
    { name: "Other", value: invoices.filter((i) => !["NEEDS_REVIEW", "DUPLICATE", "APPROVED", "SYNCED", "FAILED"].includes(i.status)).length, fill: "#8a96a3" },
  ].filter((d) => d.value > 0);
  if (!mounted) return <div className="h-48" />;
  return (
    <ResponsiveContainer width="100%" height={192}>
      <BarChart data={data} layout="vertical" margin={{ left: 16 }}>
        <CartesianGrid stroke="#e4dfd6" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "#5d6b7a" }} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#5d6b7a" }} width={96} />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="value" name="Invoices" radius={[0, 3, 3, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ExceptionChart({ invoices }: { invoices: Invoice[] }) {
  const mounted = useMounted();
  const counts: Record<string, number> = {};
  for (const invoice of invoices) {
    for (const issue of invoice.issues) {
      counts[issue.code] = (counts[issue.code] ?? 0) + 1;
    }
  }
  const data = Object.entries(counts).map(([name, value]) => ({ name: name.replaceAll("_", " "), value }));
  if (!mounted) return <div className="h-48" />;
  if (data.length === 0) return <p className="py-10 text-center text-sm text-muted">No open exception categories.</p>;
  return (
    <ResponsiveContainer width="100%" height={192}>
      <BarChart data={data}>
        <CartesianGrid stroke="#e4dfd6" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#5d6b7a" }} interval={0} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#5d6b7a" }} width={28} />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="value" fill="#b42318" name="Issues" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DurationChart({
  data,
}: {
  data: { date: string; hours: number }[];
}) {
  const mounted = useMounted();
  if (!mounted) return <div className="h-48" />;
  return (
    <ResponsiveContainer width="100%" height={192}>
      <BarChart data={data}>
        <CartesianGrid stroke="#e4dfd6" vertical={false} />
        <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(5)} tick={{ fontSize: 11, fill: "#5d6b7a" }} />
        <YAxis tick={{ fontSize: 11, fill: "#5d6b7a" }} width={28} unit="h" />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="hours" fill="#185fa5" name="Hours" />
      </BarChart>
    </ResponsiveContainer>
  );
}
