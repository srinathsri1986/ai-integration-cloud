import type {
  AuditLogEntry,
  AuditLogSummary,
  LoginResponse,
  CfoDashboardSummary,
  ConnectorDefinition,
  ConnectorListItem,
  ConnectorTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowId,
  FlowLifecycleAction,
  FlowLifecycleResponse,
  FlowRunResponse,
  FlowSuggestionRequest,
  FlowSuggestionResponse,
  MappingSuggestionRequest,
  MappingSuggestionResponse,
  MappingDefinition,
  MappingDefinitionUpsertRequest,
  MappingLifecycleAction,
  MappingLifecycleResponse,
  MappingSimulationResponse,
  NetSuiteConnectionTestResponse,
  NetSuiteConnectorConfig,
  NetSuiteConnectorConfigUpdate,
  OverdueProjectsByManagerResponse,
  OrchestratorQueryRequest,
  OrchestratorQueryResponse,
  PlVsBudgetResponse,
  RestApiApprovedObject,
  RestApiConnectionTestResponse,
  RestApiConnectorConfig,
  RestApiConnectorConfigUpdate,
  RestApiSchemaDiscoveryRequest,
  RestApiSchemaDiscoveryResponse,
  RestApiSchemaPromotionRequest,
  RestApiSchemaPromotionResponse,
  RunningProjectsResponse,
  SubsidiaryDrilldownResponse,
  YoyComparisonResponse
} from "@ai-integration-cloud/shared";

// Browser-facing URL (exposed to client bundle via NEXT_PUBLIC_ prefix)
const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
// Server-only URL for SSR fetches inside Docker (container-to-container)
// Falls back to PUBLIC_API_BASE_URL for local dev (both resolve to localhost)
const SERVER_API_BASE_URL = process.env.SERVER_API_BASE_URL ?? PUBLIC_API_BASE_URL;

/** Returns the correct base URL depending on execution context. */
function apiBaseUrl(): string {
  return typeof window === "undefined" ? SERVER_API_BASE_URL : PUBLIC_API_BASE_URL;
}

export const LOCAL_AUTH_TOKEN_KEY = "netsuite-cfo-placeholder-token";
const LOCAL_AUTH_STORAGE_KEY = LOCAL_AUTH_TOKEN_KEY;
export const LOCAL_AUTH_ROLE_KEY = "netsuite-cfo-placeholder-role";
export const LOCAL_AUTH_EMAIL_KEY = "netsuite-cfo-placeholder-email";

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

const fallbackRestApiConnectorConfig: RestApiConnectorConfig = {
  connectorId: "rest-api",
  displayName: "Generic REST API",
  baseUrlPlaceholder: "https://api.example.com",
  authMode: "placeholder",
  mockMode: true,
  mode: "mock",
  status: "not_configured",
  lastTestedAt: null,
  baseUrlConfigured: false,
  credentialsConfigured: false,
  approvedObjects: ["customer", "invoice", "opportunity"],
  approvedActions: ["read_sample", "validate_payload", "simulate_post_placeholder"]
};

