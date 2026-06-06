import pytest

from app.connectors.netsuite.mock_connector import MockNetSuiteConnector
from app.connectors.netsuite.query_templates import run_approved_mock_template
from app.connectors.netsuite.live_connector_stub import (
    NetSuiteSandboxConnectionConfig,
    NetSuiteSandboxConnector,
    NetSuiteSandboxConnectorError,
)


def test_mock_connector_returns_pl_vs_budget_for_approved_template() -> None:
    connector = MockNetSuiteConnector()

    response = connector.pl_vs_budget(period="2026-Q1", subsidiary_id="NA")

    assert response.source == "mock"
    assert response.period == "2026-Q1"
    assert response.subsidiary_id == "NA"
    assert {line.line for line in response.lines} == {"Revenue", "Cost of revenue"}


def test_mock_connector_filters_overdue_projects_by_days() -> None:
    connector = MockNetSuiteConnector()

    response = connector.overdue_projects_by_account_manager(min_days_overdue=30)

    assert response.source == "mock"
    assert [manager.account_manager for manager in response.managers] == ["Maya Rao"]


def test_unknown_or_sql_like_template_is_rejected() -> None:
    with pytest.raises(KeyError):
        run_approved_mock_template("select * from transaction")


def test_sandbox_connector_reports_configuration_readiness() -> None:
    connector = NetSuiteSandboxConnector(
        NetSuiteSandboxConnectionConfig(
            account_id="SANDBOX-123",
            base_url="https://sandbox.suitetalk.api.netsuite.com",
            consumer_key="consumer-key",
            consumer_secret="consumer-secret",
            token_id="token-id",
            token_secret="token-secret",
        )
    )

    success, message = connector.test_connection()

    assert success is True
    assert "ready" in message


def test_sandbox_connector_rejects_unknown_template_before_execution() -> None:
    connector = NetSuiteSandboxConnector(
        NetSuiteSandboxConnectionConfig(
            account_id="SANDBOX-123",
            base_url="https://sandbox.suitetalk.api.netsuite.com",
            consumer_key="consumer-key",
            consumer_secret="consumer-secret",
            token_id="token-id",
            token_secret="token-secret",
        )
    )

    with pytest.raises(KeyError):
        connector.run_template("select * from transaction")


def test_sandbox_connector_blocks_template_execution_until_mapped() -> None:
    connector = NetSuiteSandboxConnector(
        NetSuiteSandboxConnectionConfig(
            account_id="SANDBOX-123",
            base_url="https://sandbox.suitetalk.api.netsuite.com",
            consumer_key="consumer-key",
            consumer_secret="consumer-secret",
            token_id="token-id",
            token_secret="token-secret",
        )
    )

    with pytest.raises(NetSuiteSandboxConnectorError):
        connector.run_template("pl_vs_budget")
