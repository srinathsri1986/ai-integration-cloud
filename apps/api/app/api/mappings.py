from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_permissions
from app.models.mapping import MappingSuggestionRequest, MappingSuggestionResponse
from app.services.mapping_suggestion_service import mapping_suggestion_service

router = APIRouter(prefix="/mappings", tags=["mappings"])


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
