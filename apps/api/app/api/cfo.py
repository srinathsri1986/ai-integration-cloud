from fastapi import APIRouter, HTTPException, status

from app.connectors.netsuite.query_templates import list_approved_templates
from app.models.cfo import CfoDashboardSummary, NetSuiteTemplateResult
from app.services.cfo_service import CfoService

router = APIRouter(prefix="/cfo", tags=["cfo"])
service = CfoService()


@router.get("/dashboard-summary", response_model=CfoDashboardSummary)
def dashboard_summary() -> CfoDashboardSummary:
    return service.dashboard_summary()


@router.get("/netsuite/templates")
def approved_templates() -> list[dict[str, str]]:
    return [
        {"id": template.id, "description": template.description}
        for template in list_approved_templates()
    ]


@router.post("/netsuite/templates/{template_id}/run", response_model=NetSuiteTemplateResult)
def run_template(template_id: str) -> NetSuiteTemplateResult:
    try:
        return service.run_template(template_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown approved NetSuite query template.",
        ) from exc
