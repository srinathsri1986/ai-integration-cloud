from dataclasses import dataclass

from app.connectors.netsuite.query_templates import APPROVED_QUERY_TEMPLATES
from app.models.cfo import (
    OverdueProjectsByManagerResponse,
    PlVsBudgetResponse,
    RunningProjectsResponse,
    SubsidiaryDrilldownResponse,
    YoyComparisonResponse,
)


class NetSuiteSandboxConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class NetSuiteSandboxConnectionConfig:
    account_id: str
    base_url: str | None
    consumer_key: str | None
    consumer_secret: str | None
    token_id: str | None
    token_secret: str | None
    timeout_seconds: int = 15

    @property
    def base_url_configured(self) -> bool:
        return bool(self.base_url and self.base_url.startswith("https://"))

    @property
    def credentials_configured(self) -> bool:
        return all(
            [
                self.consumer_key,
                self.consumer_secret,
                self.token_id,
                self.token_secret,
            ]
        )


class NetSuiteSandboxConnector:
    source = "sandbox"

    def __init__(self, config: NetSuiteSandboxConnectionConfig) -> None:
        self.config = config

    def test_connection(self) -> tuple[bool, str]:
        if not self.config.base_url_configured:
            return False, "NetSuite sandbox base URL is not configured."

        if not self.config.credentials_configured:
            return False, "NetSuite sandbox credentials are not fully configured."

        return True, "NetSuite sandbox configuration is ready for approved API calls."

    def run_template(self, template_id: str) -> list[dict[str, str | float]]:
        if template_id not in APPROVED_QUERY_TEMPLATES:
            raise KeyError(f"Unsupported NetSuite query template: {template_id}")

        raise NetSuiteSandboxConnectorError(
            "Sandbox template execution is not enabled yet. V1.3 only validates secure "
            "sandbox configuration and preserves approved-template dispatch."
        )

    def pl_vs_budget(self, period: str, subsidiary_id: str | None = None) -> PlVsBudgetResponse:
        self.run_template("pl_vs_budget")

    def yoy_comparison(
        self,
        current_year: int,
        prior_year: int,
        subsidiary_id: str | None = None,
    ) -> YoyComparisonResponse:
        self.run_template("yoy_comparison")

    def subsidiary_drilldown(self, period: str, subsidiary_id: str) -> SubsidiaryDrilldownResponse:
        self.run_template("subsidiary_drilldown")

    def running_projects(
        self,
        account_manager: str | None = None,
        subsidiary_id: str | None = None,
    ) -> RunningProjectsResponse:
        self.run_template("running_projects")

    def overdue_projects_by_account_manager(
        self,
        min_days_overdue: int = 1,
    ) -> OverdueProjectsByManagerResponse:
        self.run_template("overdue_projects_by_account_manager")
