# Release Notes v1.3

## NetSuite Sandbox Connector Foundation

- Added `NETSUITE_MODE=sandbox` support while keeping `mock` as the default.
- Added placeholder-only NetSuite sandbox environment variables to `.env.example`.
- Added a sandbox connector skeleton with secure readiness checks for HTTPS base URL and token-based auth configuration.
- Added a NetSuite connector factory so backend CFO services can select mock or sandbox mode from configuration.
- Preserved approved-template-only access and rejected unknown or SQL-like template IDs.
- Kept sandbox template execution fail-closed until each real CFO template is explicitly mapped.
- Updated Docker Compose to pass NetSuite connector settings through environment variables.
- Extended connector API responses with safe readiness metadata:
  - `mode`
  - `baseUrlConfigured`
  - `credentialsConfigured`
- Refreshed Connector Studio into a polished connector workbench with runtime mode, readiness posture, secure secret handling, and test connection feedback.
- Added mocked backend tests for sandbox readiness, missing credential behavior, and approved-template enforcement.

No real credentials, SQL, SuiteQL, raw NetSuite query execution, or secret values are stored, logged, returned, or shown in the UI.
