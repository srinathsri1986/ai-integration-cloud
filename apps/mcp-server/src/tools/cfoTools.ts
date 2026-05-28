import {
  cfoDashboardSummarySchema,
  overdueProjectsByAccountManagerInputSchema,
  overdueProjectsByManagerResponseSchema,
  plVsBudgetInputSchema,
  plVsBudgetResponseSchema,
  runningProjectsInputSchema,
  runningProjectsResponseSchema,
  subsidiaryDrilldownInputSchema,
  subsidiaryDrilldownResponseSchema,
  yoyComparisonInputSchema,
  yoyComparisonResponseSchema
} from "../schemas/cfo.js";
import { getJson, withQuery } from "./apiClient.js";

function textResult(data: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(data, null, 2)
      }
    ]
  };
}

function dashboardSummaryFromApi(body: any) {
  return {
    generatedAt: body.generated_at,
    mode: body.mode,
    cashPosition: body.cash_position,
    openReceivables: body.open_receivables,
    monthlyRevenue: body.monthly_revenue,
    kpis: body.kpis
  };
}

function plVsBudgetFromApi(body: any) {
  return {
    source: body.source,
    period: body.period,
    subsidiaryId: body.subsidiary_id,
    lines: body.lines.map((line: any) => ({
      period: line.period,
      subsidiaryId: line.subsidiary_id,
      line: line.line,
      actual: line.actual,
      budget: line.budget,
      variance: line.variance,
      variancePct: line.variance_pct,
      currency: line.currency
    }))
  };
}

function yoyComparisonFromApi(body: any) {
  return {
    source: body.source,
    currentYear: body.current_year,
    priorYear: body.prior_year,
    subsidiaryId: body.subsidiary_id,
    lines: body.lines.map((line: any) => ({
      currentYear: line.current_year,
      priorYear: line.prior_year,
      subsidiaryId: line.subsidiary_id,
      metric: line.metric,
      currentValue: line.current_value,
      priorValue: line.prior_value,
      change: line.change,
      changePct: line.change_pct,
      currency: line.currency
    }))
  };
}

function subsidiaryDrilldownFromApi(body: any) {
  return {
    source: body.source,
    period: body.period,
    subsidiaryId: body.subsidiary_id,
    lines: body.lines.map((line: any) => ({
      period: line.period,
      subsidiaryId: line.subsidiary_id,
      subsidiaryName: line.subsidiary_name,
      department: line.department,
      revenue: line.revenue,
      expenses: line.expenses,
      operatingIncome: line.operating_income,
      currency: line.currency
    }))
  };
}

function runningProjectsFromApi(body: any) {
  return {
    source: body.source,
    accountManager: body.account_manager,
    subsidiaryId: body.subsidiary_id,
    projects: body.projects.map((project: any) => ({
      projectId: project.project_id,
      projectName: project.project_name,
      customer: project.customer,
      accountManager: project.account_manager,
      subsidiaryId: project.subsidiary_id,
      status: project.status,
      budget: project.budget,
      actualCost: project.actual_cost,
      forecastCost: project.forecast_cost,
      currency: project.currency
    }))
  };
}

function overdueProjectsFromApi(body: any) {
  return {
    source: body.source,
    minDaysOverdue: body.min_days_overdue,
    managers: body.managers.map((manager: any) => ({
      accountManager: manager.account_manager,
      overdueProjectCount: manager.overdue_project_count,
      totalOverdueAmount: manager.total_overdue_amount,
      maxDaysOverdue: manager.max_days_overdue,
      currency: manager.currency
    }))
  };
}

export async function getCfoDashboardSummary() {
  const body = await getJson<unknown>("/api/v1/cfo/dashboard-summary");
  const summary = cfoDashboardSummarySchema.parse(dashboardSummaryFromApi(body));
  return textResult(summary);
}

export async function getPlVsBudget(input: unknown) {
  const parsed = plVsBudgetInputSchema.parse(input);
  const body = await getJson<unknown>(
    withQuery("/api/v1/cfo/pl-vs-budget", {
      period: parsed.period,
      subsidiary_id: parsed.subsidiaryId
    })
  );
  const result = plVsBudgetResponseSchema.parse(plVsBudgetFromApi(body));
  return textResult(result);
}

export async function getYoyComparison(input: unknown) {
  const parsed = yoyComparisonInputSchema.parse(input);
  const body = await getJson<unknown>(
    withQuery("/api/v1/cfo/yoy-comparison", {
      current_year: parsed.currentYear,
      prior_year: parsed.priorYear,
      subsidiary_id: parsed.subsidiaryId
    })
  );
  const result = yoyComparisonResponseSchema.parse(yoyComparisonFromApi(body));
  return textResult(result);
}

export async function getSubsidiaryDrilldown(input: unknown) {
  const parsed = subsidiaryDrilldownInputSchema.parse(input);
  const body = await getJson<unknown>(
    withQuery("/api/v1/cfo/subsidiary-drilldown", {
      period: parsed.period,
      subsidiary_id: parsed.subsidiaryId
    })
  );
  const result = subsidiaryDrilldownResponseSchema.parse(subsidiaryDrilldownFromApi(body));
  return textResult(result);
}

export async function getRunningProjects(input: unknown) {
  const parsed = runningProjectsInputSchema.parse(input);
  const body = await getJson<unknown>(
    withQuery("/api/v1/cfo/running-projects", {
      account_manager: parsed.accountManager,
      subsidiary_id: parsed.subsidiaryId
    })
  );
  const result = runningProjectsResponseSchema.parse(runningProjectsFromApi(body));
  return textResult(result);
}

export async function getOverdueProjectsByAccountManager(input: unknown) {
  const parsed = overdueProjectsByAccountManagerInputSchema.parse(input);
  const body = await getJson<unknown>(
    withQuery("/api/v1/cfo/overdue-projects/by-account-manager", {
      min_days_overdue: parsed.minDaysOverdue
    })
  );
  const result = overdueProjectsByManagerResponseSchema.parse(overdueProjectsFromApi(body));
  return textResult(result);
}
