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

The orchestrator includes a safe AI intent layer with a provider abstraction. Local build and tests do not require real API keys or local model services.

```bash
AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TIMEOUT_SECONDS=30
```

Supported provider modes:

- `disabled`: uses the deterministic rule-based router.
- `mock`: default; uses the local `MockLLMProvider` for deterministic mock intent extraction.
- `openai`: calls OpenAI only when `OPENAI_API_KEY` is configured.
- `ollama`: calls a local Ollama server only when reachable.

The real OpenAI provider is limited to structured intent extraction. The model can only return an intent and confidence score, and its output is validated against the existing supported intent schema before any approved CFO service is called. The model does not call tools and must not generate SQL, SuiteQL, or raw NetSuite queries.

If the OpenAI call fails, no key is present, or the model output is invalid, the orchestrator falls back to the rule-based router. Orchestrator responses and audit logs include `aiProvider`, `aiMode`, `modelName`, `modelCallAttempted`, `modelCallSucceeded`, and `usedFallbackRouter`.

## Local Ollama Provider v1.1

Hardware check from the local Mac used for this setup:

- MacBook Pro with Apple M3 Pro
- 11 CPU cores
- 18 GB memory
- About 163 GiB free disk space

Model guidance:

- `qwen3:30b`: recommended primary local quality model for this hardware class, though it may be slow because 18 GB RAM is tight.
- `deepseek-r1:32b`: similar memory pressure to `qwen3:30b`; useful as an alternate reasoning model if `qwen3:30b` is not suitable.
- `llama3.1:70b`: not recommended on 18 GB RAM.
- `qwen2.5-coder:7b`: recommended smaller fallback for fast structured JSON extraction.
- `llama3.1:8b`: practical fallback if 30B/32B models are too slow.

Install and run Ollama on macOS:

```bash
brew install --cask ollama
open -a Ollama
curl http://localhost:11434/api/tags
```

Pull selected models:

```bash
ollama pull qwen3:30b
ollama pull qwen2.5-coder:7b
```

Validate JSON behavior:

```bash
ollama list
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:30b",
  "prompt": "Return only JSON: {\"intent\":\"PL_VS_BUDGET\",\"confidence\":0.95}",
  "stream": false
}'
```

For FastAPI running directly on the Mac, use:

```bash
OLLAMA_BASE_URL=http://localhost:11434
```

For FastAPI running in Docker Compose while Ollama runs on the Mac host, use:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

The Ollama provider is limited to structured intent extraction. It does not receive credentials and must not generate SQL, SuiteQL, raw NetSuite queries, or tool calls. If Ollama is unavailable, times out, returns invalid JSON, or returns an unsupported intent, the orchestrator falls back to the rule-based router and records that fallback in audit metadata.

### Docker Compose AI Provider Wiring

The API container receives AI provider settings through `infra/docker-compose.yml`.

Run with the default mock provider:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Run with local Ollama from Docker:

```bash
export AI_PROVIDER=ollama
export OLLAMA_BASE_URL=http://host.docker.internal:11434
export OLLAMA_MODEL=qwen2.5-coder:7b
export OLLAMA_TIMEOUT_SECONDS=30
docker compose -f infra/docker-compose.yml up --build
```

Docker uses `host.docker.internal` because Ollama runs on the Mac host while FastAPI runs inside the API container. For non-Docker FastAPI, use `OLLAMA_BASE_URL=http://localhost:11434`.

Verify provider behavior through the audit log:

```bash
curl -X POST "http://localhost:8000/api/v1/orchestrator/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me P/L vs budget for Q1","periodRange":"2026-Q1","subsidiary":"NA"}'
curl "http://localhost:8000/api/v1/audit/logs"
```

Recent audit entries should show `aiProvider` as `ollama`, `aiMode` as `ollama`, `modelName` as `qwen2.5-coder:7b`, and `modelCallAttempted` as `true` when Ollama is reachable. If Ollama fails or returns invalid output, `usedFallbackRouter` becomes `true`.

## Safe CFO Narrative Generation v1.2

The orchestrator now generates a short CFO executive narrative after it retrieves data from an approved CFO service:

