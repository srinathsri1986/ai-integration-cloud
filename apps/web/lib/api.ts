import type {
  AuditLogEntry,
  AuditLogSummary,
  LoginResponse,
  CfoDashboardSummary,
  ConnectorListItem,
  FlowDefinition,
  FlowId,
  FlowRunResponse,
  NetSuiteConnectionTestResponse,
  NetSuiteConnectorConfig,
  NetSuiteConnectorConfigUpdate,
  OverdueProjectsByManagerResponse,
  OrchestratorQueryRequest,
  OrchestratorQueryResponse,
  PlVsBudgetResponse,
  RunningProjectsResponse,
  SubsidiaryDrilldownResponse,
  YoyComparisonResponse
} from "@netsuite-cfo/shared";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const LOCAL_AUTH_STORAGE_KEY = "netsuite-cfo-placeholder-token";

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
  executiveNarrative: "The AI Query Console could not generate an executive narrative.",
  fallbackUsed: true,
  aiProvider: "none",
  aiMode: "rule_based",
  modelName: null,
  modelCallAttempted: false,
  modelCallSucceeded: false,
  usedFallbackRouter: true,
  narrativeProvider: "none",
  narrativeModel: null,
  narrativeGenerated: false,
  narrativeFallbackUsed: false
};

const fallbackAuditLogs: AuditLogEntry[] = [];

const fallbackAuditSummary: AuditLogSummary = {
  total: 0,
  successes: 0,
  failures: 0,
  fallbackCount: 0,
  averageLatencyMs: 0,
  byIntent: {}
};

const fallbackNetSuiteConnectorConfig: NetSuiteConnectorConfig = {
  accountId: "MOCK-ACCOUNT",
  environment: "sandbox",
  authMode: "placeholder",
  mockMode: true,
  mode: "mock",
  status: "not_configured",
  lastTestedAt: null,
  baseUrlConfigured: false,
  credentialsConfigured: false
};

const fallbackConnectorList: ConnectorListItem[] = [
  {
    id: "netsuite",
    name: "NetSuite",
    status: "not_configured",
    mockMode: true,
    mode: "mock",
    lastTestedAt: null
  }
];

const fallbackConnectionTestResponse: NetSuiteConnectionTestResponse = {
  connectorId: "netsuite",
  success: false,
  status: "test_failed",
  message: "The connector API is unavailable.",
  testedAt: new Date(0).toISOString(),
  mockMode: true,
  mode: "mock",
  baseUrlConfigured: false,
  credentialsConfigured: false
};

const fallbackFlows: FlowDefinition[] = [
  {
    flowId: "netsuite-cfo-dashboard-refresh",
    name: "NetSuite CFO dashboard refresh",
    description: "Refreshes executive CFO dashboard metrics from approved mock NetSuite data.",
    sourceConnector: "netsuite",
    targetModule: "cfo_dashboard",
    status: "active",
    lastRunAt: null,
    lastRunStatus: "never_run",
    steps: [
      {
        id: "summary",
        name: "Load CFO summary",
        description: "Fetch cash, receivables, revenue, and KPI summary.",
        approvedTool: "cfo.dashboard_summary"
      },
      {
        id: "budget",
        name: "Load P/L vs budget",
        description: "Fetch approved P/L vs budget mock data for 2026-Q1.",
        approvedTool: "cfo.pl_vs_budget"
      }
    ]
  },
  {
    flowId: "netsuite-project-risk-refresh",
    name: "NetSuite project risk refresh",
    description: "Refreshes running project exposure and overdue project risk views.",
    sourceConnector: "netsuite",
    targetModule: "project_risk",
    status: "active",
    lastRunAt: null,
    lastRunStatus: "never_run",
    steps: [
      {
        id: "running-projects",
        name: "Load running projects",
        description: "Fetch active project financial exposure from approved mock data.",
        approvedTool: "cfo.running_projects"
      },
      {
        id: "overdue-projects",
        name: "Load overdue projects",
        description: "Summarize overdue projects by account manager.",
        approvedTool: "cfo.overdue_projects_by_account_manager"
      }
    ]
  },
  {
    flowId: "netsuite-subsidiary-drilldown-refresh",
    name: "NetSuite subsidiary drilldown refresh",
    description: "Refreshes subsidiary operating performance using approved mock data.",
    sourceConnector: "netsuite",
    targetModule: "subsidiary_drilldown",
    status: "active",
    lastRunAt: null,
    lastRunStatus: "never_run",
    steps: [
      {
        id: "subsidiary",
        name: "Load subsidiary drilldown",
        description: "Fetch EMEA operating performance for 2026-Q1.",
        approvedTool: "cfo.subsidiary_drilldown"
      },
      {
        id: "orchestrator-summary",
        name: "Route CFO summary prompt",
        description: "Route a deterministic supported CFO summary question.",
        approvedTool: "orchestrator.query"
      }
    ]
  }
];

