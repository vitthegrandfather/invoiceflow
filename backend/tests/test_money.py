"""Integer-cents monetary calculations. Never float."""

from __future__ import annotations

import pytest

from app.core.errors import ValidationFailedError
from app.core.money import (
    abs_cents,
    add_cents,
    assert_cents,
    format_money,
    money_to_decimal,
    parse_decimal_to_cents,
    totals_match,
    variance_pct,
)


def test_add_cents_exact() -> None:
    assert add_cents(114000, 10860) == 124860
    assert totals_match(114000, 10860, 124860)


def test_add_cents_rejects_float() -> None:
    with pytest.raises(ValidationFailedError):
        assert_cents(12.4)  # type: ignore[arg-type]


def test_money_to_decimal_no_float_repr() -> None:
    assert money_to_decimal(124860) == "1248.60"
    assert money_to_decimal(0) == "0.00"
    assert money_to_decimal(-150) == "-1.50"


def test_parse_decimal_to_cents() -> None:
    assert parse_decimal_to_cents("1248.60") == 124860
    assert parse_decimal_to_cents("$1,248.60") == 124860
    assert parse_decimal_to_cents("€4,510.00") == 451000


def test_parse_rejects_three_decimals() -> None:
    with pytest.raises(ValidationFailedError):
        parse_decimal_to_cents("1.234")


def test_format_money() -> None:
    assert format_money(124860, "USD") == "$1,248.60"
    assert format_money(451000, "EUR") == "€4,510.00"


def test_variance_pct_po_mismatch() -> None:
    assert variance_pct(410000, 451000) == 10.0
    assert abs_cents(451000 - 410000) == 41000


def test_variance_zero_expected() -> None:
    assert variance_pct(0, 0) == 0.0
    assert variance_pct(0, 100) == 100.0
