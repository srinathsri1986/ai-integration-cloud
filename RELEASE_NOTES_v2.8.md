# Release Notes v2.8

## Runtime Execution Timeline and Debug Console

V2.8 adds step-level runtime visibility for flow runs.

## Added

- Added `executionTimeline` to flow run records.
- Persisted timeline steps with each flow run.
- Added `GET /api/v1/flows/runs/{request_id}`.
- Added lightweight DB column migration for `flow_runs.execution_timeline`.
- Added timeline entries for built-in flow runs.
- Added timeline entries for fail-closed flow runs.
- Added timeline entries for mapped custom flow runtime preview.
- Added mapping definition IDs and warnings to timeline steps.
- Added Flow Catalog runtime debug console.
- Added run detail refresh action in the UI.
- Added tests for persisted timeline detail and unknown run lookup.

## Governance

- Timeline visibility is observational only.
- No external systems are called.
- No arbitrary code, SQL, SuiteQL, credentials, or raw access is introduced.
- Runtime output remains mock/sample-payload based.

## Validation

Run locally:

```bash
cd /Users/srinathsrinivasan/Projects/ai-integration-cloud
apps/api/.venv/bin/python -m pytest apps/api/tests
apps/api/.venv/bin/ruff check apps/api/app apps/api/tests
pnpm -r build
docker compose -f infra/docker-compose.yml config --services
git diff --check
```