```bash
curl -X POST "http://localhost:8000/api/v1/orchestrator/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me P/L vs budget for Q1","periodRange":"2026-Q1","subsidiary":"NA"}'
```

Narratives are generated only from compact, approved CFO/orchestrator summaries. The narrative service does not send credentials, raw transactions, arbitrary SQL, SuiteQL, raw NetSuite queries, or raw NetSuite access details to any model.

Provider behavior:

- `AI_PROVIDER=mock`: default; uses the local mock provider for deterministic narrative output.
- `AI_PROVIDER=ollama`: preferred local LLM mode; sends approved summarized JSON to the local Ollama model.
- `AI_PROVIDER=openai`: optional hosted mode; sends approved summarized JSON only when `OPENAI_API_KEY` is configured.
- `AI_PROVIDER=disabled`: uses deterministic template narratives only.

If the selected model is unavailable, times out, returns invalid JSON, returns an overlong narrative, or includes blocked raw-query/sensitive language, the API falls back to deterministic template narrative generation. Orchestrator responses and audit logs include `narrativeProvider`, `narrativeModel`, `narrativeGenerated`, and `narrativeFallbackUsed`.

## NetSuite Sandbox Connector Foundation v1.3

The connector layer now supports an explicit sandbox mode for local readiness checks:

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

Mock mode remains the default and is still the recommended mode for local MVP work:

```bash
NETSUITE_MODE=mock
```

The sandbox connector validates that a HTTPS base URL and token-based auth values are configured, but V1.3 does not execute real SuiteQL or Saved Search calls yet. Approved template dispatch is preserved, unknown template IDs are rejected, and sandbox template execution fails closed until each approved CFO template is explicitly mapped.

The Connector Studio UI shows sandbox readiness with safe metadata only:

- runtime mode
- status
- auth mode
- base URL configured
- credentials configured
- last tested timestamp

It never displays, stores, or accepts real token values in the web UI.

## Secrets and Runtime Hardening v1.4

V1.4 adds startup configuration validation and centralized secret redaction. Mock mode remains the default, so local development does not require real NetSuite or OpenAI credentials.

Recommended local secret workflow:

```bash
cp .env.example .env.local
```

Put real local-only values in `.env.local` when needed. Files matching `.env.*` are ignored by Git except `.env.example`, so placeholders stay documented without committing secrets.

Runtime validation checks:

- `NETSUITE_MODE` must be `mock` or `sandbox`.
- `AI_PROVIDER` must be `disabled`, `mock`, `openai`, or `ollama`.
- Sandbox mode reports safe warnings when base URL or token-based auth values are incomplete.
- OpenAI and Ollama modes report safe warnings when provider configuration is incomplete.

Runtime posture logs and readiness metadata use booleans only, such as `credentialsConfigured`, and never log raw token, password, key, or secret values. Audit entries are redacted before storage to mask accidental inline secret patterns such as `password=...`, `token:...`, and bearer tokens.

Future production secret options:

- Docker secrets for containerized local demos.
- OCI Vault, AWS Secrets Manager, or Azure Key Vault through a provider abstraction.
- Per-tenant secret references rather than stored plaintext values.

## Persistent Audit and Flow History v1.5

Audit events and flow runs now persist through a database-backed repository layer. The Docker Compose API service uses PostgreSQL through `DATABASE_URL`, while tests use SQLite so the suite does not require Docker.

Tables are created at API startup for the local MVP:

- `audit_logs`: append-only audit events with indexed request, intent, provider, success, and timestamp fields.
- `flow_runs`: append-only flow execution records with indexed request, flow, status, and timestamp fields.

The audit log API supports filtered and paginated reads:

```bash
curl "http://localhost:8000/api/v1/audit/logs?intent=PL_VS_BUDGET&provider=ollama&success=true&limit=50&offset=0"
curl "http://localhost:8000/api/v1/audit/logs?requestId=<request-id>"
```

Flow run history is available through:

```bash
curl "http://localhost:8000/api/v1/flows/runs?flow_id=netsuite-cfo-dashboard-refresh&run_status=succeeded"
```

