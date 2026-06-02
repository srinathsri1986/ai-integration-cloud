from app.core.database import SessionLocal
from app.models.mapping import (
    MappingDefinition,
    MappingDefinitionUpsertRequest,
    MappingLifecycleAction,
    MappingLifecycleResponse,
)
from app.repositories.mapping_definition_repository import MappingDefinitionRepository
from app.services.audit_service import audit_service
from app.services.mapping_catalog import get_mapping_object


class MappingDefinitionService:
    def list_mappings(self) -> list[MappingDefinition]:
        with SessionLocal() as session:
            return MappingDefinitionRepository(session).list_mappings()

    def get_mapping(self, mapping_id: str) -> MappingDefinition:
        with SessionLocal() as session:
            return MappingDefinitionRepository(session).get_mapping(mapping_id)

    def upsert_mapping(self, request: MappingDefinitionUpsertRequest) -> MappingDefinition:
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
            saved = MappingDefinitionRepository(session).upsert(mapping)

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
    ) -> MappingLifecycleResponse:
        mapping = self.get_mapping(mapping_id)
        next_status = self._next_status(mapping.status, action)

        with SessionLocal() as session:
            updated = MappingDefinitionRepository(session).update_status(mapping_id, next_status)

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

    def clear_for_tests(self) -> None:
        with SessionLocal() as session:
            MappingDefinitionRepository(session).clear()

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


mapping_definition_service = MappingDefinitionService()
