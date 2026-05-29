# V1.0 Release Notes - AI Integration Cloud MVP

## Summary
V1.0 introduces optional real OpenAI provider integration through environment variables while preserving mock mode as the default and rule-based fallback for safety.

## Capabilities
- NetSuite CFO dashboard with mock connector
- Approved CFO backend APIs
- MCP CFO tools
- AI Query Console
- Rule-based orchestrator
- Audit logging
- Connector Studio
- Flow Catalog
- LLM provider abstraction
- Optional OpenAI intent extraction

## Guardrails
- No real credentials committed
- No arbitrary SQL or SuiteQL
- No raw NetSuite access exposed
- Model cannot call tools directly
- Invalid model outputs fall back to rule-based routing
- Mock provider remains default

## Validation
- Backend tests passed
- pnpm -r build passed
- Docker stack validated
