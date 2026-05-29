# Release Notes v1.4

## Secrets and Runtime Hardening

- Added centralized secret masking and recursive redaction helpers.
- Added startup configuration validation for NetSuite and AI provider modes.
- Added safe runtime posture logging with readiness booleans instead of raw values.
- Added audit log redaction before entries are stored.
- Added tests for secret masking, redaction, runtime validation, and audit masking.
- Documented `.env.local` usage for local-only real values.
- Documented future Docker secret and vault integration direction.

Mock mode remains the default. Real credentials are not committed, logged, returned, or displayed.
