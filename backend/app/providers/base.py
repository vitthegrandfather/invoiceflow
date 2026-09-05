"""Provider protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ExtractionResult:
    method: str
    overall_confidence: float
    raw_text: str
    fields: list[dict[str, Any]]


@dataclass
class BillResult:
    ok: bool
    status_code: int
    retryable: bool
    provider_bill_id: str | None
    error: str | None
    duration_ms: int
    provider: str


class ExtractionProvider(Protocol):
    async def extract(self, invoice: dict[str, Any]) -> ExtractionResult: ...


class AccountingProvider(Protocol):
    async def create_bill(self, invoice: dict[str, Any], *, attempt_number: int) -> BillResult: ...


class NotificationProvider(Protocol):
    async def notify_ops(self, payload: dict[str, Any]) -> None: ...


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...

    async def exists(self, key: str) -> bool: ...
