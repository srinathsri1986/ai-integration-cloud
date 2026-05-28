import {
  cfoDashboardSummarySchema,
  overdueProjectsByManagerResponseSchema,
  plVsBudgetResponseSchema,
  runningProjectsResponseSchema,
  subsidiaryDrilldownResponseSchema,
  yoyComparisonResponseSchema
} from "@netsuite-cfo/shared";
import { z } from "zod";

export const periodSchema = z.string().regex(/^\d{4}-(Q[1-4]|0[1-9]|1[0-2])$/);
export const subsidiaryIdSchema = z.string().min(2).max(16);

export const plVsBudgetInputSchema = z.object({
  period: periodSchema.default("2026-Q1"),
  subsidiaryId: subsidiaryIdSchema.optional()
});

export const yoyComparisonInputObjectSchema = z.object({
  currentYear: z.number().int().min(2000).max(2100).default(2026),
  priorYear: z.number().int().min(2000).max(2100).default(2025),
  subsidiaryId: subsidiaryIdSchema.optional()
});

export const yoyComparisonInputSchema = yoyComparisonInputObjectSchema.refine(
  (input) => input.priorYear < input.currentYear,
  {
    message: "priorYear must be earlier than currentYear",
    path: ["priorYear"]
  }
);

export const subsidiaryDrilldownInputSchema = z.object({
  period: periodSchema.default("2026-Q1"),
  subsidiaryId: subsidiaryIdSchema.default("EMEA")
});

export const runningProjectsInputSchema = z.object({
  accountManager: z.string().min(2).max(80).optional(),
  subsidiaryId: subsidiaryIdSchema.optional()
});

export const overdueProjectsByAccountManagerInputSchema = z.object({
  minDaysOverdue: z.number().int().min(1).max(365).default(1)
});

export {
  cfoDashboardSummarySchema,
  overdueProjectsByManagerResponseSchema,
  plVsBudgetResponseSchema,
  runningProjectsResponseSchema,
  subsidiaryDrilldownResponseSchema,
  yoyComparisonResponseSchema
};