The service keeps queryable operational fields as indexed columns and stores full redacted event metadata as JSON/JSONB for future governance views. This keeps V1.5 simple for the MVP while leaving room for monthly partitioning, retention policies, async write buffering, and analytics stores later.

## Placeholder Auth and RBAC v1.6

The API includes local placeholder JWT authentication for MVP governance testing. This is not production SSO; it is a local role boundary for protected connector, audit, flow, and orchestrator actions.

Create a local placeholder token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","role":"Integration Admin"}'
```

Supported roles:

- `CFO`
- `Finance Controller`
- `Integration Admin`
- `Viewer`
- `Developer`

Role boundaries:

- CFO and Finance Controller can read CFO data and use the AI Query Console.
- Integration Admin and Developer can manage connectors and run flows.
- Viewer can read audit/flow/CFO views but cannot run flows or test connectors.
- Audit logs are readable by Integration Admin, Developer, and Viewer.

The web app includes a local role selector that stores the placeholder token in browser local storage for client-side actions. Missing auth defaults to a local Integration Admin only for this local MVP workflow.

## Flow Designer Lite v1.7

V1.7 adds a controlled form-based flow designer before the full drag-and-drop canvas. Integration Admins and Developers can save flow definitions using approved building blocks only.

Flow definitions support:

- flow ID
- name
- description
- source connector: `netsuite`
- target module
- status: `draft`, `active`, `paused`
- trigger type: `manual` or `schedule_placeholder`
- one or more approved steps

Approved step actions:

- `cfo.dashboard_summary`
- `cfo.pl_vs_budget`
- `cfo.yoy_comparison`
- `cfo.subsidiary_drilldown`
- `cfo.running_projects`
- `cfo.overdue_projects_by_account_manager`
- `orchestrator.query`

Save a controlled flow definition:

```bash
curl -X POST "http://localhost:8000/api/v1/flows/definitions" \
  -H "Content-Type: application/json" \
  -d '{
    "flowId":"custom-cfo-refresh",
    "name":"Custom CFO refresh",
    "description":"Refresh CFO dashboard data with approved CFO actions.",
    "sourceConnector":"netsuite",
    "targetModule":"cfo_dashboard",
    "status":"draft",
    "triggerType":"manual",
    "steps":[{"id":"summary","name":"Load summary","description":"Load approved CFO summary data.","approvedTool":"cfo.dashboard_summary"}]
  }'
