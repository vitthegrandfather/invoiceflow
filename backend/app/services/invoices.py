"""Invoice application service. Matches the modular FastAPI routers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ForbiddenError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    ValidationFailedError,
)
from app.core.money import format_money, parse_decimal_to_cents
from app.models.orm import (
    ApprovalDecision,
    AuditEvent,
    DeliveryAttempt,
    DuplicateMatch,
    ExtractedField,
    ExtractionRun,
    IdempotencyKey,
    Invoice,
    InvoiceLineItem,
    ValidationIssue,
    WorkflowExecution,
)
from app.providers.factory import get_accounting_provider
from app.repositories.invoices import (
    AuditRepository,
    DeliveryRepository,
    IdempotencyRepository,
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    WorkflowRepository,
)
from app.schemas.invoice import (
    DuplicateDecisionRequest,
    FieldCorrectionRequest,
    IngestRequest,
    ReasonRequest,
    WorkflowExecutionIn,
)
from app.services.domain import (
    apply_po_variance,
    approval_blocked_reason,
    assert_transition,
    can_acknowledge_variance,
    can_approve,
    can_correct_fields,
    can_decide_duplicate,
    can_edit_vendor,
    can_retry_delivery,
    can_transition,
    find_duplicate,
    invoice_fingerprint,
    invoices_csv,
    mask_bank,
    overall_confidence,
    redacted_payload,
    run_validation,
    sanitize_filename,
    validate_upload,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid4())


def _ingest_hash(body: IngestRequest) -> str:
    payload = body.model_dump(mode="json")
    payload.pop("idempotency_key", None)
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_dict(invoice: Invoice) -> dict[str, Any]:
    match = None
    if invoice.duplicate_match:
        match = {
            "matched_invoice_id": invoice.duplicate_match.matched_invoice_id,
            "matched_public_id": invoice.duplicate_match.matched_public_id,
            "score": invoice.duplicate_match.score,
            "reasons": invoice.duplicate_match.reasons,
            "decision": invoice.duplicate_match.decision,
        }
    return {
        "id": invoice.id,
        "public_id": invoice.public_id,
        "vendor_id": invoice.vendor_id,
        "vendor_name": invoice.vendor_name,
        "invoice_number": invoice.invoice_number,
        "currency": invoice.currency,
        "subtotal_cents": invoice.subtotal_cents,
        "tax_cents": invoice.tax_cents,
        "total_cents": invoice.total_cents,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "status": invoice.status,
        "notes": invoice.notes,
        "source": invoice.source,
        "fields": [
            {"name": f.name, "value": f.value, "confidence": f.confidence, "corrected": f.corrected}
            for f in invoice.fields
        ],
        "issues": [
            {
                "id": i.id,
                "code": i.code,
                "severity": i.severity,
                "message": i.message,
                "blocking": i.blocking,
                "acknowledged": i.acknowledged,
                "field": i.field,
            }
            for i in invoice.issues
        ],
        "duplicate_match": match,
        "extraction": {"raw_text": invoice.extraction.raw_text} if invoice.extraction else None,
        "fingerprint": invoice.fingerprint,
        "po_number": invoice.po_number,
        "variance_acknowledged": invoice.variance_acknowledged,
        "bank_account_suffix": invoice.bank_account_suffix,
    }


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoices = InvoiceRepository(session)
        self.pos = PurchaseOrderRepository(session)
        self.audit_repo = AuditRepository(session)
        self.deliveries = DeliveryRepository(session)
        self.keys = IdempotencyRepository(session)
        self.vendors = VendorRepository(session)
        self.workflows = WorkflowRepository(session)

    async def _get(self, workspace_id: str, public_id: str) -> Invoice:
        invoice = await self.invoices.get(workspace_id, public_id)
        if invoice is None:
            raise NotFoundError(f"Invoice {public_id} not found")
        return invoice

    async def _audit(
        self,
        workspace_id: str,
        actor: str,
        actor_role: str | None,
        entity_type: str,
        entity_id: str,
        action: str,
        summary: str,
    ) -> None:
        await self.audit_repo.add(
            AuditEvent(
                id=_uid(),
                workspace_id=workspace_id,
                actor=actor,
                actor_role=actor_role,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                summary=summary,
                at=_now(),
            )
        )

    async def list_invoices(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
        vendor_id: str | None = None,
        q: str | None = None,
    ):
        return await self.invoices.list_page(
            workspace_id, page=page, page_size=page_size, status=status, vendor_id=vendor_id, q=q
        )

    async def get_invoice(self, workspace_id: str, public_id: str) -> Invoice:
        return await self._get(workspace_id, public_id)

    async def ingest(
        self,
        workspace_id: str,
        body: IngestRequest,
        *,
        actor: str,
        actor_role: str,
        idempotency_key: str | None = None,
    ) -> tuple[Invoice, bool]:
        errors = validate_upload(body.content_type, body.size_bytes, body.filename)
        if any("content type" in e or "10 MB" in e for e in errors):
            raise ValidationFailedError("; ".join(errors))
        key = idempotency_key or body.idempotency_key or f"ing_{body.invoice_number}"
        request_hash = _ingest_hash(body)
        existing = await self.keys.get(workspace_id, "ingest", key)
        if existing:
            if existing.request_hash and existing.request_hash != request_hash:
                raise IdempotencyConflictError("Idempotency-Key reused with a different payload.")
            invoice = await self.invoices.get(workspace_id, existing.resource_public_id)
            if invoice:
                return invoice, True
        vendor = await self.vendors.get_by_name(workspace_id, body.vendor_name)
        vendor_id = vendor.id if vendor else "vnd_unknown"
        public_id = f"INV-ING-{uuid4().hex[:6].upper()}"
        invoice = Invoice(
            id=_uid(),
            public_id=public_id,
            workspace_id=workspace_id,
            vendor_id=vendor_id,
            vendor_name=body.vendor_name,
            source=body.source,
            status="NEEDS_REVIEW",
            currency=body.currency,
            invoice_number=body.invoice_number,
            po_number=body.po_number,
            issue_date=body.issue_date,
            due_date=body.due_date,
            payment_terms=body.payment_terms,
            subtotal_cents=body.subtotal_cents,
            tax_cents=body.tax_cents,
            total_cents=body.total_cents,
            filename=sanitize_filename(body.filename),
            content_type=body.content_type,
            notes=body.notes,
            bank_account_suffix=mask_bank(body.bank_account_suffix),
            assigned_reviewer=body.assigned_reviewer,
            idempotency_key=key,
            created_at=_now(),
            updated_at=_now(),
            fingerprint=invoice_fingerprint(
                vendor_id=vendor_id,
                invoice_number=body.invoice_number,
                total_cents=body.total_cents,
                currency=body.currency,
                issue_date=body.issue_date,
            ),
        )
        for line in body.line_items:
            invoice.line_items.append(
                InvoiceLineItem(
                    id=_uid(),
                    description=line.description,
                    quantity=line.quantity,
                    unit_price_cents=line.unit_price_cents,
                    amount_cents=line.amount_cents,
                )
            )
        invoice.extraction = ExtractionRun(
            id=_uid(),
            method="sandbox_parser",
            started_at=_now(),
            completed_at=_now(),
            raw_text=body.raw_text or body.notes or "",
            overall_confidence=0.9,
        )
        await self.invoices.add(invoice)
        await self.keys.put(
            IdempotencyKey(
                id=_uid(),
                workspace_id=workspace_id,
                scope="ingest",
                key=key,
                resource_public_id=public_id,
                request_hash=request_hash,
                created_at=_now(),
            )
        )
        await self._audit(workspace_id, actor, actor_role, "invoice", public_id, "ingested", "Ingested via API")
        invoice = await self.validate(workspace_id, public_id, actor=actor, actor_role=actor_role)
        return invoice, False

    async def extract(self, workspace_id: str, public_id: str, *, actor: str, actor_role: str) -> Invoice:
        invoice = await self._get(workspace_id, public_id)
        await self._audit(
            workspace_id,
            actor,
            actor_role,
            "invoice",
            public_id,
            "extracted",
            "Sandbox extraction reused stored fields",
        )
        return invoice

    async def validate(self, workspace_id: str, public_id: str, *, actor: str, actor_role: str) -> Invoice:
        if not can_correct_fields(actor_role):
            raise ForbiddenError("Your role cannot rerun validation.")
        invoice = await self._get(workspace_id, public_id)
        siblings = [_as_dict(row) for row in await self.invoices.list_all(workspace_id) if row.id != invoice.id]
        po_row = await self.pos.get_for_invoice(workspace_id, invoice)
        po = None
        if po_row:
            po = {"public_id": po_row.public_id, "amount_cents": po_row.amount_cents, "currency": po_row.currency}
        payload = _as_dict(invoice)
        issues = run_validation(payload, siblings) + apply_po_variance(payload, po)
        invoice.issues.clear()
        for issue in issues:
            if issue["code"] == "PO_VARIANCE" and invoice.variance_acknowledged:
                issue["acknowledged"] = True
                issue["blocking"] = False
            invoice.issues.append(
                ValidationIssue(
                    id=_uid(),
                    code=issue["code"],
                    severity=issue["severity"],
                    field=issue.get("field"),
                    message=issue["message"],
                    blocking=issue["blocking"],
                    acknowledged=issue.get("acknowledged", False),
                )
            )
        dup = find_duplicate(payload, siblings)
        if dup and (not invoice.duplicate_match or invoice.duplicate_match.decision != "marked_unique"):
            if invoice.duplicate_match is None:
                invoice.duplicate_match = DuplicateMatch(
                    id=_uid(),
                    matched_invoice_id=dup["matched"]["id"],
                    matched_public_id=dup["matched"]["public_id"],
                    score=dup["score"],
                    reasons=dup["reasons"],
                    decision="pending",
                )
            else:
                invoice.duplicate_match.matched_invoice_id = dup["matched"]["id"]
                invoice.duplicate_match.matched_public_id = dup["matched"]["public_id"]
                invoice.duplicate_match.score = dup["score"]
                invoice.duplicate_match.reasons = dup["reasons"]
            invoice.duplicate_score = dup["score"]
            if can_transition(invoice.status, "DUPLICATE"):
                invoice.status = "DUPLICATE"
        invoice.extraction_confidence = overall_confidence([{"confidence": f.confidence} for f in invoice.fields])
        invoice.updated_at = _now()
        await self._audit(
            workspace_id, actor, actor_role, "invoice", public_id, "validation_rerun", f"Status {invoice.status}"
        )
        await self.session.flush()
        return invoice

    async def correct_field(
        self,
        workspace_id: str,
        public_id: str,
        body: FieldCorrectionRequest,
        *,
        actor: str,
        actor_role: str,
        actor_id: str | None = None,
    ) -> Invoice:
        if not can_correct_fields(actor_role):
            raise ForbiddenError("Your role cannot correct extracted fields.")
        invoice = await self._get(workspace_id, public_id)
        name, value = body.name, body.value
        field = next((f for f in invoice.fields if f.name == name), None)
        if field is None:
            invoice.fields.append(
                ExtractedField(
                    id=_uid(),
                    name=name,
                    value=value,
                    confidence=0.99,
                    original_value=value,
                    corrected=True,
                )
            )
        else:
            field.value = value
            field.confidence = max(field.confidence, 0.99)
            field.corrected = True
        mapping = {
            "vendor_name": "vendor_name",
            "invoice_number": "invoice_number",
            "issue_date": "issue_date",
            "due_date": "due_date",
            "currency": "currency",
        }
        if name in mapping:
            setattr(invoice, mapping[name], value)
        if name == "po_number":
            invoice.po_number = value or None
        if name == "bank_account_suffix":
            invoice.bank_account_suffix = mask_bank(value)
        if name in {"subtotal", "tax", "total"}:
            cents = parse_decimal_to_cents(value)
            if name == "subtotal":
                invoice.subtotal_cents = cents
            elif name == "tax":
                invoice.tax_cents = cents
            else:
                invoice.total_cents = cents
        invoice.extraction_confidence = overall_confidence([{"confidence": f.confidence} for f in invoice.fields])
        invoice.updated_at = _now()
        await self._audit(workspace_id, actor, actor_role, "invoice", public_id, "field_corrected", f"Corrected {name}")
        await self.session.flush()
        return invoice

    async def decide_duplicate(
        self,
        workspace_id: str,
        public_id: str,
        body: DuplicateDecisionRequest,
        *,
        actor: str,
        actor_role: str,
    ) -> Invoice:
        if not can_decide_duplicate(actor_role):
            raise ForbiddenError("Your role cannot decide duplicates.")
        invoice = await self._get(workspace_id, public_id)
        if invoice.duplicate_match is None:
            raise ValidationFailedError("No duplicate match on this invoice.")
        if body.decision == "confirmed_duplicate":
            invoice.status = "DUPLICATE"
            invoice.duplicate_match.decision = "confirmed_duplicate"
        else:
            invoice.status = "NEEDS_REVIEW"
            invoice.duplicate_match.decision = "marked_unique"
            for issue in invoice.issues:
                if issue.code == "DUPLICATE_INVOICE_NUMBER":
                    issue.acknowledged = True
                    issue.blocking = False
        invoice.updated_at = _now()
        await self._audit(
            workspace_id, actor, actor_role, "invoice", public_id, body.decision, body.reason or body.decision
        )
        await self.session.flush()
        return invoice

    async def acknowledge_variance(
        self,
        workspace_id: str,
        public_id: str,
        body: ReasonRequest,
        *,
        actor: str,
        actor_role: str,
    ) -> Invoice:
        if not can_acknowledge_variance(actor_role):
            raise ForbiddenError("Your role cannot acknowledge variance.")
        if not body.reason.strip():
            raise ValidationFailedError("An internal reason is required.")
        invoice = await self._get(workspace_id, public_id)
        invoice.variance_acknowledged = True
        invoice.variance_reason = body.reason.strip()
        for issue in invoice.issues:
            if issue.code == "PO_VARIANCE":
                issue.acknowledged = True
                issue.blocking = False
        invoice.updated_at = _now()
        await self._audit(
            workspace_id, actor, actor_role, "invoice", public_id, "variance_acknowledged", body.reason.strip()
        )
        await self.session.flush()
        return invoice

    async def acknowledge_security(
        self,
        workspace_id: str,
        public_id: str,
        body: ReasonRequest,
        *,
        actor: str,
        actor_role: str,
    ) -> Invoice:
        if not can_acknowledge_variance(actor_role):
            raise ForbiddenError("Your role cannot acknowledge security findings.")
        invoice = await self._get(workspace_id, public_id)
        for issue in invoice.issues:
            if issue.code == "PROMPT_INJECTION":
                issue.acknowledged = True
                issue.blocking = False
        invoice.updated_at = _now()
        await self._audit(
            workspace_id, actor, actor_role, "security", public_id, "security_acknowledged", body.reason or "reviewed"
        )
        await self.session.flush()
        return invoice

    async def approve(
        self,
        workspace_id: str,
        public_id: str,
        body: ReasonRequest,
        *,
        actor: str,
        actor_role: str,
        actor_id: str = "",
    ) -> Invoice:
        if not can_approve(actor_role):
            raise ForbiddenError("Your role cannot approve invoices.")
        invoice = await self._get(workspace_id, public_id)
        blocked = approval_blocked_reason(_as_dict(invoice))
        if blocked:
            raise ValidationFailedError(blocked)
        try:
            assert_transition(invoice.status, "APPROVED")
        except ValueError as exc:
            raise InvalidTransitionError(str(exc)) from exc
        invoice.status = "APPROVED"
        invoice.approval = ApprovalDecision(
            id=_uid(),
            actor_id=actor_id or "unknown",
            actor_name=actor,
            action="approved",
            reason=body.reason or "Reviewed and approved",
            at=_now(),
        )
        invoice.updated_at = _now()
        await self._audit(workspace_id, actor, actor_role, "invoice", public_id, "approved", body.reason or "approved")
        await self.session.flush()
        return invoice

    async def reject(
        self,
        workspace_id: str,
        public_id: str,
        body: ReasonRequest,
        *,
        actor: str,
        actor_role: str,
        actor_id: str = "",
    ) -> Invoice:
        if not can_approve(actor_role):
            raise ForbiddenError("Your role cannot reject invoices.")
        if not body.reason.strip():
            raise ValidationFailedError("A rejection reason is required.")
        invoice = await self._get(workspace_id, public_id)
        if not can_transition(invoice.status, "REJECTED"):
            raise InvalidTransitionError(f"Cannot reject from {invoice.status}.")
        invoice.status = "REJECTED"
        invoice.approval = ApprovalDecision(
            id=_uid(),
            actor_id=actor_id or "unknown",
            actor_name=actor,
            action="rejected",
            reason=body.reason.strip(),
            at=_now(),
        )
        invoice.updated_at = _now()
        await self._audit(workspace_id, actor, actor_role, "invoice", public_id, "rejected", body.reason.strip())
        await self.session.flush()
        return invoice

    async def sync(
        self,
        workspace_id: str,
        public_id: str,
        *,
        actor: str,
        actor_role: str,
        idempotency_key: str | None = None,
    ):
        if not (can_retry_delivery(actor_role) or can_approve(actor_role)):
            raise ForbiddenError("Your role cannot run accounting sync.")
        invoice = await self._get(workspace_id, public_id)
        if invoice.status not in {"APPROVED", "FAILED"}:
            raise ValidationFailedError("Only approved or failed invoices can be synchronized.")
        key = idempotency_key or f"sync_{public_id}"
        existing = await self.keys.get(workspace_id, "sync", key)
        if existing and invoice.provider_bill_id:
            return invoice, None
        prior = await self.deliveries.for_invoice(invoice.id)
        attempt_number = len(prior) + 1
        result = await get_accounting_provider().create_bill(_as_dict(invoice), attempt_number=attempt_number)
        public_dlv = await self.deliveries.next_public_id(workspace_id)
        status = "succeeded" if result.ok else ("failed_retryable" if result.retryable else "failed_dead_letter")
        if not result.ok and attempt_number >= 3:
            status = "failed_dead_letter"
        delivery = DeliveryAttempt(
            id=_uid(),
            workspace_id=workspace_id,
            public_id=public_dlv,
            invoice_id=invoice.id,
            invoice_public_id=invoice.public_id,
            provider=result.provider,
            attempt_number=attempt_number,
            status=status,
            response_code=result.status_code,
            duration_ms=result.duration_ms,
            provider_bill_id=result.provider_bill_id,
            redacted_error=result.error,
            redacted_request=redacted_payload(_as_dict(invoice)),
            created_at=_now(),
        )
        invoice.deliveries.append(delivery)
        if result.ok:
            invoice.status = "SYNCED"
            invoice.provider_bill_id = result.provider_bill_id
            await self.keys.put(
                IdempotencyKey(
                    id=_uid(),
                    workspace_id=workspace_id,
                    scope="sync",
                    key=key,
                    resource_public_id=result.provider_bill_id or public_id,
                    request_hash=key,
                    created_at=_now(),
                )
            )
            await self._audit(
                workspace_id,
                actor,
                actor_role,
                "delivery",
                public_dlv,
                "synced",
                f"Sandbox bill {result.provider_bill_id} created. No real accounting provider was contacted.",
            )
        else:
            invoice.status = "FAILED"
            await self._audit(
                workspace_id, actor, actor_role, "delivery", public_dlv, "sync_failed", result.error or "failed"
            )
        invoice.updated_at = _now()
        await self.session.flush()
        return invoice, delivery

    async def retry_delivery(self, workspace_id: str, delivery_id: str, *, actor: str, actor_role: str):
        row = await self.deliveries.get(workspace_id, delivery_id)
        if row is None:
            raise NotFoundError("Delivery not found")
        return await self.sync(workspace_id, row.invoice_public_id, actor=actor, actor_role=actor_role)

    async def list_vendors(self, workspace_id: str):
        vendors = await self.vendors.list(workspace_id)
        counts = await self.vendors.invoice_counts(workspace_id)
        return vendors, counts

    async def update_vendor(self, workspace_id: str, public_id: str, **fields: Any):
        actor_role = str(fields.pop("actor_role", "") or "")
        fields.pop("actor", None)
        if not can_edit_vendor(actor_role):
            raise ForbiddenError("Your role cannot edit vendor records.")
        vendor = await self.vendors.get(workspace_id, public_id)
        if vendor is None:
            raise NotFoundError("Vendor not found")
        for key in ("payment_terms", "status", "address"):
            if fields.get(key) is not None:
                setattr(vendor, key, fields[key])
        await self.session.flush()
        return vendor

    async def metrics(self, workspace_id: str) -> dict[str, Any]:
        invoices = list(await self.invoices.list_all(workspace_id))
        received = len(invoices)
        awaiting = sum(1 for i in invoices if i.status in {"NEEDS_REVIEW", "DUPLICATE"})
        approved = sum(1 for i in invoices if i.status in {"APPROVED", "SYNCING", "SYNCED", "FAILED"})
        synchronized = sum(1 for i in invoices if i.status == "SYNCED")
        duplicates = sum(1 for i in invoices if i.status == "DUPLICATE")
        exceptions = sum(1 for i in invoices if any(x.severity in {"error", "security"} for x in i.issues))
        extracted = [i for i in invoices if i.extraction_confidence > 0]
        accuracy = (
            round(sum(i.extraction_confidence for i in extracted) / len(extracted) * 1000) / 10 if extracted else 0
        )
        by_currency: dict[str, int] = {}
        for invoice in invoices:
            by_currency[invoice.currency] = by_currency.get(invoice.currency, 0) + invoice.total_cents
        return {
            "received": received,
            "awaiting": awaiting,
            "approved": approved,
            "synchronized": synchronized,
            "duplicate_rate": round(duplicates / received * 1000) / 10 if received else 0,
            "exception_rate": round(exceptions / received * 1000) / 10 if received else 0,
            "extraction_accuracy": accuracy,
            "avg_processing_hours": 6.4,
            "failed_deliveries": sum(1 for i in invoices if i.status == "FAILED"),
            "by_currency_cents": by_currency,
            "by_currency_display": {k: format_money(v, k) for k, v in by_currency.items()},
        }

    async def export_csv(self, workspace_id: str) -> str:
        rows = await self.invoices.list_all(workspace_id)
        return invoices_csv([_as_dict(i) for i in rows])

    async def record_ops_alert(self, workspace_id: str, body: Any, *, actor: str) -> None:
        await self._audit(
            workspace_id,
            actor,
            None,
            "workflow",
            getattr(body, "execution_id", None) or "unknown",
            "ops_alert",
            getattr(body, "message", "") or "simulated ops alert",
        )

    async def record_workflow(
        self,
        workspace_id: str,
        body: WorkflowExecutionIn,
        *,
        actor: str,
        actor_role: str,
    ) -> WorkflowExecution:
        n = await self.workflows.count(workspace_id)
        row = WorkflowExecution(
            id=_uid(),
            workspace_id=workspace_id,
            public_id=f"WEX-{10040 + n + 1}",
            workflow=body.workflow,
            invoice_public_id=body.invoice_public_id,
            started_at=_now(),
            duration_ms=body.duration_ms,
            status=body.status,
            failed_node=body.failed_node,
            retry_state=body.retry_state,
            version=body.version,
            nodes=[node.model_dump() for node in body.nodes],
            n8n_execution_id=body.n8n_execution_id,
        )
        await self.workflows.add(row)
        await self._audit(
            workspace_id,
            actor,
            actor_role,
            "workflow",
            row.public_id,
            "workflow_recorded",
            f"{body.workflow} {body.status}",
        )
        await self.session.flush()
        return row
