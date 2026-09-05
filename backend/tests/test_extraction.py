"""Extraction normalization and field confidence."""

from __future__ import annotations

import pytest

from app.core.constants import CONFIDENCE_THRESHOLD
from app.providers.extraction import SandboxExtractionProvider
from app.services.domain import (
    low_confidence_fields,
    normalize_extracted_fields,
    normalize_invoice_number,
    overall_confidence,
)


def test_normalize_invoice_number() -> None:
    assert normalize_invoice_number("  ns-44190 ") == "NS-44190"


def test_normalize_extracted_fields_masks_bank() -> None:
    out = normalize_extracted_fields(
        {"invoice_number": " ns-1 ", "vendor_name": " Northstar ", "currency": "usd", "bank_account_suffix": "0004412"}
    )
    assert out["invoice_number"] == "NS-1"
    assert out["bank_account_suffix"] == "••••4412"
    assert out["currency"] == "USD"


def test_overall_confidence_average() -> None:
    fields = [{"confidence": 0.98}, {"confidence": 0.94}]
    assert overall_confidence(fields) == 0.96


def test_low_confidence_threshold() -> None:
    fields = [
        {"name": "vendor_name", "confidence": 0.72},
        {"name": "total", "confidence": 0.96},
    ]
    low = low_confidence_fields(fields)
    assert len(low) == 1
    assert low[0]["name"] == "vendor_name"
    assert CONFIDENCE_THRESHOLD == 0.85


@pytest.mark.asyncio
async def test_sandbox_extraction_harborline_glyphs() -> None:
    provider = SandboxExtractionProvider()
    result = await provider.extract(
        {
            "public_id": "INV-2026-00104",
            "vendor_name": "Harborline Facilities",
            "invoice_number": "HL-190-A",
            "issue_date": "2026-08-20",
            "due_date": "2026-09-19",
            "subtotal_cents": 181375,
            "tax_cents": 36275,
            "total_cents": 217650,
            "currency": "GBP",
            "po_number": "PO-HL-190",
            "bank_account_suffix": "2271",
            "filename": "scan_HL190_aug.tiff",
            "content_type": "image/tiff",
            "notes": "",
        }
    )
    by_name = {f["name"]: f for f in result.fields}
    assert by_name["vendor_name"]["value"] == "Haborline Facilites"
    assert by_name["vendor_name"]["confidence"] < CONFIDENCE_THRESHOLD
    assert result.method == "ocr_sandbox"
