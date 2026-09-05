export type Currency = "USD" | "EUR" | "GBP";

export type InvoiceStatus =
  | "RECEIVED"
  | "EXTRACTING"
  | "NEEDS_REVIEW"
  | "VALIDATED"
  | "APPROVED"
  | "REJECTED"
  | "SYNCING"
  | "SYNCED"
  | "FAILED"
  | "DUPLICATE";

export type InvoiceSource = "upload" | "email_webhook" | "api";

export type Role = "admin" | "ap_manager" | "reviewer" | "viewer";

export type FieldName =
  | "vendor_name"
  | "invoice_number"
  | "issue_date"
  | "due_date"
  | "subtotal"
  | "tax"
  | "total"
  | "currency"
  | "po_number"
  | "bank_account_suffix";

export type IssueSeverity = "error" | "warning" | "info" | "security";

export type DeliveryStatus =
  | "pending"
  | "succeeded"
  | "failed_retryable"
  | "failed_dead_letter"
  | "retrying";

export type WorkflowName = "invoice-intake" | "accounting-sync" | "error-handler";

export type WorkflowRunStatus = "running" | "succeeded" | "failed" | "waiting_review";

export interface Workspace {
  id: string;
  publicId: string;
  name: string;
  slug: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  title: string;
}

export interface Vendor {
  id: string;
  publicId: string;
  name: string;
  legalName: string;
  email: string;
  domain: string;
  currency: Currency;
  paymentTerms: string;
  bankAccountSuffix: string;
  taxId: string;
  address: string;
  status: "active" | "on_hold" | "inactive";
  invoiceCount: number;
  lastInvoiceAt: string;
}

export interface ExtractedField {
  name: FieldName;
  value: string;
  confidence: number;
  originalValue: string;
  corrected: boolean;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: string;
  unitPriceCents: number;
  amountCents: number;
}

export interface ValidationIssue {
  id: string;
  code: string;
  severity: IssueSeverity;
  field?: string;
  message: string;
  blocking: boolean;
  acknowledged: boolean;
}

export interface DuplicateMatch {
  matchedInvoiceId: string;
  matchedPublicId: string;
  score: number;
  reasons: string[];
  decision: "pending" | "confirmed_duplicate" | "marked_unique";
}

export interface PurchaseOrder {
  id: string;
  publicId: string;
  vendorId: string;
  amountCents: number;
  currency: Currency;
  issuedOn: string;
  description: string;
}

export interface ApprovalDecision {
  id: string;
  actorId: string;
  actorName: string;
  action: "approved" | "rejected";
  reason: string;
  at: string;
}

export interface DeliveryAttempt {
  id: string;
  publicId: string;
  invoiceId: string;
  invoicePublicId: string;
  provider: string;
  attemptNumber: number;
  status: DeliveryStatus;
  responseCode: number;
  durationMs: number;
  nextRetryAt: string | null;
  providerBillId: string | null;
  redactedError: string | null;
  redactedRequest: string;
  createdAt: string;
}

export interface AuditEvent {
  id: string;
  at: string;
  actor: string;
  actorRole?: Role;
  entityType: "invoice" | "vendor" | "delivery" | "workflow" | "workspace" | "security";
  entityId: string;
  action: string;
  summary: string;
  details?: Record<string, string>;
}

export interface WorkflowNodeState {
  name: string;
  status: "pending" | "running" | "succeeded" | "failed" | "skipped";
  durationMs?: number;
  note?: string;
}

export interface WorkflowExecution {
  id: string;
  publicId: string;
  workflow: WorkflowName;
  invoicePublicId: string | null;
  startedAt: string;
  durationMs: number;
  status: WorkflowRunStatus;
  failedNode: string | null;
  retryState: string;
  version: string;
  nodes: WorkflowNodeState[];
}

export interface ExtractionRun {
  id: string;
  method: "sandbox_parser" | "ocr_sandbox";
  startedAt: string;
  completedAt: string;
  overallConfidence: number;
  rawText: string;
}

export interface Invoice {
  id: string;
  publicId: string;
  workspaceId: string;
  vendorId: string;
  vendorName: string;
  source: InvoiceSource;
  status: InvoiceStatus;
  currency: Currency;
  invoiceNumber: string;
  poNumber: string | null;
  poId: string | null;
  issueDate: string;
  dueDate: string;
  paymentTerms: string;
  subtotalCents: number;
  taxCents: number;
  totalCents: number;
  extractionConfidence: number;
  duplicateScore: number;
  assignedReviewer: string | null;
  createdAt: string;
  updatedAt: string;
  filename: string;
  contentType: string;
  notes: string;
  bankAccountSuffix: string;
  lineItems: InvoiceLineItem[];
  fields: ExtractedField[];
  issues: ValidationIssue[];
  duplicateMatch: DuplicateMatch | null;
  extraction: ExtractionRun;
  approval: ApprovalDecision | null;
  varianceAcknowledged: boolean;
  varianceReason: string | null;
  providerBillId: string | null;
  idempotencyKey: string;
  fingerprint: string;
}

export interface DailyVolume {
  date: string;
  received: number;
  reviewed: number;
  synced: number;
}

export interface AppState {
  workspace: Workspace;
  users: User[];
  currentUserId: string;
  vendors: Vendor[];
  invoices: Invoice[];
  purchaseOrders: PurchaseOrder[];
  deliveries: DeliveryAttempt[];
  auditEvents: AuditEvent[];
  workflowExecutions: WorkflowExecution[];
  dailyVolume: DailyVolume[];
  ingestionKeys: Record<string, string>;
  syncKeys: Record<string, string>;
}

export const CONFIDENCE_THRESHOLD = 0.85;
export const SUPPORTED_CURRENCIES: Currency[] = ["USD", "EUR", "GBP"];
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ALLOWED_CONTENT_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/tiff",
];

export const STATUS_LABEL: Record<InvoiceStatus, string> = {
  RECEIVED: "Received",
  EXTRACTING: "Extracting",
  NEEDS_REVIEW: "Needs review",
  VALIDATED: "Validated",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  SYNCING: "Syncing",
  SYNCED: "Synced",
  FAILED: "Failed",
  DUPLICATE: "Duplicate",
};

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  ap_manager: "AP Manager",
  reviewer: "Reviewer",
  viewer: "Viewer",
};