const fallbackFlowRunResponse: FlowRunResponse = {
  requestId: "unavailable",
  flowId: "netsuite-cfo-dashboard-refresh",
  status: "failed",
  startedAt: new Date(0).toISOString(),
  completedAt: new Date(0).toISOString(),
  toolsUsed: [],
  message: "The flow API is unavailable.",
  data: {}
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

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") {
    return {};
  }

  const token = window.localStorage.getItem(LOCAL_AUTH_STORAGE_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
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

export async function getAuditLogs(): Promise<ApiResult<AuditLogEntry[]>> {
  return getApiResult("/api/v1/audit/logs", fallbackAuditLogs, (body) => body);
}

export async function getAuditSummary(): Promise<ApiResult<AuditLogSummary>> {
  return getApiResult("/api/v1/audit/summary", fallbackAuditSummary, (body) => body);
}

export async function getConnectors(): Promise<ApiResult<ConnectorListItem[]>> {
  return getApiResult("/api/v1/connectors", fallbackConnectorList, (body) => body);
}

export async function getNetSuiteConnectorConfig(): Promise<ApiResult<NetSuiteConnectorConfig>> {
  return getApiResult(
    "/api/v1/connectors/netsuite",
    fallbackNetSuiteConnectorConfig,
    (body) => body
  );
}

export async function testNetSuiteConnection(): Promise<
  ClientApiResult<NetSuiteConnectionTestResponse>
> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/connectors/netsuite/test`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallbackConnectionTestResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackConnectionTestResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function updateNetSuiteConnectorConfig(
  request: NetSuiteConnectorConfigUpdate
): Promise<ClientApiResult<NetSuiteConnectorConfig>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/connectors/netsuite/config`, {
      body: JSON.stringify({ ...request, mockMode: true, authMode: "placeholder" }),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "PUT"
    });

    if (!response.ok) {
      return {
        data: fallbackNetSuiteConnectorConfig,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackNetSuiteConnectorConfig,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function getFlows(): Promise<ApiResult<FlowDefinition[]>> {
  return getApiResult("/api/v1/flows", fallbackFlows, (body) => body);
}

export async function runFlow(flowId: FlowId): Promise<ClientApiResult<FlowRunResponse>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/flows/${flowId}/run`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: { ...fallbackFlowRunResponse, flowId },
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { ...fallbackFlowRunResponse, flowId },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function submitOrchestratorQuery(
  request: OrchestratorQueryRequest
): Promise<ClientApiResult<OrchestratorQueryResponse>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/orchestrator/query`, {
      body: JSON.stringify(request),
      cache: "no-store",
      headers: {
        ...authHeaders(),
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

export async function loginWithRole(role: LoginResponse["user"]["role"]): Promise<ClientApiResult<LoginResponse>> {
  const fallback: LoginResponse = {
    accessToken: "",
    tokenType: "bearer",
    user: {
      email: "local-dev@example.com",
      role,
      userId: "local-dev-user"
    }
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      body: JSON.stringify({ email: "local-dev@example.com", role }),
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallback,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCAL_AUTH_STORAGE_KEY, body.accessToken);
    }
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallback,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}
