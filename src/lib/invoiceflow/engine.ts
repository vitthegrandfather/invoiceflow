import {
  approvalBlockedReason,
  applyPoVariance,
  assertTransition,
  canAcknowledgeVariance,
  canApprove,
  canCorrectFields,
  canDecideDuplicate,
  canReject,
  canResetDemo,
  canRetryDelivery,
  canTransition,
  findDuplicate,
  formatMoney,
  isoNow,
  newId,
  nextRetryIso,
  overallConfidence,
  parseDecimalToCents,
  redactedPayload,
  runValidation,
  userById,
} from "./domain.ts";
import { createSeedState } from "./seed.ts";
import type {
  AppState,
  AuditEvent,
  DeliveryAttempt,
  FieldName,
  Invoice,
  InvoiceStatus,
  Role,
  WorkflowExecution,
  WorkflowNodeState,
} from "./types.ts";
import { CONFIDENCE_THRESHOLD } from "./types.ts";

export interface ActionResult {
  state: AppState;
  toast: { title: string; description?: string; tone?: "success" | "error" | "info" } | null;
  error?: string;
}

function audit(
  state: AppState,
  partial: Omit<AuditEvent, "id" | "at"> & { at?: string },
): AuditEvent {
  return {
    id: newId("aud"),
    at: partial.at ?? isoNow(),
    ...partial,
  };
}

function replaceInvoice(state: AppState, invoice: Invoice): AppState {
  return {
    ...state,
    invoices: state.invoices.map((item) => (item.id === invoice.id ? invoice : item)),
  };
}

function actor(state: AppState) {
  return userById(state.users, state.currentUserId);
}

function deny(state: AppState, message: string): ActionResult {
  return { state, toast: { title: message, tone: "error" }, error: message };
}

export function switchUser(state: AppState, userId: string): ActionResult {
  const user = state.users.find((u) => u.id === userId);
  if (!user) return deny(state, "Unknown demo user.");
  return {
    state: { ...state, currentUserId: userId },
    toast: { title: `Signed in as ${user.name}`, description: `${user.title} · ${user.role.replace("_", " ")}`, tone: "info" },
  };
}

export function resetDemo(state: AppState): ActionResult {
  const user = actor(state);
  if (!canResetDemo(user.role)) return deny(state, "Only an Admin can reset demo data.");
  const next = createSeedState();
  next.currentUserId = user.id;
  next.auditEvents = [
    audit(next, {
      actor: user.name,
      actorRole: user.role,
      entityType: "workspace",
      entityId: next.workspace.publicId,
      action: "demo_reset",
      summary: "Demo workspace restored to the seeded fictional dataset.",
    }),
    ...next.auditEvents,
  ];
  return {
    state: next,
    toast: { title: "Demo data reset", description: "Seeded invoices, vendors, and deliveries restored.", tone: "success" },
  };
}

export function correctField(state: AppState, publicId: string, name: FieldName, value: string): ActionResult {
  const user = actor(state);
  if (!canCorrectFields(user.role)) return deny(state, "Your role cannot correct extracted fields.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");

  const fields = invoice.fields.map((field) =>
    field.name === name
      ? { ...field, value, confidence: Math.max(field.confidence, 0.99), corrected: true }
      : field,
  );

  const nextInvoice: Invoice = { ...invoice, fields, updatedAt: isoNow() };
  if (name === "vendor_name") nextInvoice.vendorName = value;
  if (name === "invoice_number") nextInvoice.invoiceNumber = value;
  if (name === "issue_date") nextInvoice.issueDate = value;
  if (name === "due_date") nextInvoice.dueDate = value;
  if (name === "currency") nextInvoice.currency = value as Invoice["currency"];
  if (name === "po_number") nextInvoice.poNumber = value || null;
  if (name === "bank_account_suffix") nextInvoice.bankAccountSuffix = value.replace(/\D/g, "").slice(-4).padStart(4, "0").replace(/^/, "••••");
  if (name === "subtotal") {
    const parsed = parseDecimalToCents(value);
    if (parsed === null) return deny(state, "Subtotal must be a decimal amount.");
    nextInvoice.subtotalCents = parsed;
  }
  if (name === "tax") {
    const parsed = parseDecimalToCents(value);
    if (parsed === null) return deny(state, "Tax must be a decimal amount.");
    nextInvoice.taxCents = parsed;
  }
  if (name === "total") {
    const parsed = parseDecimalToCents(value);
    if (parsed === null) return deny(state, "Total must be a decimal amount.");
    nextInvoice.totalCents = parsed;
  }

  nextInvoice.extractionConfidence = overallConfidence(nextInvoice.fields);
  const withAudit = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...withAudit,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "field_corrected",
          summary: `Corrected ${name.replaceAll("_", " ")} to “${value}”.`,
        }),
        ...withAudit.auditEvents,
      ],
    },
    toast: { title: "Field saved", description: `${name.replaceAll("_", " ")} updated. Rerun validation to refresh issues.`, tone: "success" },
  };
}

