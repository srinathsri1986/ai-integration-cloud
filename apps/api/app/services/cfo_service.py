from app.connectors.netsuite.mock_data import MOCK_CFO_SUMMARY
from app.connectors.netsuite.query_templates import run_approved_mock_template
from app.models.cfo import CfoDashboardSummary, NetSuiteTemplateResult


class CfoService:
    def dashboard_summary(self) -> CfoDashboardSummary:
        return CfoDashboardSummary.model_validate(MOCK_CFO_SUMMARY)

    def run_template(self, template_id: str) -> NetSuiteTemplateResult:
        rows = run_approved_mock_template(template_id)
        return NetSuiteTemplateResult(template_id=template_id, source="mock", rows=rows)