```

Custom flow definitions are persisted and audited, but custom execution fails closed until explicit runtime mappings are added. This preserves governance while establishing the product shape for the later React Flow canvas.

## Visual Flow Canvas Shell v1.8

V1.8 adds the first visual orchestration canvas on top of Flow Designer Lite. The canvas renders a governed trigger, connector, approved action nodes, and audit node, with a right-side properties panel and save action that writes through the existing flow definition API.

The canvas supports:

- drag approved action nodes from the palette into a draft flow
- visual trigger, connector, action, and audit nodes
- guarded properties panel for flow ID, name, and status
- validate-and-save through `POST /api/v1/flows/definitions`
- saved-flow preview from the current catalog

This version intentionally keeps runtime execution governed by V1.7 flow definitions. Custom visual flows save successfully but still fail closed at execution time until explicit runtime mappings are added.

Note: this local implementation uses a repo-native visual canvas shell. The package manager sandbox could not install the React Flow dependency in this session, so a future V1.8.x/V1.9 step can swap the shell to `@xyflow/react` once dependencies are installed locally.

## AI-Assisted Flow Draft Generation v1.9

V1.9 adds a governed "Describe a flow" panel to the visual canvas. Users can describe an integration need in natural language, and the backend proposes a draft through `POST /api/v1/flows/suggestions`.

The suggestion service can use the configured mock, Ollama, or OpenAI provider, but every model response is validated against the approved flow definition schema before it reaches the UI. Invalid or unavailable model output falls back to deterministic templates. Suggested flows remain drafts only; the user must review and save them manually, and custom flows still fail closed until runtime mappings are explicitly implemented.

## Persona-Based Enterprise UI v2.0

The web app now uses a persona-based platform structure instead of one combined MVP dashboard. The root route redirects to `/login`, where users choose a local placeholder persona and land in the workspace that matches their role:

- CFO and Finance Controller: `/cfo`
- Integration Admin: `/flows`
- Developer: `/orchestrator`
- Viewer: `/cfo`

Dedicated pages are available for `/cfo`, `/orchestrator`, `/flows`, `/connectors`, `/audit`, and `/admin`. The shared platform shell provides role-aware navigation, local environment/model status, and a cleaner enterprise workbench layout while preserving the existing placeholder RBAC backend.

## Human Approval and Publish Workflow v2.1

Flow definitions now move through an explicit governance lifecycle:

- `draft`
- `pending_approval`
- `approved`
- `published`
- `paused`

The flow API exposes lifecycle actions through `POST /api/v1/flows/{flow_id}/lifecycle`. Users can submit a draft for approval, approve or reject it, publish an approved flow, and pause a published flow. The UI surfaces these actions in the Flow Catalog.

Only `published` flows can be run. Built-in mapped flows can execute after publication, while custom published flows still fail closed until explicit runtime mappings are implemented. AI-generated drafts cannot publish themselves; a human lifecycle action is required.

## SaaS-Ready System-Agnostic Integration Workbench v2.2

V2.2 shifts the product experience from a NetSuite-specific MVP toward a SaaS-ready **AI Integration Cloud**. NetSuite CFO Intelligence remains the first packaged solution/template, while the Integration Studio introduces a broader system-agnostic workbench.

The `/flows` page now includes:

- a guided no-code integration path
- connector marketplace-style system cards
- visual source-to-target pipeline preview
- SaaS workspace posture badges for tenant, environment, plan, and governance
- placeholder systems for NetSuite, Salesforce, Oracle Fusion, ServiceNow, PostgreSQL, REST API, SFTP/CSV, and platform-native actions
- business-friendly language such as choose a system, pick data, match fields, review, and publish

This release is frontend-first. It does not add real connector credentials, arbitrary SQL, SuiteQL, raw system access, or unrestricted execution. The next natural step is Data Mapping Studio Lite.

## Data Mapping Studio Lite v2.3

V2.3 adds a frontend-first `/mapping` workspace for visually matching fields between systems. The studio is system-agnostic and includes mock object schemas for NetSuite, Salesforce, Oracle Fusion, REST API payloads, and SFTP/CSV files.

The mapping workspace includes:

- source system and object selection
- target system and object selection
- source field tray
- target field tray
- click-to-map field matching
- governed transformation choices: direct, rename, format date, lookup placeholder, and constant placeholder
- required target field validation
- source and target sample payload previews

Mappings are validated locally in this release. Persistence, backend mapping definitions, and AI-assisted mapping suggestions are planned next. No arbitrary code transformations, SQL, SuiteQL, credentials, or raw system access are introduced.

## AI-Assisted Mapping Suggestions v2.4

V2.4 adds governed natural-language mapping suggestions to `/mapping`. Integrators can describe the mapping goal, choose source and target objects, and ask the configured AI provider to propose field matches.

The mapping suggestion path supports mock, Ollama, and OpenAI through the existing LLM provider abstraction. Ollama remains the preferred local provider for sensitive mapping work. The model receives only the selected object metadata, field descriptions, allowed transforms, and the user's mapping goal. It never receives credentials, raw transactions, SQL, SuiteQL, raw system access, or arbitrary execution instructions.

The backend exposes:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/suggestions" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"Map NetSuite project customer, budget, due date, and owner fields into Salesforce opportunity fields.",
    "sourceObjectId":"netsuite-project",
    "targetObjectId":"salesforce-opportunity"
  }'
```

Every model response is validated against known source fields, known target fields, and approved transforms before the UI sees it. Invalid or unavailable model output falls back to deterministic templates. Suggestions remain human-reviewed drafts only; accepting a suggestion adds it to the local mapping grid, while publishing/runtime persistence is still a future step.

## Mapping Persistence and Governance v2.5

