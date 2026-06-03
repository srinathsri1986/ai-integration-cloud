# Release Notes v3.4

## Active Integration Management Console

V3.4 makes Integration Studio behave like a real SaaS operating console for saved integrations.

## Added

- Added `DELETE /api/v1/flows/{flow_id}` for user-created integration definitions.
- Added `DELETE /api/v1/mappings/definitions/{mapping_id}` for saved mapping definitions.
- Added audit entries for flow and mapping delete actions.
- Protected built-in demo integrations from deletion.
- Added backend tests for integration deletion, built-in integration protection, and mapping deletion.
- Added frontend API helpers for deleting integrations and mappings.
- Added a new Active Integrations console on `/flows`.
- Added status filters for draft, pending approval, approved, published, and paused integrations.
- Added a selected integration review pane with lifecycle, run, mapping simulation, and delete actions.
- Added a compact real draft creation form backed by the flow definition API.

## Governance

- Delete actions are explicit user actions.
- Built-in demo integrations remain protected.
- Lifecycle actions remain human controlled.
- Published integrations are still required before runtime execution.
- Mapping simulation remains preview-only.
- No external system execution, credentials, SQL, SuiteQL, or arbitrary code execution was added.

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
