from collections.abc import Mapping, Sequence
import re
from typing import Any


SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "client_secret",
    "consumer_key",
    "consumer_secret",
    "password",
    "secret",
    "token",
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def mask_secret(value: str | None) -> str | None:
    if value is None:
        return None

    if value == "":
        return ""

    if len(value) <= 4:
        return "****"

    return f"{value[:2]}****{value[-2:]}"


def redact_text(value: str) -> str:
    patterns = [
        r"(?i)\b(api[_ -]?key|password|secret|token|consumer[_ -]?secret)\s*[:=]\s*([^\s,;]+)",
        r"(?i)\b(bearer)\s+([A-Za-z0-9._\-]+)",
    ]
    redacted = value

    for pattern in patterns:
        redacted = re.sub(pattern, lambda match: f"{match.group(1)}=****", redacted)

    return redacted


def redact_mapping(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: mask_secret(str(item)) if is_sensitive_key(str(key)) else redact_mapping(item)
            for key, item in value.items()
        }

    if isinstance(value, str):
        return redact_text(value)

    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [redact_mapping(item) for item in value]

    return value
