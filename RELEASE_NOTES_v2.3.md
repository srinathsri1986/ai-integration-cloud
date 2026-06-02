# Release Notes v2.3

## Data Mapping Studio Lite

- Added `/mapping` as a dedicated Data Mapping Studio workspace.
- Added Data Mapping navigation for Integration Admin and Developer personas.
- Added a system-agnostic mock mapping catalog for NetSuite, Salesforce, Oracle Fusion, REST API payloads, and SFTP/CSV files.
- Added source and target object selectors.
- Added source and target field trays with field type, sample value, description, and required markers.
- Added click-to-map field matching.
- Added mapping grid with governed transformation choices:
  - Direct
  - Rename
  - Format date
  - Lookup placeholder
  - Constant placeholder
- Added required target field validation.
- Added source and target sample payload previews.

## Guardrails

- Mappings validate locally only in this release.
- No arbitrary code transformations were added.
- No SQL, SuiteQL, raw system access, credentials, or secrets were added.
- Backend persistence and AI-assisted mapping suggestions are planned follow-up milestones.
