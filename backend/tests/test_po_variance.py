"""Purchase-order variance (absolute cents + percent)."""

from __future__ import annotations

from app.core.money import variance_pct
from app.services.domain import apply_po_variance


def test_po_variance_meridian() -> None:
    invoice = {
        "id": "inv_00103",
        "public_id": "INV-2026-00103",
        "po_number": "PO-ML-2204",
        "total_cents": 451000,
        "currency": "EUR",
        "variance_acknowledged": False,
    }
    po = {"public_id": "PO-ML-2204", "amount_cents": 410000, "currency": "EUR"}
    issues = apply_po_variance(invoice, po)
    assert len(issues) == 1
    assert issues[0]["code"] == "PO_VARIANCE"
    assert issues[0]["blocking"] is True
    assert "10.00%" in issues[0]["message"]
    assert variance_pct(410000, 451000) == 10.0


def test_matching_po_no_issue() -> None:
    invoice = {
        "id": "inv_00101",
        "po_number": "PO-88421",
        "total_cents": 124860,
        "currency": "USD",
        "variance_acknowledged": False,
    }
    po = {"public_id": "PO-88421", "amount_cents": 124860, "currency": "USD"}
    assert apply_po_variance(invoice, po) == []


def test_acknowledged_flag_copied() -> None:
    invoice = {
        "id": "inv_00103",
        "po_number": "PO-ML-2204",
        "total_cents": 451000,
        "currency": "EUR",
        "variance_acknowledged": True,
    }
    po = {"public_id": "PO-ML-2204", "amount_cents": 410000, "currency": "EUR"}
    issues = apply_po_variance(invoice, po)
    assert issues[0]["acknowledged"] is True
