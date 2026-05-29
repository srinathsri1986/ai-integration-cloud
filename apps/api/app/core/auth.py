import base64
import hashlib
import hmac
import json
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.models.auth import AuthUser, UserRole


ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    "CFO": {"cfo:read", "orchestrator:query"},
    "Finance Controller": {"cfo:read", "orchestrator:query"},
    "Integration Admin": {
        "audit:read",
        "cfo:read",
        "connector:admin",
        "flow:read",
        "flow:run",
        "orchestrator:query",
    },
    "Viewer": {"audit:read", "cfo:read", "flow:read"},
    "Developer": {
        "audit:read",
        "cfo:read",
        "connector:admin",
        "flow:read",
        "flow:run",
        "orchestrator:query",
    },
}


def create_placeholder_token(user: AuthUser) -> str:
    payload = user.model_dump(by_alias=True)
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization:
        return AuthUser(userId="local-dev-user", email="local-dev@example.com", role="Integration Admin")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid placeholder auth header.",
        )

    try:
        payload_part, signature = token.rsplit(".", 1)
        expected_signature = _sign(payload_part)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("invalid signature")

        payload = json.loads(_base64url_decode(payload_part))
        return AuthUser.model_validate(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid placeholder token.",
        ) from exc


def require_permissions(*permissions: str) -> Callable[[AuthUser], AuthUser]:
    def dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        allowed = ROLE_PERMISSIONS[user.role]
        if not set(permissions).issubset(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role is not allowed to perform this action.",
            )

        return user

    return dependency


def _sign(payload: str) -> str:
    secret = get_settings().placeholder_jwt_secret.encode("utf-8")
    digest = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
