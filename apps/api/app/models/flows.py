from typing import Any, Literal

from croniter import croniter
from pydantic import BaseModel, Field, field_validator, model_validator


FlowId = str
FlowStatus = Literal["draft", "pending_approval", "approved", "published", "paused"]
FlowLifecycleAction = Literal["submit_for_approval", "approve", "reject", "publish", "pause"]
FlowRunStatus = Literal["never_run", "running", "succeeded", "failed"]
FlowRunStepStatus = Literal["succeeded", "failed", "skipped"]
FlowTriggerType = Literal["manual", "schedule", "webhook"]
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
    trigger_cron: str | None = Field(default=None, alias="triggerCron")
    webhook_secret: str | None = Field(default=None, alias="webhookSecret")
    mapping_definition_id: str | None = Field(default=None, alias="mappingDefinitionId")
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
    trigger_cron: str | None = Field(default=None, alias="triggerCron", max_length=100)
    mapping_definition_id: str | None = Field(default=None, alias="mappingDefinitionId", max_length=96)
    steps: list[FlowStep] = Field(min_length=1, max_length=8)

    @field_validator("description", "name", "target_module")
    @classmethod
    def reject_raw_query_language(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["select *", "suiteql", "sql query", "raw query", "script execution"]
        if any(term in normalized for term in blocked):
            raise ValueError("Flow definitions cannot contain raw query or code execution language.")

        return value

    @model_validator(mode="after")
    def validate_trigger_config(self) -> "FlowDefinitionUpsertRequest":
        if self.trigger_type == "schedule":
            if not self.trigger_cron:
                raise ValueError("trigger_cron is required when trigger_type is 'schedule'.")
            if not croniter.is_valid(self.trigger_cron):
                raise ValueError(f"trigger_cron '{self.trigger_cron}' is not a valid cron expression.")
        return self

    @field_validator("status")
    @classmethod
    def require_lifecycle_for_non_draft_status(cls, value: FlowStatus) -> FlowStatus:
        if value != "draft":
            raise ValueError("Flow definitions must be saved as draft before lifecycle actions.")

        return value


class FlowSuggestionRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=1000)
    require_live_ai: bool = Field(default=False, alias="requireLiveAi")


class FlowSuggestionResponse(BaseModel):
    prompt: str
    suggested_flow: FlowDefinitionUpsertRequest = Field(alias="suggestedFlow")
    rationale: str = Field(min_length=10, max_length=600)
    suggestion_provider: str = Field(alias="suggestionProvider")
    suggestion_model: str | None = Field(default=None, alias="suggestionModel")
    suggestion_generated: bool = Field(alias="suggestionGenerated")
    suggestion_fallback_used: bool = Field(alias="suggestionFallbackUsed")
    model_call_attempted: bool = Field(alias="modelCallAttempted")
    model_call_succeeded: bool = Field(alias="modelCallSucceeded")


class FlowLifecycleRequest(BaseModel):
    action: FlowLifecycleAction
    note: str | None = Field(default=None, max_length=300)


class FlowLifecycleResponse(BaseModel):
    flow: FlowDefinition
    action: FlowLifecycleAction
    message: str


class FlowRunTimelineStep(BaseModel):
    id: str
    name: str
    status: FlowRunStepStatus
    started_at: str = Field(alias="startedAt")
    completed_at: str = Field(alias="completedAt")
    latency_ms: int = Field(alias="latencyMs")
    approved_tool: str | None = Field(default=None, alias="approvedTool")
    mapping_definition_id: str | None = Field(default=None, alias="mappingDefinitionId")
    warnings: list[str] = Field(default_factory=list)


class FlowRunInspection(BaseModel):
    duration_ms: int = Field(alias="durationMs")
    step_count: int = Field(alias="stepCount")
    succeeded_steps: int = Field(alias="succeededSteps")
    failed_steps: int = Field(alias="failedSteps")
    skipped_steps: int = Field(alias="skippedSteps")
    warning_count: int = Field(alias="warningCount")
    mapping_definition_id: str | None = Field(default=None, alias="mappingDefinitionId")
    has_source_payload: bool = Field(alias="hasSourcePayload")
    has_target_payload: bool = Field(alias="hasTargetPayload")
    audit_request_id: str = Field(alias="auditRequestId")


class FlowRunResponse(BaseModel):
    request_id: str = Field(alias="requestId")
    flow_id: FlowId = Field(alias="flowId")
    status: FlowRunStatus
    started_at: str = Field(alias="startedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    tools_used: list[str] = Field(alias="toolsUsed")
    message: str
    data: dict[str, Any]
    execution_timeline: list[FlowRunTimelineStep] = Field(default_factory=list, alias="executionTimeline")
    inspection: FlowRunInspection | None = Field(default=None, alias="inspection")
