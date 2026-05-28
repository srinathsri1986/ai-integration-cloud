from dataclasses import dataclass

from app.connectors.netsuite.mock_data import MOCK_TEMPLATE_ROWS


@dataclass(frozen=True)
class NetSuiteQueryTemplate:
    id: str
    description: str
    mock_rows_key: str


APPROVED_QUERY_TEMPLATES: dict[str, NetSuiteQueryTemplate] = {
    "cash_position_summary": NetSuiteQueryTemplate(
        id="cash_position_summary",
        description="Summarized cash balances by approved cash account group.",
        mock_rows_key="cash_position_summary",
    ),
    "ar_aging_summary": NetSuiteQueryTemplate(
        id="ar_aging_summary",
        description="Accounts receivable aging by finance-approved bucket.",
        mock_rows_key="ar_aging_summary",
    ),
    "monthly_revenue_trend": NetSuiteQueryTemplate(
        id="monthly_revenue_trend",
        description="Monthly recognized revenue trend for CFO dashboarding.",
        mock_rows_key="monthly_revenue_trend",
    ),
}


def list_approved_templates() -> list[NetSuiteQueryTemplate]:
    return list(APPROVED_QUERY_TEMPLATES.values())


def run_approved_mock_template(template_id: str) -> list[dict[str, str | float]]:
    template = APPROVED_QUERY_TEMPLATES.get(template_id)
    if template is None:
        raise KeyError(f"Unsupported NetSuite query template: {template_id}")

    return MOCK_TEMPLATE_ROWS[template.mock_rows_key]
