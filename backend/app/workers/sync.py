"""Accounting-sync worker helpers. Max 3 attempts; 5xx retryable; 4xx dead-letter."""

from __future__ import annotations

from app.providers.base import BillResult

MAX_ATTEMPTS = 3


def classify_delivery(result: BillResult, attempt_number: int) -> str:
    if result.ok:
        return "succeeded"
    if (not result.retryable) or attempt_number >= MAX_ATTEMPTS:
        return "failed_dead_letter"
    return "failed_retryable"


def should_retry(status_code: int, attempt_number: int) -> bool:
    if attempt_number >= MAX_ATTEMPTS:
        return False
    return 500 <= status_code <= 599
