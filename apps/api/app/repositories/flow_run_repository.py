from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import FlowRunRecord
from app.models.flows import FlowRunInspection, FlowRunResponse


class FlowRunRepository:
    def __init__(self, session: Session, tenant_id: int | None = None) -> None:
        self.session = session
        self._tenant_id = tenant_id

    def create_running(self, flow_id: str, request_id: str, started_at: str) -> None:
        record = FlowRunRecord(
            tenant_id=self._tenant_id,
            request_id=request_id,
            flow_id=flow_id,
            status="running",
            started_at=started_at,
            completed_at=None,
            tools_used=[],
            message="Execution in progress.",
            data={},
            execution_timeline=[],
        )
        self.session.add(record)
        self.session.commit()

    def update_completed(self, request_id: str, run: "FlowRunResponse") -> None:
        record = self.session.scalars(
            select(FlowRunRecord).where(FlowRunRecord.request_id == request_id).limit(1)
        ).first()
        if record is None:
            return
        record.status = run.status
        record.completed_at = run.completed_at
        record.tools_used = run.tools_used
        record.message = run.message
        record.data = run.data
        record.execution_timeline = [
            step.model_dump(by_alias=True) for step in run.execution_timeline
        ]
        self.session.commit()

    def append(self, run: "FlowRunResponse") -> None:
        record = FlowRunRecord(
            tenant_id=self._tenant_id,
            request_id=run.request_id,
            flow_id=run.flow_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            tools_used=run.tools_used,
            message=run.message,
            data=run.data,
            execution_timeline=[
                step.model_dump(by_alias=True) for step in run.execution_timeline
            ],
        )
        self.session.add(record)
        self.session.commit()

    def count(
        self,
        *,
        flow_id: str | None = None,
        status: str | None = None,
    ) -> int:
        """Total runs matching the given filters for this tenant."""
        statement = self._scope(select(func.count()).select_from(FlowRunRecord))
        if flow_id:
            statement = statement.where(FlowRunRecord.flow_id == flow_id)
        if status:
            statement = statement.where(FlowRunRecord.status == status)
        return self.session.scalar(statement) or 0

    def list_runs(
        self,
        *,
        flow_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FlowRunResponse]:
        statement = self._scope(
            select(FlowRunRecord).order_by(FlowRunRecord.created_at.desc())
        )
        if flow_id:
            statement = statement.where(FlowRunRecord.flow_id == flow_id)
        if status:
            statement = statement.where(FlowRunRecord.status == status)

        records = self.session.scalars(statement.limit(limit).offset(offset)).all()
        return [self._to_response(record) for record in records]

    def latest_for_flow(self, flow_id: str) -> FlowRunResponse | None:
        record = self.session.scalars(
            self._scope(
                select(FlowRunRecord)
                .where(FlowRunRecord.flow_id == flow_id)
                .order_by(FlowRunRecord.created_at.desc())
                .limit(1)
            )
        ).first()
        return self._to_response(record) if record else None

    def get_by_request_id(self, request_id: str) -> FlowRunResponse:
        record = self.session.scalars(
            self._scope(
                select(FlowRunRecord).where(FlowRunRecord.request_id == request_id).limit(1)
            )
        ).first()
        if record is None:
            raise KeyError(request_id)
        return self._to_response(record)

    def clear(self) -> None:
        self.session.execute(delete(FlowRunRecord))
        self.session.commit()

    def _scope(self, statement):
        if self._tenant_id is not None:
            statement = statement.where(
                or_(
                    FlowRunRecord.tenant_id == self._tenant_id,
                    FlowRunRecord.tenant_id.is_(None),
                )
            )
        return statement

    def _to_response(self, record: FlowRunRecord) -> FlowRunResponse:
        timeline = record.execution_timeline
        data = record.data
        return FlowRunResponse(
            requestId=record.request_id,
            flowId=record.flow_id,
            status=record.status,
            startedAt=record.started_at,
            completedAt=record.completed_at,
            toolsUsed=record.tools_used,
            message=record.message,
            data=data,
            executionTimeline=timeline,
            inspection=self._inspection(record, timeline, data),
        )

    def _inspection(self, record: FlowRunRecord, timeline: list[dict], data: dict) -> FlowRunInspection:
        mapping_simulation = data.get("mappingSimulation") if isinstance(data, dict) else None
        mapping_definition_id = data.get("mappingDefinitionId") if isinstance(data, dict) else None
        if not mapping_definition_id:
            mapping_definition_id = next(
                (
                    step.get("mappingDefinitionId")
                    for step in timeline
                    if isinstance(step, dict) and step.get("mappingDefinitionId")
                ),
                None,
            )
        return FlowRunInspection(
            durationMs=self._duration_ms(record.started_at, record.completed_at),
            stepCount=len(timeline),
            succeededSteps=sum(1 for step in timeline if step.get("status") == "succeeded"),
            failedSteps=sum(1 for step in timeline if step.get("status") == "failed"),
            skippedSteps=sum(1 for step in timeline if step.get("status") == "skipped"),
            warningCount=sum(len(step.get("warnings", [])) for step in timeline if isinstance(step, dict)),
            mappingDefinitionId=mapping_definition_id,
            hasSourcePayload=bool(isinstance(mapping_simulation, dict) and mapping_simulation.get("sourcePayload")),
            hasTargetPayload=bool(isinstance(mapping_simulation, dict) and mapping_simulation.get("targetPayload")),
            auditRequestId=record.request_id,
        )

    def _duration_ms(self, started_at: str, completed_at: str | None) -> int:
        if not completed_at:
            return 0
        try:
            started = datetime.fromisoformat(started_at)
            completed = datetime.fromisoformat(completed_at)
        except ValueError:
            return 0
        return max(0, int((completed - started).total_seconds() * 1000))
