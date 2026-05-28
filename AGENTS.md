# Project: NetSuite CFO Intelligence Orchestrator

## Product goal
Build an AI-native integration platform MVP similar in spirit to OIC/Boomi, starting with NetSuite CFO analytics.

## Working rules
- Never store real credentials in source code.
- Use .env.example for placeholders only.
- Do not expose arbitrary SQL to users or LLMs.
- Use named approved NetSuite query templates only.
- Use mock NetSuite data first.
- Build incrementally.
- Ask before destructive commands.
- Add README instructions for every module.
- Add tests for backend and connector logic.
- Keep architecture production-grade, not toy/demo-only.
- Do not create a full Boomi/OIC clone in one step.
- Build one module at a time.

## Target stack
- Frontend: Next.js, TypeScript, Tailwind, shadcn/ui
- Backend: FastAPI
- Database: PostgreSQL
- Cache: Redis
- MCP server: TypeScript
- Deployment: Docker Compose
- Auth: placeholder JWT
- Observability: structured logs

## Safety rules
- Do not run rm -rf without asking.
- Do not overwrite .env files.
- Do not commit secrets.
- Do not introduce real NetSuite credentials.
- Do not generate arbitrary SuiteQL execution endpoints.
