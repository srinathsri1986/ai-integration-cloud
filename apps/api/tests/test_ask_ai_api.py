"""TDD tests for POST /api/v1/ai/ask — the universal Ask AI endpoint.

Contract:
- POST /api/v1/ai/ask accepts { question, pageContext? }
- Returns { question, intent, answer, action?, provider, model, thinkUsed }
- Intent values: CREATE_FLOW | SUGGEST_MAPPING | EXPLAIN_ERROR | GENERAL
- Action types:  SUGGEST_FLOW | OPEN_MAPPING | OPEN_ERROR_DEBUGGER | INFO
- Answer is always a non-empty human-readable string (>=10 chars)
- For CREATE_FLOW: action.type == "SUGGEST_FLOW" and action.payload has suggestedFlow
- For SUGGEST_MAPPING: action.type == "OPEN_MAPPING" with navigateTo
- Rejects blank / too-short / query-language questions (422)

Auth: The platform allows local-dev identity without a token in test environments
(same pattern as all other test files in this repo).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: endpoint exists and responds to valid questions
# ---------------------------------------------------------------------------

def test_ask_ai_endpoint_exists() -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": "create a flow to sync data between systems"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2: top-level response shape
# ---------------------------------------------------------------------------

def test_ask_ai_response_shape() -> None:
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "create a flow to sync NetSuite to Salesforce"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "question" in body
    assert "intent" in body
    assert "answer" in body
    assert "provider" in body
    assert "thinkUsed" in body
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) >= 10


# ---------------------------------------------------------------------------
# Test 3: CREATE_FLOW intent detected from NL flow prompts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "create a flow to sync NetSuite customers to Salesforce accounts every 15 minutes",
    "build an integration workflow to sync SAP vendors to Salesforce",
    "generate a flow that sends a Slack notification when a new invoice is created",
    "schedule a workflow to pull Oracle ERP data nightly",
])
def test_ask_ai_detects_create_flow_intent(question: str) -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": question})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "CREATE_FLOW"
    assert body["action"] is not None
    assert body["action"]["type"] == "SUGGEST_FLOW"
    assert body["action"]["payload"] is not None
    assert "suggestedFlow" in body["action"]["payload"]


# ---------------------------------------------------------------------------
# Test 4: SUGGEST_MAPPING intent detected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "how should I map fields from Salesforce Account to NetSuite Customer",
    "what field mappings do I need for SAP vendor to Salesforce",
    "suggest field mapping between source and target schema",
])
def test_ask_ai_detects_suggest_mapping_intent(question: str) -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": question})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "SUGGEST_MAPPING"
    assert body["action"] is not None
    assert body["action"]["type"] == "OPEN_MAPPING"
    assert body["action"]["navigateTo"] is not None


# ---------------------------------------------------------------------------
# Test 5: EXPLAIN_ERROR intent detected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "why did my NetSuite sync fail with a 400 error",
    "how do I fix the entityId missing error in my flow",
    "debug the failed workflow RUN-10491",
])
def test_ask_ai_detects_explain_error_intent(question: str) -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": question})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "EXPLAIN_ERROR"


# ---------------------------------------------------------------------------
# Test 6: GENERAL intent for platform / informational questions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "what connectors are available on this platform",
    "how does the approval center work",
    "what is the difference between mock and live mode",
])
def test_ask_ai_detects_general_intent(question: str) -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": question})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "GENERAL"
    assert len(body["answer"]) >= 10


# ---------------------------------------------------------------------------
# Test 7: question field is validated
# ---------------------------------------------------------------------------

def test_ask_ai_rejects_too_short_question() -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": "hi"})
    assert resp.status_code == 422


def test_ask_ai_rejects_blank_question() -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_ai_rejects_raw_query_language() -> None:
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "select * from customers where password is not null"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 8: pageContext is optional and accepted
# ---------------------------------------------------------------------------

def test_ask_ai_accepts_page_context() -> None:
    resp = client.post(
        "/api/v1/ai/ask",
        json={
            "question": "create a flow to sync Salesforce to HubSpot",
            "pageContext": "flows",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["question"] == "create a flow to sync Salesforce to HubSpot"


# ---------------------------------------------------------------------------
# Test 9: CREATE_FLOW action payload has required flow fields
# ---------------------------------------------------------------------------

def test_ask_ai_create_flow_payload_shape() -> None:
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "build a workflow to sync SAP vendors to Salesforce accounts daily"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "CREATE_FLOW"
    flow = body["action"]["payload"]["suggestedFlow"]
    assert "name" in flow
    assert "steps" in flow
    assert isinstance(flow["steps"], list)
    assert len(flow["steps"]) >= 1


# ---------------------------------------------------------------------------
# Test 10: provider info is always present
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Test 11: SUGGEST_MAPPING payload carries pre-fill context
# ---------------------------------------------------------------------------

def test_ask_ai_mapping_payload_has_context_keys() -> None:
    """action.payload must contain the 4 pre-fill keys for the mapping studio."""
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "Map SAP vendor fields to Salesforce Account"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "SUGGEST_MAPPING"
    payload = body["action"]["payload"]
    assert payload is not None
    for key in ("sourceSystemId", "sourceObjectId", "targetSystemId", "targetObjectId"):
        assert key in payload, f"Missing key: {key}"


@pytest.mark.parametrize("question,expected", [
    (
        "Map SAP vendor fields to Salesforce Account",
        {"sourceSystemId": "sap", "sourceObjectId": "sap-vendor",
         "targetSystemId": "salesforce", "targetObjectId": "salesforce-account"},
    ),
    (
        "Map NetSuite customers to Salesforce",
        {"sourceSystemId": "netsuite", "sourceObjectId": "netsuite-customer",
         "targetSystemId": "salesforce", "targetObjectId": "salesforce-account"},
    ),
    (
        "How should I map fields from NetSuite contacts to Salesforce contacts",
        {"sourceSystemId": "netsuite", "sourceObjectId": "netsuite-contact",
         "targetSystemId": "salesforce", "targetObjectId": "salesforce-contact"},
    ),
    (
        "Map NetSuite invoice fields to Salesforce opportunity",
        {"sourceSystemId": "netsuite", "sourceObjectId": "netsuite-invoice",
         "targetSystemId": "salesforce", "targetObjectId": "salesforce-opportunity"},
    ),
])
def test_ask_ai_mapping_payload_values(question: str, expected: dict) -> None:
    resp = client.post("/api/v1/ai/ask", json={"question": question})
    assert resp.status_code == 200
    payload = resp.json()["action"]["payload"]
    for key, val in expected.items():
        assert payload[key] == val, f"question={question!r}: {key} expected {val!r}, got {payload[key]!r}"


def test_ask_ai_mapping_payload_has_prompt() -> None:
    """action.payload must include a ready-made mappingPrompt for the studio textarea."""
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "Map SAP vendor fields to Salesforce Account"},
    )
    payload = resp.json()["action"]["payload"]
    assert "mappingPrompt" in payload
    assert len(payload["mappingPrompt"]) >= 10


def test_ask_ai_always_returns_provider_info() -> None:
    resp = client.post(
        "/api/v1/ai/ask",
        json={"question": "what connectors does this platform support"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] in ("mock", "ollama", "openai", "template")
    assert isinstance(body["thinkUsed"], bool)