const fallbackConnectorList: ConnectorListItem[] = [
  { id: "salesforce", name: "Salesforce",      status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "netsuite",   name: "Oracle NetSuite",  status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "sap",        name: "SAP",              status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "oracle",     name: "Oracle ERP",       status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "hcm",        name: "HCM (Workday)",    status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "postgres",   name: "PostgreSQL",       status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "rest-api",   name: "REST API",         status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
  { id: "slack",      name: "Slack",            status: "not_configured", mockMode: true, mode: "mock", lastTestedAt: null },
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

const fallbackRestApiConnectionTestResponse: RestApiConnectionTestResponse = {
  connectorId: "rest-api",
  success: false,
  status: "test_failed",
  message: "The REST connector API is unavailable.",
  testedAt: new Date(0).toISOString(),
  mockMode: true,
  mode: "mock",
  baseUrlConfigured: false,
  credentialsConfigured: false,
  approvedObjects: ["customer", "invoice", "opportunity"],
  approvedActions: ["read_sample", "validate_payload", "simulate_post_placeholder"]
};

const fallbackRestApiObjects: RestApiApprovedObject[] = [
  {
    objectId: "customer",
    label: "Customer",
    description: "Approved customer profile shape for REST API mappings.",
    fields: [
      { name: "externalId", label: "External ID", type: "string", required: true },
      { name: "displayName", label: "Display name", type: "string", required: true },
      { name: "status", label: "Status", type: "string", required: false },
      { name: "region", label: "Region", type: "string", required: false }
    ]
  },
  {
    objectId: "invoice",
    label: "Invoice",
    description: "Approved invoice header shape for finance API mappings.",
    fields: [
      { name: "invoiceNumber", label: "Invoice number", type: "string", required: true },
      { name: "customerExternalId", label: "Customer external ID", type: "string", required: true },
      { name: "amount", label: "Amount", type: "number", required: true },
      { name: "invoiceDate", label: "Invoice date", type: "date", required: true }
    ]
  },
  {
    objectId: "opportunity",
    label: "Opportunity",
    description: "Approved opportunity shape for pipeline-to-finance handoffs.",
    fields: [
      { name: "opportunityId", label: "Opportunity ID", type: "string", required: true },
      { name: "accountName", label: "Account name", type: "string", required: true },
      { name: "amount", label: "Amount", type: "number", required: false },
      { name: "closeDate", label: "Close date", type: "date", required: false }
    ]
  }
];

const fallbackRestApiSchemaDiscoveryResponse: RestApiSchemaDiscoveryResponse = {
  connectorId: "rest-api",
  objectId: "rest-discovered-fallback-object",
  objectLabel: "Fallback Object",
  mode: "schema_discovery",
  fields: [],
  warnings: ["The REST schema discovery API is unavailable."],
  generatedFromSample: false,
  executable: false
};

const fallbackRestApiSchemaPromotionResponse: RestApiSchemaPromotionResponse = {
  connectorId: "rest-api",
  promoted: false,
  objectId: "rest-governed-fallback-object",
  objectLabel: "Fallback Object",
  mappingObject: {
    displayName: "Fallback Object",
    fields: [],
    id: "rest-governed-fallback-object",
    systemId: "rest-api"
  },
  message: "The REST schema promotion API is unavailable.",
  warnings: ["Promotion could not be completed."]
};

const fallbackFlows: FlowDefinition[] = [
  {
    flowId: "demo-netsuite-cfo-dashboard",
    name: "NetSuite CFO Dashboard Refresh",
    description: "Refreshes executive CFO dashboard metrics from approved mock NetSuite data.",
    sourceConnector: "netsuite",
    targetModule: "cfo_dashboard",
    status: "published",
    triggerType: "manual",
    mappingDefinitionId: null,
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
    flowId: "demo-salesforce-opportunity-sync",
    name: "Salesforce Opportunity Sync",
    description: "Pulls open opportunities from Salesforce CRM and lists them in the activity feed.",
    sourceConnector: "salesforce",
    targetModule: "crm_sync",
    status: "published",
    triggerType: "manual",
    mappingDefinitionId: null,
    lastRunAt: null,
    lastRunStatus: "never_run",
    steps: [
      {
        id: "list-opportunities",
        name: "List open opportunities",
        description: "Fetch open opportunities from Salesforce.",
        approvedTool: "list_opportunities"
      }
    ]
  },
  {
    flowId: "demo-slack-alert-dispatch",
    name: "Slack Alert Dispatch",
    description: "Posts a system alert message to the approved Slack alerts channel.",
    sourceConnector: "slack",
    targetModule: "alerting",
    status: "published",
    triggerType: "manual",
    mappingDefinitionId: null,
    lastRunAt: null,
    lastRunStatus: "never_run",
    steps: [
      {
        id: "post-alert",
        name: "Post alert message",
        description: "Send alert text to the approved alerts channel.",
        approvedTool: "post_message"
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
  data: {},
  executionTimeline: [],
  inspection: {
    auditRequestId: "unavailable",
    durationMs: 0,
    failedSteps: 0,
    hasSourcePayload: false,
    hasTargetPayload: false,
    mappingDefinitionId: null,
    skippedSteps: 0,
    stepCount: 0,
    succeededSteps: 0,
    warningCount: 0
  }
};

const fallbackFlowLifecycleResponse: FlowLifecycleResponse = {
  action: "pause",
  flow: fallbackFlows[0],
  message: "The flow lifecycle API is unavailable."
};

const fallbackFlowSuggestionResponse: FlowSuggestionResponse = {
  prompt: "Create a CFO dashboard refresh flow.",
  suggestedFlow: {
    description: "Draft CFO orchestration generated from approved NetSuite actions only.",
    flowId: "ai-drafted-cfo-flow",
    name: "AI drafted CFO flow",
    sourceConnector: "netsuite",
    status: "draft",
    mappingDefinitionId: null,
    steps: [
      {
        approvedTool: "cfo.dashboard_summary",
        description: "Load approved CFO dashboard summary data.",
        id: "load-cfo-summary",
        name: "Load CFO summary"
      },
      {
        approvedTool: "cfo.pl_vs_budget",
        description: "Compare approved P/L actuals against budget.",
        id: "compare-pl-budget",
        name: "Compare P/L vs budget"
      }
    ],
    targetModule: "cfo_dashboard",
    triggerType: "manual"
  },
  rationale: "Fallback draft uses only approved NetSuite CFO actions.",
  suggestionProvider: "template",
  suggestionModel: null,
  suggestionGenerated: true,
  suggestionFallbackUsed: true,
  modelCallAttempted: false,
  modelCallSucceeded: false
};

const fallbackMappingSuggestionResponse: MappingSuggestionResponse = {
  prompt: "Map project fields into the selected target object.",
  sourceObjectId: "netsuite-project",
  targetObjectId: "salesforce-opportunity",
  suggestions: [
    {
      confidence: 0.94,
      rationale: "Customer names align to the target account reference.",
      sourceField: "customer_name",
      targetField: "AccountName",
      transform: "direct"
    },
    {
      confidence: 0.91,
      rationale: "Budget and amount fields share numeric finance meaning.",
      sourceField: "budget_amount",
      targetField: "Amount",
      transform: "direct"
    },
    {
      confidence: 0.88,
      rationale: "Date values need target system date formatting.",
      sourceField: "due_date",
      targetField: "CloseDate",
      transform: "format_date"
    }
  ],
  suggestionProvider: "template",
  suggestionModel: null,
  suggestionGenerated: true,
  suggestionFallbackUsed: true,
  modelCallAttempted: false,
  modelCallSucceeded: false
};

const fallbackMappingDefinitions: MappingDefinition[] = [];

const fallbackMappingDefinition: MappingDefinition = {
  createdAt: null,
  description: "Local fallback mapping definition.",
  mappingId: "fallback-mapping",
  mappings: [],
  name: "Fallback mapping",
  sourceObjectId: "netsuite-project",
  status: "draft",
  targetObjectId: "salesforce-opportunity",
  updatedAt: null
};

const fallbackMappingLifecycleResponse: MappingLifecycleResponse = {
  action: "pause",
  mapping: fallbackMappingDefinition,
  message: "The mapping lifecycle API is unavailable."
};

const fallbackMappingSimulationResponse: MappingSimulationResponse = {
  mappingId: "fallback-mapping",
  simulatedAt: new Date(0).toISOString(),
  sourceObjectId: "netsuite-project",
  sourcePayload: {},
  status: "draft",
  targetObjectId: "salesforce-opportunity",
  targetPayload: {},
  transformsApplied: [],
  warnings: ["The mapping simulation API is unavailable."]
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
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: "no-store",
      // Include auth token on the client; authHeaders() returns {} on the server
      headers: authHeaders(),
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

export interface AuditLogsFilter {
  intent?: string;
  success?: boolean;
  since?: string;   // ISO date "YYYY-MM-DD"
  until?: string;   // ISO date "YYYY-MM-DD"
  limit?: number;
  offset?: number;
}

export async function getAuditLogs(filter?: AuditLogsFilter): Promise<ApiResult<AuditLogEntry[]>> {
  const params = new URLSearchParams();
  if (filter?.intent)              params.set("intent", filter.intent);
  if (filter?.success !== undefined) params.set("success", String(filter.success));
  if (filter?.since)               params.set("since", filter.since);
  if (filter?.until)               params.set("until", filter.until);
  if (filter?.limit !== undefined) params.set("limit", String(filter.limit));
  if (filter?.offset !== undefined) params.set("offset", String(filter.offset));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return getApiResult(`/api/v1/audit/logs${qs}`, fallbackAuditLogs, (body) => body);
}

export async function getAuditSummary(): Promise<ApiResult<AuditLogSummary>> {
  return getApiResult("/api/v1/audit/summary", fallbackAuditSummary, (body) => body);
}

export interface AuditMetrics {
  totalEvents: number;
  successRate: number;
  averageLatencyMs: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  byIntent: Record<string, number>;
  byConnector: Record<string, number>;
  eventsPerDay: Array<{ date: string; total: number; successes: number; failures: number }>;
  distinctIntents: string[];
}

const fallbackAuditMetrics: AuditMetrics = {
  totalEvents: 0, successRate: 0, averageLatencyMs: 0,
  p50LatencyMs: 0, p95LatencyMs: 0,
  byIntent: {}, byConnector: {}, eventsPerDay: [], distinctIntents: [],
};

export async function getAuditMetrics(days = 30): Promise<ApiResult<AuditMetrics>> {
  return getApiResult(`/api/v1/audit/metrics?days=${days}`, fallbackAuditMetrics, (body) => body);
}

/** Build a direct download URL for the audit CSV export. */
export function auditExportUrl(filter?: AuditLogsFilter): string {
  const base = apiBaseUrl();
  const params = new URLSearchParams();
  if (filter?.intent)              params.set("intent", filter.intent);
  if (filter?.success !== undefined) params.set("success", String(filter.success));
  if (filter?.since)               params.set("since", filter.since);
  if (filter?.until)               params.set("until", filter.until);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return `${base}/api/v1/audit/export.csv${qs}`;
}

/** Returns all registered connectors (generic, connector-agnostic format). */
export async function getConnectors(): Promise<ApiResult<ConnectorDefinition[]>> {
  const fallbackGeneric: ConnectorDefinition[] = fallbackConnectorList.map((c) => ({
    connectorId: c.id,
    name: c.name,
    logoSlug: c.id,
    authScheme: "api_key" as const,
    status: c.status as ConnectorDefinition["status"],
    mode: c.mode as ConnectorDefinition["mode"],
    toolCount: 0,
    lastTestedAt: c.lastTestedAt ?? null,
  }));
  return getApiResult("/api/v1/connectors", fallbackGeneric, (body) =>
    Array.isArray(body)
      ? body.map((c: any) => ({
          connectorId: c.connectorId ?? c.id,
          name: c.name,
          logoSlug: c.logoSlug ?? c.id,
          authScheme: c.authScheme ?? "none",
          status: c.status ?? "not_configured",
          mode: c.mode ?? "mock",
          toolCount: c.toolCount ?? 0,
          lastTestedAt: c.lastTestedAt ?? null,
        }))
      : fallbackGeneric
  );
}

/** Returns tools for a specific connector. */
export async function getConnectorTools(connectorId: string): Promise<ApiResult<ConnectorTool[]>> {
  return getApiResult(
    `/api/v1/connectors/${encodeURIComponent(connectorId)}/tools`,
    [],
    (body) =>
      Array.isArray(body)
        ? body.map((t: any) => ({
            toolId: t.toolId,
            label: t.label,
            description: t.description,
            connectorId: t.connectorId,
            params: t.params,
          }))
        : []
  );
}

/** Test a connector connection (generic). Returns { ok, message }. */
export async function testConnector(connectorId: string): Promise<ClientApiResult<{ ok: boolean; message: string }>> {
  const fallback = { ok: false, message: "The connector API is unavailable." };
  try {
    const response = await fetch(
      `${apiBaseUrl()}/api/v1/connectors/${encodeURIComponent(connectorId)}/test`,
      { cache: "no-store", headers: authHeaders(), method: "POST" }
    );
    if (!response.ok) return { data: fallback, error: `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: await response.json(), isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

export async function getNetSuiteConnectorConfig(): Promise<ApiResult<NetSuiteConnectorConfig>> {
  return getApiResult(
    "/api/v1/connectors/netsuite/config",
    fallbackNetSuiteConnectorConfig,
    (body) => body
  );
}

export async function getRestApiConnectorConfig(): Promise<ApiResult<RestApiConnectorConfig>> {
  return getApiResult(
    "/api/v1/connectors/rest-api/config",
    fallbackRestApiConnectorConfig,
    (body) => body
  );
}

export async function getRestApiObjects(): Promise<ApiResult<RestApiApprovedObject[]>> {
  return getApiResult(
    "/api/v1/connectors/rest-api/objects",
    fallbackRestApiObjects,
    (body) => body
  );
}

export async function discoverRestApiSchema(
  request: RestApiSchemaDiscoveryRequest
): Promise<ClientApiResult<RestApiSchemaDiscoveryResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/rest-api/discover-schema`, {
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
        data: fallbackRestApiSchemaDiscoveryResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackRestApiSchemaDiscoveryResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function promoteRestApiSchema(
  request: RestApiSchemaPromotionRequest
): Promise<ClientApiResult<RestApiSchemaPromotionResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/rest-api/promote-schema`, {
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
        data: fallbackRestApiSchemaPromotionResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackRestApiSchemaPromotionResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function testNetSuiteConnection(): Promise<
  ClientApiResult<NetSuiteConnectionTestResponse>
> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/netsuite/legacy-test`, {
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

export async function testRestApiConnection(): Promise<
  ClientApiResult<RestApiConnectionTestResponse>
> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/rest-api/legacy-test`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallbackRestApiConnectionTestResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackRestApiConnectionTestResponse,
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
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/netsuite/config`, {
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

export async function updateRestApiConnectorConfig(
  request: RestApiConnectorConfigUpdate
): Promise<ClientApiResult<RestApiConnectorConfig>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/connectors/rest-api/config`, {
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
        data: fallbackRestApiConnectorConfig,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackRestApiConnectorConfig,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

const fallbackPaginatedFlows = {
  items: fallbackFlows,
  total: fallbackFlows.length,
  limit: 50,
  offset: 0,
};

export async function getFlows(): Promise<ApiResult<{ items: FlowDefinition[]; total: number; limit: number; offset: number }>> {
  return getApiResult(
    "/api/v1/flows",
    fallbackPaginatedFlows,
    (body) => ({
      items: Array.isArray(body) ? body : (body.items ?? []),
      total: body.total ?? (Array.isArray(body) ? body.length : 0),
      limit: body.limit ?? 50,
      offset: body.offset ?? 0,
    })
  );
}

export async function getFlow(flowId: FlowId): Promise<ApiResult<FlowDefinition>> {
  return getApiResult(
    `/api/v1/flows/${flowId}`,
    fallbackFlows[0],
    (body) => body
  );
}

export async function getFlowRunsForFlow(
  flowId: FlowId,
  limit = 10
): Promise<ApiResult<FlowRunResponse[]>> {
  return getApiResult(
    `/api/v1/flows/${flowId}/runs?limit=${limit}`,
    [],
    (body) => body.items ?? []
  );
}

export async function getRecentFlowRuns(limit = 20): Promise<ApiResult<FlowRunResponse[]>> {
  return getApiResult(
    `/api/v1/flows/runs?limit=${limit}`,
    [],
    (body) => body.items ?? []
  );
}

export async function runFlow(flowId: FlowId): Promise<ClientApiResult<FlowRunResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/${flowId}/run`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (response.status !== 202 && !response.ok) {
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

export async function replayFlowRun(requestId: string): Promise<ClientApiResult<FlowRunResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/runs/${requestId}/replay`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (response.status !== 202 && !response.ok) {
      const body = await response.json().catch(() => undefined);
      return {
        data: { ...fallbackFlowRunResponse, requestId },
        error: body?.detail ?? `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { ...fallbackFlowRunResponse, requestId },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function getFlowRun(requestId: string): Promise<ClientApiResult<FlowRunResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/runs/${requestId}`, {
      cache: "no-store",
      headers: authHeaders()
    });

    if (!response.ok) {
      return {
        data: { ...fallbackFlowRunResponse, requestId },
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { ...fallbackFlowRunResponse, requestId },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function transitionFlowLifecycle(
  flowId: FlowId,
  action: FlowLifecycleAction
): Promise<ClientApiResult<FlowLifecycleResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/${flowId}/lifecycle`, {
      body: JSON.stringify({ action }),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallbackFlowLifecycleResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackFlowLifecycleResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function deleteFlowDefinition(
  flowId: FlowId
): Promise<ClientApiResult<{ flowId: string; message: string }>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/${flowId}`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "DELETE"
    });

    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      return {
        data: { flowId, message: "Integration could not be deleted." },
        error: body?.detail ? String(body.detail) : `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { flowId, message: "Integration could not be deleted." },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function saveFlowDefinition(
  request: FlowDefinitionUpsertRequest
): Promise<ClientApiResult<FlowDefinition>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/definitions`, {
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
        data: fallbackFlows[0],
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackFlows[0],
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function suggestFlowDefinition(
  request: FlowSuggestionRequest
): Promise<ClientApiResult<FlowSuggestionResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/flows/suggestions`, {
      body: JSON.stringify(request),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      return {
        data: fallbackFlowSuggestionResponse,
        error: body?.detail ? String(body.detail) : `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: body.suggestionFallbackUsed, ok: true };
  } catch (error) {
    return {
      data: fallbackFlowSuggestionResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function suggestMappingDefinition(
  request: MappingSuggestionRequest
): Promise<ClientApiResult<MappingSuggestionResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/suggestions`, {
      body: JSON.stringify(request),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      return {
        data: {
          ...fallbackMappingSuggestionResponse,
          prompt: request.prompt,
          sourceObjectId: request.sourceObjectId,
          targetObjectId: request.targetObjectId
        },
        error: body?.detail ? String(body.detail) : `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: body.suggestionFallbackUsed, ok: true };
  } catch (error) {
    return {
      data: {
        ...fallbackMappingSuggestionResponse,
        prompt: request.prompt,
        sourceObjectId: request.sourceObjectId,
        targetObjectId: request.targetObjectId
      },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function getMappingDefinitions(): Promise<ClientApiResult<MappingDefinition[]>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/definitions`, {
      cache: "no-store",
      headers: authHeaders()
    });

    if (!response.ok) {
      return {
        data: fallbackMappingDefinitions,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackMappingDefinitions,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function saveMappingDefinition(
  request: MappingDefinitionUpsertRequest
): Promise<ClientApiResult<MappingDefinition>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/definitions`, {
      body: JSON.stringify(request),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      const detail = body?.detail
        ? Array.isArray(body.detail)
          ? body.detail.map((item: any) => item.msg ?? String(item)).join("; ")
          : String(body.detail)
        : undefined;
      return {
        data: { ...fallbackMappingDefinition, ...request },
        error: detail ?? `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { ...fallbackMappingDefinition, ...request },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function transitionMappingLifecycle(
  mappingId: string,
  action: MappingLifecycleAction,
  note?: string
): Promise<ClientApiResult<MappingLifecycleResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/definitions/${mappingId}/lifecycle`, {
      body: JSON.stringify({ action, note }),
      cache: "no-store",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: fallbackMappingLifecycleResponse,
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: fallbackMappingLifecycleResponse,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function deleteMappingDefinition(
  mappingId: string
): Promise<ClientApiResult<{ mappingId: string; message: string }>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/definitions/${mappingId}`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "DELETE"
    });

    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      return {
        data: { mappingId, message: "Mapping definition could not be deleted." },
        error: body?.detail ? String(body.detail) : `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { mappingId, message: "Mapping definition could not be deleted." },
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

export async function simulateMappingDefinition(
  mappingId: string
): Promise<ClientApiResult<MappingSimulationResponse>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/mappings/definitions/${mappingId}/simulate`, {
      cache: "no-store",
      headers: authHeaders(),
      method: "POST"
    });

    if (!response.ok) {
      return {
        data: { ...fallbackMappingSimulationResponse, mappingId },
        error: `API returned ${response.status}`,
        isFallback: true,
        ok: false
      };
    }

    const body = await response.json();
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return {
      data: { ...fallbackMappingSimulationResponse, mappingId },
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
    const response = await fetch(`${apiBaseUrl()}/api/v1/orchestrator/query`, {
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

// --- Real auth API calls ---

export type RegisterPayload = { email: string; password: string; role?: string };
export type LoginPayload = { email: string; password: string };

export async function registerUser(payload: RegisterPayload): Promise<ClientApiResult<{ email: string; message: string }>> {
  const fallback = { email: payload.email, message: "Registration failed." };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/register`, {
      body: JSON.stringify(payload),
      cache: "no-store",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    const body = await response.json();
    if (!response.ok) {
      return { data: fallback, error: body?.detail ?? `API returned ${response.status}`, isFallback: true, ok: false };
    }
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

export async function loginUser(payload: LoginPayload): Promise<ClientApiResult<LoginResponse>> {
  const fallback: LoginResponse = { accessToken: "", tokenType: "bearer", user: { email: payload.email, role: "Integration Admin", userId: "" } };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
      body: JSON.stringify(payload),
      cache: "no-store",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    const body = await response.json();
    if (!response.ok) {
      return { data: fallback, error: body?.detail ?? `API returned ${response.status}`, isFallback: true, ok: false };
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCAL_AUTH_ROLE_KEY, body.user.role);
      window.localStorage.setItem(LOCAL_AUTH_EMAIL_KEY, body.user.email);
    }
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${apiBaseUrl()}/api/v1/auth/logout`, { method: "POST", credentials: "include", cache: "no-store" });
  } catch {
    // best-effort
  }
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(LOCAL_AUTH_ROLE_KEY);
    window.localStorage.removeItem(LOCAL_AUTH_EMAIL_KEY);
    window.localStorage.removeItem(LOCAL_AUTH_STORAGE_KEY);
  }
}

export async function forgotPassword(email: string): Promise<ClientApiResult<{ message: string }>> {
  const fallback = { message: "If that email exists, a reset link has been sent." };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/forgot-password`, {
      body: JSON.stringify({ email }),
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    const body = await response.json();
    return { data: body, isFallback: false, ok: response.ok };
  } catch {
    return { data: fallback, isFallback: true, ok: false };
  }
}

export async function resetPassword(token: string, password: string): Promise<ClientApiResult<{ message: string }>> {
  const fallback = { message: "Password reset failed." };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/reset-password`, {
      body: JSON.stringify({ token, password }),
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    const body = await response.json();
    if (!response.ok) {
      return { data: fallback, error: body?.detail ?? `API returned ${response.status}`, isFallback: true, ok: false };
    }
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

// --- Legacy placeholder login (dev / persona picker) ---

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
    const response = await fetch(`${apiBaseUrl()}/api/v1/auth/login/placeholder`, {
      body: JSON.stringify({ email: "local-dev@example.com", role }),
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      method: "POST"
    });

    if (!response.ok) {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(LOCAL_AUTH_STORAGE_KEY);
        window.localStorage.setItem(LOCAL_AUTH_ROLE_KEY, fallback.user.role);
        window.localStorage.setItem(LOCAL_AUTH_EMAIL_KEY, fallback.user.email);
      }

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
      window.localStorage.setItem(LOCAL_AUTH_ROLE_KEY, body.user.role);
      window.localStorage.setItem(LOCAL_AUTH_EMAIL_KEY, body.user.email);
    }
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(LOCAL_AUTH_STORAGE_KEY);
      window.localStorage.setItem(LOCAL_AUTH_ROLE_KEY, fallback.user.role);
      window.localStorage.setItem(LOCAL_AUTH_EMAIL_KEY, fallback.user.email);
    }

    return {
      data: fallback,
      error: error instanceof Error ? error.message : "API unavailable",
      isFallback: true,
      ok: false
    };
  }
}

// --- Tenant API ---

export type TenantInfo = { id: number; name: string; slug: string; plan: string };
export type TenantMember = { userId: number; email: string; role: string };
export type PendingInvite = { id: number; email: string; role: string };

export async function getCurrentTenant(): Promise<ClientApiResult<TenantInfo>> {
  const fallback: TenantInfo = { id: 0, name: "Local Workspace", slug: "local", plan: "MVP" };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/tenants/me`, {
      cache: "no-store",
      credentials: "include",
      headers: authHeaders()
    });
    if (!response.ok) return { data: fallback, error: `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: await response.json(), isFallback: false, ok: true };
  } catch {
    return { data: fallback, isFallback: true, ok: false };
  }
}

export async function getTenantMembers(): Promise<ClientApiResult<TenantMember[]>> {
  const fallback: TenantMember[] = [];
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/tenants/me/members`, {
      cache: "no-store",
      credentials: "include",
      headers: authHeaders()
    });
    if (!response.ok) return { data: fallback, error: `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: await response.json(), isFallback: false, ok: true };
  } catch {
    return { data: fallback, isFallback: true, ok: false };
  }
}

export async function getPendingInvites(): Promise<ClientApiResult<PendingInvite[]>> {
  const fallback: PendingInvite[] = [];
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/tenants/me/members/invites`, {
      cache: "no-store",
      credentials: "include",
      headers: authHeaders()
    });
    if (!response.ok) return { data: fallback, error: `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: await response.json(), isFallback: false, ok: true };
  } catch {
    return { data: fallback, isFallback: true, ok: false };
  }
}

export async function inviteMember(email: string, role: string): Promise<ClientApiResult<{ message: string; email: string; role: string }>> {
  const fallback = { message: "Invite failed.", email, role };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/tenants/me/members/invite`, {
      body: JSON.stringify({ email, role }),
      cache: "no-store",
      credentials: "include",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      method: "POST"
    });
    const body = await response.json();
    if (!response.ok) return { data: fallback, error: body?.detail ?? `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

export async function removeMember(userId: number): Promise<ClientApiResult<{ message: string }>> {
  const fallback = { message: "Remove failed." };
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/tenants/me/members/${userId}`, {
      cache: "no-store",
      credentials: "include",
      headers: authHeaders(),
      method: "DELETE"
    });
    const body = await response.json();
    if (!response.ok) return { data: fallback, error: body?.detail ?? `API returned ${response.status}`, isFallback: true, ok: false };
    return { data: body, isFallback: false, ok: true };
  } catch (error) {
    return { data: fallback, error: error instanceof Error ? error.message : "API unavailable", isFallback: true, ok: false };
  }
}

// ---------------------------------------------------------------------------
// Webhook delivery tracking — Release 12.0
// ---------------------------------------------------------------------------

export interface WebhookDelivery {
  deliveryId: string;
  flowId: string;
  receivedAt: string;
  payloadHash: string;
  status: "processing" | "succeeded" | "failed" | "dead_letter";
  attemptCount: number;
  maxAttempts: number;
  lastError: string | null;
  requestId: string | null;
  nextRetryAt: string | null;
  completedAt: string | null;
}

export interface WebhookDeliveryStats {
  total: number;
  succeeded: number;
  failed: number;
  deadLetter: number;
  processing: number;
}

const _fallbackDeliveries: WebhookDelivery[] = [];
const _fallbackStats: WebhookDeliveryStats = { total: 0, succeeded: 0, failed: 0, deadLetter: 0, processing: 0 };

export async function getWebhookDeliveries(opts?: {
  flowId?: string;
  status?: string;
  limit?: number;
}): Promise<ApiResult<WebhookDelivery[]>> {
  const params = new URLSearchParams();
  if (opts?.flowId)  params.set("flow_id", opts.flowId);
  if (opts?.status)  params.set("status", opts.status);
  if (opts?.limit)   params.set("limit", String(opts.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return getApiResult(`/api/v1/webhooks/deliveries${qs}`, _fallbackDeliveries, (b) => b);
}

export async function getWebhookDeliveryStats(): Promise<ApiResult<WebhookDeliveryStats>> {
  return getApiResult("/api/v1/webhooks/deliveries/stats", _fallbackStats, (b) => b);
}

export async function getDeadLetterCount(): Promise<ApiResult<number>> {
  return getApiResult("/api/v1/webhooks/deliveries/dead-letter-count", 0, (b) => b);
}

export async function retryWebhookDelivery(deliveryId: string): Promise<ClientApiResult<unknown>> {
  const fallback = {};
  try {
    const response = await fetch(
      `${apiBaseUrl()}/api/v1/webhooks/deliveries/${encodeURIComponent(deliveryId)}/retry`,
      { method: "POST", credentials: "include" }
    );
    const body = await response.json();
    if (!response.ok) return { data: fallback, error: body?.detail ?? `HTTP ${response.status}`, isFallback: true, ok: false };
    return { data: body, isFallback: false, ok: true };
  } catch (err) {
    return { data: fallback, error: err instanceof Error ? err.message : "API unavailable", isFallback: true, ok: false };
  }
}

// ---------------------------------------------------------------------------
// Connector schema — Release 13.0
// ---------------------------------------------------------------------------

export interface ConnectorSchemaField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  updateable: boolean;
  sample: string | null;
}

export interface ConnectorSchemaObject {
  objectId: string;
  label: string;
  fields: ConnectorSchemaField[];
}

export interface ConnectorSchema {
  connectorId: string;
  mode: string;   // "live" | "mock"
  objects: ConnectorSchemaObject[];
  fetchedAt: string;
}

const _fallbackSchema: ConnectorSchema = {
  connectorId: "",
  mode: "mock",
  objects: [],
  fetchedAt: new Date(0).toISOString(),
};

export async function getConnectorSchema(
  connectorId: string,
): Promise<ApiResult<ConnectorSchema>> {
  return getApiResult(
    `/api/v1/connectors/${encodeURIComponent(connectorId)}/schema`,
    _fallbackSchema,
    (b) => b,
  );
}

// ─── R18a: Custom endpoint API ────────────────────────────────────────────────

import type {
  CustomEndpoint,
  FieldInfo,
  InlineFieldMapping,
  SchemaDiscoveryResponse,
} from "@ai-integration-cloud/shared";

export type { CustomEndpoint, FieldInfo, InlineFieldMapping, SchemaDiscoveryResponse };

export interface CustomEndpointCreatePayload {
  name: string;
  description?: string;
  baseUrl: string;
  authScheme: "none" | "api_key" | "bearer" | "basic";
  defaultPath?: string;
  httpMethod?: "GET" | "POST" | "PUT" | "PATCH";
  // Credentials — optional, encrypted server-side
  apiKey?: string;
  bearerToken?: string;
  username?: string;
  password?: string;
}

const _fallbackEndpoint: CustomEndpoint = {
  endpointId: "",
  tenantId: null,
  name: "Unknown",
  description: "",
  baseUrl: "",
  authScheme: "none",
  defaultPath: "/",
  httpMethod: "GET",
  fieldSchema: [],
  fieldCount: 0,
  hasCredentials: false,
  createdAt: new Date(0).toISOString(),
  updatedAt: new Date(0).toISOString(),
};

export async function createCustomEndpoint(
  payload: CustomEndpointCreatePayload,
): Promise<ClientApiResult<CustomEndpoint>> {
  try {
    const resp = await fetch(`${apiBaseUrl()}/api/v1/custom-endpoints`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
      return { data: _fallbackEndpoint, ok: false, isFallback: true, error: err.detail ?? `HTTP ${resp.status}` };
    }
    const data = await resp.json();
    return { data, ok: true, isFallback: false };
  } catch (e) {
    return { data: _fallbackEndpoint, ok: false, isFallback: true, error: e instanceof Error ? e.message : "API unavailable" };
  }
}

export async function listCustomEndpoints(): Promise<ApiResult<CustomEndpoint[]>> {
  return getApiResult("/api/v1/custom-endpoints", [], (b) => b);
}

export async function getCustomEndpoint(endpointId: string): Promise<ApiResult<CustomEndpoint>> {
  return getApiResult(`/api/v1/custom-endpoints/${encodeURIComponent(endpointId)}`, _fallbackEndpoint, (b) => b);
}

export async function discoverCustomEndpointSchema(
  endpointId: string,
  options: { path?: string; openapiUrl?: string; openapiSchemaName?: string } = {},
): Promise<ClientApiResult<SchemaDiscoveryResponse>> {
  const fallback: SchemaDiscoveryResponse = {
    endpointId,
    fields: [],
    fieldCount: 0,
    discoveryMethod: "probe",
    warnings: ["Discovery unavailable — API unreachable."],
  };
  try {
    const resp = await fetch(`${apiBaseUrl()}/api/v1/custom-endpoints/${encodeURIComponent(endpointId)}/discover-schema`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
      return { data: fallback, ok: false, isFallback: true, error: err.detail ?? `HTTP ${resp.status}` };
    }
    const data = await resp.json();
    return { data, ok: true, isFallback: false };
  } catch (e) {
    return { data: fallback, ok: false, isFallback: true, error: e instanceof Error ? e.message : "API unavailable" };
  }
}

export async function testCustomEndpointConnection(
  endpointId: string,
): Promise<ClientApiResult<{ ok: boolean; statusCode: number | null; message: string; latencyMs: number }>> {
  const fallback = { ok: false, statusCode: null, message: "Test unavailable.", latencyMs: 0 };
  try {
    const resp = await fetch(`${apiBaseUrl()}/api/v1/custom-endpoints/${encodeURIComponent(endpointId)}/test`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!resp.ok) {
      return { data: fallback, ok: false, isFallback: true, error: `HTTP ${resp.status}` };
    }
    const data = await resp.json();
    return { data, ok: true, isFallback: false };
  } catch (e) {
    return { data: fallback, ok: false, isFallback: true, error: e instanceof Error ? e.message : "API unavailable" };
  }
}

export async function getCustomEndpointSchema(
  endpointId: string,
): Promise<ApiResult<{ endpointId: string; fields: FieldInfo[]; fieldCount: number }>> {
  return getApiResult(
    `/api/v1/custom-endpoints/${encodeURIComponent(endpointId)}/schema`,
    { endpointId, fields: [], fieldCount: 0 },
    (b) => b,
  );
}
