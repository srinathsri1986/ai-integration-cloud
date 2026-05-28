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
