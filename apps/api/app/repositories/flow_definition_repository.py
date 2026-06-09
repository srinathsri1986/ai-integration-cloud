from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import FlowDefinitionRecord
from app.models.flows import FlowDefinition


class FlowDefinitionRepository:
    def __init__(self, session: Session, tenant_id: int | None = None) -> None:
        self.session = session
        self._tenant_id = tenant_id

    def seed_missing(self, flows: list[FlowDefinition]) -> None:
        for flow in flows:
            existing = self.session.get(FlowDefinitionRecord, flow.flow_id)
            if existing is None:
                record = self._to_record(flow)
                record.tenant_id = None  # built-ins are global (no tenant)
                self.session.add(record)
            elif existing.status == "active":
                existing.status = flow.status
        self.session.commit()

    def count(self) -> int:
        """Total number of flows visible to this tenant."""
        return self.session.scalar(
            self._scope(select(func.count()).select_from(FlowDefinitionRecord))
        ) or 0

    def list_flows(self, limit: int = 50, offset: int = 0) -> list[FlowDefinition]:
        records = self.session.scalars(
            self._scope(
                select(FlowDefinitionRecord)
                .order_by(FlowDefinitionRecord.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [self._to_model(record) for record in records]

    def get_flow(self, flow_id: str) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(flow_id)
        self._assert_visible(record)
        return self._to_model(record)

    def upsert(self, flow: FlowDefinition) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow.flow_id)
        if record is None:
            record = self._to_record(flow)
            record.tenant_id = self._tenant_id
            self.session.add(record)
        else:
            record.name = flow.name
            record.description = flow.description
            record.source_connector = flow.source_connector
            record.target_module = flow.target_module
            record.status = flow.status
            record.trigger_type = flow.trigger_type
            record.trigger_cron = flow.trigger_cron
            # preserve existing webhook_secret — only set if not already present
            if flow.webhook_secret and not record.webhook_secret:
                record.webhook_secret = flow.webhook_secret
            record.mapping_definition_id = flow.mapping_definition_id
            record.steps = [step.model_dump(by_alias=True) for step in flow.steps]
            # R18a
            record.target_connector = flow.target_connector
            record.field_mappings = [m.model_dump(by_alias=True) for m in flow.field_mappings]

        self.session.commit()
        return self.get_flow(flow.flow_id)

    def update_last_run(self, flow_id: str, completed_at: str, status: str) -> None:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(flow_id)
        record.last_run_at = completed_at
        record.last_run_status = status
        self.session.commit()

    def update_status(self, flow_id: str, status: str) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(flow_id)
        record.status = status
        self.session.commit()
        return self.get_flow(flow_id)

    def update_mapping_definition_id(self, flow_id: str, mapping_definition_id: str | None) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(f"Unknown flow: '{flow_id}'")
        record.mapping_definition_id = mapping_definition_id
        self.session.commit()
        return self.get_flow(flow_id)

    def delete_flow(self, flow_id: str) -> None:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(flow_id)
        self.session.delete(record)
        self.session.commit()

    def clear(self) -> None:
        self.session.execute(delete(FlowDefinitionRecord))
        self.session.commit()

    def _scope(self, statement):
        if self._tenant_id is not None:
            statement = statement.where(
                or_(
                    FlowDefinitionRecord.tenant_id == self._tenant_id,
                    FlowDefinitionRecord.tenant_id.is_(None),
                )
            )
        return statement

    def _assert_visible(self, record: FlowDefinitionRecord) -> None:
        if self._tenant_id is not None:
            if record.tenant_id is not None and record.tenant_id != self._tenant_id:
                raise KeyError(record.flow_id)

    def list_scheduled_flow_specs(self) -> list[dict]:
        """Return minimal specs for all published scheduled flows (for Beat scheduler)."""
        records = self.session.scalars(
            select(FlowDefinitionRecord).where(
                FlowDefinitionRecord.status == "published",
                FlowDefinitionRecord.trigger_type == "schedule",
                FlowDefinitionRecord.trigger_cron.isnot(None),
            )
        ).all()
        return [
            {
                "flow_id": r.flow_id,
                "tenant_id": r.tenant_id,
                "trigger_cron": r.trigger_cron,
                "last_run_at": r.last_run_at,
            }
            for r in records
        ]

    def get_by_webhook_secret(self, flow_id: str, webhook_secret: str) -> FlowDefinition:
        record = self.session.scalars(
            select(FlowDefinitionRecord).where(
                FlowDefinitionRecord.flow_id == flow_id,
                FlowDefinitionRecord.webhook_secret == webhook_secret,
            ).limit(1)
        ).first()
        if record is None:
            raise KeyError(flow_id)
        return self._to_model(record)

    def _to_record(self, flow: FlowDefinition) -> FlowDefinitionRecord:
        return FlowDefinitionRecord(
            flow_id=flow.flow_id,
            name=flow.name,
            description=flow.description,
            source_connector=flow.source_connector,
            target_module=flow.target_module,
            status=flow.status,
            trigger_type=flow.trigger_type,
            trigger_cron=flow.trigger_cron,
            webhook_secret=flow.webhook_secret,
            mapping_definition_id=flow.mapping_definition_id,
            last_run_at=flow.last_run_at,
            last_run_status=flow.last_run_status,
            steps=[step.model_dump(by_alias=True) for step in flow.steps],
            # R18a
            target_connector=flow.target_connector,
            field_mappings=[m.model_dump(by_alias=True) for m in flow.field_mappings],
        )

    def _to_model(self, record: FlowDefinitionRecord) -> FlowDefinition:
        import json
        from app.models.custom_endpoint import InlineFieldMapping
        status = "published" if record.status == "active" else record.status
        # Deserialise field_mappings from JSON column (list of dicts → Pydantic models)
        raw_mappings = getattr(record, "field_mappings", None) or []
        if isinstance(raw_mappings, str):
            raw_mappings = json.loads(raw_mappings)
        field_mappings = []
        for m in raw_mappings:
            try:
                field_mappings.append(InlineFieldMapping.model_validate(m))
            except Exception:
                pass
        return FlowDefinition(
            flowId=record.flow_id,
            name=record.name,
            description=record.description,
            sourceConnector=record.source_connector,
            targetModule=record.target_module,
            targetConnector=getattr(record, "target_connector", None),
            fieldMappings=field_mappings,
            status=status,
            triggerType=record.trigger_type,
            triggerCron=getattr(record, "trigger_cron", None),
            webhookSecret=getattr(record, "webhook_secret", None),
            mappingDefinitionId=record.mapping_definition_id,
            lastRunAt=record.last_run_at,
            lastRunStatus=record.last_run_status,
            steps=record.steps,
        )
