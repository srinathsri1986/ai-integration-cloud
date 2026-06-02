# Release Notes v2.6

## Mapping Runtime Simulation

V2.6 adds safe preview execution for saved mapping definitions.

## Added

- Added `POST /api/v1/mappings/definitions/{mapping_id}/simulate`.
- Added mapping simulation response model with source payload, target payload, warnings, transforms, and timestamp.
- Added approved sample payload helper for mapping catalog objects.
- Added simulation audit events as `MAPPING_SIMULATION`.
- Added backend transform behavior for `direct`, `rename`, `format_date`, `lookup_placeholder`, and `constant_placeholder`.
- Added Mapping Studio simulation button for saved mappings.
- Added side-by-side source and mapped target output preview.
- Added backend tests for successful simulation, unknown mapping, audit logging, and required-field warnings.

## Governance

- Simulation uses approved sample payloads only.
- Simulation does not call external systems.
- Simulation does not execute arbitrary code.
- Simulation does not generate SQL, SuiteQL, raw queries, credentials, or secrets.
- Draft mappings can be simulated, but lifecycle approval and publishing remain human-controlled.

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
