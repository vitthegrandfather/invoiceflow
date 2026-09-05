import { formatMoney } from "./domain.ts";
import type { Currency, InvoiceSource, InvoiceStatus } from "./types.ts";
import { STATUS_LABEL } from "./types.ts";

export function formatDate(iso: string): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

export function formatDateTime(iso: string): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/\.\d+Z$/, " UTC").replace("Z", " UTC");
}

export function formatAmount(centsValue: number, currency: Currency): string {
  return formatMoney(centsValue, currency);
}

export function sourceLabel(source: InvoiceSource): string {
  if (source === "email_webhook") return "Email webhook";
  if (source === "api") return "API";
  return "Upload";
}

export function statusLabel(status: InvoiceStatus): string {
  return STATUS_LABEL[status];
}

export function confidencePct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function fieldLabel(name: string): string {
  return name.replaceAll("_", " ");
}
