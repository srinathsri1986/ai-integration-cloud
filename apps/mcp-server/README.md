# MCP Server

TypeScript MCP server exposing CFO intelligence tools backed by the local FastAPI service.

## Local development

```bash
pnpm install
pnpm --filter @netsuite-cfo/mcp-server dev
```

The MCP server expects the FastAPI backend to be reachable at `MCP_API_BASE_URL`, defaulting to `http://localhost:8000`.

## Tools

- `get_cfo_dashboard_summary`: returns mock CFO KPIs from the API.
- `get_pl_vs_budget`: returns P/L actuals vs budget.
  - Input: `{ "period": "2026-Q1", "subsidiaryId": "NA" }`
- `get_yoy_comparison`: returns YoY CFO comparison.
  - Input: `{ "currentYear": 2026, "priorYear": 2025, "subsidiaryId": "NA" }`
- `get_subsidiary_drilldown`: returns subsidiary-level operating detail.
  - Input: `{ "period": "2026-Q1", "subsidiaryId": "EMEA" }`
- `get_running_projects`: returns active project financials.
  - Input: `{ "accountManager": "Maya Rao", "subsidiaryId": "NA" }`
- `get_overdue_projects_by_account_manager`: returns overdue project aging by account manager.
  - Input: `{ "minDaysOverdue": 20 }`

All tools call approved `/api/v1/cfo/...` backend endpoints. The server never accepts arbitrary SQL, SuiteQL, or raw NetSuite access.

## Tests

```bash
pnpm --filter @netsuite-cfo/mcp-server test
```
