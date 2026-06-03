from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.mapping import (
    MappingDefinition,
    MappingDefinitionUpsertRequest,
    MappingLifecycleAction,
    MappingLifecycleResponse,
    MappingSimulationResponse,
)
from app.repositories.mapping_definition_repository import MappingDefinitionRepository
from app.services.audit_service import audit_service
from app.services.mapping_catalog import get_mapping_object, sample_payload_for_object


class MappingDefinitionService:
    def list_mappings(self, tenant_id: int | None = None) -> list[MappingDefinition]:
        with SessionLocal() as session:
            return MappingDefinitionRepository(session, tenant_id).list_mappings()

    def get_mapping(self, mapping_id: str, tenant_id: int | None = None) -> MappingDefinition:
        with SessionLocal() as session:
            return MappingDefinitionRepository(session, tenant_id).get_mapping(mapping_id)

    def upsert_mapping(self, request: MappingDefinitionUpsertRequest, tenant_id: int | None = None) -> MappingDefinition:
        self._validate_rows(request)
        mapping = MappingDefinition(
            mappingId=request.mapping_id,
            name=request.name,
            description=request.description,
            sourceObjectId=request.source_object_id,
            targetObjectId=request.target_object_id,
            status=request.status,
            mappings=request.mappings,
        )

        with SessionLocal() as session:
            saved = MappingDefinitionRepository(session, tenant_id).upsert(mapping)

        audit_service.record_mapping_definition_action(
            mapping_id=saved.mapping_id,
            action="upsert",
            tools_used=["mapping.definition.upsert"],
        )
        return saved

    def transition_mapping(
        self,
        mapping_id: str,
        action: MappingLifecycleAction,
        note: str | None = None,
        tenant_id: int | None = None,
    ) -> MappingLifecycleResponse:
        mapping = self.get_mapping(mapping_id, tenant_id)
        next_status = self._next_status(mapping.status, action)

        with SessionLocal() as session:
            updated = MappingDefinitionRepository(session, tenant_id).update_status(mapping_id, next_status)

        audit_service.record_mapping_definition_action(
            mapping_id=updated.mapping_id,
            action=action,
            tools_used=["mapping.definition.lifecycle"],
        )
        note_suffix = f" Note: {note}" if note else ""
        return MappingLifecycleResponse(
            mapping=updated,
            action=action,
            message=f"{updated.name} moved to {next_status}.{note_suffix}",
        )

    def simulate_mapping(self, mapping_id: str, tenant_id: int | None = None) -> MappingSimulationResponse:
        request_id = str(uuid4())
        started = perf_counter()
        success = False

        try:
            mapping = self.get_mapping(mapping_id)
            source_payload = sample_payload_for_object(mapping.source_object_id)
            target_object = get_mapping_object(mapping.target_object_id)
            target_payload: dict[str, str | int | float | bool | None] = {}
            warnings: list[str] = []
            transforms_applied: list[str] = []

            for row in mapping.mappings:
                source_value = source_payload.get(row.source_field)
                if row.source_field not in source_payload:
                    warnings.append(f"Source field {row.source_field} is missing from the sample payload.")
                    continue

                target_payload[row.target_field] = self._apply_transform(row.transform, source_value)
                transforms_applied.append(row.transform)

            for field in target_object.fields:
                if field.required and field.name not in target_payload:
                    warnings.append(f"Required target field {field.name} was not populated.")

            success = True
            return MappingSimulationResponse(
                mappingId=mapping.mapping_id,
                status=mapping.status,
                sourceObjectId=mapping.source_object_id,
                targetObjectId=mapping.target_object_id,
                sourcePayload=source_payload,
                targetPayload=target_payload,
                warnings=warnings,
                transformsApplied=transforms_applied,
                simulatedAt=datetime.now(UTC).isoformat(),
            )
        finally:
            audit_service.record_mapping_simulation_action(
                request_id=request_id,
                mapping_id=mapping_id,
                success=success,
                latency_ms=int((perf_counter() - started) * 1000),
            )

    def delete_mapping(self, mapping_id: str, tenant_id: int | None = None) -> dict[str, str]:
        with SessionLocal() as session:
            MappingDefinitionRepository(session, tenant_id).delete_mapping(mapping_id)

        audit_service.record_mapping_definition_action(
            mapping_id=mapping_id,
            action="delete",
            tools_used=["mapping.definition.delete"],
        )
        return {
            "mappingId": mapping_id,
            "message": "Mapping definition deleted.",
        }

    def clear_for_tests(self, tenant_id: int | None = None) -> None:
        with SessionLocal() as session:
            MappingDefinitionRepository(session, tenant_id).clear()

    def _validate_rows(self, request: MappingDefinitionUpsertRequest) -> None:
        source_object = get_mapping_object(request.source_object_id)
        target_object = get_mapping_object(request.target_object_id)
        source_fields = {field.name: field for field in source_object.fields}
        target_fields = {field.name: field for field in target_object.fields}
        seen_targets: set[str] = set()

        for row in request.mappings:
            if row.source_field not in source_fields:
                raise ValueError(f"Unknown source field: {row.source_field}")
            if row.target_field not in target_fields:
                raise ValueError(f"Unknown target field: {row.target_field}")
            if row.target_field in seen_targets:
                raise ValueError(f"Target field is mapped more than once: {row.target_field}")
            if row.transform == "format_date" and source_fields[row.source_field].type != "date":
                raise ValueError("format_date can only be used with date source fields")
            seen_targets.add(row.target_field)

        missing_required = [
            field.name for field in target_object.fields if field.required and field.name not in seen_targets
        ]
        if missing_required:
            raise ValueError(f"Missing required target fields: {', '.join(missing_required)}")

    def _next_status(self, current_status: str, action: MappingLifecycleAction) -> str:
        allowed = {
            "draft": {"submit_for_approval": "pending_approval", "pause": "paused"},
            "pending_approval": {"approve": "approved", "reject": "draft", "pause": "paused"},
            "approved": {"publish": "published", "reject": "draft", "pause": "paused"},
            "published": {"pause": "paused"},
            "paused": {"submit_for_approval": "pending_approval"},
        }
        next_status = allowed.get(current_status, {}).get(action)
        if next_status is None:
            raise ValueError(f"Cannot apply {action} to a {current_status} mapping.")

        return next_status

    def _apply_transform(
        self,
        transform: str,
        source_value: str | int | float | bool | None,
    ) -> str | int | float | bool | None:
        if transform in {"direct", "rename", "format_date"}:
            return source_value

        if transform == "lookup_placeholder":
            return f"lookup:{source_value}" if source_value is not None else None

        if transform == "constant_placeholder":
            return "reviewed_constant_placeholder"

        raise ValueError(f"Unsupported mapping transform: {transform}")


mapping_definition_service = MappingDefinitionService()
