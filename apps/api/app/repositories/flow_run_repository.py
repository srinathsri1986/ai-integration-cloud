from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import FlowRunRecord
from app.models.flows import FlowRunResponse


class FlowRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, run: FlowRunResponse) -> None:
        record = FlowRunRecord(
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

    def list_runs(
        self,
        *,
        flow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FlowRunResponse]:
        statement = select(FlowRunRecord).order_by(FlowRunRecord.created_at.desc())

        if flow_id:
            statement = statement.where(FlowRunRecord.flow_id == flow_id)
        if status:
            statement = statement.where(FlowRunRecord.status == status)

        records = self.session.scalars(statement.limit(limit).offset(offset)).all()
        return [self._to_response(record) for record in records]

    def latest_for_flow(self, flow_id: str) -> FlowRunResponse | None:
        record = self.session.scalars(
            select(FlowRunRecord)
            .where(FlowRunRecord.flow_id == flow_id)
            .order_by(FlowRunRecord.created_at.desc())
            .limit(1)
        ).first()
        return self._to_response(record) if record else None

    def get_by_request_id(self, request_id: str) -> FlowRunResponse:
        record = self.session.scalars(
            select(FlowRunRecord).where(FlowRunRecord.request_id == request_id).limit(1)
        ).first()
        if record is None:
            raise KeyError(request_id)
        return self._to_response(record)

    def clear(self) -> None:
        self.session.execute(delete(FlowRunRecord))
        self.session.commit()

    def _to_response(self, record: FlowRunRecord) -> FlowRunResponse:
        return FlowRunResponse(
            requestId=record.request_id,
            flowId=record.flow_id,
            status=record.status,
            startedAt=record.started_at,
            completedAt=record.completed_at,
            toolsUsed=record.tools_used,
            message=record.message,
            data=record.data,
            executionTimeline=record.execution_timeline,
        )
