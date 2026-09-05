"""Pure domain rules ported from the InvoiceFlow browser engine.

These functions operate on plain dicts so they can be unit-tested without a database.
Money is always integer cents.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.constants import (
    ALLOWED_CONTENT_TYPES,
    CONFIDENCE_THRESHOLD,
    INJECTION_PATTERNS,
    MAX_UPLOAD_BYTES,
    SUPPORTED_CURRENCIES,
    TRANSITIONS,
)
from app.core.money import abs_cents, add_cents, format_money, money_to_decimal, variance_pct

COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, ())


def assert_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"Invalid status transition {from_status} → {to_status}")


def can_approve(role: str) -> bool:
    return role in {"admin", "ap_manager", "reviewer"}


def can_reject(role: str) -> bool:
    return can_approve(role)


def can_retry_delivery(role: str) -> bool:
    return role in {"admin", "ap_manager"}


def can_edit_vendor(role: str) -> bool:
    return role in {"admin", "ap_manager"}


def can_reset_demo(role: str) -> bool:
    return role == "admin"


def can_correct_fields(role: str) -> bool:
    return role in {"admin", "ap_manager", "reviewer"}


def can_decide_duplicate(role: str) -> bool:
    return can_correct_fields(role)


def can_acknowledge_variance(role: str) -> bool:
    return can_correct_fields(role)


def mask_bank(suffix: str) -> str:
    last4 = re.sub(r"\D", "", suffix)[-4:] or "0000"
    return f"••••{last4}"


def sanitize_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1] or "document"
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:180]
    return cleaned or "document"


def validate_upload(content_type: str, size_bytes: int, filename: str) -> list[str]:
    errors: list[str] = []
    if content_type not in ALLOWED_CONTENT_TYPES:
        errors.append(f"Unsupported content type: {content_type}")
    if size_bytes > MAX_UPLOAD_BYTES:
        errors.append("File exceeds 10 MB upload limit")
    if filename != sanitize_filename(filename):
        errors.append("Filename contains disallowed characters and was sanitized")
    return errors


def detect_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in COMPILED_INJECTION)


def escape_html(value: str) -> str:
    return (
        value.replace("&", "\u0026amp;")
        .replace("<", "\u0026lt;")
        .replace(">", "\u0026gt;")
        .replace('"', "\u0026quot;")
        .replace("'", "\u0026#39;")
    )


def formula_safe_cell(value: str) -> str:
    if value and value[0] in {"=", "+", "-", "@", "\t", "\r"}:
        return f"'{value}"
    return value


def to_csv(rows: list[list[str]]) -> str:
    lines: list[str] = []
    for row in rows:
        cells: list[str] = []
        for cell in row:
            safe = formula_safe_cell(cell)
            if any(ch in safe for ch in '",\n'):
                cells.append('"' + safe.replace('"', '""') + '"')
            else:
                cells.append(safe)
        lines.append(",".join(cells))
    return "\n".join(lines)


def invoice_fingerprint(
    *,
    vendor_id: str,
    invoice_number: str,
    total_cents: int,
    currency: str,
    issue_date: str,
) -> str:
    return "|".join(
        [
            vendor_id,
            invoice_number.strip().upper(),
            str(total_cents),
            currency,
            issue_date,
        ]
    )


def overall_confidence(fields: list[dict[str, Any]]) -> float:
    if not fields:
        return 0.0
    total = sum(float(f["confidence"]) for f in fields)
    return round((total / len(fields)) * 100) / 100


def low_confidence_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in fields if float(f["confidence"]) < CONFIDENCE_THRESHOLD]


def has_blocking_issues(issues: list[dict[str, Any]]) -> bool:
    return any(issue.get("blocking") and not issue.get("acknowledged") for issue in issues)


def approval_blocked_reason(invoice: dict[str, Any]) -> str | None:
    status = invoice["status"]
    match = invoice.get("duplicate_match")
    if status == "DUPLICATE" and (not match or match.get("decision") != "marked_unique"):
        return "Duplicate invoices cannot be approved until they are marked unique or confirmed."
    if status == "REJECTED":
        return "Rejected invoices cannot be approved."
    if status == "SYNCED":
        return "Already synchronized."
    if status not in {"NEEDS_REVIEW", "VALIDATED"}:
        return f"Cannot approve from {status}."
    for issue in invoice.get("issues", []):
        if issue.get("code") == "PO_VARIANCE" and issue.get("blocking") and not issue.get("acknowledged"):
            return "Purchase-order variance must be acknowledged before approval."
        if issue.get("severity") == "security" and issue.get("blocking") and not issue.get("acknowledged"):
            return "Security finding must be acknowledged before approval."
    if has_blocking_issues(invoice.get("issues", [])):
        return "Resolve or acknowledge blocking validation issues first."
    return None


def _issue(
    issue_id: str,
    code: str,
    severity: str,
    message: str,
    blocking: bool,
    field: str | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "code": code,
        "severity": severity,
        "message": message,
        "blocking": blocking,
        "field": field,
        "acknowledged": False,
    }


def run_validation(invoice: dict[str, Any], siblings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    invoice_id = invoice["id"]
    try:
        summed = add_cents(int(invoice["subtotal_cents"]), int(invoice["tax_cents"]))
    except Exception:
        summed = None
    if summed is None or summed != int(invoice["total_cents"]):
        issues.append(
            _issue(
                f"{invoice_id}-math",
                "TOTAL_MISMATCH",
                "error",
                (
                    f"Subtotal {money_to_decimal(int(invoice['subtotal_cents']))} plus tax "
                    f"{money_to_decimal(int(invoice['tax_cents']))} does not equal total "
                    f"{money_to_decimal(int(invoice['total_cents']))}."
                ),
                True,
                "total",
            )
        )
    if invoice["currency"] not in SUPPORTED_CURRENCIES:
        issues.append(
            _issue(
                f"{invoice_id}-ccy",
                "UNSUPPORTED_CURRENCY",
                "error",
                f"Currency {invoice['currency']} is not supported.",
                True,
                "currency",
            )
        )
    if invoice["due_date"] < invoice["issue_date"]:
        issues.append(
            _issue(
                f"{invoice_id}-due",
                "DUE_BEFORE_ISSUE",
                "error",
                "Due date is before issue date.",
                True,
                "due_date",
            )
        )
    if not str(invoice.get("vendor_name") or "").strip():
        issues.append(
            _issue(f"{invoice_id}-vnd", "VENDOR_REQUIRED", "error", "Vendor name is required.", True, "vendor_name")
        )
    if not str(invoice.get("invoice_number") or "").strip():
        issues.append(
            _issue(
                f"{invoice_id}-num",
                "INVOICE_NUMBER_REQUIRED",
                "error",
                "Invoice number is required.",
                True,
                "invoice_number",
            )
        )

    number = str(invoice.get("invoice_number") or "").strip().upper()
    for other in siblings:
        if other["id"] == invoice["id"]:
            continue
        if other.get("status") == "REJECTED":
            continue
        if (
            other.get("vendor_id") == invoice.get("vendor_id")
            and str(other.get("invoice_number") or "").strip().upper() == number
        ):
            issues.append(
                _issue(
                    f"{invoice_id}-numdup",
                    "DUPLICATE_INVOICE_NUMBER",
                    "error",
                    f"Invoice number {invoice['invoice_number']} already exists for this vendor as {other['public_id']}.",
                    True,
                    "invoice_number",
                )
            )
            break

    for field in invoice.get("fields", []):
        if float(field["confidence"]) < CONFIDENCE_THRESHOLD:
            label = str(field["name"]).replace("_", " ")
            pct = f"{float(field['confidence']) * 100:.0f}"
            issues.append(
                _issue(
                    f"{invoice_id}-cf-{field['name']}",
                    "LOW_CONFIDENCE",
                    "warning",
                    f"{label} confidence {pct}% is below the 85% review threshold.",
                    False,
                    field["name"],
                )
            )

    notes = invoice.get("notes") or ""
    raw = ""
    extraction = invoice.get("extraction")
    if extraction:
        raw = extraction.get("raw_text") or ""
    if notes and detect_prompt_injection(notes):
        issues.append(
            _issue(
                f"{invoice_id}-inj",
                "PROMPT_INJECTION",
                "security",
                "Untrusted document contents include an instruction-like phrase. "
                "Document text is treated as data only; the instruction was ignored.",
                True,
                "notes",
            )
        )
    elif raw and detect_prompt_injection(raw):
        issues.append(
            _issue(
                f"{invoice_id}-inj-raw",
                "PROMPT_INJECTION",
                "security",
                "Extracted text contains a prompt-injection style instruction. "
                "Extraction continued with the document treated as untrusted data.",
                True,
                "notes",
            )
        )
    return issues


def apply_po_variance(invoice: dict[str, Any], po: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not po or not invoice.get("po_number"):
        return []
    if po["currency"] != invoice["currency"] or int(po["amount_cents"]) != int(invoice["total_cents"]):
        diff = int(invoice["total_cents"]) - int(po["amount_cents"])
        pct = variance_pct(int(po["amount_cents"]), int(invoice["total_cents"]))
        return [
            {
                "id": f"{invoice['id']}-po",
                "code": "PO_VARIANCE",
                "severity": "error",
                "field": "po_number",
                "blocking": True,
                "acknowledged": bool(invoice.get("variance_acknowledged")),
                "message": (
                    f"Invoice total {format_money(int(invoice['total_cents']), invoice['currency'])} differs from PO "
                    f"{po['public_id']} expected {format_money(int(po['amount_cents']), po['currency'])} by "
                    f"{format_money(abs_cents(diff), invoice['currency'])} ({pct:.2f}%)."
                ),
            }
        ]
    return []


def find_duplicate(invoice: dict[str, Any], siblings: list[dict[str, Any]]) -> dict[str, Any] | None:
    fp = invoice_fingerprint(
        vendor_id=invoice["vendor_id"],
        invoice_number=invoice["invoice_number"],
        total_cents=int(invoice["total_cents"]),
        currency=invoice["currency"],
        issue_date=invoice["issue_date"],
    )
    for other in siblings:
        if other["id"] == invoice["id"] or other.get("status") == "REJECTED":
            continue
        if other.get("fingerprint") == fp:
            return {
                "matched": other,
                "score": 1.0,
                "reasons": [
                    "Same vendor",
                    "Same invoice number",
                    "Same total",
                    "Same currency",
                    "Same issue date",
                ],
            }

    best: dict[str, Any] | None = None
    for other in siblings:
        if other["id"] == invoice["id"] or other.get("status") == "REJECTED":
            continue
        reasons: list[str] = []
        score = 0.0
        if other.get("vendor_id") == invoice.get("vendor_id"):
            reasons.append("Same vendor")
            score += 0.25
        if (
            str(other.get("invoice_number") or "").strip().upper()
            == str(invoice.get("invoice_number") or "").strip().upper()
        ):
            reasons.append("Same invoice number")
            score += 0.35
        if int(other.get("total_cents") or 0) == int(invoice["total_cents"]) and other.get("currency") == invoice.get(
            "currency"
        ):
            reasons.append("Same amount and currency")
            score += 0.25
        if other.get("issue_date") == invoice.get("issue_date"):
            reasons.append("Same issue date")
            score += 0.15
        if score >= 0.75 and (best is None or score > best["score"]):
            best = {"matched": other, "score": min(score, 0.99), "reasons": reasons}
    return best


def normalize_invoice_number(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).upper()


def normalize_extracted_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize sandbox extraction output: trim, uppercase invoice numbers, mask bank."""
    out = dict(raw)
    if "invoice_number" in out and out["invoice_number"]:
        out["invoice_number"] = normalize_invoice_number(str(out["invoice_number"]))
    if "vendor_name" in out and out["vendor_name"]:
        out["vendor_name"] = str(out["vendor_name"]).strip()
    if "currency" in out and out["currency"]:
        out["currency"] = str(out["currency"]).strip().upper()
    if "bank_account_suffix" in out and out["bank_account_suffix"]:
        out["bank_account_suffix"] = mask_bank(str(out["bank_account_suffix"]))
    for money_key in ("subtotal", "tax", "total"):
        if money_key in out and out[money_key] is not None:
            text = str(out[money_key]).strip().replace(",", "")
            out[money_key] = text
    return out


