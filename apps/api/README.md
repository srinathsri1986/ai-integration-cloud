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

## AI-assisted mapping suggestions

Field mapping suggestions can be requested from approved object metadata:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/suggestions" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Map NetSuite project customer, budget, due date, and owner fields into Salesforce opportunity fields.","sourceObjectId":"netsuite-project","targetObjectId":"salesforce-opportunity"}'
```

The service can use mock, Ollama, or OpenAI through the shared LLM provider abstraction. The model receives only the selected object metadata, field descriptions, allowed transforms, and the mapping goal. The API validates every suggestion against known source fields, known target fields, and approved transforms before returning it to the UI. Invalid provider output falls back to deterministic templates.

Mapping suggestions are advisory only. They do not save, publish, execute, generate SQL/SuiteQL, access credentials, or access raw systems.

## Mapping definitions

Reviewed mappings can be saved as governed draft definitions:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/definitions" \
  -H "Content-Type: application/json" \
  -d '{"mappingId":"netsuite-project-to-salesforce-opportunity","name":"NetSuite Project to Salesforce Opportunity","description":"Maps approved project fields into Salesforce opportunity fields.","sourceObjectId":"netsuite-project","targetObjectId":"salesforce-opportunity","status":"draft","mappings":[{"id":"project-to-name","sourceField":"project_id","targetField":"Name","transform":"rename"},{"id":"customer-to-account","sourceField":"customer_name","targetField":"AccountName","transform":"direct"},{"id":"budget-to-amount","sourceField":"budget_amount","targetField":"Amount","transform":"direct"},{"id":"date-to-close","sourceField":"due_date","targetField":"CloseDate","transform":"format_date"}]}'
```

Lifecycle actions are explicit and human controlled:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle" \
  -H "Content-Type: application/json" \
  -d '{"action":"submit_for_approval"}'
```

The API validates known source and target fields, required target fields, duplicate targets, allowed transforms, and blocked raw-query/secret language. Mapping saves and lifecycle transitions are audited as `MAPPING_DEFINITION`.

## Mapping simulation

Saved mapping definitions can be simulated with approved sample payloads:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/simulate"
```

Simulation is preview-only. It applies approved transforms to catalog sample values and returns source payload, target payload, transform names, warnings, and simulation timestamp. It does not execute arbitrary code, call external systems, or access secrets. Simulation actions are audited as `MAPPING_SIMULATION`.

## Flow-to-mapping linkage

Flow definitions can optionally reference a published mapping definition:

```bash
curl -X POST "http://localhost:8000/api/v1/flows/definitions" \
  -H "Content-Type: application/json" \
  -d '{"flowId":"mapped-runtime-preview","name":"Mapped runtime preview","description":"Preview a mapped payload through approved actions.","sourceConnector":"netsuite","targetModule":"salesforce_opportunity","status":"draft","triggerType":"manual","mappingDefinitionId":"netsuite-project-to-salesforce-opportunity","steps":[{"id":"summary","name":"Load summary","description":"Load approved CFO summary data.","approvedTool":"cfo.dashboard_summary"}]}'
```

Referenced mappings must exist and be `published`; draft or missing mappings are rejected. Custom published flows with an attached published mapping run a safe runtime preview and return the mapping simulation result in the flow run payload. Custom flows without a mapping remain fail-closed.

## Flow run details and execution timeline

Flow run records include an execution timeline:

```bash
curl "http://localhost:8000/api/v1/flows/runs"
curl "http://localhost:8000/api/v1/flows/runs/{request_id}"
```

Each timeline step includes status, timestamps, latency, approved tool, attached mapping definition ID, and warnings. Built-in flows show approved CFO service steps. Custom mapped flows include both approved action steps and a mapping simulation step.

## Generic REST connector foundation

The API exposes a governed mock REST connector for system-agnostic integration design:

```bash
curl "http://localhost:8000/api/v1/connectors/rest-api"
curl "http://localhost:8000/api/v1/connectors/rest-api/objects"
curl -X POST "http://localhost:8000/api/v1/connectors/rest-api/discover-schema" \
  -H "Content-Type: application/json" \
  -d '{"objectLabel":"Customer Event","samplePayload":{"externalId":"CUST-100","displayName":"Acme Manufacturing","amount":2500.75,"invoiceDate":"2026-06-02","isActive":true}}'
curl -X POST "http://localhost:8000/api/v1/connectors/rest-api/test"
curl -X PUT "http://localhost:8000/api/v1/connectors/rest-api/config" \
  -H "Content-Type: application/json" \
  -d '{"displayName":"Customer REST Gateway","baseUrlPlaceholder":"https://customer-api.example.com","authMode":"placeholder","mockMode":true}'
```

The connector returns approved object metadata for `customer`, `invoice`, and `opportunity`. The mock test action writes a connector audit event but does not perform an outbound HTTP call. Config updates accept placeholder metadata only and reject non-placeholder auth modes. Secret-like fields such as API keys, bearer tokens, passwords, and secrets are not part of the response model.

Schema discovery is design-time only. It infers top-level scalar fields from pasted sample JSON, skips secret-like field names, warns on nested values, and returns `executable:false`. Discovery does not save connector credentials, execute HTTP requests, or create runtime mappings automatically.

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
