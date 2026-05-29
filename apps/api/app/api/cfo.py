from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_permissions
from app.connectors.netsuite.query_templates import list_approved_templates
from app.models.cfo import (
    CfoDashboardSummary,
    NetSuiteTemplateResult,
    OverdueProjectsByManagerResponse,
    OverdueProjectsQuery,
    PeriodQuery,
    PlVsBudgetResponse,
    RunningProjectsQuery,
    RunningProjectsResponse,
    SubsidiaryDrilldownQuery,
    SubsidiaryDrilldownResponse,
    YoyComparisonQuery,
    YoyComparisonResponse,
)
from app.services.cfo_service import CfoService

router = APIRouter(prefix="/cfo", tags=["cfo"])
service = CfoService()


@router.get("/dashboard-summary", response_model=CfoDashboardSummary)
def dashboard_summary(user=Depends(require_permissions("cfo:read"))) -> CfoDashboardSummary:
    return service.dashboard_summary()


@router.get("/pl-vs-budget", response_model=PlVsBudgetResponse)
def pl_vs_budget(
    query: PeriodQuery = Depends(),
    user=Depends(require_permissions("cfo:read")),
) -> PlVsBudgetResponse:
    return service.pl_vs_budget(period=query.period, subsidiary_id=query.subsidiary_id)


@router.get("/yoy-comparison", response_model=YoyComparisonResponse)
def yoy_comparison(
    query: YoyComparisonQuery = Depends(),
    user=Depends(require_permissions("cfo:read")),
) -> YoyComparisonResponse:
    if query.prior_year >= query.current_year:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="prior_year must be earlier than current_year",
        )

    return service.yoy_comparison(
        current_year=query.current_year,
        prior_year=query.prior_year,
        subsidiary_id=query.subsidiary_id,
    )


@router.get("/subsidiary-drilldown", response_model=SubsidiaryDrilldownResponse)
def subsidiary_drilldown(
    query: SubsidiaryDrilldownQuery = Depends(),
    user=Depends(require_permissions("cfo:read")),
) -> SubsidiaryDrilldownResponse:
    return service.subsidiary_drilldown(
        period=query.period,
        subsidiary_id=query.subsidiary_id,
    )


@router.get("/running-projects", response_model=RunningProjectsResponse)
def running_projects(
    query: RunningProjectsQuery = Depends(),
    user=Depends(require_permissions("cfo:read")),
) -> RunningProjectsResponse:
    return service.running_projects(
        account_manager=query.account_manager,
        subsidiary_id=query.subsidiary_id,
    )


@router.get("/overdue-projects/by-account-manager", response_model=OverdueProjectsByManagerResponse)
def overdue_projects_by_account_manager(
    query: OverdueProjectsQuery = Depends(),
    user=Depends(require_permissions("cfo:read")),
) -> OverdueProjectsByManagerResponse:
    return service.overdue_projects_by_account_manager(
        min_days_overdue=query.min_days_overdue,
    )


@router.get("/netsuite/templates")
def approved_templates(user=Depends(require_permissions("connector:admin"))) -> list[dict[str, str]]:
    return [
        {"id": template.id, "description": template.description}
        for template in list_approved_templates()
    ]


@router.post("/netsuite/templates/{template_id}/run", response_model=NetSuiteTemplateResult)
def run_template(
    template_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> NetSuiteTemplateResult:
    try:
        return service.run_template(template_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown approved NetSuite query template.",
        ) from exc
