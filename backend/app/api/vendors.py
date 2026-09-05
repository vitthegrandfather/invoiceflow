"""Vendor list and manager-only edits."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user, get_invoice_service
from app.schemas.invoice import VendorListResponse, VendorOut, VendorUpdateRequest
from app.services.invoices import InvoiceService

router = APIRouter(tags=["vendors"])


@router.get("/vendors", response_model=VendorListResponse)
async def list_vendors(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> VendorListResponse:
    vendors, counts = await service.list_vendors(user.workspace_id)
    items = []
    for vendor in vendors:
        out = VendorOut.model_validate(vendor)
        out.invoice_count = counts.get(vendor.id, 0)
        items.append(out)
    return VendorListResponse(items=items)


@router.patch("/vendors/{public_id}", response_model=VendorOut)
async def update_vendor(
    public_id: str,
    body: VendorUpdateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
) -> VendorOut:
    vendor = await service.update_vendor(
        user.workspace_id,
        public_id,
        payment_terms=body.payment_terms,
        status=body.status,
        address=body.address,
        actor=user.name,
        actor_role=user.role,
    )
    return VendorOut.model_validate(vendor)
