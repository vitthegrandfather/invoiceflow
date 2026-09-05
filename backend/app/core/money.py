"""Integer-cents money helpers. Never use IEEE floats for currency amounts."""

from __future__ import annotations

import re

from app.core.constants import SUPPORTED_CURRENCIES
from app.core.errors import ValidationFailedError

_DECIMAL_RE = re.compile(r"^-?\d+(\.\d{1,2})?$")

CURRENCY_SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£"}


def assert_cents(amount: int) -> int:
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValidationFailedError("Monetary amounts must be integer cents.")
    return amount


def add_cents(*values: int) -> int:
    total = 0
    for value in values:
        total += assert_cents(value)
    return total


def abs_cents(value: int) -> int:
    return abs(assert_cents(value))


def money_to_decimal(amount_cents: int) -> str:
    assert_cents(amount_cents)
    sign = "-" if amount_cents < 0 else ""
    absolute = abs(amount_cents)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"


def format_money(amount_cents: int, currency: str) -> str:
    assert_cents(amount_cents)
    symbol = CURRENCY_SYMBOL.get(currency, "")
    sign = "-" if amount_cents < 0 else ""
    absolute = abs(amount_cents)
    whole = absolute // 100
    frac = absolute % 100
    grouped = f"{whole:,}"
    return f"{sign}{symbol}{grouped}.{frac:02d}"


def parse_decimal_to_cents(value: str) -> int:
    trimmed = value.strip().replace("$", "").replace("€", "").replace("£", "").replace(",", "").replace(" ", "")
    if not _DECIMAL_RE.match(trimmed):
        raise ValidationFailedError(f"Invalid decimal amount: {value!r}")
    negative = trimmed.startswith("-")
    unsigned = trimmed[1:] if negative else trimmed
    if "." in unsigned:
        whole_s, frac_s = unsigned.split(".", 1)
        frac_s = frac_s.ljust(2, "0")
    else:
        whole_s, frac_s = unsigned, "00"
    cents_value = int(whole_s) * 100 + int(frac_s)
    return -cents_value if negative else cents_value


def variance_pct(expected: int, received: int) -> float:
    """Percentage variance to two decimal places. Not used as a money amount."""
    assert_cents(expected)
    assert_cents(received)
    if expected == 0:
        return 0.0 if received == 0 else 100.0
    return round(abs(received - expected) * 10000 / expected) / 100


def totals_match(subtotal_cents: int, tax_cents: int, total_cents: int) -> bool:
    return add_cents(subtotal_cents, tax_cents) == assert_cents(total_cents)


def require_supported_currency(currency: str) -> str:
    if currency not in SUPPORTED_CURRENCIES:
        raise ValidationFailedError(f"Currency {currency} is not supported.")
    return currency
