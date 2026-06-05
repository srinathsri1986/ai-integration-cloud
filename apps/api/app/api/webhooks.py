"""
Inbound webhook receiver — Release 5.0 HMAC security upgrade.

POST /api/v1/webhooks/{flow_id}
  — verifies HMAC-SHA256 signature in X-Hub-Signature-256 header
  — verifies the flow is published and has trigger_type="webhook"
  — enqueues execute_flow_task and returns 202

The webhook secret is stored server-side (flow_definitions.webhook_secret).
The caller computes the signature as:
    X-Hub-Signature-256: sha256=<hmac.new(secret, body, sha256).hexdigest()>

The secret is never transmitted in the URL or response body.
"""

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, status

from app.db.models import FlowDefinitionRecord
from app.core.database import SessionLocal
from app.models.flows import FlowRunResponse
from app.services.flow_service import flow_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/{flow_id}",
    response_model=FlowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inbound webhook trigger (HMAC-authenticated)",
    description=(
        "Trigger a published webhook-type integration. "
        "The caller must include an X-Hub-Signature-256 header containing "
        "sha256=<HMAC-SHA256 of the raw request body signed with the flow's webhook secret>. "
        "Returns 202 immediately; execution is async."
    ),
)
async def receive_webhook(flow_id: str, request: Request) -> FlowRunResponse:
    # Read raw body before any parsing (needed for HMAC verification)
    body = await request.body()

    # Fetch the stored webhook secret for this flow
    with SessionLocal() as session:
        record = session.query(FlowDefinitionRecord).filter(
            FlowDefinitionRecord.flow_id == flow_id,
        ).first()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown flow.",
        )

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

    # Validate flow state and enqueue
    try:
        return flow_service.trigger_webhook_verified(flow_id, tenant_id=record.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown flow.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
