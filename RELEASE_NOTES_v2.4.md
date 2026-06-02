# Release Notes v2.4

## AI-Assisted Mapping Suggestions

V2.4 adds governed natural-language mapping suggestions to Data Mapping Studio.

## Added

- Added `POST /api/v1/mappings/suggestions`.
- Added backend mapping object metadata for the current mock systems.
- Added mock, Ollama, and OpenAI mapping suggestion support through the existing LLM provider abstraction.
- Added strict validation for suggested source fields, target fields, transforms, confidence, and rationale.
- Added deterministic template fallback when the provider is disabled, unavailable, or returns invalid output.
- Added audit logging for mapping suggestion requests.
- Added a natural-language mapping prompt and suggestion queue in `/mapping`.
- Added human accept/reject controls for suggested mappings.
- Added backend tests for valid suggestions, unknown objects, invalid model output fallback, and blocked prompt language.

## Governance

- Suggestions use only approved object metadata and allowed transforms.
- No real credentials, secrets, SQL, SuiteQL, raw system access, arbitrary code, or publish instructions are sent to or accepted from the model.
- AI suggestions cannot save, publish, or execute mappings automatically.
- Invalid model output fails closed into deterministic templates.

## Validation

Run locally:

```bash
cd /Users/srinathsrinivasan/Projects/ai-integration-cloud
cd apps/api && pytest
cd ../..
pnpm -r build
docker compose -f infra/docker-compose.yml config --services
git diff --check
```