def redacted_payload(invoice: dict[str, Any]) -> str:
    import json

    return json.dumps(
        {
            "invoice_id": invoice["public_id"],
            "vendor": invoice["vendor_name"],
            "total": money_to_decimal(int(invoice["total_cents"])),
            "currency": invoice["currency"],
            "invoice_number": invoice["invoice_number"],
            "bank_account": mask_bank(str(invoice.get("bank_account_suffix") or "")),
            "workspace": "ws_northwind_demo",
        },
        indent=2,
    )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def next_retry_iso(from_dt: datetime, attempt: int) -> str:
    minutes = min(60, 2**attempt)
    return (from_dt + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def is_retryable_status(status: str) -> bool:
    return status in {"failed_retryable", "failed_dead_letter"}


def invoices_csv(invoices: list[dict[str, Any]]) -> str:
    header = [
        "public_id",
        "vendor",
        "invoice_number",
        "status",
        "currency",
        "total",
        "issue_date",
        "due_date",
        "source",
    ]
    rows = [header]
    for invoice in invoices:
        rows.append(
            [
                invoice["public_id"],
                invoice["vendor_name"],
                invoice["invoice_number"],
                invoice["status"],
                invoice["currency"],
                money_to_decimal(int(invoice["total_cents"])),
                invoice["issue_date"],
                invoice["due_date"],
                invoice.get("source") or "",
            ]
        )
    return to_csv(rows)
