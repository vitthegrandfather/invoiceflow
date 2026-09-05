"""Invoice and related persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import (
    AuditEvent,
    DeliveryAttempt,
    IdempotencyKey,
    Invoice,
    PurchaseOrder,
    User,
    Vendor,
    WorkflowExecution,
    Workspace,
)

INVOICE_LOAD = (
    selectinload(Invoice.line_items),
    selectinload(Invoice.fields),
    selectinload(Invoice.issues),
    selectinload(Invoice.duplicate_match),
    selectinload(Invoice.extraction),
    selectinload(Invoice.approval),
    selectinload(Invoice.deliveries),
)


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, workspace_id: str, public_id: str) -> Invoice | None:
        stmt = (
            select(Invoice)
            .options(*INVOICE_LOAD)
            .where(Invoice.workspace_id == workspace_id, Invoice.public_id == public_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, workspace_id: str, invoice_id: str) -> Invoice | None:
        stmt = (
            select(Invoice).options(*INVOICE_LOAD).where(Invoice.workspace_id == workspace_id, Invoice.id == invoice_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, workspace_id: str) -> Sequence[Invoice]:
        stmt = select(Invoice).options(*INVOICE_LOAD).where(Invoice.workspace_id == workspace_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def list_page(
        self,
        workspace_id: str,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        vendor_id: str | None = None,
        q: str | None = None,
    ) -> tuple[list[Invoice], int]:
        filters = [Invoice.workspace_id == workspace_id]
        if status:
            filters.append(Invoice.status == status)
        if vendor_id:
            filters.append(Invoice.vendor_id == vendor_id)
        if q:
            like = f"%{q}%"
            filters.append(
                Invoice.public_id.ilike(like) | Invoice.invoice_number.ilike(like) | Invoice.vendor_name.ilike(like)
            )
        total = int(
            (await self.session.execute(select(func.count()).select_from(Invoice).where(*filters))).scalar_one()
        )
        stmt = (
            select(Invoice)
            .where(*filters)
            .order_by(Invoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def add(self, invoice: Invoice) -> Invoice:
        self.session.add(invoice)
        await self.session.flush()
        return invoice


class VendorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, workspace_id: str) -> Sequence[Vendor]:
        return (await self.session.execute(select(Vendor).where(Vendor.workspace_id == workspace_id))).scalars().all()

    async def get(self, workspace_id: str, public_id: str) -> Vendor | None:
        stmt = select(Vendor).where(Vendor.workspace_id == workspace_id, Vendor.public_id == public_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_name(self, workspace_id: str, name: str) -> Vendor | None:
        stmt = select(Vendor).where(Vendor.workspace_id == workspace_id, Vendor.name == name)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def invoice_counts(self, workspace_id: str) -> dict[str, int]:
        stmt = (
            select(Invoice.vendor_id, func.count())
            .where(Invoice.workspace_id == workspace_id)
            .group_by(Invoice.vendor_id)
        )
        return {row[0]: int(row[1]) for row in (await self.session.execute(stmt)).all()}


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        return (await self.session.execute(select(User).where(User.email == email))).scalar_one_or_none()

    async def get(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_demo(self) -> Workspace | None:
        from app.core.constants import WORKSPACE_PUBLIC_ID

        stmt = select(Workspace).where(Workspace.public_id == WORKSPACE_PUBLIC_ID)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: AuditEvent) -> None:
        self.session.add(event)

    async def list_page(self, workspace_id: str, *, page: int, page_size: int) -> tuple[list[AuditEvent], int]:
        filters = [AuditEvent.workspace_id == workspace_id]
        total = int(
            (await self.session.execute(select(func.count()).select_from(AuditEvent).where(*filters))).scalar_one()
        )
        stmt = (
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).scalars().all()), total


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, workspace_id: str, public_id: str) -> DeliveryAttempt | None:
        stmt = select(DeliveryAttempt).where(
            DeliveryAttempt.workspace_id == workspace_id,
            (DeliveryAttempt.public_id == public_id) | (DeliveryAttempt.id == public_id),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_invoice(self, invoice_id: str) -> Sequence[DeliveryAttempt]:
        stmt = (
            select(DeliveryAttempt)
            .where(DeliveryAttempt.invoice_id == invoice_id)
            .order_by(DeliveryAttempt.attempt_number)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def next_public_id(self, workspace_id: str) -> str:
        stmt = select(func.count()).select_from(DeliveryAttempt).where(DeliveryAttempt.workspace_id == workspace_id)
        n = int((await self.session.execute(stmt)).scalar_one()) + 1
        return f"DLV-2026-{n:05d}"


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, workspace_id: str, scope: str, key: str) -> IdempotencyKey | None:
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.workspace_id == workspace_id,
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def put(self, row: IdempotencyKey) -> None:
        self.session.add(row)
        await self.session.flush()


class PurchaseOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_invoice(self, workspace_id: str, invoice: Invoice) -> PurchaseOrder | None:
        if invoice.po_id:
            row = await self.session.get(PurchaseOrder, invoice.po_id)
            if row and row.workspace_id == workspace_id:
                return row
        if invoice.po_number:
            stmt = select(PurchaseOrder).where(
                PurchaseOrder.workspace_id == workspace_id,
                PurchaseOrder.public_id == invoice.po_number,
            )
            return (await self.session.execute(stmt)).scalar_one_or_none()
        return None


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: WorkflowExecution) -> None:
        self.session.add(row)
        await self.session.flush()

    async def list(self, workspace_id: str) -> Sequence[WorkflowExecution]:
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.workspace_id == workspace_id)
            .order_by(WorkflowExecution.started_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def count(self, workspace_id: str) -> int:
        stmt = select(func.count()).select_from(WorkflowExecution).where(WorkflowExecution.workspace_id == workspace_id)
        return int((await self.session.execute(stmt)).scalar_one())
