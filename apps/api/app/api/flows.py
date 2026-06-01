from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_permissions
from app.models.flows import (
    FlowDefinition,
    FlowDefinitionUpsertRequest,
    FlowId,
    FlowLifecycleRequest,
    FlowLifecycleResponse,
    FlowRunResponse,
    FlowSuggestionRequest,
    FlowSuggestionResponse,
)
from app.services.flow_suggestion_service import flow_suggestion_service
from app.services.flow_service import flow_service

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("", response_model=list[FlowDefinition])
def list_flows(user=Depends(require_permissions("flow:read"))) -> list[FlowDefinition]:
    return flow_service.list_flows()


@router.get("/runs", response_model=list[FlowRunResponse])
def list_flow_runs(
    flow_id: str | None = None,
    run_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    user=Depends(require_permissions("flow:read")),
) -> list[FlowRunResponse]:
    return flow_service.list_runs(
        flow_id=flow_id,
        status=run_status,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )


@router.post("/definitions", response_model=FlowDefinition)
def upsert_flow_definition(
    request: FlowDefinitionUpsertRequest,
    user=Depends(require_permissions("flow:run")),
) -> FlowDefinition:
    return flow_service.upsert_flow(request)


@router.post("/suggestions", response_model=FlowSuggestionResponse)
def suggest_flow_definition(
    request: FlowSuggestionRequest,
    user=Depends(require_permissions("flow:run")),
) -> FlowSuggestionResponse:
    return flow_suggestion_service.suggest(request)


@router.post("/{flow_id}/lifecycle", response_model=FlowLifecycleResponse)
def transition_flow_lifecycle(
    flow_id: FlowId,
    request: FlowLifecycleRequest,
    user=Depends(require_permissions("flow:run")),
) -> FlowLifecycleResponse:
    try:
        return flow_service.transition_flow(flow_id, request.action, request.note)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/{flow_id}", response_model=FlowDefinition)
def get_flow(flow_id: FlowId, user=Depends(require_permissions("flow:read"))) -> FlowDefinition:
    try:
        return flow_service.get_flow(flow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc


@router.post("/{flow_id}/run", response_model=FlowRunResponse)
def run_flow(flow_id: FlowId, user=Depends(require_permissions("flow:run"))) -> FlowRunResponse:
    try:
        return flow_service.run_flow(flow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc
