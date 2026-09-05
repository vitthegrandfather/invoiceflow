"""Shared constants for InvoiceFlow. Money is always integer cents."""

from __future__ import annotations

CONFIDENCE_THRESHOLD = 0.85
SUPPORTED_CURRENCIES = ("USD", "EUR", "GBP")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
)

FIELD_NAMES = (
    "vendor_name",
    "invoice_number",
    "issue_date",
    "due_date",
    "subtotal",
    "tax",
    "total",
    "currency",
    "po_number",
    "bank_account_suffix",
)

DEMO_PASSWORD = "demo-only"
WORKSPACE_PUBLIC_ID = "WS-NORTHWIND"
WORKSPACE_SLUG = "northwind-demo"
WORKSPACE_NAME = "Northwind Trading Demo"
WORKSPACE_ID = "11111111-0000-4000-8000-000000000001"

INVOICE_STATUSES = (
    "RECEIVED",
    "EXTRACTING",
    "NEEDS_REVIEW",
    "VALIDATED",
    "APPROVED",
    "REJECTED",
    "SYNCING",
    "SYNCED",
    "FAILED",
    "DUPLICATE",
)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "RECEIVED": ("EXTRACTING",),
    "EXTRACTING": ("NEEDS_REVIEW", "VALIDATED", "DUPLICATE", "FAILED"),
    "NEEDS_REVIEW": ("VALIDATED", "APPROVED", "REJECTED", "DUPLICATE"),
    "VALIDATED": ("APPROVED", "REJECTED", "NEEDS_REVIEW"),
    "APPROVED": ("SYNCING", "REJECTED"),
    "REJECTED": (),
    "SYNCING": ("SYNCED", "FAILED"),
    "SYNCED": (),
    "FAILED": ("SYNCING",),
    "DUPLICATE": ("NEEDS_REVIEW", "REJECTED"),
}

APPROVER_ROLES = frozenset({"admin", "ap_manager", "reviewer"})
MANAGER_ROLES = frozenset({"admin", "ap_manager"})
ADMIN_ROLES = frozenset({"admin"})

INJECTION_PATTERNS = (
    r"ignore (all )?previous instructions",
    r"skip validation",
    r"approve (this invoice )?immediately",
    r"set confidence to 1",
    r"mark as paid",
    r"do not flag",
    r"override (the )?policy",
    r"you are now",
    r"system prompt",
    r"disregard (all )?(rules|validation)",
)
