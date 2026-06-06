from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.core.config import get_settings
from app.models.audit import AuditLogEntry
from app.models.llm import AIProvider
from app.models.mapping import (
    MappingObject,
    MappingSuggestionItem,
    MappingSuggestionRequest,
    MappingSuggestionResponse,
)
from app.services.audit_service import audit_service
from app.services.llm_provider import LLMProvider, LLMProviderError, make_llm_provider
from app.services.mapping_catalog import APPROVED_MAPPING_TRANSFORMS, get_mapping_object


@dataclass(frozen=True)
class MappingSuggestionMetadata:
    provider: str
    model: str | None
    fallback_used: bool
    model_call_attempted: bool
    model_call_succeeded: bool


class LiveAIRequiredError(RuntimeError):
    pass


class MappingSuggestionService:
    def __init__(
        self,
        ai_provider: AIProvider | None = None,
        model_name: str | None = None,
        llm_provider: LLMProvider | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.ai_provider: AIProvider = ai_provider or settings.ai_provider  # type: ignore[assignment]
        self.model_name = model_name or self._default_model_name()
        self.openai_api_key = openai_api_key if openai_api_key is not None else settings.openai_api_key
        self.llm_provider = llm_provider or make_llm_provider(
            provider=self.ai_provider,
            model_name=self.model_name,
            openai_api_key=self.openai_api_key,
            ollama_base_url=settings.ollama_base_url,
            ollama_timeout_seconds=settings.ollama_timeout_seconds,
        )

    def suggest(self, request: MappingSuggestionRequest) -> MappingSuggestionResponse:
        request_id = str(uuid4())
        started = perf_counter()
        success = False
        failure_reason: str | None = None
        metadata = MappingSuggestionMetadata(
            provider="template",
            model=None,
            fallback_used=False,
            model_call_attempted=False,
            model_call_succeeded=False,
        )

        try:
            source_object = get_mapping_object(request.source_object_id)
            target_object = get_mapping_object(request.target_object_id)
            suggestions, metadata = self._suggest_mappings(request, source_object, target_object)
            success = True
            return MappingSuggestionResponse(
                prompt=request.prompt,
                sourceObjectId=source_object.id,
                targetObjectId=target_object.id,
                suggestions=suggestions,
                suggestionProvider=metadata.provider,
                suggestionModel=metadata.model,
                suggestionGenerated=True,
                suggestionFallbackUsed=metadata.fallback_used,
                modelCallAttempted=metadata.model_call_attempted,
                modelCallSucceeded=metadata.model_call_succeeded,
            )
        except Exception as exc:
            failure_reason = exc.__class__.__name__
            raise
        finally:
            latency_ms = int((perf_counter() - started) * 1000)
            audit_service.record(
                AuditLogEntry(
                    timestamp=datetime.now(UTC).isoformat(),
                    requestId=request_id,
                    user="local-dev-user",
                    channel="web",
                    question=request.prompt,
                    detectedIntent="MAPPING_SUGGESTION",
                    confidence=1,
                    toolsUsed=["mapping.suggest"],
                    endpointCalled="/api/v1/mappings/suggestions",
                    fallbackUsed=metadata.fallback_used,
                    success=success,
                    failureReason=failure_reason,
                    latencyMs=latency_ms,
                    aiProvider=metadata.provider,
                    aiMode=self._ai_mode_for_provider(metadata.provider),
                    modelName=metadata.model,
                    modelCallAttempted=metadata.model_call_attempted,
                    modelCallSucceeded=metadata.model_call_succeeded,
                    usedFallbackRouter=metadata.fallback_used,
                    narrativeProvider="none",
                    narrativeModel=None,
                    narrativeGenerated=False,
                    narrativeFallbackUsed=False,
                )
            )

    def _suggest_mappings(
        self,
        request: MappingSuggestionRequest,
        source_object: MappingObject,
        target_object: MappingObject,
    ) -> tuple[list[MappingSuggestionItem], MappingSuggestionMetadata]:
        if self.ai_provider == "disabled" or self.llm_provider is None:
            if request.require_live_ai:
                raise LiveAIRequiredError("Live AI was requested, but no live AI provider is configured.")
            return (
                self._template_suggestions(source_object, target_object),
                MappingSuggestionMetadata(
                    provider="template",
                    model=None,
                    fallback_used=False,
                    model_call_attempted=False,
                    model_call_succeeded=False,
                ),
            )

        context = {
            "prompt": request.prompt,
            "sourceObject": source_object.model_dump(by_alias=True),
            "targetObject": target_object.model_dump(by_alias=True),
            "allowedTransforms": APPROVED_MAPPING_TRANSFORMS,
            "policy": (
                "Suggest draft field mappings only. Use only the provided field names and allowed "
                "transforms. Do not generate SQL, SuiteQL, arbitrary code, credentials, secrets, "
                "or execution instructions. Humans must accept or reject every suggestion."
            ),
        }

        try:
            result = self.llm_provider.generate_mapping_suggestion(context)
            suggestions = self._validate_suggestions(
                result.suggestions,
                source_object,
                target_object,
            )
            if not suggestions:
                raise ValueError("Model returned no valid mapping suggestions.")

            return (
                suggestions,
                MappingSuggestionMetadata(
                    provider=result.provider_name,
                    model=result.model_name,
                    fallback_used=False,
                    model_call_attempted=result.model_call_attempted,
                    model_call_succeeded=result.model_call_succeeded,
                ),
            )
        except Exception as exc:
            attempted = exc.model_call_attempted if isinstance(exc, LLMProviderError) else False
            succeeded = exc.model_call_succeeded if isinstance(exc, LLMProviderError) else False
            if request.require_live_ai and self.ai_provider in {"ollama", "openai"}:
                raise LiveAIRequiredError(
                    "Live AI was requested, but the configured provider returned invalid or unavailable output."
                ) from exc
            return (
                self._template_suggestions(source_object, target_object),
                MappingSuggestionMetadata(
                    provider=self.ai_provider,
                    model=self.model_name,
                    fallback_used=True,
                    model_call_attempted=attempted,
                    model_call_succeeded=succeeded,
                ),
            )

    def _validate_suggestions(
        self,
        suggestions: list[dict],
        source_object: MappingObject,
        target_object: MappingObject,
    ) -> list[MappingSuggestionItem]:
        source_fields = {field.name: field for field in source_object.fields}
        target_fields = {field.name: field for field in target_object.fields}
        validated: list[MappingSuggestionItem] = []
        seen_targets: set[str] = set()

        for raw_suggestion in suggestions[:12]:
            suggestion = MappingSuggestionItem.model_validate(raw_suggestion)
            if suggestion.source_field not in source_fields:
                raise ValueError(f"Unknown source field: {suggestion.source_field}")
            if suggestion.target_field not in target_fields:
                raise ValueError(f"Unknown target field: {suggestion.target_field}")
            if suggestion.target_field in seen_targets:
                continue
            if suggestion.transform == "format_date" and source_fields[suggestion.source_field].type != "date":
                raise ValueError("format_date can only be used with date source fields")

            seen_targets.add(suggestion.target_field)
            validated.append(suggestion)

        return validated

    def _template_suggestions(
        self,
        source_object: MappingObject,
        target_object: MappingObject,
    ) -> list[MappingSuggestionItem]:
        source_fields = {field.name: field for field in source_object.fields}
        target_fields = {field.name: field for field in target_object.fields}
        candidates = [
            # NetSuite → Salesforce
            ("customer_name", "AccountName", "direct", 0.94, "Customer names align to the target account reference."),
            ("budget_amount", "Amount", "direct", 0.91, "Budget and amount fields share numeric finance meaning."),
            ("due_date", "CloseDate", "format_date", 0.88, "Date values need target system date formatting."),
            ("account_manager", "OwnerName", "direct", 0.84, "Owner fields represent the responsible business person."),
            ("project_id", "Name", "rename", 0.8, "Project identifier can seed a reviewed opportunity name."),
            # REST API / CSV → Salesforce / REST
            ("project_id", "externalId", "rename", 0.78, "The project identifier can seed an external reference."),
            ("customer", "displayName", "rename", 0.86, "Customer text can become the display name."),
            ("invoice_number", "externalId", "rename", 0.82, "Invoice number can be retained as an external identifier."),
            ("amount", "Amount", "direct", 0.9, "Amount fields share numeric meaning."),
            ("invoice_date", "CloseDate", "format_date", 0.8, "Invoice date can be formatted for target dates."),
            # SAP Cost Center → Oracle GL
            ("cost_center_id", "account_segment", "rename", 0.79, "Cost center maps to an Oracle GL account segment."),
            ("budget_amount", "entered_dr", "direct", 0.83, "Budget amount maps to the GL debit side."),
            ("valid_from", "period_name", "format_date", 0.72, "Validity date can be formatted as an Oracle period name."),
            ("controlling_area", "ledger_id", "rename", 0.68, "Controlling area codes can seed Oracle ledger identifiers."),
            # SAP Journal → Salesforce
            ("reference", "Name", "rename", 0.75, "Document reference can seed the opportunity name."),
            ("amount", "Amount", "direct", 0.9, "Amount fields share numeric meaning."),
            ("posting_date", "CloseDate", "format_date", 0.82, "Posting date can be formatted as a Salesforce close date."),
            # HCM Employee → Salesforce Opportunity (team assignment)
            ("full_name", "OwnerName", "direct", 0.88, "Employee name directly maps to the opportunity owner."),
            ("employee_id", "externalId", "rename", 0.76, "Employee ID can become an external reference."),
            # HCM Employee → Slack alert
            ("full_name", "text", "rename", 0.82, "Employee name seeds the Slack message body."),
            ("department", "channel", "rename", 0.70, "Department name maps to a Slack channel identifier."),
            # PostgreSQL Analytics → SAP Journal (budget variance posting)
            ("metric_value", "amount", "direct", 0.86, "Metric value maps to the SAP transaction amount."),
            ("metric_name", "gl_account", "lookup_placeholder", 0.72, "Metric name requires a lookup to resolve the GL account."),
            ("recorded_at", "posting_date", "format_date", 0.85, "Metric timestamp maps to the SAP posting date."),
            ("row_id", "reference", "rename", 0.74, "Row ID can serve as the document reference."),
            # NetSuite → SAP journal (cross-system repost)
            ("budget_amount", "amount", "direct", 0.88, "Budget amount maps to the SAP journal amount."),
            ("due_date", "posting_date", "format_date", 0.85, "Project due date can map to the SAP posting date."),
            ("customer_name", "reference", "rename", 0.72, "Customer name can seed the SAP document reference."),
        ]
        suggestions: list[MappingSuggestionItem] = []
        seen_targets: set[str] = set()

        for source_field, target_field, transform, confidence, rationale in candidates:
            if source_field not in source_fields or target_field not in target_fields:
                continue
            if target_field in seen_targets:
                continue
            seen_targets.add(target_field)
            suggestions.append(
                MappingSuggestionItem(
                    sourceField=source_field,
                    targetField=target_field,
                    transform=transform,
                    confidence=confidence,
                    rationale=rationale,
                )
            )

        return suggestions[:8]

    def _default_model_name(self) -> str:
        settings = get_settings()

        if self.ai_provider == "openai":
            return settings.openai_model

        if self.ai_provider == "ollama":
            return settings.ollama_model

        return "mock-mapping-suggestion-v0"

    def _ai_mode_for_provider(self, provider_name: str) -> str:
        if provider_name == "mock":
            return "mock_llm"

        if provider_name in {"openai", "ollama"}:
            return provider_name

        if provider_name == "template":
            return "rule_based"

        return "disabled"


mapping_suggestion_service = MappingSuggestionService()
