"""SQLAlchemy 2 mapped entities. Internal IDs are UUID strings; public IDs are human-readable."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)

    users: Mapped[list[User]] = relationship(back_populates="workspace")
    vendors: Mapped[list[Vendor]] = relationship(back_populates="workspace")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="workspace")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("workspace_id", "email", name="uq_user_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200), default="")

    workspace: Mapped[Workspace] = relationship(back_populates="users")


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("workspace_id", "public_id", name="uq_vendor_public"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    public_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str] = mapped_column(String(300))
    email: Mapped[str] = mapped_column(String(320))
    domain: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3))
    payment_terms: Mapped[str] = mapped_column(String(64))
    bank_account_suffix: Mapped[str] = mapped_column(String(16))
    tax_id: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_invoice_at: Mapped[str] = mapped_column(String(40), default="")

    workspace: Mapped[Workspace] = relationship(back_populates="vendors")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="vendor")
    purchase_orders: Mapped[list[PurchaseOrder]] = relationship(back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("workspace_id", "public_id", name="uq_po_public"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    public_id: Mapped[str] = mapped_column(String(64), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    issued_on: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(String(400))

    vendor: Mapped[Vendor] = relationship(back_populates="purchase_orders")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("workspace_id", "public_id", name="uq_invoice_public"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    public_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True)
    vendor_name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    invoice_number: Mapped[str] = mapped_column(String(80), index=True)
    po_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    po_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    issue_date: Mapped[str] = mapped_column(String(10))
    due_date: Mapped[str] = mapped_column(String(10))
    payment_terms: Mapped[str] = mapped_column(String(64), default="")
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    tax_cents: Mapped[int] = mapped_column(Integer)
    total_cents: Mapped[int] = mapped_column(Integer)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    duplicate_score: Mapped[float] = mapped_column(Float, default=0.0)
    assigned_reviewer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(80))
    notes: Mapped[str] = mapped_column(Text, default="")
    bank_account_suffix: Mapped[str] = mapped_column(String(16))
    variance_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    variance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_bill_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), index=True)
    fingerprint: Mapped[str] = mapped_column(String(300), index=True)
    object_key: Mapped[str | None] = mapped_column(String(300), nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="invoices")
    vendor: Mapped[Vendor] = relationship(back_populates="invoices")
    line_items: Mapped[list[InvoiceLineItem]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    extraction: Mapped[ExtractionRun | None] = relationship(
        back_populates="invoice", uselist=False, cascade="all, delete-orphan"
    )
    fields: Mapped[list[ExtractedField]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    issues: Mapped[list[ValidationIssue]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    duplicate_match: Mapped[DuplicateMatch | None] = relationship(
        back_populates="invoice", uselist=False, cascade="all, delete-orphan"
    )
    approval: Mapped[ApprovalDecision | None] = relationship(
        back_populates="invoice", uselist=False, cascade="all, delete-orphan"
    )
    deliveries: Mapped[list[DeliveryAttempt]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(400))
    quantity: Mapped[str] = mapped_column(String(32))
    unit_price_cents: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int] = mapped_column(Integer)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), unique=True)
    method: Mapped[str] = mapped_column(String(32), default="sandbox_parser")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    raw_text: Mapped[str] = mapped_column(Text, default="")

    invoice: Mapped[Invoice] = relationship(back_populates="extraction")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(400))
    confidence: Mapped[float] = mapped_column(Float)
    original_value: Mapped[str] = mapped_column(String(400))
    corrected: Mapped[bool] = mapped_column(Boolean, default=False)

    invoice: Mapped[Invoice] = relationship(back_populates="fields")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    invoice: Mapped[Invoice] = relationship(back_populates="issues")


class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), unique=True)
    matched_invoice_id: Mapped[str] = mapped_column(String(36))
    matched_public_id: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(32), default="pending")

    invoice: Mapped[Invoice] = relationship(back_populates="duplicate_match")


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), unique=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    actor_name: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    invoice: Mapped[Invoice] = relationship(back_populates="approval")


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (UniqueConstraint("workspace_id", "public_id", name="uq_delivery_public"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    public_id: Mapped[str] = mapped_column(String(64), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    invoice_public_id: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64), default="sandbox-quickbooks")
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    response_code: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_bill_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    redacted_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    redacted_request: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    invoice: Mapped[Invoice] = relationship(back_populates="deliveries")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    workflow: Mapped[str] = mapped_column(String(64), index=True)
    invoice_public_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32))
    failed_node: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retry_state: Mapped[str] = mapped_column(String(32), default="none")
    version: Mapped[str] = mapped_column(String(16), default="1.0.0")
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    n8n_execution_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    actor: Mapped[str] = mapped_column(String(200))
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("workspace_id", "scope", "key", name="uq_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    scope: Mapped[str] = mapped_column(String(32))  # ingest | sync
    key: Mapped[str] = mapped_column(String(160))
    resource_public_id: Mapped[str] = mapped_column(String(64))
    request_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
