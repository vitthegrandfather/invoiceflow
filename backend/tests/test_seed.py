"""Demo seed is idempotent when run twice."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.orm import AuditEvent, DeliveryAttempt, Invoice, Vendor
from app.seed.runner import seed_database


async def test_seed_twice_does_not_duplicate(engine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        first = await seed_database(session)
        await session.commit()
        assert first["invoices"] >= 18
        second = await seed_database(session)
        await session.commit()
        assert second["invoices"] == 0
        assert second["vendors"] == 0
        invoices = int((await session.execute(select(func.count()).select_from(Invoice))).scalar_one())
        vendors = int((await session.execute(select(func.count()).select_from(Vendor))).scalar_one())
        deliveries = int((await session.execute(select(func.count()).select_from(DeliveryAttempt))).scalar_one())
        audit = int((await session.execute(select(func.count()).select_from(AuditEvent))).scalar_one())
        assert invoices == 18
        assert vendors == 8
        assert deliveries == 8
        assert audit >= 25


async def test_seeded_key_invoices(session) -> None:
    one = (await session.execute(select(Invoice).where(Invoice.public_id == "INV-2026-00101"))).scalar_one()
    assert one.total_cents == 124860
    assert one.status == "NEEDS_REVIEW"
    two = (await session.execute(select(Invoice).where(Invoice.public_id == "INV-2026-00102"))).scalar_one()
    assert two.status == "DUPLICATE"
    assert two.invoice_number == "NS-44190"
