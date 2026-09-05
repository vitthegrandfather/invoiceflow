"""Resolve providers from settings. Unknown production names fail closed."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.errors import ProviderMisconfiguredError
from app.providers.accounting import QuickBooksAccountingProvider, SandboxAccountingProvider, XeroAccountingProvider
from app.providers.extraction import ProductionExtractionProvider, SandboxExtractionProvider
from app.providers.notification import SandboxNotificationProvider, SlackNotificationProvider
from app.providers.storage import S3ObjectStorage, get_sandbox_storage


def get_extraction_provider(
    settings: Settings | None = None,
) -> SandboxExtractionProvider | ProductionExtractionProvider:
    settings = settings or get_settings()
    name = (settings.extraction_provider or "sandbox").lower()
    if name in {"sandbox", "demo"}:
        return SandboxExtractionProvider()
    return ProductionExtractionProvider(name)


def get_accounting_provider(
    settings: Settings | None = None,
) -> SandboxAccountingProvider | QuickBooksAccountingProvider | XeroAccountingProvider:
    settings = settings or get_settings()
    name = (settings.accounting_provider or "sandbox").lower()
    if name in {"sandbox", "demo"}:
        return SandboxAccountingProvider()
    if name in {"quickbooks", "qbo"}:
        return QuickBooksAccountingProvider(settings.quickbooks_client_id, settings.quickbooks_client_secret)
    if name == "xero":
        return XeroAccountingProvider(settings.xero_client_id, settings.xero_client_secret)
    raise ProviderMisconfiguredError(
        f"Unknown ACCOUNTING_PROVIDER={name!r}. Supported: sandbox. "
        "Production names fail closed and never fall back to sandbox."
    )


def get_notification_provider(
    settings: Settings | None = None,
) -> SandboxNotificationProvider | SlackNotificationProvider:
    settings = settings or get_settings()
    name = (settings.notification_provider or "sandbox").lower()
    if name in {"sandbox", "demo"}:
        return SandboxNotificationProvider()
    if name == "slack":
        return SlackNotificationProvider(None)
    raise ProviderMisconfiguredError(f"Unknown NOTIFICATION_PROVIDER={name!r}.")


def get_storage(settings: Settings | None = None):
    settings = settings or get_settings()
    name = (settings.object_storage_provider or "sandbox").lower()
    if name in {"sandbox", "demo"}:
        return get_sandbox_storage()
    if name == "s3":
        return S3ObjectStorage(None, None, None)
    raise ProviderMisconfiguredError(f"Unknown OBJECT_STORAGE_PROVIDER={name!r}.")
