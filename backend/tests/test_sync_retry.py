"""Sandbox sync retry classification and dead-letter."""

from __future__ import annotations

import pytest

from app.core.errors import ProviderMisconfiguredError
from app.providers.accounting import QuickBooksAccountingProvider, SandboxAccountingProvider
from app.workers.sync import classify_delivery, should_retry


@pytest.mark.asyncio
async def test_atlas_retries_then_dead_letter() -> None:
    provider = SandboxAccountingProvider()
    invoice = {
        "public_id": "INV-2026-00105",
        "invoice_number": "ATLAS-2026-440",
        "total_cents": 1840000,
        "bank_account_suffix": "••••6610",
        "vendor_name": "Atlas Cloud Services",
        "currency": "USD",
    }
    first = await provider.create_bill(invoice, attempt_number=1)
    assert first.status_code == 503
    assert first.retryable
    assert classify_delivery(first, 1) == "failed_retryable"
    third = await provider.create_bill(invoice, attempt_number=3)
    assert third.status_code == 422
    assert classify_delivery(third, 3) == "failed_dead_letter"


@pytest.mark.asyncio
async def test_success_bill_id_deterministic() -> None:
    provider = SandboxAccountingProvider()
    result = await provider.create_bill(
        {
            "public_id": "INV-2026-00101",
            "invoice_number": "NS-88421",
            "total_cents": 124860,
            "bank_account_suffix": "4412",
            "vendor_name": "Northstar",
            "currency": "USD",
        },
        attempt_number=1,
    )
    assert result.ok
    assert result.provider_bill_id == "QBO-SB-88421"


def test_should_retry_5xx_only() -> None:
    assert should_retry(503, 1)
    assert not should_retry(422, 1)
    assert not should_retry(503, 3)


def test_quickbooks_without_credentials_fails_closed() -> None:
    with pytest.raises(ProviderMisconfiguredError, match="will not silently fall back"):
        QuickBooksAccountingProvider(None, None)
