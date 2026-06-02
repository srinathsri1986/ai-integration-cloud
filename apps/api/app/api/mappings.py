from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_permissions
from app.models.mapping import (
    MappingDefinition,
    MappingDefinitionUpsertRequest,
    MappingLifecycleRequest,
    MappingLifecycleResponse,
    MappingSimulationResponse,
    MappingSuggestionRequest,
    MappingSuggestionResponse,
)
from app.services.mapping_definition_service import mapping_definition_service
from app.services.mapping_suggestion_service import mapping_suggestion_service

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.get("/definitions", response_model=list[MappingDefinition])
def list_mapping_definitions(
    user=Depends(require_permissions("flow:read")),
) -> list[MappingDefinition]:
    return mapping_definition_service.list_mappings()


@router.post("/definitions", response_model=MappingDefinition)
def upsert_mapping_definition(
    request: MappingDefinitionUpsertRequest,
    user=Depends(require_permissions("flow:run")),
) -> MappingDefinition:
    try:
        return mapping_definition_service.upsert_mapping(request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mapping object.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/suggestions", response_model=MappingSuggestionResponse)
def suggest_mapping(
    request: MappingSuggestionRequest,
    user=Depends(require_permissions("flow:run")),
) -> MappingSuggestionResponse:
    try:
        return mapping_suggestion_service.suggest(request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mapping object.",
        ) from exc


@router.get("/definitions/{mapping_id}", response_model=MappingDefinition)
def get_mapping_definition(
    mapping_id: str,
    user=Depends(require_permissions("flow:read")),
) -> MappingDefinition:
    try:
        return mapping_definition_service.get_mapping(mapping_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mapping definition.",
        ) from exc


@router.post("/definitions/{mapping_id}/lifecycle", response_model=MappingLifecycleResponse)
def transition_mapping_lifecycle(
    mapping_id: str,
    request: MappingLifecycleRequest,
    user=Depends(require_permissions("flow:run")),
) -> MappingLifecycleResponse:
    try:
        return mapping_definition_service.transition_mapping(mapping_id, request.action, request.note)
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


@router.post("/definitions/{mapping_id}/simulate", response_model=MappingSimulationResponse)
def simulate_mapping_definition(
    mapping_id: str,
    user=Depends(require_permissions("flow:run")),
) -> MappingSimulationResponse:
    try:
        return mapping_definition_service.simulate_mapping(mapping_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown mapping definition.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
