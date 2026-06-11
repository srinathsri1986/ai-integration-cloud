from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import require_permissions, require_tenant
from app.models.flows import (
    FlowDefinition,
    FlowDefinitionUpsertRequest,
    FlowId,
    FlowLifecycleRequest,
    FlowLifecycleResponse,
    FlowRunResponse,
    FlowSuggestionRequest,
    FlowSuggestionResponse,
    PaginatedFlowRuns,
    PaginatedFlows,
)
from app.services.flow_suggestion_service import LiveAIRequiredError, flow_suggestion_service
from app.services.flow_service import flow_service

router = APIRouter(prefix="/flows", tags=["flows"])


class LinkMappingRequest(BaseModel):
    mapping_definition_id: str | None = Field(
        default=None,
        alias="mappingDefinitionId",
        max_length=96,
        description="ID of a published MappingDefinition to attach, or null to detach.",
    )

    model_config = {"populate_by_name": True}


class PatchStepRequest(BaseModel):
    """Narrow patch for a single flow step — only updates the fields supplied.

    At minimum, callers must provide `approvedTool` (the connector tool ID).
    Additional per-step fields may be added here as the engine grows.
    """

    approved_tool: str = Field(
        alias="approvedTool",
        min_length=1,
        max_length=128,
        description="Connector tool ID for this step, e.g. 'list_vendors'.",
    )
    name: str | None = Field(
        default=None,
        max_length=128,
        description="Human-readable step label (optional, defaults to current value).",
    )

    model_config = {"populate_by_name": True}


@router.get("", response_model=PaginatedFlows)
def list_flows(
    limit: int = 50,
    offset: int = 0,
    user=Depends(require_permissions("flow:read")),
) -> PaginatedFlows:
    return flow_service.list_flows(
        tenant_id=user.tenant_id,
        limit=limit,
        offset=offset,
    )


@router.get("/runs", response_model=PaginatedFlowRuns)
def list_flow_runs(
    flow_id: str | None = None,
    run_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(require_permissions("flow:read")),
) -> PaginatedFlowRuns:
    return flow_service.list_runs(
        tenant_id=user.tenant_id,
        flow_id=flow_id,
        status=run_status,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{request_id}", response_model=FlowRunResponse)
def get_flow_run(
    request_id: str,
    user=Depends(require_permissions("flow:read")),
) -> FlowRunResponse:
    try:
        return flow_service.get_run(request_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown flow run.",
        ) from exc


@router.post("/definitions", response_model=FlowDefinition)
def upsert_flow_definition(
    request: FlowDefinitionUpsertRequest,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowDefinition:
    try:
        return flow_service.upsert_flow(request, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mapping definition.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/suggestions", response_model=FlowSuggestionResponse)
def suggest_flow_definition(
    request: FlowSuggestionRequest,
    user=Depends(require_permissions("flow:run")),
) -> FlowSuggestionResponse:
    try:
        return flow_suggestion_service.suggest(request)
    except LiveAIRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/{flow_id}/lifecycle", response_model=FlowLifecycleResponse)
def transition_flow_lifecycle(
    flow_id: FlowId,
    request: FlowLifecycleRequest,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowLifecycleResponse:
    try:
        return flow_service.transition_flow(flow_id, request.action, request.note, tenant_id=user.tenant_id)
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


@router.delete("/{flow_id}", response_model=dict[str, str])
def delete_flow_definition(
    flow_id: FlowId,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> dict[str, str]:
    try:
        return flow_service.delete_flow(flow_id, tenant_id=user.tenant_id)
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


@router.get("/{flow_id}/runs", response_model=PaginatedFlowRuns)
def list_flow_runs_for_flow(
    flow_id: FlowId,
    limit: int = 10,
    offset: int = 0,
    user=Depends(require_permissions("flow:read")),
) -> PaginatedFlowRuns:
    """Paginated run history for a specific flow. Convenience alias for GET /runs?flow_id=X."""
    try:
        # Verify flow exists and is visible
        flow_service.get_flow(flow_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown flow.",
        ) from exc
    return flow_service.list_runs(
        tenant_id=user.tenant_id,
        flow_id=flow_id,
        limit=limit,
        offset=offset,
    )


@router.patch("/{flow_id}/mapping", response_model=FlowDefinition)
def link_mapping(
    flow_id: FlowId,
    body: LinkMappingRequest,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowDefinition:
    """Attach or detach a published MappingDefinition on any flow, regardless of lifecycle status.

    The regular upsert endpoint only accepts draft-status flows, making it
    impossible to add a mapping to an already-published integration. This
    endpoint is intentionally narrow — it only touches `mapping_definition_id`
    and nothing else, so it cannot accidentally regress status or steps.
    """
    try:
        return flow_service.link_mapping(
            flow_id,
            mapping_definition_id=body.mapping_definition_id,
            tenant_id=user.tenant_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{flow_id}/steps/{step_id}", response_model=FlowDefinition)
def patch_flow_step(
    flow_id: FlowId,
    step_id: str,
    body: PatchStepRequest,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowDefinition:
    """Update a single step inside any flow, regardless of lifecycle status.

    Intentionally narrow: only `approvedTool` (and optionally `name`) are
    touched. Everything else — flow status, other steps, mapping linkage —
    is left unchanged. Audited so the change is traceable.
    """
    try:
        return flow_service.patch_step(
            flow_id,
            step_id=step_id,
            approved_tool=body.approved_tool,
            name=body.name,
            tenant_id=user.tenant_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{flow_id}", response_model=FlowDefinition)
def get_flow(flow_id: FlowId, user=Depends(require_permissions("flow:read"))) -> FlowDefinition:
    try:
        return flow_service.get_flow(flow_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc


@router.post("/{flow_id}/run", response_model=FlowRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_flow(
    flow_id: FlowId,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowRunResponse:
    try:
        return flow_service.enqueue_flow_run(flow_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mock integration flow.",
        ) from exc


@router.post("/runs/{request_id}/replay", response_model=FlowRunResponse, status_code=status.HTTP_202_ACCEPTED)
def replay_flow_run(
    request_id: str,
    user=Depends(require_permissions("flow:run")),
    _tenant=Depends(require_tenant),
) -> FlowRunResponse:
    """Re-trigger the flow that produced the given run. Useful for retrying failed runs
    or re-executing a flow with the same configuration without navigating to the flow page."""
    try:
        original = flow_service.get_run(request_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original run not found.",
        ) from exc
    try:
        return flow_service.enqueue_flow_run(original.flow_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow definition not found — it may have been deleted.",
        ) from exc
