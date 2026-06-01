# API

FastAPI service for CFO intelligence endpoints. The first connector mode is `mock`, using named NetSuite query templates only.

## Local development

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## CFO endpoints

The API includes mock v0.2 CFO reads:

```bash
curl "http://localhost:8000/api/v1/cfo/pl-vs-budget?period=2026-Q1&subsidiary_id=NA"
curl "http://localhost:8000/api/v1/cfo/yoy-comparison?current_year=2026&prior_year=2025"
curl "http://localhost:8000/api/v1/cfo/subsidiary-drilldown?period=2026-Q1&subsidiary_id=EMEA"
curl "http://localhost:8000/api/v1/cfo/running-projects?account_manager=Maya%20Rao"
curl "http://localhost:8000/api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=20"
```

## Safe CFO narratives

The orchestrator adds an executive narrative to `/api/v1/orchestrator/query` responses. Narrative generation is handled by `app/services/narrative_service.py` and uses only approved structured CFO service output that the orchestrator has already retrieved.

The model prompt receives compact summarized JSON, tool names, and source policy text only. It never receives credentials, raw transactions, arbitrary SQL, SuiteQL, raw NetSuite queries, or raw NetSuite access details. If the configured provider fails or returns invalid output, the service falls back to deterministic template text.

## NetSuite sandbox mode

The API can be started with `NETSUITE_MODE=sandbox` to validate local sandbox connector readiness:

```bash
NETSUITE_MODE=sandbox
NETSUITE_ACCOUNT_ID=placeholder-account
NETSUITE_BASE_URL=https://placeholder-account.suitetalk.api.netsuite.com
NETSUITE_CONSUMER_KEY=
NETSUITE_CONSUMER_SECRET=
NETSUITE_TOKEN_ID=
NETSUITE_TOKEN_SECRET=
NETSUITE_TIMEOUT_SECONDS=15
```

V1.3 validates HTTPS base URL and token-based auth readiness only. It does not expose arbitrary SuiteQL, does not execute raw NetSuite queries, and does not return secret values through API responses or audit logs. Real CFO sandbox template execution must be added one approved service method at a time.

## Runtime config validation and redaction

Startup validation runs when the FastAPI app starts. Invalid runtime modes fail closed, while incomplete optional provider settings are reported as safe warnings. Logged configuration posture uses booleans only and does not include raw secret values.

Audit entries are redacted before storage. Inline secret-like patterns such as `password=...`, `token:...`, API keys, and bearer tokens are masked if they accidentally appear in request text.

Use `.env.local` for local-only real values. Do not commit `.env`, `.env.local`, or any file containing real NetSuite/OpenAI secrets.

## Persistent audit and flow history

The API initializes local MVP persistence tables on startup:

- `audit_logs`
- `flow_runs`

Audit writes are redacted before persistence. Audit reads support filters and pagination:

```bash
curl "http://localhost:8000/api/v1/audit/logs?intent=PL_VS_BUDGET&provider=ollama&success=true&limit=50&offset=0"
curl "http://localhost:8000/api/v1/audit/summary"
```

Flow runs are appended after successful mock flow execution:

```bash
curl "http://localhost:8000/api/v1/flows/runs"
curl "http://localhost:8000/api/v1/flows/runs?flow_id=netsuite-project-risk-refresh"
```

PostgreSQL uses JSONB for flexible metadata. Tests use SQLite through `tests/conftest.py` to keep local test runs isolated from Docker.

## Placeholder auth and RBAC

Local placeholder JWT auth is available for MVP role testing:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","role":"Integration Admin"}'
```

Protected endpoint groups use role permissions:

- `connector:admin` for connector config and test actions.
- `audit:read` for audit logs and summaries.
- `flow:run` for flow execution.
- `flow:read` for flow catalog/history.
- `cfo:read` and `orchestrator:query` for finance workflows.

This is placeholder local auth only. Production SSO/OIDC/SAML and tenant-aware policy enforcement are future work.

## Flow Designer Lite

Flow definitions can be saved through controlled forms or API calls:

```bash
curl -X POST "http://localhost:8000/api/v1/flows/definitions" \
  -H "Content-Type: application/json" \
  -d '{"flowId":"custom-cfo-refresh","name":"Custom CFO refresh","description":"Refresh CFO dashboard data with approved CFO actions.","sourceConnector":"netsuite","targetModule":"cfo_dashboard","status":"draft","triggerType":"manual","steps":[{"id":"summary","name":"Load summary","description":"Load approved CFO summary data.","approvedTool":"cfo.dashboard_summary"}]}'
```

Definitions are persisted in `flow_definitions`, audited as `FLOW_DEFINITION`, and validated against approved tools. Raw SQL, SuiteQL, and arbitrary code execution language are rejected. Custom flow execution is intentionally fail-closed until runtime mappings are implemented.

The web app also includes a visual flow canvas shell that saves through this same governed endpoint. It is a visual builder layer only; it does not introduce arbitrary execution.

## AI-assisted flow suggestions

Flow drafts can be suggested from natural-language prompts:

```bash
curl -X POST "http://localhost:8000/api/v1/flows/suggestions" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a monthly CFO dashboard refresh flow from NetSuite that compares P/L vs budget and highlights overdue projects."}'
```

Suggestions use the configured mock, Ollama, or OpenAI provider only to produce structured draft metadata. The API validates the draft against approved connectors and approved tools, falls back to deterministic templates when model output is invalid, and never publishes or executes the draft automatically.

## Flow approval and publishing

Flow definitions must move through the human approval lifecycle before execution:

```bash
curl -X POST "http://localhost:8000/api/v1/flows/custom-cfo-refresh/lifecycle" \
  -H "Content-Type: application/json" \
  -d '{"action":"submit_for_approval"}'

curl -X POST "http://localhost:8000/api/v1/flows/custom-cfo-refresh/lifecycle" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve"}'

curl -X POST "http://localhost:8000/api/v1/flows/custom-cfo-refresh/lifecycle" \
  -H "Content-Type: application/json" \
  -d '{"action":"publish"}'
```

Only `published` flows can be run. Built-in mapped flows can execute after publication. Custom flows remain fail-closed even after publication until explicit runtime mappings are implemented.

## Safety model

- No real NetSuite credentials are used.
- No arbitrary SQL or SuiteQL endpoint is exposed.
- Connector access goes through approved template IDs in `app/connectors/netsuite/query_templates.py`.
- Application code depends on `app/connectors/netsuite/interface.py` instead of raw query strings.
