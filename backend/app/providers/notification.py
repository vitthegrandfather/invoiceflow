"""Sandbox ops notifications. Never posts to a real Slack workspace."""

from __future__ import annotations

import logging
from typing import Any

from app.core.errors import ProviderMisconfiguredError
from app.core.logging import redact

logger = logging.getLogger(__name__)


class SandboxNotificationProvider:
    async def notify_ops(self, payload: dict[str, Any]) -> None:
        logger.info("sandbox_ops_alert %s", redact(str(payload)))


class SlackNotificationProvider:
    def __init__(self, webhook_url: str | None) -> None:
        if not webhook_url:
            raise ProviderMisconfiguredError(
                "NOTIFICATION_PROVIDER=slack requires a webhook URL. "
                "InvoiceFlow will not silently fall back to the sandbox notifier."
            )
        raise ProviderMisconfiguredError("Live Slack notifications are disabled in this fictional demonstration.")

    async def notify_ops(self, payload: dict[str, Any]) -> None:
        raise ProviderMisconfiguredError("Live Slack is disabled in this demonstration.")
