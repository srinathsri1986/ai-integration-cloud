# MCP Server

TypeScript MCP server exposing CFO intelligence tools backed by the local FastAPI service.

## Local development

```bash
pnpm install
pnpm --filter @netsuite-cfo/mcp-server dev
```

## Tools

- `get_cfo_dashboard_summary`: returns mock CFO KPIs from the API.
- `run_approved_netsuite_template`: runs one named approved mock NetSuite template.

The server never accepts arbitrary SQL or SuiteQL. Callers must use approved template IDs.
