import type {
  CfoDashboardSummary,
  OverdueProjectsByManagerResponse,
  OrchestratorQueryRequest,
  OrchestratorQueryResponse,
  PlVsBudgetResponse,
  RunningProjectsResponse,
  SubsidiaryDrilldownResponse,
  YoyComparisonResponse
} from "@netsuite-cfo/shared";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiResult<T> = {
  data: T;
  error?: string;
  isFallback: boolean;
};

export type ClientApiResult<T> = ApiResult<T> & {
  ok: boolean;
};

const fallbackDashboardSummary: CfoDashboardSummary = {
  generatedAt: new Date(0).toISOString(),
  mode: "mock",
  cashPosition: {
    amount: 4_250_000,
    currency: "USD"
  },
  openReceivables: {
    amount: 1_175_000,
    currency: "USD"
  },
  monthlyRevenue: {
    amount: 2_980_000,
    currency: "USD"
  },
  kpis: [
    {
      label: "Cash runway",
      value: "14.2 months",
      trend: "up",
      narrative: "Mock operating cash trend improved against the prior period."
    },
    {
      label: "DSO",
      value: 42,
      trend: "down",
      narrative: "Mock receivables collection velocity improved by 3 days."
    },
    {
      label: "Gross margin",
      value: "61.4%",
      trend: "flat",
      narrative: "Mock margin stayed within the expected operating band."
    }
  ]
};

const fallbackPlVsBudget: PlVsBudgetResponse = {
  source: "mock",
  period: "2026-Q1",
  subsidiaryId: "NA",
  lines: [
    {
      period: "2026-Q1",
      subsidiaryId: "NA",
      line: "Revenue",
      actual: 8_270_000,
      budget: 7_950_000,
      variance: 320_000,
      variancePct: 4.03,
      currency: "USD"
    },
    {
      period: "2026-Q1",
      subsidiaryId: "NA",
      line: "Cost of revenue",
      actual: 3_180_000,
      budget: 3_250_000,
      variance: 70_000,
      variancePct: 2.15,
      currency: "USD"
    }
  ]
};

const fallbackYoyComparison: YoyComparisonResponse = {
  source: "mock",
  currentYear: 2026,
  priorYear: 2025,
  subsidiaryId: "NA",
  lines: [
    {
      currentYear: 2026,
      priorYear: 2025,
      subsidiaryId: "NA",
      metric: "Revenue",
      currentValue: 8_270_000,
      priorValue: 7_610_000,
      change: 660_000,
      changePct: 8.67,
      currency: "USD"
    },
    {
      currentYear: 2026,
      priorYear: 2025,
      subsidiaryId: "NA",
      metric: "Gross margin",
      currentValue: 5_090_000,
      priorValue: 4_630_000,
      change: 460_000,
      changePct: 9.94,
      currency: "USD"
    }
  ]
};

const fallbackSubsidiaryDrilldown: SubsidiaryDrilldownResponse = {
  source: "mock",
  period: "2026-Q1",
  subsidiaryId: "EMEA",
  lines: [
    {
      period: "2026-Q1",
      subsidiaryId: "EMEA",
      subsidiaryName: "EMEA",
      department: "Enterprise Services",
      revenue: 4_430_000,
      expenses: 1_820_000,
      operatingIncome: 2_610_000,
      currency: "USD"
    }
  ]
};

const fallbackRunningProjects: RunningProjectsResponse = {
  source: "mock",
  accountManager: null,
  subsidiaryId: null,
  projects: [
    {
      projectId: "PRJ-1001",
      projectName: "Revenue Automation Rollout",
      customer: "Aster Manufacturing",
      accountManager: "Maya Rao",
      subsidiaryId: "NA",
      status: "on_track",
      budget: 420_000,
      actualCost: 231_000,
      forecastCost: 398_000,
      currency: "USD"
    },
    {
      projectId: "PRJ-1002",
      projectName: "Multi-Book Close Optimization",
      customer: "Northstar Retail",
      accountManager: "Ethan Chen",
      subsidiaryId: "NA",
      status: "at_risk",
      budget: 360_000,
      actualCost: 292_000,
      forecastCost: 388_000,
      currency: "USD"
    },
    {
      projectId: "PRJ-2001",
      projectName: "EMEA RevRec Controls",
      customer: "Helio Foods",
      accountManager: "Maya Rao",
      subsidiaryId: "EMEA",
      status: "on_track",
      budget: 280_000,
      actualCost: 141_000,
      forecastCost: 265_000,
      currency: "USD"
    }
  ]
};

