# Release Notes v1.2

## Safe CFO Narrative Generation

- Added governed CFO executive narrative generation to orchestrator query responses.
- Added a backend narrative service that builds compact approved CFO summaries before any model call.
- Kept `mock` as the default provider and deterministic template narratives available for disabled or failed model modes.
- Added Ollama and OpenAI narrative generation using summarized JSON only.
- Validates narrative output length and blocks raw-query or sensitive-language output.
- Falls back to deterministic templates when model calls fail, time out, or return invalid output.
- Added narrative audit metadata:
  - `narrativeProvider`
  - `narrativeModel`
  - `narrativeGenerated`
  - `narrativeFallbackUsed`
- Updated the AI Query Console to show the executive narrative, narrative provider metadata, tools used, and structured results.
- Added backend tests for deterministic templates, mocked Ollama/OpenAI narrative responses, and fallback handling.

No credentials, raw transactions, SQL, SuiteQL, raw NetSuite access, or tool calls are sent through narrative generation.
