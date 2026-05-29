import { z } from "zod";

export const approvedNetSuiteQueryTemplateIds = [
  "cash_position_summary",
  "ar_aging_summary",
  "monthly_revenue_trend",
  "pl_vs_budget",
  "yoy_comparison",
  "subsidiary_drilldown",
  "running_projects",
  "overdue_projects_by_account_manager"
] as const;

export const approvedNetSuiteQueryTemplateIdSchema = z.enum(
  approvedNetSuiteQueryTemplateIds
);

export type ApprovedNetSuiteQueryTemplateId = z.infer<
  typeof approvedNetSuiteQueryTemplateIdSchema
>;

export const netSuiteQueryRequestSchema = z.object({
  templateId: approvedNetSuiteQueryTemplateIdSchema,
  subsidiaryId: z.string().min(1).optional(),
  period: z.string().min(1).optional()
});

export type NetSuiteQueryRequest = z.infer<typeof netSuiteQueryRequestSchema>;

export const netSuiteQueryResultSchema = z.object({
  templateId: approvedNetSuiteQueryTemplateIdSchema,
  source: z.literal("mock"),
  rows: z.array(z.record(z.string(), z.union([z.string(), z.number()])))
});

export type NetSuiteQueryResult = z.infer<typeof netSuiteQueryResultSchema>;

export const connectorStatusSchema = z.enum([
  "not_configured",
  "configured",
  "test_passed",
  "test_failed"
]);

export type ConnectorStatus = z.infer<typeof connectorStatusSchema>;

export const netSuiteConnectorConfigSchema = z.object({
  accountId: z.string().min(3).max(64),
  environment: z.enum(["sandbox", "production"]),
  authMode: z.literal("placeholder"),
  mockMode: z.boolean(),
  status: connectorStatusSchema,
  lastTestedAt: z.string().nullable()
});

export type NetSuiteConnectorConfig = z.infer<typeof netSuiteConnectorConfigSchema>;

export const netSuiteConnectorConfigUpdateSchema = z.object({
  accountId: z.string().min(3).max(64),
  environment: z.enum(["sandbox", "production"]),
  authMode: z.literal("placeholder"),
  mockMode: z.boolean()
});

export type NetSuiteConnectorConfigUpdate = z.infer<
  typeof netSuiteConnectorConfigUpdateSchema
>;

export const connectorListItemSchema = z.object({
  id: z.literal("netsuite"),
  name: z.string(),
  status: connectorStatusSchema,
  mockMode: z.boolean(),
  lastTestedAt: z.string().nullable()
});

export type ConnectorListItem = z.infer<typeof connectorListItemSchema>;

export const netSuiteConnectionTestResponseSchema = z.object({
  connectorId: z.literal("netsuite"),
  success: z.boolean(),
  status: connectorStatusSchema,
  message: z.string(),
  testedAt: z.string(),
  mockMode: z.boolean()
});

export type NetSuiteConnectionTestResponse = z.infer<
  typeof netSuiteConnectionTestResponseSchema
>;
