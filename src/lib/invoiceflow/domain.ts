import {
  ALLOWED_CONTENT_TYPES,
  CONFIDENCE_THRESHOLD,
  type Currency,
  type DeliveryAttempt,
  type ExtractedField,
  type FieldName,
  type Invoice,
  type InvoiceStatus,
  type Role,
  type User,
  type ValidationIssue,
  MAX_UPLOAD_BYTES,
  SUPPORTED_CURRENCIES,
} from "./types.ts";

const CURRENCY_SYMBOL: Record<Currency, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
};

export function cents(amount: number): number {
  if (!Number.isInteger(amount)) {
    throw new Error("Monetary amounts must be integer cents");
  }
  return amount;
}

export function formatMoney(amountCents: number, currency: Currency): string {
  const sign = amountCents < 0 ? "-" : "";
  const abs = Math.abs(amountCents);
  const whole = Math.trunc(abs / 100);
  const frac = abs % 100;
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${sign}${CURRENCY_SYMBOL[currency]}${grouped}.${frac.toString().padStart(2, "0")}`;
}

export function moneyToDecimal(amountCents: number): string {
  const sign = amountCents < 0 ? "-" : "";
  const abs = Math.abs(amountCents);
  return `${sign}${Math.trunc(abs / 100)}.${(abs % 100).toString().padStart(2, "0")}`;
}

export function parseDecimalToCents(value: string): number | null {
  const trimmed = value.trim().replace(/[$,€£,\s]/g, "");
  if (!/^-?\d+(\.\d{1,2})?$/.test(trimmed)) return null;
  const negative = trimmed.startsWith("-");
  const [whole, frac = ""] = trimmed.replace("-", "").split(".");
  const centsValue = Number.parseInt(whole, 10) * 100 + Number.parseInt(frac.padEnd(2, "0"), 10);
  return negative ? -centsValue : centsValue;
}

export function addCents(...values: number[]): number {
  return values.reduce((sum, v) => {
    if (!Number.isInteger(v)) throw new Error("Non-integer cents");
    return sum + v;
  }, 0);
}

export function absCents(value: number): number {
  return Math.abs(value);
}

export function variancePct(expected: number, received: number): number {
  if (expected === 0) return received === 0 ? 0 : 100;
  return Math.round((Math.abs(received - expected) / expected) * 10000) / 100;
}

export const TRANSITIONS: Record<InvoiceStatus, InvoiceStatus[]> = {
  RECEIVED: ["EXTRACTING"],
  EXTRACTING: ["NEEDS_REVIEW", "VALIDATED", "DUPLICATE", "FAILED"],
  NEEDS_REVIEW: ["VALIDATED", "APPROVED", "REJECTED", "DUPLICATE"],
  VALIDATED: ["APPROVED", "REJECTED", "NEEDS_REVIEW"],
  APPROVED: ["SYNCING", "REJECTED"],
  REJECTED: [],
  SYNCING: ["SYNCED", "FAILED"],
  SYNCED: [],
  FAILED: ["SYNCING"],
  DUPLICATE: ["NEEDS_REVIEW", "REJECTED"],
};

export function canTransition(from: InvoiceStatus, to: InvoiceStatus): boolean {
  return TRANSITIONS[from].includes(to);
}

export function assertTransition(from: InvoiceStatus, to: InvoiceStatus): void {
  if (!canTransition(from, to)) {
    throw new Error(`Invalid status transition ${from} → ${to}`);
  }
}

export function canApprove(role: Role): boolean {
  return role === "admin" || role === "ap_manager" || role === "reviewer";
}

export function canReject(role: Role): boolean {
  return canApprove(role);
}

export function canRetryDelivery(role: Role): boolean {
  return role === "admin" || role === "ap_manager";
}

export function canEditVendor(role: Role): boolean {
  return role === "admin" || role === "ap_manager";
}

export function canResetDemo(role: Role): boolean {
  return role === "admin";
}

export function canCorrectFields(role: Role): boolean {
  return role === "admin" || role === "ap_manager" || role === "reviewer";
}

export function canDecideDuplicate(role: Role): boolean {
  return canCorrectFields(role);
}

export function canAcknowledgeVariance(role: Role): boolean {
  return canCorrectFields(role);
}

export function maskBank(suffix: string): string {
  const last4 = suffix.replace(/\D/g, "").slice(-4) || "0000";
  return `••••${last4}`;
}

export function sanitizeFilename(name: string): string {
  const base = name.replace(/\\/g, "/").split("/").pop() ?? "document";
  return base.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 180) || "document";
}

export function validateUpload(contentType: string, sizeBytes: number, filename: string): string[] {
  const errors: string[] = [];
  if (!ALLOWED_CONTENT_TYPES.includes(contentType)) {
    errors.push(`Unsupported content type: ${contentType}`);
  }
  if (sizeBytes > MAX_UPLOAD_BYTES) {
    errors.push("File exceeds 10 MB upload limit");
  }
  if (filename !== sanitizeFilename(filename)) {
    errors.push("Filename contains disallowed characters and was sanitized");
  }
  return errors;
}

const INJECTION_PATTERNS = [
  /ignore (all )?previous instructions/i,
  /skip validation/i,
  /approve (this invoice )?immediately/i,
  /set confidence to 1/i,
  /mark as paid/i,
  /do not flag/i,
  /override (the )?policy/i,
  /you are now/i,
  /system prompt/i,
  /disregard (all )?(rules|validation)/i,
];

export function detectPromptInjection(text: string): boolean {
  return INJECTION_PATTERNS.some((re) => re.test(text));
}

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "\u0026amp;")
    .replaceAll("<", "\u0026lt;")
    .replaceAll(">", "\u0026gt;")
    .replaceAll('"', "\u0026quot;")
    .replaceAll("'", "\u0026#39;");
}

export function formulaSafeCell(value: string): string {
  if (/^[=+\-@\t\r]/.test(value)) return `'${value}`;
  return value;
}