export function rerunValidation(state: AppState, publicId: string): ActionResult {
  const user = actor(state);
  if (!canCorrectFields(user.role)) return deny(state, "Your role cannot rerun validation.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");

  const po = state.purchaseOrders.find((p) => p.id === invoice.poId || p.publicId === invoice.poNumber);
  const siblings = state.invoices.filter((i) => i.id !== invoice.id);
  const issues = [
    ...runValidation(invoice, siblings),
    ...applyPoVariance(invoice, po),
  ].map((issue) =>
    issue.code === "PO_VARIANCE" && invoice.varianceAcknowledged
      ? { ...issue, acknowledged: true, blocking: false }
      : issue.code === "PROMPT_INJECTION"
        ? { ...issue, acknowledged: invoice.issues.find((i) => i.code === "PROMPT_INJECTION")?.acknowledged ?? false }
        : issue,
  );

  const dup = findDuplicate(invoice, siblings);
  let status: InvoiceStatus = invoice.status;
  let duplicateMatch = invoice.duplicateMatch;
  if (dup && invoice.duplicateMatch?.decision !== "marked_unique") {
    duplicateMatch = {
      matchedInvoiceId: dup.matched.id,
      matchedPublicId: dup.matched.publicId,
      score: dup.score,
      reasons: dup.reasons,
      decision: invoice.duplicateMatch?.decision ?? "pending",
    };
    if (canTransition(invoice.status, "DUPLICATE") && duplicateMatch.decision !== "marked_unique") {
      status = "DUPLICATE";
    }
  }

  const blocking = issues.some((i) => i.blocking && !i.acknowledged);
  const low = invoice.fields.some((f) => f.confidence < CONFIDENCE_THRESHOLD && !f.corrected);
  if (status !== "DUPLICATE") {
    if (!blocking && !low && (invoice.status === "NEEDS_REVIEW" || invoice.status === "VALIDATED")) {
      status = "VALIDATED";
    } else if (blocking || low) {
      status = invoice.status === "VALIDATED" ? "NEEDS_REVIEW" : invoice.status;
    }
  }

  const nextInvoice: Invoice = {
    ...invoice,
    issues,
    status,
    duplicateMatch,
    duplicateScore: duplicateMatch?.score ?? 0,
    extractionConfidence: overallConfidence(invoice.fields),
    updatedAt: isoNow(),
  };

  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "validation_rerun",
          summary: `Validation rerun. Status ${status}. Confidence ${nextInvoice.extractionConfidence.toFixed(2)}. ${issues.length} issue(s).`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: {
      title: "Validation rerun",
      description: `Status ${status.replaceAll("_", " ")} · confidence ${nextInvoice.extractionConfidence.toFixed(2)}`,
      tone: "success",
    },
  };
}

export function acknowledgeVariance(state: AppState, publicId: string, reason: string): ActionResult {
  const user = actor(state);
  if (!canAcknowledgeVariance(user.role)) return deny(state, "Your role cannot acknowledge variance.");
  if (!reason.trim()) return deny(state, "An internal reason is required.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");

  const issues = invoice.issues.map((issue) =>
    issue.code === "PO_VARIANCE" ? { ...issue, acknowledged: true, blocking: false } : issue,
  );
  const nextInvoice: Invoice = {
    ...invoice,
    issues,
    varianceAcknowledged: true,
    varianceReason: reason.trim(),
    updatedAt: isoNow(),
  };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "variance_acknowledged",
          summary: `PO variance acknowledged: ${reason.trim()}`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Variance acknowledged", description: "Approval is now available if no other blockers remain.", tone: "success" },
  };
}

export function acknowledgeSecurity(state: AppState, publicId: string, reason: string): ActionResult {
  const user = actor(state);
  if (!canAcknowledgeVariance(user.role)) return deny(state, "Your role cannot acknowledge security findings.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");
  const issues = invoice.issues.map((issue) =>
    issue.code === "PROMPT_INJECTION" ? { ...issue, acknowledged: true, blocking: false } : issue,
  );
  const nextInvoice: Invoice = { ...invoice, issues, updatedAt: isoNow() };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "security",
          entityId: publicId,
          action: "security_acknowledged",
          summary: `Hostile document instruction remains ignored. Operator note: ${reason.trim() || "reviewed"}`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Security event acknowledged", description: "The document instruction was not executed.", tone: "info" },
  };
}

