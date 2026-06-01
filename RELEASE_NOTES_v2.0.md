# Release Notes v2.0

## Persona-Based Enterprise UI Redesign

- Added a polished `/login` experience with local persona selection.
- Added role-aware routing for CFO, Finance Controller, Integration Admin, Developer, and Viewer personas.
- Replaced the single combined landing page with dedicated workspaces:
  - `/cfo`
  - `/orchestrator`
  - `/flows`
  - `/connectors`
  - `/audit`
  - `/admin`
- Added a shared platform shell with sidebar navigation, top status bar, role badge, and modern enterprise styling.
- Preserved existing CFO dashboard, AI query console, connector studio, flow designer, visual canvas, and audit functionality.

## Guardrails

- The redesign uses the existing placeholder JWT and RBAC model only.
- No real credentials, secrets, arbitrary SQL, SuiteQL, or raw NetSuite access were added.
- Backend permission enforcement remains the system of record for protected operations.
