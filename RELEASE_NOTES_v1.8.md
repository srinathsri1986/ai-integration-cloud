# Release Notes v1.8

## Visual Flow Canvas Shell

- Added a visual orchestration canvas workbench to the web app.
- Added a left-side node palette with governed trigger, connector, and approved action nodes.
- Added a central canvas that renders trigger, connector, approved action, and audit nodes.
- Added a right-side properties panel for flow ID, name, status, saved-flow preview, and validate/save.
- Added drag/drop from approved action palette into the draft flow.
- Saves visual draft flows through the existing governed `POST /api/v1/flows/definitions` endpoint.
- Preserves V1.7 guardrails: no raw SQL, no SuiteQL input, no arbitrary code execution, and no arbitrary runtime execution.

This is a repo-native visual canvas shell. React Flow dependency installation was blocked by the local package-store sandbox in this session, so a future dependency-enabled step can migrate the shell to `@xyflow/react`.