export function approveInvoice(state: AppState, publicId: string, reason = "Reviewed and approved"): ActionResult {
  const user = actor(state);
  if (!canApprove(user.role)) return deny(state, "Your role cannot approve invoices.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");
  const blocked = approvalBlockedReason(invoice);
  if (blocked) return deny(state, blocked);
  try {
    assertTransition(invoice.status, "APPROVED");
  } catch (err) {
    return deny(state, err instanceof Error ? err.message : "Invalid transition");
  }
  const nextInvoice: Invoice = {
    ...invoice,
    status: "APPROVED",
    updatedAt: isoNow(),
    approval: { id: newId("ap"), actorId: user.id, actorName: user.name, action: "approved", reason, at: isoNow() },
  };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "approved",
          summary: `Approved by ${user.name}. ${reason}`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Invoice approved", description: `${publicId} is ready for sandbox accounting sync.`, tone: "success" },
  };
}

export function rejectInvoice(state: AppState, publicId: string, reason: string): ActionResult {
  const user = actor(state);
  if (!canReject(user.role)) return deny(state, "Your role cannot reject invoices.");
  if (!reason.trim()) return deny(state, "A rejection reason is required.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");
  if (!canTransition(invoice.status, "REJECTED")) return deny(state, `Cannot reject from ${invoice.status}.`);
  const nextInvoice: Invoice = {
    ...invoice,
    status: "REJECTED",
    updatedAt: isoNow(),
    approval: { id: newId("ap"), actorId: user.id, actorName: user.name, action: "rejected", reason: reason.trim(), at: isoNow() },
  };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "rejected",
          summary: `Rejected: ${reason.trim()}`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Invoice rejected", description: reason.trim(), tone: "info" },
  };
}

export function confirmDuplicate(state: AppState, publicId: string): ActionResult {
  const user = actor(state);
  if (!canDecideDuplicate(user.role)) return deny(state, "Your role cannot decide duplicates.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice?.duplicateMatch) return deny(state, "No duplicate match on this invoice.");
  const nextInvoice: Invoice = {
    ...invoice,
    status: "DUPLICATE",
    duplicateMatch: { ...invoice.duplicateMatch, decision: "confirmed_duplicate" },
    updatedAt: isoNow(),
  };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "duplicate_confirmed",
          summary: `Confirmed duplicate of ${invoice.duplicateMatch.matchedPublicId}. Record retained.`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Duplicate confirmed", description: `${publicId} is retained as a duplicate of ${invoice.duplicateMatch.matchedPublicId}.`, tone: "success" },
  };
}

export function markUnique(state: AppState, publicId: string, reason: string): ActionResult {
  const user = actor(state);
  if (!canDecideDuplicate(user.role)) return deny(state, "Your role cannot decide duplicates.");
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice?.duplicateMatch) return deny(state, "No duplicate match on this invoice.");
  const nextInvoice: Invoice = {
    ...invoice,
    status: "NEEDS_REVIEW",
    duplicateMatch: { ...invoice.duplicateMatch, decision: "marked_unique" },
    issues: invoice.issues.map((issue) =>
      issue.code === "DUPLICATE_INVOICE_NUMBER" ? { ...issue, acknowledged: true, blocking: false } : issue,
    ),
    updatedAt: isoNow(),
  };
  const next = replaceInvoice(state, nextInvoice);
  return {
    state: {
      ...next,
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "invoice",
          entityId: publicId,
          action: "marked_unique",
          summary: `Marked unique versus ${invoice.duplicateMatch.matchedPublicId}. ${reason.trim()}`,
        }),
        ...next.auditEvents,
      ],
    },
    toast: { title: "Marked as unique", description: "Invoice returned to the review queue.", tone: "success" },
  };
}

