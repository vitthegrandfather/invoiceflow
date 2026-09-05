"""HTTP API: auth, list, permissions, validation, health."""

from __future__ import annotations

from tests.conftest import login


async def test_health(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "invoiceflow-api"


async def test_login_and_list_seeded_invoices(client) -> None:
    headers = await login(client)
    resp = await client.get("/invoices?page_size=50", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 18
    public_ids = {item["public_id"] for item in body["items"]}
    assert "INV-2026-00101" in public_ids


async def test_invoice_00101_clean_review(client) -> None:
    headers = await login(client)
    resp = await client.get("/invoices/INV-2026-00101", headers=headers)
    body = resp.json()
    assert body["status"] == "NEEDS_REVIEW"
    assert body["total_cents"] == 124860
    assert body["extraction_confidence"] == 0.96
    assert body["currency"] == "USD"
    assert body["vendor_name"] == "Northstar Office Supply"


async def test_viewer_cannot_approve(client) -> None:
    headers = await login(client, "eliot.ward@invoiceflow.example")
    resp = await client.post("/invoices/INV-2026-00101/approve", json={"reason": "nope"}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


async def test_approve_requires_valid_status(client) -> None:
    headers = await login(client)
    # 00105 is FAILED — cannot approve
    resp = await client.post("/invoices/INV-2026-00105/approve", json={"reason": "x"}, headers=headers)
    assert resp.status_code in {409, 422}


async def test_po_variance_blocks_approval(client) -> None:
    headers = await login(client)
    resp = await client.post("/invoices/INV-2026-00103/approve", json={"reason": "ignore variance"}, headers=headers)
    assert resp.status_code == 422
    assert "variance" in resp.json()["error"]["message"].lower()


async def test_ack_variance_then_approve(client) -> None:
    headers = await login(client)
    ack = await client.post(
        "/invoices/INV-2026-00103/acknowledge-variance",
        json={"reason": "Fuel surcharge approved by logistics"},
        headers=headers,
    )
    assert ack.status_code == 200, ack.text
    approved = await client.post(
        "/invoices/INV-2026-00103/approve",
        json={"reason": "Variance accepted"},
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"


async def test_hostile_invoice_stays_in_review(client) -> None:
    headers = await login(client)
    resp = await client.get("/invoices/INV-2026-00106", headers=headers)
    body = resp.json()
    assert body["status"] == "NEEDS_REVIEW"
    codes = {i["code"] for i in body["issues"]}
    assert "PROMPT_INJECTION" in codes
    approve = await client.post("/invoices/INV-2026-00106/approve", json={"reason": "obey notes"}, headers=headers)
    assert approve.status_code == 422


async def test_error_shape(client) -> None:
    resp = await client.get("/invoices")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert "code" in err and "message" in err and "request_id" in err


async def test_upload_rejects_exe(client) -> None:
    headers = await login(client)
    payload = {
        "vendor_name": "Northstar Office Supply",
        "invoice_number": "NS-BAD",
        "currency": "USD",
        "issue_date": "2026-08-30",
        "due_date": "2026-09-29",
        "subtotal_cents": 100,
        "tax_cents": 0,
        "total_cents": 100,
        "filename": "payload.exe",
        "content_type": "application/x-msdownload",
        "size_bytes": 12,
    }
    resp = await client.post("/invoices/ingest", json=payload, headers=headers)
    assert resp.status_code == 422


async def test_field_correction_and_validation(client) -> None:
    headers = await login(client, "priya.shah@invoiceflow.example")
    corr = await client.post(
        "/invoices/INV-2026-00104/corrections",
        json={"name": "vendor_name", "value": "Harborline Facilities"},
        headers=headers,
    )
    assert corr.status_code == 200, corr.text
    assert corr.json()["vendor_name"] == "Harborline Facilities"
    rerun = await client.post("/invoices/INV-2026-00104/validate", headers=headers)
    assert rerun.status_code == 200


async def test_duplicate_decision(client) -> None:
    headers = await login(client)
    resp = await client.post(
        "/invoices/INV-2026-00102/duplicate-decision",
        json={"decision": "confirmed_duplicate"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["duplicate_match"]["decision"] == "confirmed_duplicate"


async def test_metrics_and_vendors(client) -> None:
    headers = await login(client)
    metrics = await client.get("/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["received"] >= 18
    vendors = await client.get("/vendors", headers=headers)
    assert vendors.status_code == 200
    assert len(vendors.json()["items"]) == 8


async def test_export_csv_formula_safe(client) -> None:
    headers = await login(client)
    resp = await client.get("/export/csv", headers=headers)
    assert resp.status_code == 200
    assert "INV-2026-00101" in resp.text
    assert resp.headers["content-type"].startswith("text/csv")


async def test_viewer_cannot_reset(client) -> None:
    headers = await login(client, "eliot.ward@invoiceflow.example")
    resp = await client.post("/demo/reset", headers=headers)
    assert resp.status_code == 403


async def test_admin_reset(client) -> None:
    headers = await login(client, "jordan.hale@invoiceflow.example")
    resp = await client.post("/demo/reset", headers=headers)
    assert resp.status_code == 200, resp.text
    listed = await client.get("/invoices?page_size=50", headers=headers)
    assert listed.json()["total"] >= 18