V2.5 makes reviewed field mappings persistent platform assets. Integrators can save accepted mappings as governed drafts, list saved mapping definitions, reopen them in Data Mapping Studio, and move them through a human lifecycle before publication.

The backend exposes:

```bash
curl "http://localhost:8000/api/v1/mappings/definitions"

curl -X POST "http://localhost:8000/api/v1/mappings/definitions" \
  -H "Content-Type: application/json" \
  -d '{
    "mappingId":"netsuite-project-to-salesforce-opportunity",
    "name":"NetSuite Project to Salesforce Opportunity",
    "description":"Maps approved project fields into Salesforce opportunity fields.",
    "sourceObjectId":"netsuite-project",
    "targetObjectId":"salesforce-opportunity",
    "status":"draft",
    "mappings":[
      {"id":"project-to-name","sourceField":"project_id","targetField":"Name","transform":"rename"},
      {"id":"customer-to-account","sourceField":"customer_name","targetField":"AccountName","transform":"direct"},
      {"id":"budget-to-amount","sourceField":"budget_amount","targetField":"Amount","transform":"direct"},
      {"id":"date-to-close","sourceField":"due_date","targetField":"CloseDate","transform":"format_date"}
    ]
  }'
```

Mapping definitions support `draft`, `pending_approval`, `approved`, `published`, and `paused` states through explicit lifecycle actions. The server validates every saved row against known source fields, known target fields, duplicate target usage, required target fields, and approved transforms. No mapping can introduce arbitrary code, SQL, SuiteQL, credentials, or raw system access.

## Mapping Runtime Simulation v2.6

V2.6 adds safe runtime preview for saved mapping definitions. Integrators can simulate a saved mapping against approved sample payloads and inspect the mapped target output before approving or publishing.

The backend exposes:

```bash
curl -X POST "http://localhost:8000/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/simulate"
```

Simulation uses only catalog sample payloads and approved transforms. It does not call external systems, execute code, generate SQL/SuiteQL, or access credentials. The response includes the source sample payload, mapped target output, transform list, warnings for missing required target fields, and an audit event recorded as `MAPPING_SIMULATION`.

The Mapping Studio UI now includes a **Simulate saved mapping** action and a side-by-side source/output preview panel.

## Flow-to-Mapping Linkage v2.7

V2.7 links governed mappings to custom flows. Flow definitions now support an optional `mappingDefinitionId`. Custom flows without a mapping still fail closed, while custom flows with an attached published mapping can run a safe runtime preview that includes the mapping simulation output.

The flow definition API accepts:

```json
{
  "flowId": "mapped-runtime-preview",
  "name": "Mapped runtime preview",
  "description": "Preview a mapped payload through approved actions.",
  "sourceConnector": "netsuite",
  "targetModule": "salesforce_opportunity",
  "status": "draft",
  "triggerType": "manual",
  "mappingDefinitionId": "netsuite-project-to-salesforce-opportunity",
  "steps": [
    {
      "id": "summary",
      "name": "Load summary",
      "description": "Load approved CFO summary data.",
      "approvedTool": "cfo.dashboard_summary"
    }
  ]
}
```

The backend validates that referenced mappings exist and are `published` before saving a flow reference. Flow runs include the mapping ID in audit logs and return a runtime preview payload under `data.mappingSimulation`.

The Flow Catalog UI now loads published mappings and exposes a mapping selector in Recipe Designer Lite.

## Runtime Execution Timeline and Debug Console v2.8

V2.8 adds runtime visibility for flow runs. Flow run records now include an `executionTimeline` with step-level status, timestamps, latency, approved tool, mapping ID, and warnings.

The backend exposes flow run detail lookup:

```bash
curl "http://localhost:8000/api/v1/flows/runs/{request_id}"
```

Flow Catalog now shows a runtime debug console after a flow run, including:

- run status
- request ID
- step timeline
- approved tool per step
- mapping definition used
- warnings
- mapped payload preview when a mapped custom flow runs

This remains a safe mock/runtime-preview layer. It does not call external systems, execute arbitrary code, or expose SQL/SuiteQL.

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
