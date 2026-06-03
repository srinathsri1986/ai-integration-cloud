# Release Notes v3.1

## Discovered Schema to Mapping Workspace

V3.1 makes REST schema discovery usable inside the visual Mapping Studio.

## Added

- Added `Use as Source` action for discovered REST sample schemas.
- Added `Use as Target` action for discovered REST sample schemas.
- Converted discovered schema fields into session-scoped mapping tray objects.
- Added discovered field samples, type labels, and required status to the active mapping trays.
- Updated the mapping prompt automatically when a discovered schema is selected.
- Added a guard that prevents session-scoped discovered schemas from being saved as persistent mappings.

## Governance

- Discovered schema objects are browser/session scoped only.
- Persistent mapping saves still require governed catalog object IDs.
- No external REST API calls are made.
- No headers, credentials, bearer tokens, passwords, API keys, or secrets are stored.
- No arbitrary code, SQL, SuiteQL, or payload execution is introduced.

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
