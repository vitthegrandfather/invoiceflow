"""Invoice HTTP API. Handlers stay thin and delegate to InvoiceService."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.api.deps import CurrentUser, actor_from, get_current_user, get_invoice_service
from app.schemas.invoice import (
    DuplicateDecisionRequest,
    FieldCorrectionRequest,
    IngestRequest,
    InvoiceDetail,
    InvoiceListResponse,
    InvoiceSummary,
    ReasonRequest,
    SyncRequest,
)
from app.services.invoices import InvoiceService

router = APIRouter(tags=["invoices"])


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    vendor_id: str | None = None,
    q: str | None = None,
) -> InvoiceListResponse:
    items, total = await service.list_invoices(
        user.workspace_id, page=page, page_size=page_size, status=status, vendor_id=vendor_id, q=q
    )
    return InvoiceListResponse(
        items=[InvoiceSummary.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/invoices/ingest", response_model=InvoiceDetail, status_code=201)
async def ingest_invoice(
    body: IngestRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> InvoiceDetail:
    invoice, replayed = await service.ingest(
        user.workspace_id,
        body,
        actor=user.name,
        actor_role=user.role,
        idempotency_key=idempotency_key,
    )
    detail = InvoiceDetail.model_validate(invoice)
    if replayed:
        return detail
    return detail


@router.get("/invoices/{public_id}", response_model=InvoiceDetail)
async def get_invoice(
    public_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.get_invoice(user.workspace_id, public_id)
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/extract", response_model=InvoiceDetail)
async def extract_invoice(
    public_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.extract(user.workspace_id, public_id, actor=user.name, actor_role=user.role)
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/validate", response_model=InvoiceDetail)
async def validate_invoice(
    public_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.validate(user.workspace_id, public_id, actor=user.name, actor_role=user.role)
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/corrections", response_model=InvoiceDetail)
async def correct_field(
    public_id: str,
    body: FieldCorrectionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.correct_field(user.workspace_id, public_id, body, **actor_from(user))
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/duplicate-decision", response_model=InvoiceDetail)
async def duplicate_decision(
    public_id: str,
    body: DuplicateDecisionRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.decide_duplicate(user.workspace_id, public_id, body, actor=user.name, actor_role=user.role)
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/acknowledge-variance", response_model=InvoiceDetail)
async def acknowledge_variance(
    public_id: str,
    body: ReasonRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.acknowledge_variance(
        user.workspace_id, public_id, body, actor=user.name, actor_role=user.role
    )
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/acknowledge-security", response_model=InvoiceDetail)
async def acknowledge_security(
    public_id: str,
    body: ReasonRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.acknowledge_security(
        user.workspace_id, public_id, body, actor=user.name, actor_role=user.role
    )
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/approve", response_model=InvoiceDetail)
async def approve_invoice(
    public_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    body: ReasonRequest | None = None,
) -> InvoiceDetail:
    invoice = await service.approve(
        user.workspace_id, public_id, body or ReasonRequest(reason="Reviewed and approved"), **actor_from(user)
    )
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/reject", response_model=InvoiceDetail)
async def reject_invoice(
    public_id: str,
    body: ReasonRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice = await service.reject(user.workspace_id, public_id, body, **actor_from(user))
    return InvoiceDetail.model_validate(invoice)


@router.post("/invoices/{public_id}/sync", response_model=InvoiceDetail)
async def sync_invoice(
    public_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    body: SyncRequest | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> InvoiceDetail:
    key = idempotency_key or (body.idempotency_key if body else None)
    invoice, _delivery = await service.sync(
        user.workspace_id, public_id, actor=user.name, actor_role=user.role, idempotency_key=key
    )
    return InvoiceDetail.model_validate(invoice)


@router.post("/deliveries/{delivery_id}/retry", response_model=InvoiceDetail)
async def retry_delivery(
    delivery_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> InvoiceDetail:
    invoice, _delivery = await service.retry_delivery(
        user.workspace_id, delivery_id, actor=user.name, actor_role=user.role
    )
    return InvoiceDetail.model_validate(invoice)
