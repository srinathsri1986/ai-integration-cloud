"""POST /api/v1/ai/ask — universal Ask AI endpoint.

Powers the 'Ask AI' button present in every screen of the integration studio.
Accepts a natural language question, detects intent, and routes to the
appropriate governed sub-service (flow suggestion, mapping, error diagnosis).

All generated artifacts are drafts — none are executed or published automatically.
Human approval is required before any production action.
"""
from fastapi import APIRouter, Depends

from app.core.auth import require_permissions
from app.models.ai import AskAIRequest, AskAIResponse
from app.services.ask_ai_service import ask_ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskAIResponse)
def ask_ai(
    request: AskAIRequest,
    user=Depends(require_permissions("flow:read")),
) -> AskAIResponse:
    """Natural language question → intent detection → governed AI response.

    Intents:
    - CREATE_FLOW: generates a draft workflow from NL description
    - SUGGEST_MAPPING: navigates to the field mapping studio
    - EXPLAIN_ERROR: navigates to the AI Error Debugger
    - GENERAL: returns a platform knowledge answer

    All responses include an action object telling the frontend what to render next.
    """
    return ask_ai_service.ask(request)
