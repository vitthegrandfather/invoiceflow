"""Shared schemas and error envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    field_errors: list[dict[str, str]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
    extra: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    service: str = "invoiceflow-api"
    database: str = "ok"
    provider: str = "sandbox"
    demo: bool = True
    note: str = "Fictional portfolio demonstration. No real accounting, email, or bank provider is contacted."
