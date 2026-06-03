# Release Notes v3.0

## Connector Schema Discovery and Mapping Tray

V3.0 adds safe REST sample schema discovery and a visual discovery tray in the Mapping Studio.

## Added

- Added `POST /api/v1/connectors/rest-api/discover-schema`.
- Added REST schema discovery request and response models.
- Added top-level scalar field inference for pasted sample JSON.
- Added date, number, boolean, and string inference.
- Added secret-like field skipping for password, token, secret, API key, authorization, and bearer-style fields.
- Added warnings for nested arrays and objects.
- Added shared TypeScript schemas for REST schema discovery.
- Added frontend API helper for schema discovery.
- Added Mapping Studio REST schema discovery panel.
- Added discovered field cards with type, sample value, required status, and warnings.

## Governance

- Discovery is design-time only.
- Discovery returns `executable:false`.
- No outbound HTTP requests are made.
- No headers, credentials, bearer tokens, passwords, API keys, or secrets are stored.
- Nested payload execution and arbitrary payload execution are not introduced.
- Runtime mappings are still saved only through the existing governed mapping definition lifecycle.

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
