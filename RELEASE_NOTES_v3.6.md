# Release Notes v3.6

## Runtime Run Detail View

V3.6 makes integration runtime output inspectable from both API and UI.

## Added

- Added `inspection` summary to flow run responses.
- Added derived duration, step counts, warning count, mapping ID, payload availability, and audit trace ID.
- Added `/flows/runs/{requestId}` frontend run detail page.
- Added timeline detail UI for each execution step.
- Added source and target payload preview panels.
- Added an `Open run detail` action after running an integration from the review pane.
- Added backend test coverage for run inspection summaries.

## Governance

- Run detail is read-only.
- Payload preview uses already-governed runtime preview data.
- No external system execution, secrets, arbitrary SQL, SuiteQL, or arbitrary code execution was added.
- Audit request IDs remain visible for traceability.

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
