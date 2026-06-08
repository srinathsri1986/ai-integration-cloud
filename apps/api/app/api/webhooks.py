"""
Inbound webhook receiver with delivery tracking — Release 12.0 hardening.

POST /api/v1/webhooks/{flow_id}
  — verifies HMAC-SHA256 signature in X-Hub-Signature-256 header
  — pre-generates a delivery_id and records the delivery
  — enqueues execute_flow_task with delivery_id for full lifecycle tracking
  — returns 202

GET  /api/v1/webhooks/deliveries
  — list all recent webhook deliveries (filterable by status/flow_id)
GET  /api/v1/webhooks/deliveries/stats
  — aggregate delivery stats (total, succeeded, failed, dead_letter, processing)
GET  /api/v1/webhooks/deliveries/dead-letter-count
  — integer count of dead-lettered deliveries (used by UI badge)
GET  /api/v1/webhooks/{flow_id}/deliveries
  — deliveries for a specific flow
POST /api/v1/webhooks/deliveries/{delivery_id}/retry
  — manually re-queue a failed or dead-lettered delivery
"""

import hashlib
import hmac
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.auth import require_permissions
from app.core.database import SessionLocal
from app.db.models import FlowDefinitionRecord
from app.models.flows import FlowRunResponse
from app.models.webhooks import WebhookDelivery, WebhookDeliveryStats
from app.services import cloud_events
from app.services.flow_service import flow_service
from app.services.webhook_delivery_service import webhook_delivery_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Inbound webhook receiver — must come BEFORE /{flow_id}/deliveries catch-all
# ---------------------------------------------------------------------------


@router.post(
    "/{flow_id}",
    response_model=FlowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inbound webhook trigger (HMAC-authenticated)",
    description=(
        "Trigger a published webhook-type integration. "
        "The caller must include an X-Hub-Signature-256 header containing "
        "sha256=<HMAC-SHA256 of the raw request body signed with the flow's webhook secret>. "
        "Returns 202 immediately; execution is async. Each delivery is tracked "
        "with a unique delivery_id, enabling retry and dead-letter visibility."
    ),
)
async def receive_webhook(flow_id: str, request: Request) -> FlowRunResponse:
    body = await request.body()

    with SessionLocal() as session:
        record = session.query(FlowDefinitionRecord).filter(
            FlowDefinitionRecord.flow_id == flow_id,
        ).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown flow.")

    stored_secret = record.webhook_secret
    if not stored_secret:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Flow has no webhook secret configured.",
        )

    # Verify HMAC-SHA256 signature
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    expected_prefix = "sha256="
    if not signature_header.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed X-Hub-Signature-256 header.",
        )

    provided_sig = signature_header[len(expected_prefix):]
    expected_sig = hmac.new(
        stored_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    # Pre-generate delivery_id so we can record the delivery and pass it to the task
    delivery_id = uuid.uuid4().hex
    payload_hash = hashlib.sha256(body).hexdigest()

    # Best-effort CloudEvents detection (binary or structured content mode) —
    # e.g. events emitted by an SAP BTP Event Mesh broker. This is purely
    # additive observability: a non-CloudEvent (or malformed envelope) simply
    # yields None and the delivery is recorded exactly as it always has been.
    # Never raises — see app.services.cloud_events module docstring.
    try:
        parsed_event = cloud_events.detect_and_parse(
            request.headers, body, request.headers.get("content-type")
        )
    except Exception as exc:  # pragma: no cover - defense in depth; parser itself never raises
        logger.debug("CloudEvents detection failed for flow_id=%s: %s", flow_id, exc)
        parsed_event = None

    # Validate flow state, create run record, and enqueue task (with delivery_id)
    try:
        run_response = flow_service.trigger_webhook_verified(
            flow_id, tenant_id=record.tenant_id, delivery_id=delivery_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown flow.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Record delivery (after enqueue — task is async so the record will exist before it runs)
    webhook_delivery_service.record_received(
        flow_id=flow_id,
        payload_hash=payload_hash,
        request_id=run_response.request_id,
        tenant_id=record.tenant_id,
        max_attempts=_MAX_ATTEMPTS,
        delivery_id=delivery_id,
        cloud_event=parsed_event,
    )

    return run_response


# ---------------------------------------------------------------------------
# Delivery status & management routes
# ---------------------------------------------------------------------------


@router.get(
    "/deliveries/stats",
    response_model=WebhookDeliveryStats,
    summary="Webhook delivery aggregate stats",
)
def delivery_stats(
    user=Depends(require_permissions("audit:read")),
) -> WebhookDeliveryStats:
    """Return aggregate counts: total, succeeded, failed, dead_letter, processing."""
    return webhook_delivery_service.stats()


@router.get(
    "/deliveries/dead-letter-count",
    response_model=int,
    summary="Count of dead-lettered webhook deliveries",
)
def dead_letter_count(
    user=Depends(require_permissions("audit:read")),
) -> int:
    """Return the count of dead-lettered deliveries — used by the UI badge."""
    return webhook_delivery_service.dead_letter_count()


@router.get(
    "/deliveries",
    response_model=list[WebhookDelivery],
    summary="List webhook deliveries",
)
def list_deliveries(
    flow_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    user=Depends(require_permissions("audit:read")),
) -> list[WebhookDelivery]:
    """List recent webhook deliveries, optionally filtered by flow or status."""
    return webhook_delivery_service.list_all(
        status=status,
        flow_id=flow_id,
        limit=min(max(limit, 1), 500),
    )


@router.get(
    "/{flow_id}/deliveries",
    response_model=list[WebhookDelivery],
    summary="List deliveries for a specific flow",
)
def list_flow_deliveries(
    flow_id: str,
    limit: int = 50,
    user=Depends(require_permissions("audit:read")),
) -> list[WebhookDelivery]:
    return webhook_delivery_service.list_for_flow(flow_id, limit=min(max(limit, 1), 200))


@router.post(
    "/deliveries/{delivery_id}/retry",
    response_model=FlowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually re-queue a failed or dead-lettered delivery",
)
def retry_delivery(
    delivery_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> FlowRunResponse:
    """Re-enqueue a failed or dead-lettered webhook delivery for manual retry.

    A new flow run is created (new ``requestId``) and the delivery record is
    reset to ``processing`` with the same ``delivery_id``.
    """
    delivery = webhook_delivery_service.get(delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail=f"Delivery '{delivery_id}' not found.")

    if delivery.status not in {"failed", "dead_letter"}:
        raise HTTPException(
            status_code=409,
            detail=f"Delivery is in status '{delivery.status}'; only failed/dead_letter deliveries can be retried.",
        )

    with SessionLocal() as session:
        record = session.query(FlowDefinitionRecord).filter(
            FlowDefinitionRecord.flow_id == delivery.flow_id,
        ).first()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Flow '{delivery.flow_id}' no longer exists.")

    try:
        run_response = flow_service.trigger_webhook_verified(
            delivery.flow_id, tenant_id=record.tenant_id, delivery_id=delivery_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    webhook_delivery_service.mark_retrying(delivery_id, run_response.request_id)
    return run_response