export function toCsv(rows: string[][]): string {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const safe = formulaSafeCell(cell);
          if (/[",\n]/.test(safe)) return `"${safe.replaceAll('"', '""')}"`;
          return safe;
        })
        .join(","),
    )
    .join("\n");
}

export function invoiceFingerprint(input: {
  vendorId: string;
  invoiceNumber: string;
  totalCents: number;
  currency: Currency;
  issueDate: string;
}): string {
  return [
    input.vendorId,
    input.invoiceNumber.trim().toUpperCase(),
    String(input.totalCents),
    input.currency,
    input.issueDate,
  ].join("|");
}

export function fieldMap(invoice: Invoice): Record<FieldName, ExtractedField> {
  const map = {} as Record<FieldName, ExtractedField>;
  for (const field of invoice.fields) map[field.name] = field;
  return map;
}

export function lowConfidenceFields(invoice: Invoice): ExtractedField[] {
  return invoice.fields.filter((f) => f.confidence < CONFIDENCE_THRESHOLD);
}

export function hasBlockingIssues(invoice: Invoice): boolean {
  return invoice.issues.some((issue) => issue.blocking && !issue.acknowledged);
}

export function approvalBlockedReason(invoice: Invoice): string | null {
  if (invoice.status === "DUPLICATE" && invoice.duplicateMatch?.decision !== "marked_unique") {
    return "Duplicate invoices cannot be approved until they are marked unique or confirmed.";
  }
  if (invoice.status === "REJECTED") return "Rejected invoices cannot be approved.";
  if (invoice.status === "SYNCED") return "Already synchronized.";
  if (!["NEEDS_REVIEW", "VALIDATED"].includes(invoice.status)) {
    return `Cannot approve from ${invoice.status}.`;
  }
  const poIssue = invoice.issues.find((i) => i.code === "PO_VARIANCE" && i.blocking && !i.acknowledged);
  if (poIssue) return "Purchase-order variance must be acknowledged before approval.";
  const security = invoice.issues.find((i) => i.severity === "security" && i.blocking && !i.acknowledged);
  if (security) return "Security finding must be acknowledged before approval.";
  if (hasBlockingIssues(invoice)) return "Resolve or acknowledge blocking validation issues first.";
  return null;
}

