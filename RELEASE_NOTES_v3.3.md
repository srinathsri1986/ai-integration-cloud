# Release Notes v3.3

## Promote Discovered Schema to Governed Catalog

V3.3 closes the loop from REST sample discovery to saved mapping drafts.

## Added

- Added `POST /api/v1/connectors/rest-api/promote-schema`.
- Added schema promotion request and response models.
- Added a local governed mapping catalog registry for promoted REST objects.
- Added promotion audit logging through the connector audit path.
- Added backend tests for promotion, mapping save, simulation, and secret-like field skipping.
- Added frontend promotion API helper.
- Added `Promote to governed catalog` action in the Mapping Studio wizard.
- Added promoted REST objects to the source/target trays.
- Allowed mapping drafts to save after a discovered REST schema is promoted.

## Governance

- Promotion revalidates discovered fields.
- Secret-like field names are skipped during promotion.
- Promoted objects are local runtime catalog objects for the MVP.
- No external REST calls are made.
- No credentials, headers, bearer tokens, passwords, API keys, or secrets are stored.
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
