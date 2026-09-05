"""Demo reset and simulated ops alerts. Admin-only reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_invoice_service
from app.core.errors import ForbiddenError
from app.db.session import get_session
from app.schemas.invoice import OpsAlertIn
from app.seed.runner import reset_database
from app.services.domain import can_reset_demo
from app.services.invoices import InvoiceService

router = APIRouter(tags=["demo"])


@router.post("/demo/reset")
async def reset_demo(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    if not can_reset_demo(user.role):
        raise ForbiddenError("Only an Admin can reset demo data.")
    created = await reset_database(session)
    return {
        "message": "Demo data reset",
        "detail": "Seeded invoices, vendors, and deliveries restored.",
        "created": created,
        "actor": user.name,
    }


@router.post("/ops/alerts")
async def ops_alerts(
    body: OpsAlertIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> dict:
    await service.record_ops_alert(user.workspace_id, body, actor=user.name)
    return {"accepted": True, "note": "Simulated ops alert recorded. No real Slack workspace was contacted."}
