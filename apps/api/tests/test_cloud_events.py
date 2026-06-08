"""Tests for CloudEvents detection/parsing — Release 20.0.

Covers the standalone parser module (binary + structured content modes,
validation failures, never-raises guarantee) and an end-to-end integration
check that the inbound webhook receiver persists CloudEvents attributes onto
the delivery record when (and only when) the payload is a recognisable
CloudEvent — mirroring the shape an SAP BTP Event Mesh broker would emit.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import cloud_events
from app.services.audit_service import audit_service
from app.services.cloud_events import CloudEvent
from app.services.flow_service import flow_service
from app.services.mapping_definition_service import mapping_definition_service
from app.services.webhook_delivery_service import webhook_delivery_service

client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


# ---------------------------------------------------------------------------
# Headers shim — Starlette's Headers is case-insensitive; a plain dict isn't.
# The parser only requires `.get(name)`, so a tiny case-insensitive mapping
# is enough to exercise it without spinning up a request.
# ---------------------------------------------------------------------------


class _CIHeaders:
    def __init__(self, items: dict[str, str]) -> None:
        self._lower = {k.lower(): v for k, v in items.items()}

    def get(self, name: str):
        return self._lower.get(name.lower())


SPEC_SAMPLE = {
    "id": "evt-8f3a-001",
    "source": "/sap/btp/event-mesh/sales-order",
    "specversion": "1.0",
    "type": "sap.s4.beh.salesorder.v1.SalesOrder.Created.v1",
}


# ---------------------------------------------------------------------------
# Binary content mode
# ---------------------------------------------------------------------------


class TestBinaryContentMode:
    def test_parses_well_formed_ce_headers(self) -> None:
        headers = _CIHeaders({f"ce-{k}": v for k, v in SPEC_SAMPLE.items()})
        event = cloud_events.detect_and_parse(headers, b'{"orderId": "SO-1001"}', "application/json")
        assert event == CloudEvent(
            id=SPEC_SAMPLE["id"],
            source=SPEC_SAMPLE["source"],
            type=SPEC_SAMPLE["type"],
            spec_version="1.0",
        )

    def test_header_lookup_is_case_insensitive(self) -> None:
        headers = _CIHeaders({
            "CE-ID": SPEC_SAMPLE["id"],
            "Ce-Source": SPEC_SAMPLE["source"],
            "ce-SpecVersion": SPEC_SAMPLE["specversion"],
            "CE-TYPE": SPEC_SAMPLE["type"],
        })
        event = cloud_events.detect_and_parse(headers, b"{}", "application/json")
        assert event is not None
        assert event.id == SPEC_SAMPLE["id"]

    def test_missing_required_attribute_yields_none(self) -> None:
        partial = {k: v for k, v in SPEC_SAMPLE.items() if k != "type"}
        headers = _CIHeaders({f"ce-{k}": v for k, v in partial.items()})
        assert cloud_events.detect_and_parse(headers, b"{}", "application/json") is None

    def test_no_ce_headers_at_all_yields_none(self) -> None:
        headers = _CIHeaders({"Content-Type": "application/json"})
        assert cloud_events.detect_and_parse(headers, b'{"hello": "world"}', "application/json") is None

    def test_empty_attribute_value_yields_none(self) -> None:
        attrs = dict(SPEC_SAMPLE)
        attrs["id"] = "   "
        headers = _CIHeaders({f"ce-{k}": v for k, v in attrs.items()})
        assert cloud_events.detect_and_parse(headers, b"{}", "application/json") is None


# ---------------------------------------------------------------------------
# Structured content mode
# ---------------------------------------------------------------------------


class TestStructuredContentMode:
    def test_parses_well_formed_envelope(self) -> None:
        envelope = {**SPEC_SAMPLE, "data": {"orderId": "SO-1001"}}
        body = json.dumps(envelope).encode("utf-8")
        headers = _CIHeaders({})  # no ce-* headers — structured mode carries everything in the body
        event = cloud_events.detect_and_parse(headers, body, "application/cloudevents+json")
        assert event == CloudEvent(
            id=SPEC_SAMPLE["id"],
            source=SPEC_SAMPLE["source"],
            type=SPEC_SAMPLE["type"],
            spec_version="1.0",
        )

    def test_content_type_with_charset_suffix_still_detected(self) -> None:
        envelope = {**SPEC_SAMPLE, "data": {}}
        body = json.dumps(envelope).encode("utf-8")
        headers = _CIHeaders({})
        event = cloud_events.detect_and_parse(
            headers, body, "application/cloudevents+json; charset=utf-8"
        )
        assert event is not None

    def test_malformed_json_body_yields_none_not_raise(self) -> None:
        headers = _CIHeaders({})
        event = cloud_events.detect_and_parse(headers, b"not-json{{{", "application/cloudevents+json")
        assert event is None

    def test_non_object_json_body_yields_none(self) -> None:
        headers = _CIHeaders({})
        body = json.dumps([1, 2, 3]).encode("utf-8")
        assert cloud_events.detect_and_parse(headers, body, "application/cloudevents+json") is None

    def test_missing_required_attribute_in_envelope_yields_none(self) -> None:
        envelope = {k: v for k, v in SPEC_SAMPLE.items() if k != "source"}
        body = json.dumps(envelope).encode("utf-8")
        headers = _CIHeaders({})
        assert cloud_events.detect_and_parse(headers, body, "application/cloudevents+json") is None


# ---------------------------------------------------------------------------
# Non-CloudEvents traffic — the overwhelming majority of inbound webhooks
# ---------------------------------------------------------------------------


class TestNonCloudEventsTraffic:
    def test_plain_json_webhook_is_not_mistaken_for_cloudevent(self) -> None:
        headers = _CIHeaders({"Content-Type": "application/json"})
        body = b'{"event": "ticket.created", "id": "T-1"}'
        assert cloud_events.detect_and_parse(headers, body, "application/json") is None

    def test_detect_and_parse_never_raises_on_garbage_input(self) -> None:
        headers = _CIHeaders({"ce-id": "x", "ce-source": "y", "ce-specversion": "1.0"})  # missing ce-type
        # Should not raise even though the envelope is incomplete
        assert cloud_events.detect_and_parse(headers, b"\xff\xfe not utf8", None) is None


class TestCloudEventDataclass:
    def test_as_delivery_attributes_shape(self) -> None:
        event = CloudEvent(id="evt-1", source="/svc/x", type="x.created", spec_version="1.0")
        assert event.as_delivery_attributes() == {
            "event_id": "evt-1",
            "event_source": "/svc/x",
            "event_type": "x.created",
            "event_spec_version": "1.0",
        }


# ---------------------------------------------------------------------------
# End-to-end: inbound webhook receiver persists CloudEvents attributes
# ---------------------------------------------------------------------------


def _create_published_webhook_flow(flow_id: str) -> str:
    """Helper: create + publish a webhook-type flow, return its server-generated webhook secret.

    The flow service generates its own random `webhook_secret` on creation
    (see flow_service.upsert_flow — `secrets.token_urlsafe(32)`); any client-
    supplied `webhookSecret` is ignored. Tests must read the real secret back
    off the created flow to compute a valid HMAC signature.
    """
    payload = {
        "flowId": flow_id,
        "name": f"CloudEvents test flow {flow_id}",
        "description": "Webhook-triggered flow for CloudEvents receiver tests.",
        "sourceConnector": "netsuite",
        "targetModule": "cfo_dashboard",
        "status": "draft",
        "triggerType": "webhook",
        "steps": [
            {
                "id": "step-1",
                "name": "CFO Summary",
                "description": "Load CFO dashboard summary.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }
    r = client.post("/api/v1/flows/definitions", json=payload)
    assert r.status_code == 200, r.text
    secret = r.json()["webhookSecret"]
    for action in ["submit_for_approval", "approve", "publish"]:
        client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
    return secret


def _signed_post(flow_id: str, body: bytes, secret: str, extra_headers: dict[str, str]):
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={signature}", **extra_headers}
    return client.post(f"/api/v1/webhooks/{flow_id}", content=body, headers=headers)


class TestReceiverPersistsCloudEventsAttributes:
    def test_binary_mode_cloudevent_is_persisted_on_delivery(self) -> None:
        flow_id = "ce-binary-flow"
        secret = _create_published_webhook_flow(flow_id)

        body = json.dumps({"orderId": "SO-2002", "amount": 4200}).encode("utf-8")
        resp = _signed_post(
            flow_id,
            body,
            secret,
            extra_headers={
                "Content-Type": "application/json",
                "ce-id": "evt-bin-001",
                "ce-source": "/sap/btp/event-mesh/sales-order",
                "ce-specversion": "1.0",
                "ce-type": "sap.s4.beh.salesorder.v1.SalesOrder.Created.v1",
            },
        )
        assert resp.status_code == 202, resp.text

        deliveries = webhook_delivery_service.list_for_flow(flow_id, limit=5)
        assert len(deliveries) == 1
        d = deliveries[0]
        assert d.event_id == "evt-bin-001"
        assert d.event_source == "/sap/btp/event-mesh/sales-order"
        assert d.event_type == "sap.s4.beh.salesorder.v1.SalesOrder.Created.v1"
        assert d.event_spec_version == "1.0"

    def test_structured_mode_cloudevent_is_persisted_on_delivery(self) -> None:
        flow_id = "ce-structured-flow"
        secret = _create_published_webhook_flow(flow_id)

        envelope = {
            "id": "evt-struct-002",
            "source": "/sap/btp/event-mesh/purchase-order",
            "specversion": "1.0",
            "type": "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Changed.v1",
            "data": {"poNumber": "PO-3003"},
        }
        body = json.dumps(envelope).encode("utf-8")
        resp = _signed_post(
            flow_id, body, secret, extra_headers={"Content-Type": "application/cloudevents+json"}
        )
        assert resp.status_code == 202, resp.text

        deliveries = webhook_delivery_service.list_for_flow(flow_id, limit=5)
        assert len(deliveries) == 1
        d = deliveries[0]
        assert d.event_id == "evt-struct-002"
        assert d.event_type == "sap.s4.beh.purchaseorder.v1.PurchaseOrder.Changed.v1"

    def test_non_cloudevent_webhook_leaves_event_columns_null(self) -> None:
        flow_id = "ce-plain-flow"
        secret = _create_published_webhook_flow(flow_id)

        body = json.dumps({"hello": "world"}).encode("utf-8")
        resp = _signed_post(flow_id, body, secret, extra_headers={"Content-Type": "application/json"})
        assert resp.status_code == 202, resp.text

        deliveries = webhook_delivery_service.list_for_flow(flow_id, limit=5)
        assert len(deliveries) == 1
        d = deliveries[0]
        assert d.event_id is None
        assert d.event_source is None
        assert d.event_type is None
        assert d.event_spec_version is None
