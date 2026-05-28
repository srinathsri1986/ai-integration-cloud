from typing import Protocol

from app.models.cfo import (
    OverdueProjectsByManagerResponse,
    PlVsBudgetResponse,
    RunningProjectsResponse,
    SubsidiaryDrilldownResponse,
    YoyComparisonResponse,
)


class NetSuiteConnector(Protocol):
    def pl_vs_budget(self, period: str, subsidiary_id: str | None = None) -> PlVsBudgetResponse:
        """Return finance-approved P/L vs budget data."""

    def yoy_comparison(
        self,
        current_year: int,
        prior_year: int,
        subsidiary_id: str | None = None,
    ) -> YoyComparisonResponse:
        """Return finance-approved year-over-year comparison data."""

    def subsidiary_drilldown(self, period: str, subsidiary_id: str) -> SubsidiaryDrilldownResponse:
        """Return finance-approved subsidiary drilldown data."""

    def running_projects(
        self,
        account_manager: str | None = None,
        subsidiary_id: str | None = None,
    ) -> RunningProjectsResponse:
        """Return finance-approved running project data."""

    def overdue_projects_by_account_manager(
        self,
        min_days_overdue: int = 1,
    ) -> OverdueProjectsByManagerResponse:
        """Return finance-approved overdue project aging by account manager."""

    def run_template(self, template_id: str) -> list[dict[str, str | float]]:
        """Run an approved named template by ID."""