const fallbackOverdueProjects: OverdueProjectsByManagerResponse = {
  source: "mock",
  minDaysOverdue: 1,
  managers: [
    {
      accountManager: "Maya Rao",
      overdueProjectCount: 2,
      totalOverdueAmount: 145_000,
      maxDaysOverdue: 31,
      currency: "USD"
    },
    {
      accountManager: "Ethan Chen",
      overdueProjectCount: 1,
      totalOverdueAmount: 82_000,
      maxDaysOverdue: 18,
      currency: "USD"
    }
  ]
};

const fallbackOrchestratorResponse: OrchestratorQueryResponse = {
  detectedIntent: "UNKNOWN",
  confidence: 0,
  toolsUsed: [],
  data: { message: "The orchestrator API is unavailable." },
  executiveSummary: "The AI Query Console could not reach the rule-based orchestrator.",
  fallbackUsed: true
};

function snakeToDashboardSummary(body: any): CfoDashboardSummary {
  return {
    generatedAt: body.generated_at,
    mode: body.mode,
    cashPosition: body.cash_position,
    openReceivables: body.open_receivables,
    monthlyRevenue: body.monthly_revenue,
    kpis: body.kpis
  };
}

function snakeToPlVsBudget(body: any): PlVsBudgetResponse {
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

function snakeToYoyComparison(body: any): YoyComparisonResponse {
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

function snakeToSubsidiaryDrilldown(body: any): SubsidiaryDrilldownResponse {
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

function snakeToRunningProjects(body: any): RunningProjectsResponse {
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

function snakeToOverdueProjects(body: any): OverdueProjectsByManagerResponse {
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

async function getApiResult<T>(
  path: string,
  fallback: T,
  transform: (body: any) => T
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return {
        data: fallback,
        error: `API returned ${response.status}`,
        isFallback: true
      };
    }

    const body = await response.json();
    return { data: transform(body), isFallback: false };
  } catch (error) {
    return {
      data: fallback,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true
    };
  }
}

export async function getDashboardSummary(): Promise<ApiResult<CfoDashboardSummary>> {
  return getApiResult(
    "/api/v1/cfo/dashboard-summary",
    fallbackDashboardSummary,
    snakeToDashboardSummary
  );
}

export async function getPlVsBudget(): Promise<ApiResult<PlVsBudgetResponse>> {
  return getApiResult(
    "/api/v1/cfo/pl-vs-budget?period=2026-Q1&subsidiary_id=NA",
    fallbackPlVsBudget,
    snakeToPlVsBudget
  );
}

export async function getYoyComparison(): Promise<ApiResult<YoyComparisonResponse>> {
  return getApiResult(
    "/api/v1/cfo/yoy-comparison?current_year=2026&prior_year=2025&subsidiary_id=NA",
    fallbackYoyComparison,
    snakeToYoyComparison
  );
}

export async function getSubsidiaryDrilldown(): Promise<ApiResult<SubsidiaryDrilldownResponse>> {
  return getApiResult(
    "/api/v1/cfo/subsidiary-drilldown?period=2026-Q1&subsidiary_id=EMEA",
    fallbackSubsidiaryDrilldown,
    snakeToSubsidiaryDrilldown
  );
}

export async function getRunningProjects(): Promise<ApiResult<RunningProjectsResponse>> {
  return getApiResult(
    "/api/v1/cfo/running-projects",
    fallbackRunningProjects,
    snakeToRunningProjects
  );
}

export async function getOverdueProjects(): Promise<ApiResult<OverdueProjectsByManagerResponse>> {
  return getApiResult(
    "/api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=1",
    fallbackOverdueProjects,
    snakeToOverdueProjects
  );
}

export async function submitOrchestratorQuery(
  request: OrchestratorQueryRequest
): Promise<ClientApiResult<OrchestratorQueryResponse>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/orchestrator/query`, {
      body: JSON.stringify(request),
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallbackOrchestratorResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: Boolean(body.fallbackUsed), ok: true };
  } catch (error) {
    return {
      data: fallbackOrchestratorResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}
