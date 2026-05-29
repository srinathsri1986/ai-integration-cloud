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

## Safety model

- No real NetSuite credentials are used.
- No arbitrary SQL or SuiteQL endpoint is exposed.
- Connector access goes through approved template IDs in `app/connectors/netsuite/query_templates.py`.
- Application code depends on `app/connectors/netsuite/interface.py` instead of raw query strings.
