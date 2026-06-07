"""Field mapping execution engine — R18a.

Applies a list of InlineFieldMapping rows to transform a source payload dict
into a target payload dict.

Design constraints:
- No eval(), exec(), or compile() — all transforms are a closed set of named
  operations defined in this file.
- Dot-path access is bounded by _MAX_DEPTH to prevent stack exhaustion.
- Type coercions are best-effort and silent on failure (return None).
- This function is intentionally pure — no DB or network calls.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.models.custom_endpoint import InlineFieldMapping, MappingTransformType

logger = logging.getLogger(__name__)

_MAX_DEPTH = 20  # max dot-path segments


# ---------------------------------------------------------------------------
# Dot-path helpers
# ---------------------------------------------------------------------------

def _deep_get(obj: Any, path: str) -> Any:
    """Return value at *path* from *obj* using dot notation.
    Returns None if any intermediate key is missing.
    """
    parts = path.split(".", _MAX_DEPTH)
    cur: Any = obj
    for part in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _deep_set(obj: dict, path: str, value: Any) -> None:
    """Set value at *path* in *obj* using dot notation, creating nested dicts as needed."""
    parts = path.split(".", _MAX_DEPTH)
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


# ---------------------------------------------------------------------------
# Transform implementations — closed set, no arbitrary code
# ---------------------------------------------------------------------------

def _transform(value: Any, transform: MappingTransformType) -> Any:
    if value is None:
        return None

    if transform == "direct":
        return value

    if transform == "uppercase":
        return str(value).upper() if isinstance(value, str) else str(value).upper()

    if transform == "lowercase":
        return str(value).lower() if isinstance(value, str) else str(value).lower()

    if transform == "to_string":
        return str(value)

    if transform == "to_number":
        try:
            s = str(value).strip().replace(",", "")
            return float(s) if "." in s else int(s)
        except (ValueError, TypeError):
            return None

    if transform == "format_date":
        return _normalise_date(value)

    # Unknown transform — pass through (forward-compatible)
    logger.warning("Unknown mapping transform '%s' — passing value through.", transform)
    return value


def _normalise_date(value: Any) -> str | None:
    """Normalise a date-like value to ISO 8601 (YYYY-MM-DD).
    Returns None if value is not parseable.  Never raises.
    """
    if value is None:
        return None
    s = str(value).strip()
    # Already ISO 8601
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    # Try common formats
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y%m%d", "%d-%m-%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s[:20], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try epoch ms / epoch s
    try:
        epoch = int(s)
        if epoch > 1e10:
            epoch //= 1000  # ms → s
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        pass
    return None


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

class MappingWarning(Exception):
    """Raised (and caught) to collect non-fatal warnings without stopping execution."""


def apply_mappings(
    source: dict[str, Any],
    mappings: list[InlineFieldMapping],
) -> tuple[dict[str, Any], list[str]]:
    """Transform *source* into a target dict by applying *mappings*.

    Returns:
        (target_dict, warnings)

    Warnings are non-fatal.  Missing optional source fields are silently
    skipped; required fields generate a warning but execution continues.
    """
    target: dict[str, Any] = {}
    warnings: list[str] = []

    for mapping in mappings:
        raw_value = _deep_get(source, mapping.source_field)

        if raw_value is None:
            warnings.append(
                f"Source field '{mapping.source_field}' not found in payload "
                f"(or its value is null) — target field '{mapping.target_field}' will be null."
            )

        try:
            transformed = _transform(raw_value, mapping.transform)
        except Exception as exc:
            warnings.append(
                f"Transform '{mapping.transform}' on '{mapping.source_field}' failed: {exc} "
                f"— field will be null."
            )
            transformed = None

        _deep_set(target, mapping.target_field, transformed)

    return target, warnings


mapping_engine = object()  # sentinel — callers import apply_mappings directly
