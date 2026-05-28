from typing import Literal

from pydantic import BaseModel


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
