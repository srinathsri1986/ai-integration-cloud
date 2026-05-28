from app.connectors.netsuite.query_templates import run_approved_mock_template
from app.models.cfo import (
    OverdueProjectManager,
    OverdueProjectsByManagerResponse,
    PlVsBudgetLine,
    PlVsBudgetResponse,
    ProjectSummary,
    RunningProjectsResponse,
    SubsidiaryDrilldownLine,
    SubsidiaryDrilldownResponse,
    YoyComparisonLine,
    YoyComparisonResponse,
)


class MockNetSuiteConnector:
    source = "mock"

    def pl_vs_budget(self, period: str, subsidiary_id: str | None = None) -> PlVsBudgetResponse:
        rows = self.run_template("pl_vs_budget")
        lines = [
            PlVsBudgetLine.model_validate(row)
            for row in rows
            if row["period"] == period
            and (subsidiary_id is None or row["subsidiary_id"] == subsidiary_id)
        ]
        return PlVsBudgetResponse(
            source=self.source,
            period=period,
            subsidiary_id=subsidiary_id,
            lines=lines,
        )

    def yoy_comparison(
        self,
        current_year: int,
        prior_year: int,
        subsidiary_id: str | None = None,
    ) -> YoyComparisonResponse:
        rows = self.run_template("yoy_comparison")
        lines = [
            YoyComparisonLine.model_validate(row)
            for row in rows
            if row["current_year"] == current_year
            and row["prior_year"] == prior_year
            and (subsidiary_id is None or row["subsidiary_id"] == subsidiary_id)
        ]
        return YoyComparisonResponse(
            source=self.source,
            current_year=current_year,
            prior_year=prior_year,
            subsidiary_id=subsidiary_id,
            lines=lines,
        )

    def subsidiary_drilldown(self, period: str, subsidiary_id: str) -> SubsidiaryDrilldownResponse:
        rows = self.run_template("subsidiary_drilldown")
        lines = [
            SubsidiaryDrilldownLine.model_validate(row)
            for row in rows
            if row["period"] == period and row["subsidiary_id"] == subsidiary_id
        ]
        return SubsidiaryDrilldownResponse(
            source=self.source,
            period=period,
            subsidiary_id=subsidiary_id,
            lines=lines,
        )

    def running_projects(
        self,
        account_manager: str | None = None,
        subsidiary_id: str | None = None,
    ) -> RunningProjectsResponse:
        rows = self.run_template("running_projects")
        projects = [
            ProjectSummary.model_validate(row)
            for row in rows
            if (account_manager is None or row["account_manager"] == account_manager)
            and (subsidiary_id is None or row["subsidiary_id"] == subsidiary_id)
        ]
        return RunningProjectsResponse(
            source=self.source,
            account_manager=account_manager,
            subsidiary_id=subsidiary_id,
            projects=projects,
        )

    def overdue_projects_by_account_manager(
        self,
        min_days_overdue: int = 1,
    ) -> OverdueProjectsByManagerResponse:
        rows = self.run_template("overdue_projects_by_account_manager")
        managers = [
            OverdueProjectManager.model_validate(row)
            for row in rows
            if row["max_days_overdue"] >= min_days_overdue
        ]
        return OverdueProjectsByManagerResponse(
            source=self.source,
            min_days_overdue=min_days_overdue,
            managers=managers,
        )

    def run_template(self, template_id: str) -> list[dict[str, str | float]]:
        return run_approved_mock_template(template_id)
