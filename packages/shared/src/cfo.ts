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
