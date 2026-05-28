from app.connectors.netsuite.mock_data import MOCK_CFO_SUMMARY
from app.connectors.netsuite.mock_connector import MockNetSuiteConnector
from app.models.cfo import (
    CfoDashboardSummary,
    NetSuiteTemplateResult,
    OverdueProjectsByManagerResponse,
    PlVsBudgetResponse,
    RunningProjectsResponse,
    SubsidiaryDrilldownResponse,
    YoyComparisonResponse,
)


class CfoService:
    def __init__(self, connector: MockNetSuiteConnector | None = None) -> None:
        self.connector = connector or MockNetSuiteConnector()

    def dashboard_summary(self) -> CfoDashboardSummary:
        return CfoDashboardSummary.model_validate(MOCK_CFO_SUMMARY)

    def run_template(self, template_id: str) -> NetSuiteTemplateResult:
        rows = self.connector.run_template(template_id)
        return NetSuiteTemplateResult(template_id=template_id, source="mock", rows=rows)

    def pl_vs_budget(self, period: str, subsidiary_id: str | None = None) -> PlVsBudgetResponse:
        return self.connector.pl_vs_budget(period=period, subsidiary_id=subsidiary_id)

    def yoy_comparison(
        self,
        current_year: int,
        prior_year: int,
        subsidiary_id: str | None = None,
    ) -> YoyComparisonResponse:
        return self.connector.yoy_comparison(
            current_year=current_year,
            prior_year=prior_year,
            subsidiary_id=subsidiary_id,
        )

    def subsidiary_drilldown(
        self,
        period: str,
        subsidiary_id: str,
    ) -> SubsidiaryDrilldownResponse:
        return self.connector.subsidiary_drilldown(period=period, subsidiary_id=subsidiary_id)

    def running_projects(
        self,
        account_manager: str | None = None,
        subsidiary_id: str | None = None,
    ) -> RunningProjectsResponse:
        return self.connector.running_projects(
            account_manager=account_manager,
            subsidiary_id=subsidiary_id,
        )

    def overdue_projects_by_account_manager(
        self,
        min_days_overdue: int = 1,
    ) -> OverdueProjectsByManagerResponse:
        return self.connector.overdue_projects_by_account_manager(
            min_days_overdue=min_days_overdue,
        )
