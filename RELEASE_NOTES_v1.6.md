# Release Notes v1.6

## Placeholder Authentication and RBAC

- Added local placeholder JWT token generation and validation.
- Added `/api/v1/auth/login` and `/api/v1/auth/me`.
- Added MVP roles:
  - `CFO`
  - `Finance Controller`
  - `Integration Admin`
  - `Viewer`
  - `Developer`
- Added role permission checks for connector, audit, flow, CFO, and orchestrator endpoints.
- Added backend tests for token generation, current user lookup, invalid token rejection, and role denial.
- Added a local role selector to the web app for browser-triggered actions.
- Extended shared TypeScript schemas with auth user and login response types.

This is local placeholder auth only. Production SSO/OIDC/SAML, tenant-aware policies, and secure session handling remain future work.
