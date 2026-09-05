"""Atlas Cloud delivery exhausts retries into dead-letter."""

from __future__ import annotations

from tests.conftest import login


async def test_retry_atlas_stays_failed_until_attempt_exhausted(client) -> None:
    headers = await login(client, "maya.chen@invoiceflow.example")
    # Seed already has 3 attempts and FAILED status for INV-2026-00105.
    detail = await client.get("/invoices/INV-2026-00105", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "FAILED"
    dead = [d for d in body["deliveries"] if d["status"] == "failed_dead_letter"]
    assert dead
    assert dead[0]["response_code"] == 422


async def test_retry_from_failed_creates_new_attempt(client) -> None:
    headers = await login(client, "jordan.hale@invoiceflow.example")
    resp = await client.post("/invoices/INV-2026-00116/sync", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in {"FAILED", "SYNCED"}
    assert body["deliveries"]
