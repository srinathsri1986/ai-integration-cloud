from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


FlowId = str
FlowStatus = Literal["draft", "active", "paused"]
FlowRunStatus = Literal["never_run", "succeeded", "failed"]
FlowTriggerType = Literal["manual", "schedule_placeholder"]
ApprovedFlowTool = Literal[
    "cfo.dashboard_summary",
    "cfo.pl_vs_budget",
    "cfo.yoy_comparison",
    "cfo.subsidiary_drilldown",
    "cfo.running_projects",
    "cfo.overdue_projects_by_account_manager",
    "orchestrator.query",
]


class FlowStep(BaseModel):
    id: str
    name: str
    description: str
    approved_tool: ApprovedFlowTool = Field(alias="approvedTool")


class FlowDefinition(BaseModel):
    flow_id: FlowId = Field(alias="flowId")
    name: str
    description: str
    source_connector: Literal["netsuite"] = Field(alias="sourceConnector")
    target_module: str = Field(alias="targetModule")
    status: FlowStatus
    trigger_type: FlowTriggerType = Field(default="manual", alias="triggerType")
    last_run_at: str | None = Field(default=None, alias="lastRunAt")
    last_run_status: FlowRunStatus = Field(alias="lastRunStatus")
    steps: list[FlowStep]


class FlowDefinitionUpsertRequest(BaseModel):
    flow_id: str = Field(alias="flowId", min_length=3, max_length=96, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=500)
    source_connector: Literal["netsuite"] = Field(alias="sourceConnector")
    target_module: str = Field(alias="targetModule", min_length=3, max_length=80)
    status: FlowStatus = "draft"
    trigger_type: FlowTriggerType = Field(default="manual", alias="triggerType")
    steps: list[FlowStep] = Field(min_length=1, max_length=8)

    @field_validator("description", "name", "target_module")
    @classmethod
    def reject_raw_query_language(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["select *", "suiteql", "sql query", "raw query", "script execution"]
        if any(term in normalized for term in blocked):
            raise ValueError("Flow definitions cannot contain raw query or code execution language.")

        return value


class FlowRunResponse(BaseModel):
    request_id: str = Field(alias="requestId")
    flow_id: FlowId = Field(alias="flowId")
    status: FlowRunStatus
    started_at: str = Field(alias="startedAt")
    completed_at: str = Field(alias="completedAt")
    tools_used: list[str] = Field(alias="toolsUsed")
    message: str
    data: dict[str, Any]
