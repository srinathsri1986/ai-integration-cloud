"""CloudEvents envelope detection & parsing — Release 20.0.

Implements best-effort, spec-aligned parsing of the CNCF CloudEvents
(https://cloudevents.io) envelope as emitted by event brokers such as SAP
BTP Event Mesh, Azure Event Grid, Google Eventarc, etc. Two content modes
are supported per the spec's HTTP Protocol Binding:

Binary content mode
-------------------
Context attributes travel as HTTP headers prefixed ``ce-`` (e.g. ``ce-id``,
``ce-source``, ``ce-type``, ``ce-specversion``); the request body is the
event `data` verbatim, with `Content-Type` describing its media type.

Structured content mode
-----------------------
Everything — context attributes AND data — travels in a single JSON envelope
whose `Content-Type` is ``application/cloudevents+json`` (or a
``+json``-suffixed structured variant per the spec).

This module never raises on malformed/absent CloudEvents input — detection
and parsing are both best-effort and return ``None`` so the existing R12
webhook receiver pipeline continues to function unchanged for non-CloudEvents
callers (the vast majority of inbound webhook traffic). Parsing failures are
logged at debug level only; nothing here ever surfaces a raw parse error to
the client (compliance: no raw error traces to clients).

Only the four REQUIRED context attributes defined by the CloudEvents v1.0
spec are extracted and persisted: ``id``, ``source``, ``specversion``, and
``type``. Optional/extension attributes are intentionally not persisted —
keeping the audit surface minimal and avoiding any risk of incidentally
capturing PII that a producer might place in extension attributes.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_ATTRS = ("id", "source", "specversion", "type")

# Structured mode is signalled by a Content-Type that is exactly
# "application/cloudevents+json" or carries a "+json" structured suffix per
# the CloudEvents HTTP Protocol Binding (e.g. "application/cloudevents-batch+json").
_STRUCTURED_CONTENT_TYPE_PREFIX = "application/cloudevents"


@dataclass(frozen=True)
class CloudEvent:
    """The subset of a parsed CloudEvents envelope this platform tracks.

    Only the four REQUIRED v1.0 context attributes are modelled — see module
    docstring for why extension/optional attributes are deliberately omitted.
    """

    id: str
    source: str
    type: str
    spec_version: str

    def as_delivery_attributes(self) -> dict[str, str]:
        """Shape for persistence on a WebhookDeliveryRecord (snake_case keys)."""
        return {
            "event_id": self.id,
            "event_source": self.source,
            "event_type": self.type,
            "event_spec_version": self.spec_version,
        }


def detect_and_parse(headers: Any, body: bytes, content_type: str | None) -> CloudEvent | None:
    """Best-effort detect + parse a CloudEvent from an inbound HTTP request.

    Tries structured content mode first (it's unambiguous — a distinct
    Content-Type), then binary content mode (presence of ``ce-`` headers).
    Returns ``None`` — never raises — if the request doesn't look like a
    CloudEvent or the envelope is malformed; callers should treat that as
    "not a CloudEvent" and continue normal webhook processing.
    """
    content_type = (content_type or "").split(";")[0].strip().lower()

    if content_type.startswith(_STRUCTURED_CONTENT_TYPE_PREFIX) and content_type.endswith("+json"):
        event = _parse_structured(body)
        if event is not None:
            return event

    return _parse_binary(headers)


# ── Structured content mode ──────────────────────────────────────────────────

def _parse_structured(body: bytes) -> CloudEvent | None:
    """Parse a `Content-Type: application/cloudevents+json` JSON envelope.

    All context attributes (including `data`) live in one JSON object —
    https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md
    """
    try:
        envelope = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        logger.debug("CloudEvents structured-mode parse: body is not valid JSON: %s", exc)
        return None

    if not isinstance(envelope, dict):
        logger.debug("CloudEvents structured-mode parse: envelope is not a JSON object.")
        return None

    return _build_event(envelope, mode="structured")


# ── Binary content mode ───────────────────────────────────────────────────────

def _parse_binary(headers: Any) -> CloudEvent | None:
    """Parse `ce-*` HTTP headers per the CloudEvents HTTP Protocol Binding.

    https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/bindings/http-protocol-binding.md#31-binary-content-mode

    `headers` may be any mapping-like object exposing `.get(name)` with
    case-insensitive lookup (e.g. Starlette's `Headers`) or a plain dict.
    """
    attrs: dict[str, str] = {}
    for attr in _REQUIRED_ATTRS:
        value = _header_get(headers, f"ce-{attr}")
        if value is not None:
            attrs[attr] = value

    if not attrs:
        # No ce-* headers at all — not a binary-mode CloudEvent. Common case;
        # not worth logging at debug level for every plain webhook delivery.
        return None

    return _build_event(attrs, mode="binary")


def _header_get(headers: Any, name: str) -> str | None:
    try:
        value = headers.get(name)
    except AttributeError:
        return None
    if value is None:
        return None
    return str(value).strip() or None


# ── Shared validation ─────────────────────────────────────────────────────────

def _build_event(attrs: dict[str, Any], mode: str) -> CloudEvent | None:
    """Validate that all REQUIRED v1.0 attributes are present and non-empty strings."""
    values: dict[str, str] = {}
    for attr in _REQUIRED_ATTRS:
        raw = attrs.get(attr)
        if raw is None:
            logger.debug("CloudEvents %s-mode parse: missing required attribute '%s'.", mode, attr)
            return None
        text = str(raw).strip()
        if not text:
            logger.debug("CloudEvents %s-mode parse: required attribute '%s' is empty.", mode, attr)
            return None
        values[attr] = text

    if values["specversion"] not in ("1.0",):
        # Be permissive about future spec versions — log but still surface the
        # event rather than silently dropping useful audit context. The CloudEvents
        # spec guarantees the four REQUIRED attributes remain stable across 1.x.
        logger.debug(
            "CloudEvents %s-mode parse: unrecognised specversion '%s' — accepting anyway.",
            mode,
            values["specversion"],
        )

    return CloudEvent(
        id=values["id"],
        source=values["source"],
        type=values["type"],
        spec_version=values["specversion"],
    )
