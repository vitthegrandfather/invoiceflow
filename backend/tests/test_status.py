"""Invoice status machine. Invalid transitions must fail."""

from __future__ import annotations

import pytest

from app.services.domain import assert_transition, can_transition


def test_happy_path_transitions() -> None:
    assert can_transition("RECEIVED", "EXTRACTING")
    assert can_transition("EXTRACTING", "NEEDS_REVIEW")
    assert can_transition("NEEDS_REVIEW", "APPROVED")
    assert can_transition("APPROVED", "SYNCING")
    assert can_transition("SYNCING", "SYNCED")
    assert can_transition("FAILED", "SYNCING")
    assert can_transition("DUPLICATE", "NEEDS_REVIEW")


def test_no_auto_from_validated_to_approved_is_allowed_but_not_automatic() -> None:
    # Human approval is allowed from VALIDATED; the service never auto-approves.
    assert can_transition("VALIDATED", "APPROVED")


def test_rejected_is_terminal() -> None:
    assert can_transition("REJECTED", "APPROVED") is False
    with pytest.raises(ValueError, match="Invalid status transition"):
        assert_transition("REJECTED", "APPROVED")


def test_synced_is_terminal() -> None:
    with pytest.raises(ValueError):
        assert_transition("SYNCED", "APPROVED")


def test_cannot_skip_received_to_approved() -> None:
    with pytest.raises(ValueError):
        assert_transition("RECEIVED", "APPROVED")
