"""Duplicate detection via fingerprint and weighted score."""

from __future__ import annotations

from app.services.domain import find_duplicate, invoice_fingerprint


def _inv(**kwargs):
    base = {
        "id": "a",
        "public_id": "INV-A",
        "vendor_id": "vnd_001",
        "invoice_number": "NS-44190",
        "total_cents": 89200,
        "currency": "USD",
        "issue_date": "2026-07-03",
        "status": "SYNCED",
        "fingerprint": "",
    }
    base.update(kwargs)
    base["fingerprint"] = invoice_fingerprint(
        vendor_id=base["vendor_id"],
        invoice_number=base["invoice_number"],
        total_cents=base["total_cents"],
        currency=base["currency"],
        issue_date=base["issue_date"],
    )
    return base


def test_exact_fingerprint_duplicate() -> None:
    original = _inv(id="inv_00097", public_id="INV-2026-00097")
    resubmit = _inv(id="inv_00102", public_id="INV-2026-00102", status="NEEDS_REVIEW")
    match = find_duplicate(resubmit, [original])
    assert match is not None
    assert match["score"] == 1
    assert match["matched"]["public_id"] == "INV-2026-00097"
    assert "Same invoice number" in match["reasons"]


def test_rejected_not_duplicate() -> None:
    original = _inv(id="x", status="REJECTED")
    other = _inv(id="y", public_id="INV-Y")
    assert find_duplicate(other, [original]) is None


def test_partial_score_below_threshold() -> None:
    original = _inv(id="x", invoice_number="OTHER")
    other = _inv(id="y", invoice_number="NS-44190", total_cents=1)
    # vendor + date = 0.40, below 0.75
    other["fingerprint"] = "different"
    original["fingerprint"] = "orig"
    assert find_duplicate(other, [original]) is None
