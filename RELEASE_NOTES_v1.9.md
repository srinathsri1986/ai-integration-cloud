# Release Notes v1.9

## AI-Assisted Flow Draft Generation

- Added `POST /api/v1/flows/suggestions` for governed natural-language flow drafting.
- Added a backend suggestion service that uses mock, Ollama, or OpenAI providers for structured draft metadata only.
- Validates every suggested flow against approved connectors, approved tools, draft status, and controlled trigger types.
- Falls back to deterministic templates when model output is unavailable or invalid.
- Added a "Describe a flow" panel to the visual canvas so users can generate, review, and manually save draft flows.
- Audits flow suggestion attempts with provider, model, fallback, and model-call metadata.

## Guardrails

- No automatic publish, execution, or save.
- No arbitrary SQL, SuiteQL, raw NetSuite queries, credentials, secrets, or arbitrary code.
- Custom drafted flows still fail closed until explicit runtime mappings are implemented.
