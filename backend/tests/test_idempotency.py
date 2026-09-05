"""Ingest and sync idempotency keys."""

from __future__ import annotations

from tests.conftest import login


async def test_ingest_replay_same_key(client) -> None:
    headers = await login(client)
    payload = {
        "vendor_name": "Lumen Print Studio",
        "invoice_number": "LP-IDEMP-1",
        "currency": "USD",
        "issue_date": "2026-08-30",
        "due_date": "2026-09-29",
        "subtotal_cents": 10000,
        "tax_cents": 800,
        "total_cents": 10800,
        "source": "api",
        "filename": "LP-IDEMP-1.pdf",
        "content_type": "application/pdf",
        "notes": "idempotency check",
        "idempotency_key": "ing_lp_idemp_1",
    }
    first = await client.post("/invoices/ingest", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    public_id = first.json()["public_id"]
    second = await client.post(
        "/invoices/ingest", json=payload, headers={**headers, "Idempotency-Key": "ing_lp_idemp_1"}
    )
    assert second.status_code == 201
    assert second.json()["public_id"] == public_id


async def test_ingest_conflict_on_different_payload(client) -> None:
    headers = await login(client)
    payload = {
        "vendor_name": "Lumen Print Studio",
        "invoice_number": "LP-IDEMP-2",
        "currency": "USD",
        "issue_date": "2026-08-30",
        "due_date": "2026-09-29",
        "subtotal_cents": 10000,
        "tax_cents": 800,
        "total_cents": 10800,
        "source": "api",
        "filename": "LP-IDEMP-2.pdf",
        "content_type": "application/pdf",
        "idempotency_key": "ing_lp_idemp_2",
    }
    first = await client.post("/invoices/ingest", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    payload["total_cents"] = 99999
    second = await client.post("/invoices/ingest", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
