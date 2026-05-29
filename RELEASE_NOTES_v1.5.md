# Release Notes v1.5

## Persistent Audit and Flow History

- Added SQLAlchemy-backed persistence for local MVP audit and flow history.
- Added append-only `audit_logs` and `flow_runs` tables.
- Added database initialization during API startup.
- Added repository classes for audit events and flow runs.
- Persisted redacted audit entries before returning them through the audit API.
- Persisted mock flow run records after successful flow execution.
- Added audit log filters and pagination:
  - `requestId`
  - `intent`
  - `provider`
  - `success`
  - `limit`
  - `offset`
- Added flow run history endpoint with flow/status filters and pagination.
- Added indexed operational columns plus JSON/JSONB metadata for scalable governance queries.
- Added SQLite-backed test configuration so persistence tests do not require Docker.

Secrets remain redacted before persistence. No arbitrary SQL, SuiteQL, raw NetSuite access, or real credentials are exposed.
