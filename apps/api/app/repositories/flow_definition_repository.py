from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import FlowDefinitionRecord
from app.models.flows import FlowDefinition


class FlowDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_missing(self, flows: list[FlowDefinition]) -> None:
        for flow in flows:
            existing = self.session.get(FlowDefinitionRecord, flow.flow_id)
            if existing is None:
                self.session.add(self._to_record(flow))
            elif existing.status == "active":
                existing.status = flow.status
        self.session.commit()

    def list_flows(self) -> list[FlowDefinition]:
        records = self.session.scalars(
            select(FlowDefinitionRecord).order_by(FlowDefinitionRecord.created_at.asc())
        ).all()
        return [self._to_model(record) for record in records]

    def get_flow(self, flow_id: str) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow_id)
        if record is None:
            raise KeyError(flow_id)
        return self._to_model(record)

    def upsert(self, flow: FlowDefinition) -> FlowDefinition:
        record = self.session.get(FlowDefinitionRecord, flow.flow_id)
        if record is None:
            record = self._to_record(flow)
            self.session.add(record)
        else:
            record.name = flow.name
            record.description = flow.description
            record.source_connector = flow.source_connector
            record.target_module = flow.target_module
            record.status = flow.status
            record.trigger_type = flow.trigger_type
            record.steps = [step.model_dump(by_alias=True) for step in flow.steps]

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

    def clear(self) -> None:
        self.session.execute(delete(FlowDefinitionRecord))
        self.session.commit()

    def _to_record(self, flow: FlowDefinition) -> FlowDefinitionRecord:
        return FlowDefinitionRecord(
            flow_id=flow.flow_id,
            name=flow.name,
            description=flow.description,
            source_connector=flow.source_connector,
            target_module=flow.target_module,
            status=flow.status,
            trigger_type=flow.trigger_type,
            last_run_at=flow.last_run_at,
            last_run_status=flow.last_run_status,
            steps=[step.model_dump(by_alias=True) for step in flow.steps],
        )

    def _to_model(self, record: FlowDefinitionRecord) -> FlowDefinition:
        status = "published" if record.status == "active" else record.status
        return FlowDefinition(
            flowId=record.flow_id,
            name=record.name,
            description=record.description,
            sourceConnector=record.source_connector,
            targetModule=record.target_module,
            status=status,
            triggerType=record.trigger_type,
            lastRunAt=record.last_run_at,
            lastRunStatus=record.last_run_status,
            steps=record.steps,
        )
