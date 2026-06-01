# Release Notes v2.1

## Human Approval and Publish Workflow

- Added flow lifecycle states: `draft`, `pending_approval`, `approved`, `published`, and `paused`.
- Added `POST /api/v1/flows/{flow_id}/lifecycle` for governed lifecycle transitions.
- Added human workflow actions: submit for approval, approve, reject, publish, and pause.
- Updated the Flow Catalog UI with lifecycle action buttons and published-only run controls.
- Updated built-in mapped flows to seed as `published`.
- Added audit events for lifecycle transitions.
- Added tests for approval, publish, invalid transitions, and published custom-flow fail-closed behavior.

## Guardrails

- AI-generated flows remain drafts until a human lifecycle action changes status.
- Only `published` flows can be run.
- Custom published flows still fail closed until explicit runtime mappings are implemented.
- No arbitrary SQL, SuiteQL, raw NetSuite access, credentials, secrets, or automatic publishing were added.
