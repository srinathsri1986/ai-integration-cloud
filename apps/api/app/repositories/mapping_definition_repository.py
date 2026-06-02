from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import MappingDefinitionRecord
from app.models.mapping import MappingDefinition


class MappingDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_mappings(self) -> list[MappingDefinition]:
        records = self.session.scalars(
            select(MappingDefinitionRecord).order_by(MappingDefinitionRecord.updated_at.desc())
        ).all()
        return [self._to_model(record) for record in records]

    def get_mapping(self, mapping_id: str) -> MappingDefinition:
        record = self.session.get(MappingDefinitionRecord, mapping_id)
        if record is None:
            raise KeyError(mapping_id)
        return self._to_model(record)

    def upsert(self, mapping: MappingDefinition) -> MappingDefinition:
        record = self.session.get(MappingDefinitionRecord, mapping.mapping_id)
        mappings = [row.model_dump(by_alias=True) for row in mapping.mappings]

        if record is None:
            record = MappingDefinitionRecord(
                mapping_id=mapping.mapping_id,
                name=mapping.name,
                description=mapping.description,
                source_object_id=mapping.source_object_id,
                target_object_id=mapping.target_object_id,
                status=mapping.status,
                mappings=mappings,
            )
            self.session.add(record)
        else:
            record.name = mapping.name
            record.description = mapping.description
            record.source_object_id = mapping.source_object_id
            record.target_object_id = mapping.target_object_id
            record.status = mapping.status
            record.mappings = mappings

        self.session.commit()
        return self.get_mapping(mapping.mapping_id)

    def update_status(self, mapping_id: str, status: str) -> MappingDefinition:
        record = self.session.get(MappingDefinitionRecord, mapping_id)
        if record is None:
            raise KeyError(mapping_id)
        record.status = status
        self.session.commit()
        return self.get_mapping(mapping_id)

    def clear(self) -> None:
        self.session.execute(delete(MappingDefinitionRecord))
        self.session.commit()

    def _to_model(self, record: MappingDefinitionRecord) -> MappingDefinition:
        return MappingDefinition(
            mappingId=record.mapping_id,
            name=record.name,
            description=record.description,
            sourceObjectId=record.source_object_id,
            targetObjectId=record.target_object_id,
            status=record.status,
            mappings=record.mappings,
            createdAt=record.created_at.isoformat(),
            updatedAt=record.updated_at.isoformat(),
        )
