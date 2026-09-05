"""Idempotent seed. Running twice does not duplicate rows."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WORKSPACE_ID
from app.models.orm import (
    ApprovalDecision,
    AuditEvent,
    DeliveryAttempt,
    DuplicateMatch,
    ExtractedField,
    ExtractionRun,
    IdempotencyKey,
    Invoice,
    InvoiceLineItem,
    PurchaseOrder,
    User,
    ValidationIssue,
    Vendor,
    WorkflowExecution,
    Workspace,
)
from app.seed.data import (
    ALL_INVOICES,
    AUDIT,
    DELIVERIES,
    PURCHASE_ORDERS,
    SYNC_KEYS,
    USERS,
    VENDORS,
    WORKFLOWS,
    WORKSPACE,
)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)


async def _get(session: AsyncSession, model: type[Any], pk: str) -> Any:
    return await session.get(model, pk)


async def seed_database(session: AsyncSession) -> dict[str, int]:
    """Insert the Northwind demo if missing. Safe to call twice."""
    existing = await _get(session, Workspace, WORKSPACE_ID)
    created = {"workspace": 0, "users": 0, "vendors": 0, "invoices": 0, "deliveries": 0, "audit": 0}
    if existing is None:
        session.add(Workspace(**WORKSPACE))
        await session.flush()
        created["workspace"] = 1

    for user in USERS:
        row = await _get(session, User, user["id"])
        if row is None:
            session.add(User(workspace_id=WORKSPACE_ID, **user))
            created["users"] += 1

    for vendor in VENDORS:
        row = await _get(session, Vendor, vendor["id"])
        if row is None:
            session.add(Vendor(workspace_id=WORKSPACE_ID, **vendor))
            created["vendors"] += 1
    await session.flush()

    for po in PURCHASE_ORDERS:
        row = await _get(session, PurchaseOrder, po["id"])
        if row is None:
            session.add(PurchaseOrder(workspace_id=WORKSPACE_ID, **po))

    for inv in ALL_INVOICES:
        row = await _get(session, Invoice, inv["id"])
        if row is not None:
            continue
        invoice = Invoice(
            id=inv["id"],
            public_id=inv["public_id"],
            workspace_id=WORKSPACE_ID,
            vendor_id=inv["vendor_id"],
            vendor_name=inv["vendor_name"],
            source=inv["source"],
            status=inv["status"],
            currency=inv["currency"],
            invoice_number=inv["invoice_number"],
            po_number=inv.get("po_number"),
            po_id=inv.get("po_id"),
            issue_date=inv["issue_date"],
            due_date=inv["due_date"],
            payment_terms=inv["payment_terms"],
            subtotal_cents=inv["subtotal_cents"],
            tax_cents=inv["tax_cents"],
            total_cents=inv["total_cents"],
            extraction_confidence=inv["extraction_confidence"],
            duplicate_score=inv["duplicate_score"],
            assigned_reviewer=inv.get("assigned_reviewer"),
            created_at=_parse_dt(inv["created_at"]),
            updated_at=_parse_dt(inv["updated_at"]),
            filename=inv["filename"],
            content_type=inv["content_type"],
            notes=inv.get("notes") or "",
            bank_account_suffix=inv["bank_account_suffix"],
            variance_acknowledged=bool(inv.get("variance_acknowledged")),
            variance_reason=inv.get("variance_reason"),
            provider_bill_id=inv.get("provider_bill_id"),
            idempotency_key=inv["idempotency_key"],
            fingerprint=inv["fingerprint"],
        )
        for line in inv.get("line_items") or []:
            invoice.line_items.append(
                InvoiceLineItem(
                    id=line["id"],
                    description=line["description"],
                    quantity=line["quantity"],
                    unit_price_cents=line["unit_price_cents"],
                    amount_cents=line["amount_cents"],
                )
            )
        for field in inv.get("fields") or []:
            invoice.fields.append(
                ExtractedField(
                    name=field["name"],
                    value=field["value"],
                    confidence=field["confidence"],
                    original_value=field["original_value"],
                    corrected=field.get("corrected", False),
                )
            )
        for issue in inv.get("issues") or []:
            invoice.issues.append(
                ValidationIssue(
                    id=issue["id"],
                    code=issue["code"],
                    severity=issue["severity"],
                    field=issue.get("field"),
                    message=issue["message"],
                    blocking=issue.get("blocking", False),
                    acknowledged=issue.get("acknowledged", False),
                )
            )
        dup = inv.get("duplicate_match")
        if dup:
            invoice.duplicate_match = DuplicateMatch(
                matched_invoice_id=dup["matched_invoice_id"],
                matched_public_id=dup["matched_public_id"],
                score=dup["score"],
                reasons=list(dup["reasons"]),
                decision=dup["decision"],
            )
        extraction = inv.get("extraction")
        if extraction:
            invoice.extraction = ExtractionRun(
                id=extraction["id"],
                method=extraction["method"],
                started_at=_parse_dt(extraction["started_at"]),
                completed_at=_parse_dt(extraction["completed_at"]),
                overall_confidence=extraction["overall_confidence"],
                raw_text=extraction["raw_text"],
            )
        approval = inv.get("approval")
        if approval:
            invoice.approval = ApprovalDecision(
                id=approval["id"],
                actor_id=approval["actor_id"],
                actor_name=approval["actor_name"],
                action=approval["action"],
                reason=approval["reason"],
                at=_parse_dt(approval["at"]),
            )
        session.add(invoice)
        session.add(
            IdempotencyKey(
                workspace_id=WORKSPACE_ID,
                scope="ingest",
                key=inv["idempotency_key"],
                resource_public_id=inv["public_id"],
            )
        )
        created["invoices"] += 1
    await session.flush()

    for delivery in DELIVERIES:
        row = await _get(session, DeliveryAttempt, delivery["id"])
        if row is None:
            session.add(
                DeliveryAttempt(
                    workspace_id=WORKSPACE_ID,
                    created_at=_parse_dt(delivery["created_at"]),
                    **{k: v for k, v in delivery.items() if k != "created_at"},
                )
            )
            created["deliveries"] += 1

    for event in AUDIT:
        row = await _get(session, AuditEvent, event["id"])
        if row is None:
            session.add(
                AuditEvent(
                    workspace_id=WORKSPACE_ID,
                    at=_parse_dt(event["at"]),
                    **{k: v for k, v in event.items() if k != "at"},
                )
            )
            created["audit"] += 1

    for wf in WORKFLOWS:
        row = await _get(session, WorkflowExecution, wf["id"])
        if row is None:
            session.add(
                WorkflowExecution(
                    workspace_id=WORKSPACE_ID,
                    started_at=_parse_dt(wf["started_at"]),
                    **{k: v for k, v in wf.items() if k != "started_at"},
                )
            )

    for key, bill_id in SYNC_KEYS.items():
        existing_key = (
            await session.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.workspace_id == WORKSPACE_ID,
                    IdempotencyKey.scope == "sync",
                    IdempotencyKey.key == key,
                )
            )
        ).scalar_one_or_none()
        if existing_key is None:
            public_id = key.replace("sync_", "")
            session.add(
                IdempotencyKey(
                    workspace_id=WORKSPACE_ID,
                    scope="sync",
                    key=key,
                    resource_public_id=public_id,
                    request_hash=bill_id,
                )
            )

    await session.flush()
    return created


async def reset_database(session: AsyncSession) -> dict[str, int]:
    """Wipe demo workspace children and reseed. Admin-only at the API layer."""
    await session.execute(delete(IdempotencyKey).where(IdempotencyKey.workspace_id == WORKSPACE_ID))
    await session.execute(delete(AuditEvent).where(AuditEvent.workspace_id == WORKSPACE_ID))
    await session.execute(delete(WorkflowExecution).where(WorkflowExecution.workspace_id == WORKSPACE_ID))
    await session.execute(delete(DeliveryAttempt).where(DeliveryAttempt.workspace_id == WORKSPACE_ID))
    invoice_ids = select(Invoice.id).where(Invoice.workspace_id == WORKSPACE_ID)
    await session.execute(delete(InvoiceLineItem).where(InvoiceLineItem.invoice_id.in_(invoice_ids)))
    await session.execute(delete(ExtractedField).where(ExtractedField.invoice_id.in_(invoice_ids)))
    await session.execute(delete(ValidationIssue).where(ValidationIssue.invoice_id.in_(invoice_ids)))
    await session.execute(delete(DuplicateMatch).where(DuplicateMatch.invoice_id.in_(invoice_ids)))
    await session.execute(delete(ExtractionRun).where(ExtractionRun.invoice_id.in_(invoice_ids)))
    await session.execute(delete(ApprovalDecision).where(ApprovalDecision.invoice_id.in_(invoice_ids)))
    await session.execute(delete(Invoice).where(Invoice.workspace_id == WORKSPACE_ID))
    await session.execute(delete(PurchaseOrder).where(PurchaseOrder.workspace_id == WORKSPACE_ID))
    await session.execute(delete(Vendor).where(Vendor.workspace_id == WORKSPACE_ID))
    await session.execute(delete(User).where(User.workspace_id == WORKSPACE_ID))
    await session.execute(delete(Workspace).where(Workspace.id == WORKSPACE_ID))
    await session.flush()
    return await seed_database(session)


async def _main() -> None:
    from app.db.session import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        created = await seed_database(session)
        await session.commit()
        print(f"seed complete: {created}")


if __name__ == "__main__":
    asyncio.run(_main())