function makeDelivery(invoice: Invoice, attemptNumber: number, succeed: boolean): DeliveryAttempt {
  const at = isoNow();
  if (succeed) {
    const numericSuffix = invoice.invoiceNumber.replace(/\D/g, "").slice(-5) || "XXXXX";
    const billId = `QBO-SB-${numericSuffix}`;
    return {
      id: newId("dlv"),
      publicId: `DLV-${Date.now().toString().slice(-8)}`,
      invoiceId: invoice.id,
      invoicePublicId: invoice.publicId,
      provider: "sandbox-quickbooks",
      attemptNumber,
      status: "succeeded",
      responseCode: 201,
      durationMs: 320 + attemptNumber * 12,
      nextRetryAt: null,
      providerBillId: billId,
      redactedError: null,
      redactedRequest: redactedPayload(invoice),
      createdAt: at,
    };
  }
  return {
    id: newId("dlv"),
    publicId: `DLV-${Date.now().toString().slice(-8)}`,
    invoiceId: invoice.id,
    invoicePublicId: invoice.publicId,
    provider: "sandbox-quickbooks",
    attemptNumber,
    status: attemptNumber >= 3 ? "failed_dead_letter" : "failed_retryable",
    responseCode: 503,
    durationMs: 640,
    nextRetryAt: attemptNumber >= 3 ? null : nextRetryIso(new Date(), attemptNumber),
    providerBillId: null,
    redactedError:
      attemptNumber >= 3
        ? "Sandbox provider rejected the request after 3 attempts. Dead-lettered. No real accounting system was contacted."
        : "Sandbox provider returned 503 Service Unavailable (simulated transient).",
    redactedRequest: redactedPayload(invoice),
    createdAt: at,
  };
}

export function syncAccounting(state: AppState, publicId: string): ActionResult {
  const user = actor(state);
  if (!canRetryDelivery(user.role) && !canApprove(user.role)) {
    return deny(state, "Your role cannot run accounting sync.");
  }
  const invoice = state.invoices.find((i) => i.publicId === publicId);
  if (!invoice) return deny(state, "Invoice not found.");
  if (invoice.status !== "APPROVED" && invoice.status !== "FAILED") {
    return deny(state, "Only approved or failed invoices can be synchronized.");
  }
  const syncKey = `sync_${publicId}`;
  if (state.syncKeys[syncKey] && invoice.status === "APPROVED" && invoice.providerBillId) {
    return {
      state,
      toast: {
        title: "Idempotent replay",
        description: `Existing sandbox bill ${invoice.providerBillId} reused. No real accounting provider was contacted.`,
        tone: "info",
      },
    };
  }

  const prior = state.deliveries.filter((d) => d.invoiceId === invoice.id);
  const attemptNumber = prior.length + 1;
  const succeed = invoice.publicId !== "INV-2026-00105" || attemptNumber >= 4;
  const delivery = makeDelivery(invoice, attemptNumber, succeed);

  let nextInvoice: Invoice;
  if (succeed) {
    nextInvoice = {
      ...invoice,
      status: "SYNCED",
      providerBillId: delivery.providerBillId,
      updatedAt: isoNow(),
    };
  } else {
    nextInvoice = {
      ...invoice,
      status: "FAILED",
      updatedAt: isoNow(),
    };
  }

  const next: AppState = {
    ...replaceInvoice(state, nextInvoice),
    deliveries: [delivery, ...state.deliveries],
    syncKeys: succeed && delivery.providerBillId ? { ...state.syncKeys, [syncKey]: delivery.providerBillId } : state.syncKeys,
    auditEvents: [
      audit(state, {
        actor: user.name,
        actorRole: user.role,
        entityType: "delivery",
        entityId: delivery.publicId,
        action: succeed ? "synced" : "sync_failed",
        summary: succeed
          ? `Sandbox bill ${delivery.providerBillId} created. No real accounting provider was contacted.`
          : `Sandbox delivery failed with HTTP ${delivery.responseCode}. ${delivery.redactedError}`,
      }),
      ...state.auditEvents,
    ],
  };

  return {
    state: next,
    toast: succeed
      ? {
          title: "Sandbox bill created",
          description: `${delivery.providerBillId} · No real accounting provider was contacted.`,
          tone: "success",
        }
      : {
          title: "Sandbox delivery failed",
          description: delivery.redactedError ?? "Simulated failure",
          tone: "error",
        },
  };
}

export function retryDelivery(state: AppState, deliveryId: string): ActionResult {
  const user = actor(state);
  if (!canRetryDelivery(user.role)) return deny(state, "Your role cannot retry deliveries.");
  const delivery = state.deliveries.find((d) => d.id === deliveryId || d.publicId === deliveryId);
  if (!delivery) return deny(state, "Delivery not found.");
  return syncAccounting(state, delivery.invoicePublicId);
}

