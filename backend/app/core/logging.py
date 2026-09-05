"""Structured JSON logging with redaction of bank numbers and secrets."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

BANK_RE = re.compile(r"\b(?:\d[ -]?){8,17}\d\b")
SECRET_RE = re.compile(r"(?i)(password|secret|token|authorization|api[_-]?key)\s*[:=]\s*\S+")
ACCOUNT_RE = re.compile(r"(?i)(account(?:_number)?|iban|routing)[\"']?\s*[:=]\s*[\"']?[\dA-Za-z]+")


def redact(text: str) -> str:
    text = BANK_RE.sub("••••REDACTED", text)
    text = SECRET_RE.sub(r"\1=••••REDACTED", text)
    text = ACCOUNT_RE.sub(r"\1=••••REDACTED", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "workspace_id"):
            payload["workspace_id"] = record.workspace_id
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
