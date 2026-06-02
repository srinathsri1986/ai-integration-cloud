# Release Notes v2.7

## Flow-to-Mapping Linkage

V2.7 connects custom flow definitions to governed published mapping definitions.

## Added

- Added optional `mappingDefinitionId` to flow definitions.
- Persisted mapping references on flow definitions.
- Added lightweight DB column migration for local SQLite/PostgreSQL runtime compatibility.
- Validated that attached mappings exist and are `published` before a flow can reference them.
- Updated custom flow runtime so published custom flows with a published mapping return mapping simulation output.
- Preserved fail-closed behavior for custom flows without mappings.
- Added mapping IDs to flow-run audit traces.
- Added published mapping selector to Recipe Designer Lite.
- Displayed attached mapping IDs on flow cards.
- Added flow run preview output for mapped custom flows.
- Added backend tests for unknown mapping references, draft mapping rejection, and mapped custom flow runtime preview.

## Governance

- AI cannot attach, approve, publish, or run mappings automatically.
- Flows can reference only published mapping definitions.
- Custom flows without mappings remain fail-closed.
- Runtime preview uses mapping simulation only; no external system calls, arbitrary code, SQL, SuiteQL, credentials, or raw system access are introduced.

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
