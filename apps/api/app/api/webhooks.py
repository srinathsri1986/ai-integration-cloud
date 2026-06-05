"""
Inbound webhook receiver.

POST /api/v1/webhooks/{flow_id}/{secret}
  — validates the per-flow secret
  — verifies the flow is published and has trigger_type="webhook"
  — enqueues execute_flow_task and returns 202
"""
from fastapi import APIRouter, HTTPException, status

from app.models.flows import FlowRunResponse
from app.services.flow_service import flow_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/{flow_id}/{secret}",
    response_model=FlowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inbound webhook trigger",
    description=(
        "Trigger a published webhook-type integration by providing its flow ID and "
        "the per-flow secret generated at creation time. Returns 202 immediately."
    ),
)
def receive_webhook(flow_id: str, secret: str) -> FlowRunResponse:
    try:
        return flow_service.trigger_webhook(flow_id, secret)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown flow or invalid webhook secret.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
