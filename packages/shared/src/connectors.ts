import { z } from "zod";

// ─── Generic connector registry types ─────────────────────────────────────────

export const connectorStatusSchema = z.enum([
  "not_configured",
  "configured",
  "test_passed",
  "test_failed"
]);
export type ConnectorStatus = z.infer<typeof connectorStatusSchema>;

export const connectorModeSchema = z.enum(["mock", "sandbox", "production", "live"]);
export type ConnectorMode = z.infer<typeof connectorModeSchema>;

export const connectorAuthSchemeSchema = z.enum([
  "none",
  "api_key",
  "oauth2",
  "basic",
  "token_based"
]);
export type ConnectorAuthScheme = z.infer<typeof connectorAuthSchemeSchema>;

// A single tool exposed by a connector (e.g. "cfo.dashboard_summary" on NetSuite)
export const connectorToolSchema = z.object({
  toolId: z.string(),
  label: z.string(),
  description: z.string(),
  connectorId: z.string(),
  params: z
    .record(
      z.string(),
      z.object({ type: z.string(), required: z.boolean(), description: z.string() })
    )
    .optional()
});
export type ConnectorTool = z.infer<typeof connectorToolSchema>;

// A connector as returned by GET /connectors
export const connectorDefinitionSchema = z.object({
  connectorId: z.string(),
  name: z.string(),
  logoSlug: z.string(),
  authScheme: connectorAuthSchemeSchema,
  status: connectorStatusSchema,
  mode: connectorModeSchema,
  toolCount: z.number(),
  lastTestedAt: z.string().nullable()
});
export type ConnectorDefinition = z.infer<typeof connectorDefinitionSchema>;

// Generic connection test response (replaces NetSuite/REST-API-specific responses)
export const connectorTestResponseSchema = z.object({
  connectorId: z.string(),
  success: z.boolean(),
  status: connectorStatusSchema,
  message: z.string(),
  testedAt: z.string(),
  mode: connectorModeSchema
});
export type ConnectorTestResponse = z.infer<typeof connectorTestResponseSchema>;

// Generic connector config (opaque JSON; each connector validates its own shape server-side)
export const connectorConfigSchema = z.object({
  connectorId: z.string(),
  mode: connectorModeSchema,
  status: connectorStatusSchema,
  config: z.record(z.string(), z.unknown()),
  lastTestedAt: z.string().nullable()
});
export type ConnectorConfig = z.infer<typeof connectorConfigSchema>;

// ─── R18a: Custom endpoint registry ──────────────────────────────────────────

export const fieldTypeSchema = z.enum(["string", "number", "boolean", "date", "object", "array"]);
export type FieldType = z.infer<typeof fieldTypeSchema>;

export const fieldInfoSchema = z.object({
  name: z.string(),       // dot-path, e.g. "customer.email"
  label: z.string(),
  type: fieldTypeSchema,
  required: z.boolean().default(false),
  sample: z.string().nullable().optional(),
});
export type FieldInfo = z.infer<typeof fieldInfoSchema>;

// Canonical transform set — must match APPROVED_MAPPING_TRANSFORMS in
// apps/api/app/services/mapping_catalog.py exactly.
// Do NOT add values here without adding them to the backend allow-list first.
const mappingTransformSchema = z.enum([
  "direct",
  "rename",
  "format_date",
  "lookup_placeholder",
  "constant_placeholder",
]);

export const inlineFieldMappingSchema = z.object({
  sourceField: z.string(),
  targetField: z.string(),
  transform: mappingTransformSchema.default("direct"),
  sourceType: fieldTypeSchema.default("string"),
  targetType: fieldTypeSchema.default("string"),
});
export type InlineFieldMapping = z.infer<typeof inlineFieldMappingSchema>;

/** Normalised response from POST /connectors/{id}/test */
export const connectorTestResultSchema = z.object({
  ok: z.boolean(),
  mode: z.string().default("mock"),
  message: z.string(),
});
export type ConnectorTestResult = z.infer<typeof connectorTestResultSchema>;

export const customEndpointSchema = z.object({
  endpointId: z.string(),
  tenantId: z.number().nullable(),
  name: z.string(),
  description: z.string(),
  baseUrl: z.string(),
  authScheme: z.enum(["none", "api_key", "bearer", "basic"]),
  defaultPath: z.string(),
  httpMethod: z.string(),
  fieldSchema: z.array(fieldInfoSchema),
  fieldCount: z.number(),
  hasCredentials: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type CustomEndpoint = z.infer<typeof customEndpointSchema>;

export const schemaDiscoveryResponseSchema = z.object({
  endpointId: z.string(),
  fields: z.array(fieldInfoSchema),
  fieldCount: z.number(),
  discoveryMethod: z.string(),
  warnings: z.array(z.string()),
});
export type SchemaDiscoveryResponse = z.infer<typeof schemaDiscoveryResponseSchema>;

// NOTE: flowTriggerTypeSchema / FlowTriggerType / FlowDefinitionUpsertRequest
// are already exported by netsuite.ts — do not re-export here to avoid collision.
