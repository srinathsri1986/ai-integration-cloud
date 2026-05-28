from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OrchestratorIntent(StrEnum):
    CFO_DASHBOARD_SUMMARY = "CFO_DASHBOARD_SUMMARY"
    PL_VS_BUDGET = "PL_VS_BUDGET"
    YOY_COMPARISON = "YOY_COMPARISON"
    SUBSIDIARY_DRILLDOWN = "SUBSIDIARY_DRILLDOWN"
    RUNNING_PROJECTS = "RUNNING_PROJECTS"
    OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER = "OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER"
    UNKNOWN = "UNKNOWN"


class OrchestratorQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    period_range: str | None = Field(
        default=None,
        alias="periodRange",
        pattern=r"^\d{4}-(Q[1-4]|0[1-9]|1[0-2])$",
    )
    subsidiary: str | None = Field(default=None, min_length=2, max_length=16)
    as_of_date: str | None = Field(
        default=None,
        alias="asOfDate",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )


class OrchestratorQueryResponse(BaseModel):
    detected_intent: OrchestratorIntent = Field(alias="detectedIntent")
    confidence: float = Field(ge=0, le=1)
    tools_used: list[str] = Field(alias="toolsUsed")
    data: Any
    executive_summary: str = Field(alias="executiveSummary")
    fallback_used: bool = Field(alias="fallbackUsed")
