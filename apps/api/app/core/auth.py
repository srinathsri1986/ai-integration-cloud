import base64
import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, Header, HTTPException, status
import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.models.auth import AuthUser, UserRole

logger = logging.getLogger(__name__)

_BCRYPT_ROUNDS = 12


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

# --- Password helpers ---

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]  # bcrypt hard limit
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT helpers ---

def create_access_token(user_id: int, email: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise JWTError("Not an access token")
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc


def decode_refresh_token(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        return int(payload["sub"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.") from exc


# --- Current user extraction (accepts real JWT or placeholder for dev/tests) ---

def get_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> AuthUser:
    token: str | None = None

    if authorization:
        scheme, _, token_value = authorization.partition(" ")
        if scheme.lower() == "bearer" and token_value:
            token = token_value

    if token is None and access_token:
        token = access_token

    if token is None:
        # Dev fallback: unauthenticated request gets a default local-dev identity
        return AuthUser(userId="local-dev-user", email="local-dev@example.com", role="Integration Admin")

    # Try real JWT first
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        if payload.get("type") == "access":
            return AuthUser(
                userId=payload["sub"],
                email=payload["email"],
                role=payload["role"],
            )
    except JWTError:
        pass

    # Fall back to legacy placeholder token (for existing tests)
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
            detail="Invalid or expired token.",
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


# --- Legacy placeholder (kept for backward compat with existing tests) ---

def create_placeholder_token(user: AuthUser) -> str:
    payload = user.model_dump(by_alias=True)
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def _sign(payload: str) -> str:
    secret = get_settings().placeholder_jwt_secret.encode("utf-8")
    digest = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
