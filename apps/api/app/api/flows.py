from fastapi import APIRouter, HTTPException, status

from app.models.flows import FlowDefinition, FlowId, FlowRunResponse
from app.services.flow_service import flow_service

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("", response_model=list[FlowDefinition])
def list_flows() -> list[FlowDefinition]:
    return flow_service.list_flows()


@router.get("/{flow_id}", response_model=FlowDefinition)
def get_flow(flow_id: FlowId) -> FlowDefinition:
    try:
        return flow_service.get_flow(flow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc


@router.post("/{flow_id}/run", response_model=FlowRunResponse)
def run_flow(flow_id: FlowId) -> FlowRunResponse:
    try:
        return flow_service.run_flow(flow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc
