"""Role gates for approve / retry / reset."""

from __future__ import annotations

from app.services.domain import (
    can_approve,
    can_correct_fields,
    can_edit_vendor,
    can_reset_demo,
    can_retry_delivery,
)


def test_approvers() -> None:
    assert can_approve("admin")
    assert can_approve("ap_manager")
    assert can_approve("reviewer")
    assert not can_approve("viewer")


def test_retry_and_vendor_edit() -> None:
    assert can_retry_delivery("admin")
    assert can_retry_delivery("ap_manager")
    assert not can_retry_delivery("reviewer")
    assert not can_retry_delivery("viewer")
    assert can_edit_vendor("ap_manager")
    assert not can_edit_vendor("reviewer")


def test_reset_admin_only() -> None:
    assert can_reset_demo("admin")
    assert not can_reset_demo("ap_manager")
    assert not can_reset_demo("reviewer")
    assert not can_reset_demo("viewer")


def test_correct_fields() -> None:
    assert can_correct_fields("reviewer")
    assert not can_correct_fields("viewer")
