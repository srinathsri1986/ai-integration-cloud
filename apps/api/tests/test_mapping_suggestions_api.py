from fastapi.testclient import TestClient

from app.main import app
from app.models.mapping import MappingSuggestionRequest
from app.services.audit_service import audit_service
from app.services.mapping_suggestion_service import LiveAIRequiredError, MappingSuggestionService


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()


def test_mapping_suggestions_generate_valid_draft_matches_and_audit_log() -> None:
    response = client.post(
        "/api/v1/mappings/suggestions",
        json={
            "prompt": (
                "Map NetSuite project customer, budget, due date, and owner fields "
                "into Salesforce opportunity fields."
            ),
            "sourceObjectId": "netsuite-project",
            "targetObjectId": "salesforce-opportunity",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sourceObjectId"] == "netsuite-project"
    assert body["targetObjectId"] == "salesforce-opportunity"
    assert body["suggestions"]
    assert {
        (suggestion["sourceField"], suggestion["targetField"])
        for suggestion in body["suggestions"]
    } >= {
        ("customer_name", "AccountName"),
        ("budget_amount", "Amount"),
        ("due_date", "CloseDate"),
    }
    assert all(0 <= suggestion["confidence"] <= 1 for suggestion in body["suggestions"])
    assert "sql" not in str(body).lower()
    assert "suiteql" not in str(body).lower()

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "MAPPING_SUGGESTION"
    assert logs[0]["endpointCalled"] == "/api/v1/mappings/suggestions"
    assert logs[0]["toolsUsed"] == ["mapping.suggest"]
    assert logs[0]["success"] is True


def test_mapping_suggestions_reject_unknown_objects() -> None:
    response = client.post(
        "/api/v1/mappings/suggestions",
        json={
            "prompt": "Map source fields to target fields.",
            "sourceObjectId": "unknown-source",
            "targetObjectId": "salesforce-opportunity",
        },
    )

    assert response.status_code == 404


def test_mapping_suggestions_fallback_when_model_invents_fields() -> None:
    class InvalidMappingSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_mapping_suggestion(self, context: dict):
            return type(
                "InvalidSuggestion",
                (),
                {
                    "suggestions": [
                        {
                            "sourceField": "invented_raw_field",
                            "targetField": "AccountName",
                            "transform": "direct",
                            "confidence": 0.99,
                            "rationale": "Invalid model output for test coverage.",
                        }
                    ],
                    "model_name": "fake-local-model",
                    "model_call_attempted": True,
                    "model_call_succeeded": True,
                    "provider_name": "ollama",
                },
            )()

    service = MappingSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=InvalidMappingSuggestionProvider(),
    )

    response = service.suggest(
        MappingSuggestionRequest(
            prompt="Map NetSuite project fields into Salesforce opportunity fields.",
            sourceObjectId="netsuite-project",
            targetObjectId="salesforce-opportunity",
        )
    )

    assert response.suggestion_fallback_used is True
    assert response.suggestion_provider == "ollama"
    assert response.model_call_attempted is False
    assert {suggestion.source_field for suggestion in response.suggestions} >= {
        "customer_name",
        "budget_amount",
        "due_date",
    }
    assert "invented_raw_field" not in {suggestion.source_field for suggestion in response.suggestions}


def test_mapping_suggestions_can_require_live_ai_without_template_fallback() -> None:
    class InvalidMappingSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_mapping_suggestion(self, context: dict):
            return type(
                "InvalidSuggestion",
                (),
                {
                    "suggestions": [
                        {
                            "sourceField": "invented_raw_field",
                            "targetField": "AccountName",
                            "transform": "direct",
                            "confidence": 0.99,
                            "rationale": "Invalid model output for test coverage.",
                        }
                    ],
                    "model_name": "fake-local-model",
                    "model_call_attempted": True,
                    "model_call_succeeded": True,
                    "provider_name": "ollama",
                },
            )()

    service = MappingSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=InvalidMappingSuggestionProvider(),
    )

    try:
        service.suggest(
            MappingSuggestionRequest(
                prompt="Map NetSuite project fields into Salesforce opportunity fields.",
                sourceObjectId="netsuite-project",
                targetObjectId="salesforce-opportunity",
                requireLiveAi=True,
            )
        )
    except LiveAIRequiredError as exc:
        assert "Live AI was requested" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected live AI enforcement to reject template fallback.")


def test_mapping_prompt_rejects_raw_query_and_secret_language() -> None:
    response = client.post(
        "/api/v1/mappings/suggestions",
        json={
            "prompt": "Use SuiteQL and password fields to map objects.",
            "sourceObjectId": "netsuite-project",
            "targetObjectId": "salesforce-opportunity",
        },
    )

    assert response.status_code == 422
