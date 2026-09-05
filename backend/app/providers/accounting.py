"""Sandbox accounting adapter. Production adapters fail closed — never silent fallback."""

from __future__ import annotations

from typing import Any

from app.core.errors import ProviderMisconfiguredError
from app.core.money import money_to_decimal
from app.providers.base import BillResult
from app.services.domain import mask_bank


class SandboxAccountingProvider:
    """Deterministic fictional QuickBooks-like bill create.

    INV-2026-00105 fails 503, 503, then 422 (dead-letter) to demonstrate retries.
    INV-2026-00116 returns 504. Everything else returns 201 with QBO-SB-* ids.
    """

    provider_name = "sandbox-quickbooks"

    async def create_bill(self, invoice: dict[str, Any], *, attempt_number: int) -> BillResult:
        public_id = invoice.get("public_id") or ""
        duration = 300 + attempt_number * 40
        _ = money_to_decimal(int(invoice.get("total_cents") or 0))
        _ = mask_bank(str(invoice.get("bank_account_suffix") or ""))

        if public_id == "INV-2026-00105":
            if attempt_number < 3:
                return BillResult(
                    ok=False,
                    status_code=503,
                    retryable=True,
                    provider_bill_id=None,
                    error="Sandbox provider returned 503 Service Unavailable (transient).",
                    duration_ms=duration + 1400,
                    provider=self.provider_name,
                )
            if attempt_number == 3:
                return BillResult(
                    ok=False,
                    status_code=422,
                    retryable=False,
                    provider_bill_id=None,
                    error=(
                        "Sandbox provider rejected bill: vendor currency calendar closed for period 2026-08 "
                        "(simulated). Moved to dead-letter after 3 attempts."
                    ),
                    duration_ms=388,
                    provider=self.provider_name,
                )
        if public_id == "INV-2026-00116" and attempt_number < 3:
            return BillResult(
                ok=False,
                status_code=504,
                retryable=True,
                provider_bill_id=None,
                error="Sandbox gateway timeout (504) creating bill. Retry scheduled.",
                duration_ms=8002,
                provider=self.provider_name,
            )

        digits = "".join(ch for ch in str(invoice.get("invoice_number") or "") if ch.isdigit())
        suffix = digits[-5:] if digits else "XXXXX"
        bill_id = f"QBO-SB-{suffix}"
        return BillResult(
            ok=True,
            status_code=201,
            retryable=False,
            provider_bill_id=bill_id,
            error=None,
            duration_ms=duration,
            provider=self.provider_name,
        )


class QuickBooksAccountingProvider:
    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        if not client_id or not client_secret:
            raise ProviderMisconfiguredError(
                "ACCOUNTING_PROVIDER=quickbooks requires QUICKBOOKS_CLIENT_ID and "
                "QUICKBOOKS_CLIENT_SECRET. InvoiceFlow will not silently fall back to the sandbox. "
                "This is a fictional demo — do not point it at a live QuickBooks company."
            )
        raise ProviderMisconfiguredError(
            "ACCOUNTING_PROVIDER=quickbooks is not enabled in this portfolio demonstration. "
            "Credentials were present but live QuickBooks calls are refused by design."
        )

    async def create_bill(self, invoice: dict[str, Any], *, attempt_number: int) -> BillResult:
        raise ProviderMisconfiguredError("Live QuickBooks is disabled in this demonstration.")


class XeroAccountingProvider:
    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        if not client_id or not client_secret:
            raise ProviderMisconfiguredError(
                "ACCOUNTING_PROVIDER=xero requires XERO_CLIENT_ID and XERO_CLIENT_SECRET. "
                "InvoiceFlow will not silently fall back to the sandbox."
            )
        raise ProviderMisconfiguredError(
            "ACCOUNTING_PROVIDER=xero is not enabled in this portfolio demonstration. "
            "Live Xero calls are refused by design."
        )

    async def create_bill(self, invoice: dict[str, Any], *, attempt_number: int) -> BillResult:
        raise ProviderMisconfiguredError("Live Xero is disabled in this demonstration.")
