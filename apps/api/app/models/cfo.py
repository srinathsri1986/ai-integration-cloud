from typing import Literal

from pydantic import BaseModel, Field


Period = str
SubsidiaryId = str


class CurrencyAmount(BaseModel):
    amount: float
    currency: str


class CfoKpi(BaseModel):
    label: str
    value: str | float
    trend: Literal["up", "down", "flat"]
    narrative: str


class CfoDashboardSummary(BaseModel):
    generated_at: str
    mode: Literal["mock"]
    cash_position: CurrencyAmount
    open_receivables: CurrencyAmount
    monthly_revenue: CurrencyAmount
    kpis: list[CfoKpi]


class NetSuiteTemplateResult(BaseModel):
    template_id: str
    source: Literal["mock"]
    rows: list[dict[str, str | float]]


class PeriodQuery(BaseModel):
    period: Period = Field(pattern=r"^\d{4}-(Q[1-4]|0[1-9]|1[0-2])$")
    subsidiary_id: SubsidiaryId | None = Field(default=None, min_length=2, max_length=16)


class YoyComparisonQuery(BaseModel):
    current_year: int = Field(default=2026, ge=2000, le=2100)
    prior_year: int = Field(default=2025, ge=2000, le=2100)
    subsidiary_id: SubsidiaryId | None = Field(default=None, min_length=2, max_length=16)


class SubsidiaryDrilldownQuery(BaseModel):
    period: Period = Field(pattern=r"^\d{4}-(Q[1-4]|0[1-9]|1[0-2])$")
    subsidiary_id: SubsidiaryId = Field(min_length=2, max_length=16)


class RunningProjectsQuery(BaseModel):
    account_manager: str | None = Field(default=None, min_length=2, max_length=80)
    subsidiary_id: SubsidiaryId | None = Field(default=None, min_length=2, max_length=16)


class OverdueProjectsQuery(BaseModel):
    min_days_overdue: int = Field(default=1, ge=1, le=365)


class PlVsBudgetLine(BaseModel):
    period: str
    subsidiary_id: str
    line: str
    actual: float
    budget: float
    variance: float
    variance_pct: float
    currency: str


class PlVsBudgetResponse(BaseModel):
    source: Literal["mock"]
    period: str
    subsidiary_id: str | None
    lines: list[PlVsBudgetLine]


class YoyComparisonLine(BaseModel):
    current_year: int
    prior_year: int
    subsidiary_id: str
    metric: str
    current_value: float
    prior_value: float
    change: float
    change_pct: float
    currency: str


class YoyComparisonResponse(BaseModel):
    source: Literal["mock"]
    current_year: int
    prior_year: int
    subsidiary_id: str | None
    lines: list[YoyComparisonLine]


class SubsidiaryDrilldownLine(BaseModel):
    period: str
    subsidiary_id: str
    subsidiary_name: str
    department: str
    revenue: float
    expenses: float
    operating_income: float
    currency: str


class SubsidiaryDrilldownResponse(BaseModel):
    source: Literal["mock"]
    period: str
    subsidiary_id: str
    lines: list[SubsidiaryDrilldownLine]


class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    customer: str
    account_manager: str
    subsidiary_id: str
    status: Literal["on_track", "at_risk", "overdue"]
    budget: float
    actual_cost: float
    forecast_cost: float
    currency: str


class RunningProjectsResponse(BaseModel):
    source: Literal["mock"]
    account_manager: str | None
    subsidiary_id: str | None
    projects: list[ProjectSummary]


class OverdueProjectManager(BaseModel):
    account_manager: str
    overdue_project_count: int
    total_overdue_amount: float
    max_days_overdue: int
    currency: str


class OverdueProjectsByManagerResponse(BaseModel):
    source: Literal["mock"]
    min_days_overdue: int
    managers: list[OverdueProjectManager]
