import { z } from "zod";

export const currencyAmountSchema = z.object({
  amount: z.number(),
  currency: z.string().length(3)
});

export type CurrencyAmount = z.infer<typeof currencyAmountSchema>;

export const cfoKpiSchema = z.object({
  label: z.string(),
  value: z.union([z.string(), z.number()]),
  trend: z.enum(["up", "down", "flat"]),
  narrative: z.string()
});

export type CfoKpi = z.infer<typeof cfoKpiSchema>;

export const cfoDashboardSummarySchema = z.object({
  generatedAt: z.string(),
  mode: z.literal("mock"),
  cashPosition: currencyAmountSchema,
  openReceivables: currencyAmountSchema,
  monthlyRevenue: currencyAmountSchema,
  kpis: z.array(cfoKpiSchema)
});

export type CfoDashboardSummary = z.infer<typeof cfoDashboardSummarySchema>;

export const plVsBudgetLineSchema = z.object({
  period: z.string(),
  subsidiaryId: z.string(),
  line: z.string(),
  actual: z.number(),
  budget: z.number(),
  variance: z.number(),
  variancePct: z.number(),
  currency: z.string().length(3)
});

export const plVsBudgetResponseSchema = z.object({
  source: z.literal("mock"),
  period: z.string(),
  subsidiaryId: z.string().nullable(),
  lines: z.array(plVsBudgetLineSchema)
});

export type PlVsBudgetResponse = z.infer<typeof plVsBudgetResponseSchema>;

export const yoyComparisonLineSchema = z.object({
  currentYear: z.number(),
  priorYear: z.number(),
  subsidiaryId: z.string(),
  metric: z.string(),
  currentValue: z.number(),
  priorValue: z.number(),
  change: z.number(),
  changePct: z.number(),
  currency: z.string().length(3)
});

export const yoyComparisonResponseSchema = z.object({
  source: z.literal("mock"),
  currentYear: z.number(),
  priorYear: z.number(),
  subsidiaryId: z.string().nullable(),
  lines: z.array(yoyComparisonLineSchema)
});

export type YoyComparisonResponse = z.infer<typeof yoyComparisonResponseSchema>;

export const subsidiaryDrilldownLineSchema = z.object({
  period: z.string(),
  subsidiaryId: z.string(),
  subsidiaryName: z.string(),
  department: z.string(),
  revenue: z.number(),
  expenses: z.number(),
  operatingIncome: z.number(),
  currency: z.string().length(3)
});

export const subsidiaryDrilldownResponseSchema = z.object({
  source: z.literal("mock"),
  period: z.string(),
  subsidiaryId: z.string(),
  lines: z.array(subsidiaryDrilldownLineSchema)
});

export type SubsidiaryDrilldownResponse = z.infer<
  typeof subsidiaryDrilldownResponseSchema
>;

export const projectSummarySchema = z.object({
  projectId: z.string(),
  projectName: z.string(),
  customer: z.string(),
  accountManager: z.string(),
  subsidiaryId: z.string(),
  status: z.enum(["on_track", "at_risk", "overdue"]),
  budget: z.number(),
  actualCost: z.number(),
  forecastCost: z.number(),
  currency: z.string().length(3)
});

export const runningProjectsResponseSchema = z.object({
  source: z.literal("mock"),
  accountManager: z.string().nullable(),
  subsidiaryId: z.string().nullable(),
  projects: z.array(projectSummarySchema)
});

export type RunningProjectsResponse = z.infer<
  typeof runningProjectsResponseSchema
>;

export const overdueProjectManagerSchema = z.object({
  accountManager: z.string(),
  overdueProjectCount: z.number(),
  totalOverdueAmount: z.number(),
  maxDaysOverdue: z.number(),
  currency: z.string().length(3)
});

export const overdueProjectsByManagerResponseSchema = z.object({
  source: z.literal("mock"),
  minDaysOverdue: z.number(),
  managers: z.array(overdueProjectManagerSchema)
});

export type OverdueProjectsByManagerResponse = z.infer<
  typeof overdueProjectsByManagerResponseSchema
>;

export const orchestratorIntentSchema = z.enum([
  "CFO_DASHBOARD_SUMMARY",
  "PL_VS_BUDGET",
  "YOY_COMPARISON",
  "SUBSIDIARY_DRILLDOWN",
  "RUNNING_PROJECTS",
  "OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER",
  "UNKNOWN"
]);

export type OrchestratorIntent = z.infer<typeof orchestratorIntentSchema>;

export const orchestratorQueryRequestSchema = z.object({
  question: z.string().min(3).max(500),
  periodRange: z.string().optional(),
  subsidiary: z.string().optional(),
  asOfDate: z.string().optional()
});

export type OrchestratorQueryRequest = z.infer<
  typeof orchestratorQueryRequestSchema
>;

export const orchestratorQueryResponseSchema = z.object({
  detectedIntent: orchestratorIntentSchema,
  confidence: z.number().min(0).max(1),
  toolsUsed: z.array(z.string()),
  data: z.unknown(),
  executiveSummary: z.string(),
  fallbackUsed: z.boolean(),
  aiProvider: z.string(),
  aiMode: z.enum(["rule_based", "mock_llm", "openai", "ollama", "disabled"]),
  modelName: z.string().nullable(),
  modelCallAttempted: z.boolean(),
  modelCallSucceeded: z.boolean(),
  usedFallbackRouter: z.boolean()
});

export type OrchestratorQueryResponse = z.infer<
  typeof orchestratorQueryResponseSchema
>;

export const auditLogEntrySchema = z.object({
  timestamp: z.string(),
  requestId: z.string(),
  user: z.string(),
  channel: z.string(),
  question: z.string(),
  detectedIntent: z.string(),
  confidence: z.number().min(0).max(1),
  toolsUsed: z.array(z.string()),
  endpointCalled: z.string(),
  fallbackUsed: z.boolean(),
  success: z.boolean(),
  failureReason: z.string().nullable(),
  latencyMs: z.number(),
  aiProvider: z.string(),
  aiMode: z.string(),
  modelName: z.string().nullable(),
  modelCallAttempted: z.boolean(),
  modelCallSucceeded: z.boolean(),
  usedFallbackRouter: z.boolean()
});

export type AuditLogEntry = z.infer<typeof auditLogEntrySchema>;

export const auditLogSummarySchema = z.object({
  total: z.number(),
  successes: z.number(),
  failures: z.number(),
  fallbackCount: z.number(),
  averageLatencyMs: z.number(),
  byIntent: z.record(z.string(), z.number())
});

export type AuditLogSummary = z.infer<typeof auditLogSummarySchema>;