export const INTAKE_NODES = [
  "Webhook",
  "Validate request",
  "Idempotency key",
  "Submit to FastAPI",
  "Start extraction",
  "Run validation",
  "Branch by result",
  "Record execution",
];

export const SYNC_NODES = [
  "Receive approved ID",
  "Read normalized invoice",
  "Create sandbox bill",
  "Store provider ID",
  "Record delivery attempt",
  "Retry / dead-letter",
];

export const ERROR_NODES = [
  "Capture error",
  "Classify retryability",
  "Redact payload",
  "Notify ops channel (simulated)",
];

export function simulateWorkflow(
  state: AppState,
  workflow: WorkflowExecution["workflow"],
  invoicePublicId: string | null,
): ActionResult {
  const nodesSource = workflow === "invoice-intake" ? INTAKE_NODES : workflow === "accounting-sync" ? SYNC_NODES : ERROR_NODES;
  const nodes: WorkflowNodeState[] = nodesSource.map((name) => ({
    name,
    status: "succeeded",
    durationMs: 20 + Math.floor(name.length * 3),
  }));
  const execution: WorkflowExecution = {
    id: newId("wf"),
    publicId: `WEX-${String(10000 + state.workflowExecutions.length + 1)}`,
    workflow,
    invoicePublicId,
    startedAt: isoNow(),
    durationMs: nodes.reduce((s, n) => s + (n.durationMs ?? 0), 0),
    status: "succeeded",
    failedNode: null,
    retryState: "none",
    version: workflow === "invoice-intake" ? "1.4.0" : workflow === "accounting-sync" ? "1.2.1" : "1.1.0",
    nodes,
  };
  const user = actor(state);
  return {
    state: {
      ...state,
      workflowExecutions: [execution, ...state.workflowExecutions],
      auditEvents: [
        audit(state, {
          actor: user.name,
          actorRole: user.role,
          entityType: "workflow",
          entityId: execution.publicId,
          action: "workflow_simulated",
          summary: `Simulated ${workflow} in-process. n8n was not called.`,
        }),
        ...state.auditEvents,
      ],
    },
    toast: {
      title: "Workflow simulated in-process",
      description: `${execution.publicId} · ${workflow}. n8n was not contacted.`,
      tone: "success",
    },
  };
}

export function metrics(state: AppState) {
  const invoices = state.invoices;
  const received = invoices.length;
  const awaiting = invoices.filter((i) => i.status === "NEEDS_REVIEW" || i.status === "DUPLICATE").length;
  const approved = invoices.filter((i) => i.status === "APPROVED" || i.status === "SYNCING" || i.status === "SYNCED" || i.status === "FAILED").length;
  const synchronized = invoices.filter((i) => i.status === "SYNCED").length;
  const duplicates = invoices.filter((i) => i.status === "DUPLICATE").length;
  const exceptions = invoices.filter((i) => i.issues.some((x) => x.severity === "error" || x.severity === "security")).length;
  const extracted = invoices.filter((i) => i.extractionConfidence > 0);
  const accuracy =
    extracted.length === 0
      ? 0
      : Math.round((extracted.reduce((s, i) => s + i.extractionConfidence, 0) / extracted.length) * 1000) / 10;
  const failedDeliveries = state.deliveries.filter((d) => d.status !== "succeeded" && d.status !== "pending").length;
  const byCurrency: Record<string, number> = {};
  for (const invoice of invoices) {
    byCurrency[invoice.currency] = (byCurrency[invoice.currency] ?? 0) + invoice.totalCents;
  }
  return {
    received,
    awaiting,
    approved,
    synchronized,
    duplicateRate: received === 0 ? 0 : Math.round((duplicates / received) * 1000) / 10,
    exceptionRate: received === 0 ? 0 : Math.round((exceptions / received) * 1000) / 10,
    extractionAccuracy: accuracy,
    avgProcessingHours: 6.4,
    failedDeliveries,
    byCurrency,
  };
}

export function formatTotals(byCurrency: Record<string, number>): string {
  return Object.entries(byCurrency)
    .map(([ccy, centsValue]) => formatMoney(centsValue, ccy as Invoice["currency"]))
    .join("  ·  ");
}

export function roleCan(role: Role, action: "approve" | "retry" | "reset" | "edit_vendor" | "correct"): boolean {
  switch (action) {
    case "approve":
      return canApprove(role);
    case "retry":
      return canRetryDelivery(role);
    case "reset":
      return canResetDemo(role);
    case "edit_vendor":
      return role === "admin" || role === "ap_manager";
    case "correct":
      return canCorrectFields(role);
    default:
      return false;
  }
}
