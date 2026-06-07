"""ConnectorCredentialService — encrypted OAuth token storage.

Tokens are encrypted with Fernet (AES-128 CBC + HMAC-SHA256) before being
persisted to connector_config_records.config_json.

Production path: replace the DB store with AWS Secrets Manager calls and
set CONNECTOR_ENCRYPTION_KEY from KMS. The interface is identical.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class ConnectorCredentialService:
    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _get_fernet(self):  # type: ignore[return]
        """Return a Fernet instance if a key is configured, else None."""
        key = get_settings().connector_encryption_key
        if not key:
            return None
        try:
            from cryptography.fernet import Fernet
            return Fernet(key.encode())
        except Exception as exc:
            logger.warning("Invalid CONNECTOR_ENCRYPTION_KEY — tokens will not be encrypted: %s", exc)
            return None

    def _encrypt(self, data: dict) -> str:
        """Encrypt *data* to a base64 Fernet token string."""
        raw = json.dumps(data).encode()
        f = self._get_fernet()
        if f:
            return f.encrypt(raw).decode()
        # No key: store as base64-encoded JSON (NOT secure — dev only)
        import base64
        return base64.b64encode(raw).decode()

    def _decrypt(self, ciphertext: str) -> dict:
        """Decrypt a Fernet token string back to a dict."""
        f = self._get_fernet()
        if f:
            from cryptography.fernet import InvalidToken
            try:
                return json.loads(f.decrypt(ciphertext.encode()))
            except InvalidToken:
                raise ValueError("Token decryption failed — the encryption key may have rotated.")
        # No key: decode from base64
        import base64
        return json.loads(base64.b64decode(ciphertext.encode()))

    # ------------------------------------------------------------------
    # DB helpers (manual upsert — works correctly with NULL tenant_id)
    # ------------------------------------------------------------------

    def _is_postgres(self, session) -> bool:
        """Return True if the active DB is PostgreSQL (not SQLite)."""
        return session.bind is not None and "postgresql" in str(
            session.bind.dialect.name
        )

    def _config_cast(self, session, param: str) -> str:
        """SQL fragment for storing config_json — CAST only on PostgreSQL."""
        if self._is_postgres(session):
            return f"CAST(:{param} AS jsonb)"
        return f":{param}"

    def _upsert_config(
        self,
        connector_id: str,
        tenant_id: int | None,
        config_json: dict,
        status: str,
        mode: str,
    ) -> None:
        from datetime import UTC, datetime as _dt
        with SessionLocal() as session:
            row = session.execute(
                text(
                    "SELECT id FROM connector_config_records "
                    "WHERE connector_id = :cid AND tenant_id IS NOT DISTINCT FROM :tid"
                ),
                {"cid": connector_id, "tid": tenant_id},
            ).fetchone()
            config_cast = self._config_cast(session, "config")
            if row:
                session.execute(
                    text(
                        f"UPDATE connector_config_records "
                        f"SET config_json = {config_cast}, status = :status, "
                        f"mode = :mode, updated_at = :now "
                        f"WHERE id = :id"
                    ),
                    {
                        "config": json.dumps(config_json),
                        "status": status,
                        "mode": mode,
                        "id": row[0],
                        "now": _dt.now(UTC).isoformat(),
                    },
                )
            else:
                now_iso = _dt.now(UTC).isoformat()
                session.execute(
                    text(
                        f"INSERT INTO connector_config_records "
                        f"(connector_id, tenant_id, config_json, status, mode, created_at, updated_at) "
                        f"VALUES (:cid, :tid, {config_cast}, :status, :mode, :now, :now)"
                    ),
                    {
                        "cid": connector_id,
                        "tid": tenant_id,
                        "config": json.dumps(config_json),
                        "status": status,
                        "mode": mode,
                        "now": now_iso,
                    },
                )
            session.commit()

    def _fetch_config(
        self, connector_id: str, tenant_id: int | None
    ) -> dict | None:
        with SessionLocal() as session:
            row = session.execute(
                text(
                    "SELECT config_json, status, mode FROM connector_config_records "
                    "WHERE connector_id = :cid AND tenant_id IS NOT DISTINCT FROM :tid"
                ),
                {"cid": connector_id, "tid": tenant_id},
            ).fetchone()
        if not row:
            return None
        raw = row[0]
        if isinstance(raw, dict):
            config = raw
        elif isinstance(raw, (str, bytes, bytearray)):
            config = json.loads(raw)
        else:
            # SQLite NUMERIC affinity can coerce small JSON values (e.g. "0", "{}") to numbers.
            # Stringify and re-parse so callers always get a dict.
            config = json.loads(str(raw)) if raw is not None else {}
        return {"config": config, "status": row[1], "mode": row[2]}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_oauth_token(
        self,
        connector_id: str,
        token_data: dict[str, Any],
        tenant_id: int | None = None,
    ) -> None:
        """Encrypt *token_data* and persist to the connector config table.

        *token_data* is the raw response from the OAuth provider (e.g. Slack's
        ``oauth.v2.access`` response).  It is encrypted before hitting the DB.
        """
        encrypted = self._encrypt(token_data)
        workspace = (
            token_data.get("team", {}).get("name", "")
            if isinstance(token_data.get("team"), dict)
            else token_data.get("team_name", "")
        )
        config_json = {
            "encrypted_token": encrypted,
            "workspace": workspace,
            "authed_user": token_data.get("authed_user", {}).get("id", ""),
        }
        self._upsert_config(connector_id, tenant_id, config_json, status="configured", mode="live")
        logger.info("Stored OAuth token for connector=%s tenant=%s workspace=%s", connector_id, tenant_id, workspace)

    def get_oauth_token(
        self, connector_id: str, tenant_id: int | None = None
    ) -> dict[str, Any] | None:
        """Return the decrypted token data dict, or *None* if not configured."""
        record = self._fetch_config(connector_id, tenant_id)
        if not record or record["mode"] != "live":
            return None
        config = record["config"]
        if "encrypted_token" not in config:
            return None
        try:
            return self._decrypt(config["encrypted_token"])
        except Exception as exc:
            logger.error("Failed to decrypt token for connector=%s: %s", connector_id, exc)
            return None

    def revoke_token(
        self, connector_id: str, tenant_id: int | None = None
    ) -> None:
        """Remove OAuth credentials and reset connector to mock mode."""
        self._upsert_config(connector_id, tenant_id, {}, status="not_configured", mode="mock")
        logger.info("Revoked OAuth token for connector=%s tenant=%s", connector_id, tenant_id)

    def get_connector_mode(
        self, connector_id: str, tenant_id: int | None = None
    ) -> str:
        """Return ``"live"`` or ``"mock"`` for the given connector."""
        record = self._fetch_config(connector_id, tenant_id)
        return record["mode"] if record else "mock"

    def get_connector_status(
        self, connector_id: str, tenant_id: int | None = None
    ) -> str:
        """Return the status string stored for a connector (e.g. ``"configured"``)."""
        record = self._fetch_config(connector_id, tenant_id)
        return record["status"] if record else "not_configured"

    def store_credentials(
        self,
        connector_id: str,
        creds: dict[str, Any],
        tenant_id: int | None = None,
        extra_meta: dict | None = None,
    ) -> None:
        """Encrypt *creds* and persist for any connector type (API key, connection string, etc.).

        The credential dict is encrypted and stored under ``encrypted_credentials``.
        ``extra_meta`` is stored in plaintext alongside it (display name, instance URL, etc.).
        """
        encrypted = self._encrypt(creds)
        config_json: dict[str, Any] = {"encrypted_credentials": encrypted}
        if extra_meta:
            config_json.update(extra_meta)
        self._upsert_config(connector_id, tenant_id, config_json, status="configured", mode="live")
        logger.info(
            "Stored credentials for connector=%s tenant=%s", connector_id, tenant_id
        )

    def get_credentials(
        self, connector_id: str, tenant_id: int | None = None
    ) -> dict[str, Any] | None:
        """Return the decrypted credentials dict, or *None* if not configured."""
        record = self._fetch_config(connector_id, tenant_id)
        if not record or record["mode"] != "live":
            return None
        config = record["config"]
        if "encrypted_credentials" not in config:
            return None
        try:
            return self._decrypt(config["encrypted_credentials"])
        except Exception as exc:
            logger.error(
                "Failed to decrypt credentials for connector=%s: %s", connector_id, exc
            )
            return None

    def all_connector_modes(self, tenant_id: int | None = None) -> dict[str, str]:
        """Return connector_id → mode for all connectors visible to *tenant_id*.

        Resolution order (tenant-first, global fallback):
        1. Tenant-specific record  (tenant_id = <tenant_id>)
        2. Global default record   (tenant_id IS NULL)

        This lets platform admins set global defaults that any tenant can
        override with their own credentials.
        """
        with SessionLocal() as session:
            # Fetch both global defaults and tenant-specific overrides in one query.
            # COALESCE priority: tenant row wins over global row.
            if tenant_id is not None:
                rows = session.execute(
                    text(
                        "SELECT connector_id, mode FROM connector_config_records "
                        "WHERE tenant_id = :tid OR tenant_id IS NULL"
                    ),
                    {"tid": tenant_id},
                ).fetchall()
                # Build result: process global rows first, then tenant rows override them.
                result: dict[str, str] = {}
                global_rows: dict[str, str] = {}
                tenant_rows: dict[str, str] = {}
                for row in rows:
                    # We need to distinguish global vs tenant rows — re-query with flag
                    pass
                # Simpler: two queries (still O(n) on a tiny table of 8 connectors)
                global_result = session.execute(
                    text(
                        "SELECT connector_id, mode FROM connector_config_records "
                        "WHERE tenant_id IS NULL"
                    )
                ).fetchall()
                tenant_result = session.execute(
                    text(
                        "SELECT connector_id, mode FROM connector_config_records "
                        "WHERE tenant_id = :tid"
                    ),
                    {"tid": tenant_id},
                ).fetchall()
                result = {row[0]: row[1] for row in global_result}
                result.update({row[0]: row[1] for row in tenant_result})  # tenant overrides global
                return result
            else:
                rows = session.execute(
                    text(
                        "SELECT connector_id, mode FROM connector_config_records "
                        "WHERE tenant_id IS NULL"
                    )
                ).fetchall()
                return {row[0]: row[1] for row in rows}


credential_service = ConnectorCredentialService()
