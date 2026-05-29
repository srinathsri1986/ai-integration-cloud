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
