# Release Notes v3.5

## Guided Integration Creation and Live AI Enforcement

V3.5 adds a one-step-at-a-time integration creation wizard and makes live AI behavior explicit.

## Added

- Added `/flows/new` guided integration wizard.
- Added a visible `New integration` action from the Active Integrations console.
- Added row-level `Delete` text in the integration list, not only an icon.
- Added `requireLiveAi` to flow suggestion requests.
- Added `requireLiveAi` to mapping suggestion requests.
- Added backend enforcement so live-AI-required requests fail visibly when Ollama/OpenAI output is invalid or unavailable.
- Added frontend behavior so Mapping Studio no longer shows fallback template suggestions when live AI was requested.
- Added tests for live-AI-required flow and mapping suggestions.

## Governance

- The wizard saves drafts only.
- Human lifecycle actions are still required before publication.
- The model still cannot save, publish, run, call tools, or access systems directly.
- Live AI output is validated against approved tools, known fields, known objects, and approved transforms.
- Deterministic templates remain only as a governed fallback when callers do not require live AI.
- No credentials, external system execution, arbitrary code, SQL, or SuiteQL were added.

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
