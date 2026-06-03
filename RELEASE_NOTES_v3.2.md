# Release Notes v3.2

## Guided Integration Wizard UI

V3.2 makes the Mapping Studio easier for non-technical integrators by replacing the long workbench layout with guided steps.

## Added

- Added a four-step Mapping Studio wizard: Describe, Choose data, Map fields, Review.
- Show only the active step to reduce page clutter.
- Moved REST schema discovery into the Choose data step.
- Moved field trays and mapping grid into the Map fields step.
- Moved mapping save, saved mappings, simulation, and payload previews into the Review step.
- Added a Review integration action after required target fields are mapped.
- Kept optional AI mapping suggestions available in the Describe step.

## Governance

- This is a frontend workflow improvement only.
- No new execution capability is introduced.
- Session-discovered REST schemas remain temporary and cannot be saved as persistent mappings.
- No external API calls, credentials, headers, bearer tokens, SQL, SuiteQL, or arbitrary payload execution are introduced.

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
