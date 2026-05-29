# NetSuite CFO Intelligence Orchestrator

Production-grade MVP scaffold for an AI-native integration platform focused first on NetSuite CFO analytics.

This repository is mock-first. It does not contain real NetSuite credentials, does not expose arbitrary SQL or SuiteQL, and routes NetSuite-style reads through named approved query templates.

## Modules

- `apps/web`: Next.js frontend with TypeScript, Tailwind, and shadcn-style local UI primitives.
- `apps/api`: FastAPI backend with mock CFO analytics and approved NetSuite query templates.
- `apps/mcp-server`: TypeScript MCP server exposing CFO tools backed by the API.
- `packages/shared`: Shared TypeScript schemas and types.
- `infra/docker-compose.yml`: Local PostgreSQL, Redis, API, web, and MCP server wiring.

## Local setup

Copy placeholder environment values:

```bash
cp .env.example .env
```

Run the local stack:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

Open:

- Web app: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

The MCP server is included behind the `mcp` Compose profile because stdio MCP servers are usually launched by a host client:

```bash
docker compose --env-file .env -f infra/docker-compose.yml --profile mcp up --build mcp-server
```

## Development

Install TypeScript workspace dependencies:

```bash
pnpm install
```

Run the web app:

```bash
pnpm dev:web
```

Run the MCP server:

```bash
pnpm dev:mcp
```

Run API locally:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## CFO API v0.2

The backend exposes mock NetSuite CFO APIs through approved named templates only:

- `GET /api/v1/cfo/pl-vs-budget?period=2026-Q1&subsidiary_id=NA`
- `GET /api/v1/cfo/yoy-comparison?current_year=2026&prior_year=2025`
- `GET /api/v1/cfo/subsidiary-drilldown?period=2026-Q1&subsidiary_id=EMEA`
- `GET /api/v1/cfo/running-projects?account_manager=Maya%20Rao`
- `GET /api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=20`

All data is mock data. The API validates query parameters and never accepts raw SQL or SuiteQL.

## CFO Dashboard UI v0.3

The web dashboard at `http://localhost:3000` reads the CFO API and shows:

- Executive KPI summary
- P/L vs budget
- YoY comparison
- Subsidiary drilldown
- Running projects
- Overdue projects by account manager

When the API is unavailable, the dashboard stays usable with safe mock fallback data and labels affected sections as fallback. It does not accept SQL or SuiteQL input.

## AI Query Console v0.5

The backend includes a deterministic, rule-based orchestrator:

```bash
curl -X POST "http://localhost:8000/api/v1/orchestrator/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me P/L vs budget for Q1","periodRange":"2026-Q1","subsidiary":"NA"}'
```

Example questions:

- `Show me P/L vs budget for Q1`
- `Compare revenue year over year`
- `Show EMEA subsidiary drilldown`
- `What running projects are at risk?`
- `Which projects are overdue by account manager?`

The web dashboard includes an AI Query Console that calls only `/api/v1/orchestrator/query`. The orchestrator does not call an external LLM yet and does not accept SQL, SuiteQL, or raw NetSuite access.

## Audit Log v0.6

Orchestrator executions are recorded in an in-memory audit log. The log resets when the API process restarts.

```bash
curl "http://localhost:8000/api/v1/audit/logs"
curl "http://localhost:8000/api/v1/audit/summary"
```

The audit log records request metadata, detected intent, tools used, endpoint called, success or failure, fallback status, and latency. It does not store credentials, secrets, SQL, SuiteQL, or raw NetSuite access details.

The web dashboard includes a Tool Execution Monitoring panel that shows the latest orchestrator calls and aggregate audit counters.

## Connector Studio v0.7

The backend exposes a mock NetSuite connector configuration surface:

```bash
curl "http://localhost:8000/api/v1/connectors"
curl "http://localhost:8000/api/v1/connectors/netsuite"
curl -X POST "http://localhost:8000/api/v1/connectors/netsuite/test"
curl -X PUT "http://localhost:8000/api/v1/connectors/netsuite/config" \
  -H "Content-Type: application/json" \
  -d '{"accountId":"MOCK-CFO-SBX","environment":"sandbox","authMode":"placeholder","mockMode":true}'
```

Connector configuration is in memory only and resets when the API process restarts. V0.7 accepts placeholder fields only: `accountId`, `environment`, `authMode`, `mockMode`, `status`, and `lastTestedAt`. It does not store real NetSuite credentials, tokens, passwords, secrets, SQL, SuiteQL, or raw NetSuite access.

The web dashboard includes a Connector Studio section with a NetSuite connector card, mock mode status, placeholder config form, and a mock test connection button. Connector test actions are written to the in-memory audit log.

## Flow Catalog v0.8

The backend exposes a mock integration flow catalog:

```bash
curl "http://localhost:8000/api/v1/flows"
curl "http://localhost:8000/api/v1/flows/netsuite-cfo-dashboard-refresh"
curl -X POST "http://localhost:8000/api/v1/flows/netsuite-cfo-dashboard-refresh/run"
```

Included mock flows:

- `netsuite-cfo-dashboard-refresh`
- `netsuite-project-risk-refresh`
- `netsuite-subsidiary-drilldown-refresh`

Flow definitions and last run state are stored in memory only and reset when the API process restarts. Mock flow runs generate a `requestId`, update last run metadata, call existing approved CFO/orchestrator services only, and write an audit log event. V0.8 does not add real credentials, SQL, SuiteQL, or raw NetSuite access.

The web dashboard includes a Flow Catalog section with flow cards, step views, run buttons, status, and last run result messaging.

## LLM Provider Abstraction v1.0

The orchestrator includes a safe AI intent layer with a provider abstraction. Local build and tests do not require real API keys.

```bash
AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

Supported provider modes:

- `disabled`: uses the deterministic rule-based router.
- `mock`: default; uses the local `MockLLMProvider` for deterministic mock intent extraction.
- `openai`: calls OpenAI only when `OPENAI_API_KEY` is configured.

The real OpenAI provider is limited to structured intent extraction. The model can only return an intent and confidence score, and its output is validated against the existing supported intent schema before any approved CFO service is called. The model does not call tools and must not generate SQL, SuiteQL, or raw NetSuite queries.

If the OpenAI call fails, no key is present, or the model output is invalid, the orchestrator falls back to the rule-based router. Orchestrator responses and audit logs include `aiProvider`, `aiMode`, `modelName`, `modelCallAttempted`, `modelCallSucceeded`, and `usedFallbackRouter`.

## Tests

Backend:

```bash
cd apps/api
pytest
```

TypeScript workspaces:

```bash
pnpm test
```

## Safety constraints

- Never store real credentials in source code.
- `.env.example` contains placeholders only.
- Do not overwrite local `.env` files.
- Do not expose arbitrary SQL or SuiteQL execution.
- Use `apps/api/app/connectors/netsuite/query_templates.py` for named approved query templates.
- Use `apps/api/app/connectors/netsuite/interface.py` for connector capabilities instead of free-form query execution.
- Keep NetSuite integration in `mock` mode until real credential handling and authorization are designed.