function issue(
  id: string,
  code: string,
  severity: ValidationIssue["severity"],
  message: string,
  blocking: boolean,
  field?: string,
): ValidationIssue {
  return { id, code, severity, message, blocking, field, acknowledged: false };
}

export function runValidation(invoice: Invoice, siblings: Invoice[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const sum = addCents(invoice.subtotalCents, invoice.taxCents);
  if (sum !== invoice.totalCents) {
    issues.push(
      issue(
        `${invoice.id}-math`,
        "TOTAL_MISMATCH",
        "error",
        `Subtotal ${moneyToDecimal(invoice.subtotalCents)} plus tax ${moneyToDecimal(invoice.taxCents)} does not equal total ${moneyToDecimal(invoice.totalCents)}.`,
        true,
        "total",
      ),
    );
  }
  if (!SUPPORTED_CURRENCIES.includes(invoice.currency)) {
    issues.push(issue(`${invoice.id}-ccy`, "UNSUPPORTED_CURRENCY", "error", `Currency ${invoice.currency} is not supported.`, true, "currency"));
  }
  if (invoice.dueDate < invoice.issueDate) {
    issues.push(issue(`${invoice.id}-due`, "DUE_BEFORE_ISSUE", "error", "Due date is before issue date.", true, "due_date"));
  }
  if (!invoice.vendorName.trim()) {
    issues.push(issue(`${invoice.id}-vnd`, "VENDOR_REQUIRED", "error", "Vendor name is required.", true, "vendor_name"));
  }
  if (!invoice.invoiceNumber.trim()) {
    issues.push(issue(`${invoice.id}-num`, "INVOICE_NUMBER_REQUIRED", "error", "Invoice number is required.", true, "invoice_number"));
  }

  const numberDup = siblings.find(
    (other) =>
      other.id !== invoice.id &&
      other.vendorId === invoice.vendorId &&
      other.invoiceNumber.trim().toUpperCase() === invoice.invoiceNumber.trim().toUpperCase() &&
      other.status !== "REJECTED",
  );
  if (numberDup) {
    issues.push(
      issue(
        `${invoice.id}-numdup`,
        "DUPLICATE_INVOICE_NUMBER",
        "error",
        `Invoice number ${invoice.invoiceNumber} already exists for this vendor as ${numberDup.publicId}.`,
        true,
        "invoice_number",
      ),
    );
  }

  for (const field of invoice.fields) {
    if (field.confidence < CONFIDENCE_THRESHOLD) {
      issues.push(
        issue(
          `${invoice.id}-cf-${field.name}`,
          "LOW_CONFIDENCE",
          "warning",
          `${field.name.replaceAll("_", " ")} confidence ${(field.confidence * 100).toFixed(0)}% is below the 85% review threshold.`,
          false,
          field.name,
        ),
      );
    }
  }

  if (invoice.notes && detectPromptInjection(invoice.notes)) {
    issues.push(
      issue(
        `${invoice.id}-inj`,
        "PROMPT_INJECTION",
        "security",
        "Untrusted document contents include an instruction-like phrase. Document text is treated as data only; the instruction was ignored.",
        true,
        "notes",
      ),
    );
  }
  if (invoice.extraction?.rawText && detectPromptInjection(invoice.extraction.rawText)) {
    if (!issues.some((i) => i.code === "PROMPT_INJECTION")) {
      issues.push(
        issue(
          `${invoice.id}-inj-raw`,
          "PROMPT_INJECTION",
          "security",
          "Extracted text contains a prompt-injection style instruction. Extraction continued with the document treated as untrusted data.",
          true,
          "notes",
        ),
      );
    }
  }

  return issues;
}

export function applyPoVariance(invoice: Invoice, po: { amountCents: number; currency: Currency; publicId: string } | undefined): ValidationIssue[] {
  if (!po || !invoice.poNumber) return [];
  if (po.currency !== invoice.currency || po.amountCents !== invoice.totalCents) {
    const diff = invoice.totalCents - po.amountCents;
    const pct = variancePct(po.amountCents, invoice.totalCents);
    return [
      {
        id: `${invoice.id}-po`,
        code: "PO_VARIANCE",
        severity: "error",
        field: "po_number",
        blocking: true,
        acknowledged: invoice.varianceAcknowledged,
        message: `Invoice total ${formatMoney(invoice.totalCents, invoice.currency)} differs from PO ${po.publicId} expected ${formatMoney(po.amountCents, po.currency)} by ${formatMoney(absCents(diff), invoice.currency)} (${pct.toFixed(2)}%).`,
      },
    ];
  }
  return [];
}

export function findDuplicate(
  invoice: Invoice,
  siblings: Invoice[],
): { matched: Invoice; score: number; reasons: string[] } | null {
  const fp = invoiceFingerprint(invoice);
  const exact = siblings.find((other) => other.id !== invoice.id && other.fingerprint === fp && other.status !== "REJECTED");
  if (exact) {
    return {
      matched: exact,
      score: 1,
      reasons: [
        "Same vendor",
        "Same invoice number",
        "Same total",
        "Same currency",
        "Same issue date",
      ],
    };
  }

  let best: { matched: Invoice; score: number; reasons: string[] } | null = null;
  for (const other of siblings) {
    if (other.id === invoice.id || other.status === "REJECTED") continue;
    const reasons: string[] = [];
    let score = 0;
    if (other.vendorId === invoice.vendorId) {
      reasons.push("Same vendor");
      score += 0.25;
    }
    if (other.invoiceNumber.trim().toUpperCase() === invoice.invoiceNumber.trim().toUpperCase()) {
      reasons.push("Same invoice number");
      score += 0.35;
    }
    if (other.totalCents === invoice.totalCents && other.currency === invoice.currency) {
      reasons.push("Same amount and currency");
      score += 0.25;
    }
    if (other.issueDate === invoice.issueDate) {
      reasons.push("Same issue date");
      score += 0.15;
    }
    if (score >= 0.75 && (!best || score > best.score)) {
      best = { matched: other, score: Math.min(score, 0.99), reasons };
    }
  }
  return best;
}

export function overallConfidence(fields: ExtractedField[]): number {
  if (fields.length === 0) return 0;
  const sum = fields.reduce((acc, f) => acc + f.confidence, 0);
  return Math.round((sum / fields.length) * 100) / 100;
}

export function userById(users: User[], id: string): User {
  const user = users.find((u) => u.id === id);
  if (!user) throw new Error("Unknown user");
  return user;
}

export function nextRetryIso(from: Date, attempt: number): string {
  const minutes = Math.min(60, 2 ** attempt);
  return new Date(from.getTime() + minutes * 60_000).toISOString();
}

export function redactedPayload(invoice: Invoice): string {
  return JSON.stringify(
    {
      invoice_id: invoice.publicId,
      vendor: invoice.vendorName,
      total: moneyToDecimal(invoice.totalCents),
      currency: invoice.currency,
      invoice_number: invoice.invoiceNumber,
      bank_account: maskBank(invoice.bankAccountSuffix),
      workspace: "ws_northwind_demo",
    },
    null,
    2,
  );
}

export function newId(prefix: string): string {
  const rand = crypto.randomUUID();
  return `${prefix}_${rand.slice(0, 8)}`;
}

export function isoNow(): string {
  return new Date().toISOString();
}

export function deliveryPublicId(n: number): string {
  return `DLV-2026-${String(n).padStart(5, "0")}`;
}

export function isRetryableStatus(status: DeliveryAttempt["status"]): boolean {
  return status === "failed_retryable" || status === "failed_dead_letter";
}

export function normalizeInvoiceNumber(value: string): string {
  return value.trim().replace(/\s+/g, " ").toUpperCase();
}
