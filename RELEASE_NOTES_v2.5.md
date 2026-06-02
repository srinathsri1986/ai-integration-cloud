# Release Notes v2.5

## Mapping Persistence and Governance

V2.5 turns reviewed field mappings into persistent governed platform assets.

## Added

- Added `mapping_definitions` persistence table.
- Added mapping definition repository and service.
- Added `GET /api/v1/mappings/definitions`.
- Added `POST /api/v1/mappings/definitions`.
- Added `GET /api/v1/mappings/definitions/{mapping_id}`.
- Added `POST /api/v1/mappings/definitions/{mapping_id}/lifecycle`.
- Added lifecycle states: `draft`, `pending_approval`, `approved`, `published`, and `paused`.
- Added audit records for mapping save/update and lifecycle actions.
- Added shared TypeScript schemas for mapping definitions and lifecycle responses.
- Updated Data Mapping Studio with mapping ID/name fields, backend save, saved mapping list, reopen action, and lifecycle buttons.
- Improved mapping suggestions so the required Salesforce Opportunity `Name` field is proposed when appropriate.
- Added backend tests for save/list, validation failure, lifecycle governance, and blocked raw-query language.

## Governance

- AI suggestions cannot save, approve, publish, or execute mappings automatically.
- Saved mappings are validated server-side against known object metadata and approved transforms.
- Required target fields must be mapped before a definition can be saved.
- Duplicate target fields are rejected.
- Raw SQL, SuiteQL, arbitrary code, credentials, and secret language remain blocked.

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
