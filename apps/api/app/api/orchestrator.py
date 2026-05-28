from fastapi import APIRouter

from app.models.orchestrator import OrchestratorQueryRequest, OrchestratorQueryResponse
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
service = OrchestratorService()


@router.post("/query", response_model=OrchestratorQueryResponse)
def query(request: OrchestratorQueryRequest) -> OrchestratorQueryResponse:
    return service.query(request)
