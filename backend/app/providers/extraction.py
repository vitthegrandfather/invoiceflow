"""Deterministic sandbox extractor. Never calls a real OCR vendor."""

from __future__ import annotations

from typing import Any

from app.core.money import money_to_decimal
from app.providers.base import ExtractionResult
from app.services.domain import detect_prompt_injection, mask_bank, normalize_extracted_fields, overall_confidence

FIELD_ORDER = (
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


class SandboxExtractionProvider:
    """Returns deterministic fields from the stored invoice payload.

    Low-confidence scans (TIFF / Harborline) and hostile notes are preserved as data.
    Instruction-like phrases are never executed.
    """

    async def extract(self, invoice: dict[str, Any]) -> ExtractionResult:
        method = "ocr_sandbox" if str(invoice.get("content_type", "")).startswith("image/") else "sandbox_parser"
        raw = invoice.get("raw_text") or _synthesize_raw(invoice)
        if detect_prompt_injection(raw) or detect_prompt_injection(invoice.get("notes") or ""):
            # Keep the hostile text in the extraction record. Do not change status/approval.
            pass

        values = normalize_extracted_fields(
            {
                "vendor_name": invoice.get("vendor_name") or "",
                "invoice_number": invoice.get("invoice_number") or "",
                "issue_date": invoice.get("issue_date") or "",
                "due_date": invoice.get("due_date") or "",
                "subtotal": money_to_decimal(int(invoice.get("subtotal_cents") or 0)),
                "tax": money_to_decimal(int(invoice.get("tax_cents") or 0)),
                "total": money_to_decimal(int(invoice.get("total_cents") or 0)),
                "currency": invoice.get("currency") or "USD",
                "po_number": invoice.get("po_number") or "",
                "bank_account_suffix": mask_bank(str(invoice.get("bank_account_suffix") or "0000")),
            }
        )

        confidences = _confidences_for(invoice)
        fields = [
            {
                "name": name,
                "value": str(values.get(name) or ""),
                "confidence": confidences[name],
                "original_value": str(values.get(name) or ""),
                "corrected": False,
            }
            for name in FIELD_ORDER
        ]
        # Harborline seed: keep the misread glyphs when this is the known low-confidence scan.
        if invoice.get("public_id") == "INV-2026-00104" or invoice.get("filename", "").lower().endswith(".tiff"):
            for field in fields:
                if field["name"] == "vendor_name":
                    field["value"] = field["original_value"] = "Haborline Facilites"
                    field["confidence"] = 0.72
                if field["name"] == "invoice_number":
                    field["value"] = field["original_value"] = "HL-19O-A"
                    field["confidence"] = 0.71
                if field["name"] == "due_date":
                    field["confidence"] = 0.64
                if field["name"] == "tax":
                    field["confidence"] = 0.78
                if field["name"] == "bank_account_suffix":
                    field["confidence"] = 0.81
        return ExtractionResult(
            method=method,
            overall_confidence=overall_confidence(fields),
            raw_text=raw,
            fields=fields,
        )


def _confidences_for(invoice: dict[str, Any]) -> dict[str, float]:
    base = 0.96
    if str(invoice.get("content_type", "")).startswith("image/"):
        base = 0.78
    return {
        "vendor_name": min(0.99, base + 0.02),
        "invoice_number": min(0.99, base + 0.03),
        "issue_date": min(0.99, base + 0.01),
        "due_date": max(0.5, base - 0.01),
        "subtotal": min(0.99, base + 0.01),
        "tax": max(0.5, base - 0.01),
        "total": min(0.99, base + 0.02),
        "currency": 0.99,
        "po_number": max(0.5, base - 0.02),
        "bank_account_suffix": max(0.5, base - 0.03),
    }


def _synthesize_raw(invoice: dict[str, Any]) -> str:
    notes = invoice.get("notes") or ""
    body = (
        f"{invoice.get('vendor_name')}\n"
        f"Invoice {invoice.get('invoice_number')}\n"
        f"PO {invoice.get('po_number') or ''}\n"
        f"Issue {invoice.get('issue_date')}  Due {invoice.get('due_date')}\n"
        f"Subtotal {money_to_decimal(int(invoice.get('subtotal_cents') or 0))}  "
        f"Tax {money_to_decimal(int(invoice.get('tax_cents') or 0))}  "
        f"Total {money_to_decimal(int(invoice.get('total_cents') or 0))} {invoice.get('currency')}\n"
        f"Remit to account ending {mask_bank(str(invoice.get('bank_account_suffix') or ''))[-4:]}\n"
    )
    if notes:
        body += f"Notes:\n{notes}\n"
    return body


class ProductionExtractionProvider:
    def __init__(self, vendor: str) -> None:
        self.vendor = vendor

    async def extract(self, invoice: dict[str, Any]) -> ExtractionResult:
        from app.core.errors import ProviderMisconfiguredError

        raise ProviderMisconfiguredError(
            f"EXTRACTION_PROVIDER={self.vendor} requires vendor credentials. "
            "InvoiceFlow is a fictional demo and will not call a real OCR vendor. "
            "Set EXTRACTION_PROVIDER=sandbox."
        )
