# Release Notes v1.7

## Flow Designer Lite

- Added persistent flow definitions with a new `flow_definitions` table.
- Seeded the existing built-in flows into persistent storage.
- Added controlled flow definition create/update endpoint:
  - `POST /api/v1/flows/definitions`
- Added flow definition fields for status and trigger type.
- Added approved-tool validation for flow steps.
- Rejected raw SQL, SuiteQL, raw query, and arbitrary code execution language in flow definitions.
- Added audit events for flow definition changes.
- Added Flow Designer Lite form to the Flow Catalog UI.
- Kept custom flow execution fail-closed until explicit runtime mappings are implemented.
- Added backend tests for save, validation, audit logging, and custom execution guardrails.

This version establishes the form-based orchestration builder foundation without introducing drag-and-drop canvas complexity or arbitrary execution.
