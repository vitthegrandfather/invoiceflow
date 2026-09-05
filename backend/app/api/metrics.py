"""Workspace metrics and formula-safe CSV export."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Depends as FastDepends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_invoice_service
from app.db.session import get_session
from app.repositories.invoices import AuditRepository, WorkflowRepository
from app.schemas.invoice import AuditListResponse, MetricsOut, WorkflowExecutionIn, WorkflowExecutionOut
from app.services.invoices import InvoiceService

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsOut)
async def metrics(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> MetricsOut:
    data = await service.metrics(user.workspace_id)
    return MetricsOut(**data)


@router.get("/export/csv")
async def export_csv(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> PlainTextResponse:
    csv = await service.export_csv(user.workspace_id)
    return PlainTextResponse(content=csv, media_type="text/csv; charset=utf-8")


@router.get("/audit-events", response_model=AuditListResponse)
async def audit_events(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, FastDepends(get_session)],
    page: int = 1,
    page_size: int = 50,
) -> AuditListResponse:
    items, total = await AuditRepository(session).list_page(user.workspace_id, page=page, page_size=page_size)
    from app.schemas.invoice import AuditEventOut

    return AuditListResponse(
        items=[AuditEventOut.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/workflows")
async def list_workflows(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, FastDepends(get_session)],
) -> dict:
    rows = await WorkflowRepository(session).list(user.workspace_id)
    return {"items": [WorkflowExecutionOut.model_validate(r).model_dump() for r in rows]}


@router.post("/workflows/executions", response_model=WorkflowExecutionOut)
async def record_workflow(
    body: WorkflowExecutionIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> WorkflowExecutionOut:
    row = await service.record_workflow(user.workspace_id, body, actor=user.name, actor_role=user.role)
    return WorkflowExecutionOut.model_validate(row)
