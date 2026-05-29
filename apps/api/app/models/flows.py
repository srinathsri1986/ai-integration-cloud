from typing import Any, Literal

from pydantic import BaseModel, Field


FlowId = Literal[
    "netsuite-cfo-dashboard-refresh",
    "netsuite-project-risk-refresh",
    "netsuite-subsidiary-drilldown-refresh",
]
FlowStatus = Literal["active", "paused"]
FlowRunStatus = Literal["never_run", "succeeded", "failed"]


class FlowStep(BaseModel):
    id: str
    name: str
    description: str
    approved_tool: str = Field(alias="approvedTool")


class FlowDefinition(BaseModel):
    flow_id: FlowId = Field(alias="flowId")
    name: str
    description: str
    source_connector: Literal["netsuite"] = Field(alias="sourceConnector")
    target_module: str = Field(alias="targetModule")
    status: FlowStatus
    last_run_at: str | None = Field(default=None, alias="lastRunAt")
    last_run_status: FlowRunStatus = Field(alias="lastRunStatus")
    steps: list[FlowStep]


class FlowRunResponse(BaseModel):
    request_id: str = Field(alias="requestId")
    flow_id: FlowId = Field(alias="flowId")
    status: FlowRunStatus
    started_at: str = Field(alias="startedAt")
    completed_at: str = Field(alias="completedAt")
    tools_used: list[str] = Field(alias="toolsUsed")
    message: str
    data: dict[str, Any]
