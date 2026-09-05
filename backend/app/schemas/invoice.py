"""Invoice request and response schemas. Money fields are integer cents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LineItemIn(BaseModel):
    description: str
    quantity: str = "1"
    unit_price_cents: int
    amount_cents: int


class LineItemOut(ORMModel):
    id: str
    description: str
    quantity: str
    unit_price_cents: int
    amount_cents: int


class ExtractedFieldOut(ORMModel):
    name: str
    value: str
    confidence: float
    original_value: str
    corrected: bool


class ValidationIssueOut(ORMModel):
    id: str
    code: str
    severity: str
    field: str | None = None
    message: str
    blocking: bool
    acknowledged: bool


class DuplicateMatchOut(ORMModel):
    matched_invoice_id: str
    matched_public_id: str
    score: float
    reasons: list[str]
    decision: str


class ExtractionRunOut(ORMModel):
    id: str
    method: str
    started_at: datetime
    completed_at: datetime
    overall_confidence: float
    raw_text: str


class ApprovalDecisionOut(ORMModel):
    id: str
    actor_id: str
    actor_name: str
    action: str
    reason: str
    at: datetime


class DeliveryAttemptOut(ORMModel):
    id: str
    public_id: str
    invoice_id: str
    invoice_public_id: str
    provider: str
    attempt_number: int
    status: str
    response_code: int
    duration_ms: int
    next_retry_at: str | None
    provider_bill_id: str | None
    redacted_error: str | None
    redacted_request: str
    created_at: datetime


class InvoiceSummary(ORMModel):
    id: str
    public_id: str
    vendor_id: str
    vendor_name: str
    source: str
    status: str
    currency: str
    invoice_number: str
    po_number: str | None
    issue_date: str
    due_date: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    extraction_confidence: float
    duplicate_score: float
    assigned_reviewer: str | None
    filename: str
    created_at: datetime
    updated_at: datetime
    provider_bill_id: str | None


class InvoiceDetail(InvoiceSummary):
    workspace_id: str
    po_id: str | None
    payment_terms: str
    notes: str
    bank_account_suffix: str
    content_type: str
    variance_acknowledged: bool
    variance_reason: str | None
    idempotency_key: str
    fingerprint: str
    line_items: list[LineItemOut]
    fields: list[ExtractedFieldOut]
    issues: list[ValidationIssueOut]
    duplicate_match: DuplicateMatchOut | None = None
    extraction: ExtractionRunOut | None = None
    approval: ApprovalDecisionOut | None = None
    deliveries: list[DeliveryAttemptOut] = []


class InvoiceListResponse(BaseModel):
    items: list[InvoiceSummary]
    page: int
    page_size: int
    total: int


class IngestRequest(BaseModel):
    vendor_name: str
    invoice_number: str
    currency: Literal["USD", "EUR", "GBP"] = "USD"
    issue_date: str
    due_date: str
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    source: Literal["upload", "email_webhook", "api"] = "api"
    filename: str = "invoice.pdf"
    content_type: str = "application/pdf"
    size_bytes: int = Field(default=1024, ge=0)
    notes: str = ""
    po_number: str | None = None
    payment_terms: str = "Net 30"
    bank_account_suffix: str = "0000"
    assigned_reviewer: str | None = None
    line_items: list[LineItemIn] = []
    idempotency_key: str | None = None
    raw_text: str | None = None


class FieldCorrectionRequest(BaseModel):
    name: str
    value: str


class ReasonRequest(BaseModel):
    reason: str = ""


class DuplicateDecisionRequest(BaseModel):
    decision: Literal["confirmed_duplicate", "marked_unique"]
    reason: str = ""


class SyncRequest(BaseModel):
    idempotency_key: str | None = None


class VendorOut(ORMModel):
    id: str
    public_id: str
    name: str
    legal_name: str
    email: str
    domain: str
    currency: str
    payment_terms: str
    bank_account_suffix: str
    tax_id: str
    address: str
    status: str
    last_invoice_at: str
    invoice_count: int = 0


class VendorUpdateRequest(BaseModel):
    payment_terms: str | None = None
    status: Literal["active", "on_hold", "inactive"] | None = None
    address: str | None = None


class VendorListResponse(BaseModel):
    items: list[VendorOut]


class AuditEventOut(ORMModel):
    id: str
    at: datetime
    actor: str
    actor_role: str | None
    entity_type: str
    entity_id: str
    action: str
    summary: str
    details: dict[str, str] | None = None


class AuditListResponse(BaseModel):
    items: list[AuditEventOut]
    page: int
    page_size: int
    total: int


class MetricsOut(BaseModel):
    received: int
    awaiting: int
    approved: int
    synchronized: int
    duplicate_rate: float
    exception_rate: float
    extraction_accuracy: float
    avg_processing_hours: float
    failed_deliveries: int
    by_currency_cents: dict[str, int]
    by_currency_display: dict[str, str]
    note: str = "Fictional Northwind Trading Demo metrics. No real money moved."


class WorkflowNodeOut(BaseModel):
    name: str
    status: str
    duration_ms: int | None = None
    note: str | None = None


class WorkflowExecutionIn(BaseModel):
    workflow: Literal["invoice-intake", "accounting-sync", "error-handler"]
    invoice_public_id: str | None = None
    status: str = "succeeded"
    failed_node: str | None = None
    retry_state: str = "none"
    version: str = "1.0.0"
    duration_ms: int = 0
    nodes: list[WorkflowNodeOut] = []
    n8n_execution_id: str | None = None


class WorkflowExecutionOut(ORMModel):
    id: str
    public_id: str
    workflow: str
    invoice_public_id: str | None
    started_at: datetime
    duration_ms: int
    status: str
    failed_node: str | None
    retry_state: str
    version: str
    nodes: list[Any]
    n8n_execution_id: str | None = None


class OpsAlertIn(BaseModel):
    workflow: str
    execution_id: str | None = None
    failed_node: str | None = None
    category: str = "unknown"
    retryable: bool = False
    message: str = ""
    invoice_public_id: str | None = None
    timestamp: str | None = None
