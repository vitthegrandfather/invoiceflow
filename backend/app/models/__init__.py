"""ORM models."""

from app.db.base import Base
from app.models.orm import (
    ApprovalDecision,
    AuditEvent,
    DeliveryAttempt,
    DuplicateMatch,
    ExtractedField,
    ExtractionRun,
    IdempotencyKey,
    Invoice,
    InvoiceLineItem,
    PurchaseOrder,
    User,
    ValidationIssue,
    Vendor,
    WorkflowExecution,
    Workspace,
)

__all__ = [
    "Base",
    "Workspace",
    "User",
    "Vendor",
    "Invoice",
    "InvoiceLineItem",
    "ExtractionRun",
    "ExtractedField",
    "ValidationIssue",
    "DuplicateMatch",
    "PurchaseOrder",
    "ApprovalDecision",
    "DeliveryAttempt",
    "WorkflowExecution",
    "AuditEvent",
    "IdempotencyKey",
]


def load_models() -> None:
    """Import side-effect to register metadata for Alembic / create_all."""
