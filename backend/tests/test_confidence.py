"""Field confidence warnings at the 0.85 review threshold."""

from __future__ import annotations

from app.services.domain import run_validation


def test_low_confidence_is_warning_not_blocking() -> None:
    invoice = {
        "id": "inv_00104",
        "public_id": "INV-2026-00104",
        "vendor_id": "vnd_003",
        "vendor_name": "Harborline Facilities",
        "invoice_number": "HL-190-A",
        "issue_date": "2026-08-20",
        "due_date": "2026-09-19",
        "subtotal_cents": 181375,
        "tax_cents": 36275,
        "total_cents": 217650,
        "currency": "GBP",
        "notes": "",
        "fields": [
            {"name": "vendor_name", "confidence": 0.72},
            {"name": "invoice_number", "confidence": 0.71},
            {"name": "due_date", "confidence": 0.64},
            {"name": "tax", "confidence": 0.78},
            {"name": "total", "confidence": 0.90},
        ],
        "extraction": {"raw_text": "harborline"},
    }
    issues = run_validation(invoice, [])
    low = [i for i in issues if i["code"] == "LOW_CONFIDENCE"]
    assert len(low) == 4
    assert all(i["severity"] == "warning" and not i["blocking"] for i in low)
