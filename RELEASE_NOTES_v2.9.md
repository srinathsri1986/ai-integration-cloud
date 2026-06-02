# Release Notes v2.9

## Generic REST Connector Foundation

V2.9 adds the first system-agnostic connector foundation beyond NetSuite.

## Added

- Added a governed mock REST API connector config model.
- Added `GET /api/v1/connectors/rest-api`.
- Added `PUT /api/v1/connectors/rest-api/config`.
- Added `POST /api/v1/connectors/rest-api/test`.
- Added `GET /api/v1/connectors/rest-api/objects`.
- Added approved REST object schemas for customer, invoice, and opportunity.
- Added approved REST action metadata for sample reads, payload validation, and mock post simulation.
- Added REST connector audit logging for test actions.
- Added shared TypeScript schemas for REST connector config, test responses, and approved objects.
- Added REST connector frontend API helpers and safe fallbacks.
- Added a REST API section to Connector Studio with approved object tiles.
- Updated the integration catalog to mark the governed REST foundation as ready.

## Governance

- REST support is mock-first.
- No outbound HTTP requests are executed.
- No API keys, bearer tokens, passwords, headers, or secrets are stored or returned.
- No arbitrary URLs or arbitrary payload execution are introduced.
- REST object metadata is approved and finite.
- Connector test events are audited.

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
