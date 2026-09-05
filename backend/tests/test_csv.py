"""Formula-safe CSV export."""

from __future__ import annotations

from app.services.domain import formula_safe_cell, invoices_csv, to_csv


def test_formula_prefix_quoted() -> None:
    assert formula_safe_cell("=CMD()") == "'=CMD()"
    assert formula_safe_cell("+1+1") == "'+1+1"
    assert formula_safe_cell("-1+1") == "'-1+1"
    assert formula_safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert formula_safe_cell("Northstar") == "Northstar"


def test_invoices_csv_prefixes_dangerous_vendor() -> None:
    csv = invoices_csv(
        [
            {
                "public_id": "INV-2026-00101",
                "vendor_name": "=HYPERLINK()",
                "invoice_number": "NS-1",
                "status": "NEEDS_REVIEW",
                "currency": "USD",
                "total_cents": 124860,
                "issue_date": "2026-08-12",
                "due_date": "2026-09-11",
                "source": "email_webhook",
            }
        ]
    )
    assert "'=HYPERLINK()" in csv
    assert "1248.60" in csv


def test_to_csv_escapes_quotes() -> None:
    assert '"a""b"' in to_csv([['a"b']])
