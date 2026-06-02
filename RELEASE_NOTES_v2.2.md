# Release Notes v2.2

## SaaS-Ready System-Agnostic Integration Workbench

- Reframed the frontend from NetSuite-first to AI Integration Cloud, with NetSuite CFO Intelligence as the first solution template.
- Added a visual Integration Workbench to `/flows`.
- Added connector marketplace-style system cards for NetSuite, Salesforce, Oracle Fusion, ServiceNow, PostgreSQL, REST API, SFTP/CSV, and platform-native actions.
- Added a guided no-code integration path: start, choose system, pick data, match fields, transform, review, and publish.
- Added a visual source-to-target pipeline preview.
- Added SaaS workspace posture signals for tenant, environment, plan, and governance.
- Updated platform navigation language from connector/flow-specific wording toward Systems and Integration Studio.

## Guardrails

- No real credentials or secrets were added.
- No arbitrary SQL, SuiteQL, or raw system access was added.
- Existing approval/publish workflow and fail-closed custom runtime behavior remain intact.
- Data Mapping Studio remains the recommended next milestone.
