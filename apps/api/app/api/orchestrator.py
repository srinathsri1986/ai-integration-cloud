from fastapi import APIRouter, Depends

from app.core.auth import require_permissions
from app.models.orchestrator import OrchestratorQueryRequest, OrchestratorQueryResponse
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
service = OrchestratorService()


@router.post("/query", response_model=OrchestratorQueryResponse)
def query(
    request: OrchestratorQueryRequest,
    user=Depends(require_permissions("orchestrator:query")),
) -> OrchestratorQueryResponse:
    return service.query(request)
