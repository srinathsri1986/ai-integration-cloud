import { z } from "zod";

// ── Intent values ────────────────────────────────────────────────────────────
export const askAIIntentSchema = z.enum([
  "CREATE_FLOW",
  "SUGGEST_MAPPING",
  "EXPLAIN_ERROR",
  "GENERAL",
]);
export type AskAIIntent = z.infer<typeof askAIIntentSchema>;

// ── Action types — tell the frontend what to render next ────────────────────
export const askAIActionTypeSchema = z.enum([
  "SUGGEST_FLOW",
  "OPEN_MAPPING",
  "OPEN_ERROR_DEBUGGER",
  "INFO",
]);
export type AskAIActionType = z.infer<typeof askAIActionTypeSchema>;

// ── Request ──────────────────────────────────────────────────────────────────
export const askAIRequestSchema = z.object({
  question: z.string().min(5).max(1000),
  pageContext: z.string().optional(),
});
export type AskAIRequest = z.infer<typeof askAIRequestSchema>;

// ── Action payload ───────────────────────────────────────────────────────────
export const askAIActionSchema = z.object({
  type: askAIActionTypeSchema,
  navigateTo: z.string().nullable().optional(),
  payload: z.record(z.unknown()).nullable().optional(),
});
export type AskAIAction = z.infer<typeof askAIActionSchema>;

// ── Response ─────────────────────────────────────────────────────────────────
export const askAIResponseSchema = z.object({
  question: z.string(),
  intent: askAIIntentSchema,
  answer: z.string(),
  action: askAIActionSchema.nullable().optional(),
  provider: z.string(),
  model: z.string().nullable(),
  thinkUsed: z.boolean(),
});
export type AskAIResponse = z.infer<typeof askAIResponseSchema>;
