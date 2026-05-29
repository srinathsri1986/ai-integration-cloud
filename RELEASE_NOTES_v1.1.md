# Release Notes v1.1

## Local Ollama Provider Setup + Large Model Integration

- Added `AI_PROVIDER=ollama` to the backend LLM provider abstraction.
- Added `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_TIMEOUT_SECONDS` settings.
- Implemented safe Ollama structured intent extraction through `/api/generate`.
- Kept mock as the default provider and preserved OpenAI as optional.
- Validates Ollama output against the existing supported CFO intent schema.
- Falls back to the rule-based router when Ollama is unavailable, times out, or returns invalid output.
- Added mocked Ollama tests; the test suite does not require Ollama to be installed or running.
- Documented Mac model guidance and Docker networking via `host.docker.internal`.

No credentials, SQL, SuiteQL, raw NetSuite access, or tool calls are sent through the Ollama provider.
