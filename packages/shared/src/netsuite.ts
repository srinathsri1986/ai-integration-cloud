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

export const connectorModeSchema = z.enum(["mock", "sandbox"]);

export type ConnectorMode = z.infer<typeof connectorModeSchema>;

export const connectorIdSchema = z.enum(["netsuite", "rest-api"]);

export type ConnectorId = z.infer<typeof connectorIdSchema>;

export const netSuiteConnectorConfigSchema = z.object({
  accountId: z.string().min(3).max(64),
  environment: z.enum(["sandbox", "production"]),
  authMode: z.enum(["placeholder", "token_based_auth"]),
  mockMode: z.boolean(),
  mode: connectorModeSchema,
  status: connectorStatusSchema,
  lastTestedAt: z.string().nullable(),
  baseUrlConfigured: z.boolean(),
  credentialsConfigured: z.boolean()
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
  id: connectorIdSchema,
  name: z.string(),
  status: connectorStatusSchema,
  mockMode: z.boolean(),
  mode: connectorModeSchema,
  lastTestedAt: z.string().nullable()
});

export type ConnectorListItem = z.infer<typeof connectorListItemSchema>;

export const netSuiteConnectionTestResponseSchema = z.object({
  connectorId: z.literal("netsuite"),
  success: z.boolean(),
  status: connectorStatusSchema,
  message: z.string(),
  testedAt: z.string(),
  mockMode: z.boolean(),
  mode: connectorModeSchema,
  baseUrlConfigured: z.boolean(),
  credentialsConfigured: z.boolean()
});

export type NetSuiteConnectionTestResponse = z.infer<
  typeof netSuiteConnectionTestResponseSchema
>;

export const restApiObjectIdSchema = z.enum(["customer", "invoice", "opportunity"]);

export type RestApiObjectId = z.infer<typeof restApiObjectIdSchema>;

export const restApiActionIdSchema = z.enum([
  "read_sample",
  "validate_payload",
  "simulate_post_placeholder"
]);

export type RestApiActionId = z.infer<typeof restApiActionIdSchema>;

export const restApiObjectFieldSchema = z.object({
  name: z.string(),
  label: z.string(),
  type: z.enum(["string", "number", "boolean", "date"]),
  required: z.boolean()
});

export type RestApiObjectField = z.infer<typeof restApiObjectFieldSchema>;

export const restApiApprovedObjectSchema = z.object({
  objectId: restApiObjectIdSchema,
  label: z.string(),
  description: z.string(),
  fields: z.array(restApiObjectFieldSchema)
});

export type RestApiApprovedObject = z.infer<typeof restApiApprovedObjectSchema>;

export const restApiConnectorConfigSchema = z.object({
  connectorId: z.literal("rest-api"),
  displayName: z.string().min(3).max(80),
  baseUrlPlaceholder: z.string().min(3).max(120),
  authMode: z.literal("placeholder"),
  mockMode: z.boolean(),
  mode: z.literal("mock"),
  status: connectorStatusSchema,
  lastTestedAt: z.string().nullable(),
  baseUrlConfigured: z.boolean(),
  credentialsConfigured: z.boolean(),
  approvedObjects: z.array(restApiObjectIdSchema),
  approvedActions: z.array(restApiActionIdSchema)
});

export type RestApiConnectorConfig = z.infer<typeof restApiConnectorConfigSchema>;

export const restApiConnectorConfigUpdateSchema = z.object({
  displayName: z.string().min(3).max(80),
  baseUrlPlaceholder: z.string().min(3).max(120),
  authMode: z.literal("placeholder"),
  mockMode: z.boolean()
});

export type RestApiConnectorConfigUpdate = z.infer<
  typeof restApiConnectorConfigUpdateSchema
>;

export const restApiConnectionTestResponseSchema = z.object({
  connectorId: z.literal("rest-api"),
  success: z.boolean(),
  status: connectorStatusSchema,
  message: z.string(),
  testedAt: z.string(),
  mockMode: z.boolean(),
  mode: z.literal("mock"),
  baseUrlConfigured: z.boolean(),
  credentialsConfigured: z.boolean(),
  approvedObjects: z.array(restApiObjectIdSchema),
  approvedActions: z.array(restApiActionIdSchema)
});

export type RestApiConnectionTestResponse = z.infer<
  typeof restApiConnectionTestResponseSchema
>;

export const restApiSchemaDiscoveryRequestSchema = z.object({
  objectLabel: z.string().min(3).max(80),
  samplePayload: z.record(z.string(), z.unknown())
});

export type RestApiSchemaDiscoveryRequest = z.infer<
  typeof restApiSchemaDiscoveryRequestSchema
>;

export const restApiDiscoveredFieldSchema = z.object({
  name: z.string(),
  label: z.string(),
  type: z.enum(["string", "number", "boolean", "date"]),
  required: z.boolean(),
  sample: z.union([z.string(), z.number(), z.boolean()]).nullable().optional()
});

export type RestApiDiscoveredField = z.infer<typeof restApiDiscoveredFieldSchema>;

export const restApiSchemaDiscoveryResponseSchema = z.object({
  connectorId: z.literal("rest-api"),
  objectId: z.string(),
  objectLabel: z.string(),
  mode: z.literal("schema_discovery"),
  fields: z.array(restApiDiscoveredFieldSchema),
  warnings: z.array(z.string()),
  generatedFromSample: z.boolean(),
  executable: z.boolean()
});

export type RestApiSchemaDiscoveryResponse = z.infer<
  typeof restApiSchemaDiscoveryResponseSchema
>;

export const mappingFieldSchema = z.object({
  name: z.string(),
  description: z.string(),
  type: z.enum(["string", "number", "date", "boolean"]),
  required: z.boolean().optional(),
  sample: z.union([z.string(), z.number(), z.boolean()]).nullable().optional()
});

export type MappingField = z.infer<typeof mappingFieldSchema>;

export const mappingObjectSchema = z.object({
  id: z.string(),
  displayName: z.string(),
  systemId: z.string(),
  fields: z.array(mappingFieldSchema)
});

export type MappingObject = z.infer<typeof mappingObjectSchema>;

export const restApiSchemaPromotionRequestSchema = z.object({
  objectId: z.string().min(3).max(80),
  objectLabel: z.string().min(3).max(80),
  fields: z.array(restApiDiscoveredFieldSchema).min(1).max(24)
});

export type RestApiSchemaPromotionRequest = z.infer<
  typeof restApiSchemaPromotionRequestSchema
>;

export const restApiSchemaPromotionResponseSchema = z.object({
  connectorId: z.literal("rest-api"),
  promoted: z.boolean(),
  objectId: z.string(),
  objectLabel: z.string(),
  mappingObject: mappingObjectSchema,
  message: z.string(),
  warnings: z.array(z.string())
});

export type RestApiSchemaPromotionResponse = z.infer<
  typeof restApiSchemaPromotionResponseSchema
>;

export const flowIds = [
  "netsuite-cfo-dashboard-refresh",
  "netsuite-project-risk-refresh",
  "netsuite-subsidiary-drilldown-refresh"
] as const;

export const flowIdSchema = z.string().min(3).max(96);

export type FlowId = z.infer<typeof flowIdSchema>;

export const flowStatusSchema = z.enum([
  "draft",
  "pending_approval",
  "approved",
  "published",
  "paused"
]);
export const flowLifecycleActionSchema = z.enum([
  "submit_for_approval",
  "approve",
  "reject",
  "publish",
  "pause"
]);
export const flowRunStatusSchema = z.enum(["never_run", "succeeded", "failed"]);
export const flowRunStepStatusSchema = z.enum(["succeeded", "failed", "skipped"]);
export const flowTriggerTypeSchema = z.enum(["manual", "schedule_placeholder"]);
export const approvedFlowToolSchema = z.enum([
  "cfo.dashboard_summary",
  "cfo.pl_vs_budget",
  "cfo.yoy_comparison",
  "cfo.subsidiary_drilldown",
  "cfo.running_projects",
  "cfo.overdue_projects_by_account_manager",
  "orchestrator.query"
]);

export type FlowStatus = z.infer<typeof flowStatusSchema>;
export type FlowLifecycleAction = z.infer<typeof flowLifecycleActionSchema>;
export type FlowRunStatus = z.infer<typeof flowRunStatusSchema>;
export type FlowRunStepStatus = z.infer<typeof flowRunStepStatusSchema>;
export type FlowTriggerType = z.infer<typeof flowTriggerTypeSchema>;
export type ApprovedFlowTool = z.infer<typeof approvedFlowToolSchema>;

export const flowStepSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  approvedTool: approvedFlowToolSchema
});

export type FlowStep = z.infer<typeof flowStepSchema>;

export const flowDefinitionSchema = z.object({
  flowId: flowIdSchema,
  name: z.string(),
  description: z.string(),
  sourceConnector: z.literal("netsuite"),
  targetModule: z.string(),
  status: flowStatusSchema,
  triggerType: flowTriggerTypeSchema,
  mappingDefinitionId: z.string().nullable().optional(),
  lastRunAt: z.string().nullable(),
  lastRunStatus: flowRunStatusSchema,
  steps: z.array(flowStepSchema)
});

export type FlowDefinition = z.infer<typeof flowDefinitionSchema>;

export const flowDefinitionUpsertRequestSchema = z.object({
  flowId: z.string().min(3).max(96),
  name: z.string().min(3).max(120),
  description: z.string().min(10).max(500),
  sourceConnector: z.literal("netsuite"),
  targetModule: z.string().min(3).max(80),
  status: flowStatusSchema,
  triggerType: flowTriggerTypeSchema,
  mappingDefinitionId: z.string().max(96).nullable().optional(),
  steps: z.array(flowStepSchema).min(1).max(8)
});

export type FlowDefinitionUpsertRequest = z.infer<typeof flowDefinitionUpsertRequestSchema>;

export const flowSuggestionRequestSchema = z.object({
  prompt: z.string().min(10).max(1000)
});

export type FlowSuggestionRequest = z.infer<typeof flowSuggestionRequestSchema>;

export const flowSuggestionResponseSchema = z.object({
  prompt: z.string(),
  suggestedFlow: flowDefinitionUpsertRequestSchema,
  rationale: z.string(),
  suggestionProvider: z.string(),
  suggestionModel: z.string().nullable(),
  suggestionGenerated: z.boolean(),
  suggestionFallbackUsed: z.boolean(),
  modelCallAttempted: z.boolean(),
  modelCallSucceeded: z.boolean()
});

export type FlowSuggestionResponse = z.infer<typeof flowSuggestionResponseSchema>;

export const mappingTransformSchema = z.enum([
  "direct",
  "rename",
  "format_date",
  "lookup_placeholder",
  "constant_placeholder"
]);

export type MappingTransform = z.infer<typeof mappingTransformSchema>;

export const mappingSuggestionRequestSchema = z.object({
  prompt: z.string().min(10).max(1000),
  sourceObjectId: z.string().min(3).max(80),
  targetObjectId: z.string().min(3).max(80)
});

export type MappingSuggestionRequest = z.infer<typeof mappingSuggestionRequestSchema>;

export const mappingSuggestionItemSchema = z.object({
  sourceField: z.string(),
  targetField: z.string(),
  transform: mappingTransformSchema,
  confidence: z.number().min(0).max(1),
  rationale: z.string()
});

export type MappingSuggestionItem = z.infer<typeof mappingSuggestionItemSchema>;

export const mappingSuggestionResponseSchema = z.object({
  prompt: z.string(),
  sourceObjectId: z.string(),
  targetObjectId: z.string(),
  suggestions: z.array(mappingSuggestionItemSchema),
  suggestionProvider: z.string(),
  suggestionModel: z.string().nullable(),
  suggestionGenerated: z.boolean(),
  suggestionFallbackUsed: z.boolean(),
  modelCallAttempted: z.boolean(),
  modelCallSucceeded: z.boolean()
});

export type MappingSuggestionResponse = z.infer<typeof mappingSuggestionResponseSchema>;

export const mappingDefinitionStatusSchema = z.enum([
  "draft",
  "pending_approval",
  "approved",
  "published",
  "paused"
]);

export type MappingDefinitionStatus = z.infer<typeof mappingDefinitionStatusSchema>;

export const mappingLifecycleActionSchema = z.enum([
  "submit_for_approval",
  "approve",
  "reject",
  "publish",
  "pause"
]);

export type MappingLifecycleAction = z.infer<typeof mappingLifecycleActionSchema>;

export const mappingDefinitionRowSchema = z.object({
  id: z.string(),
  sourceField: z.string(),
  targetField: z.string(),
  transform: mappingTransformSchema,
  confidence: z.number().min(0).max(1).nullable().optional(),
  rationale: z.string().nullable().optional()
});

export type MappingDefinitionRow = z.infer<typeof mappingDefinitionRowSchema>;

export const mappingDefinitionSchema = z.object({
  mappingId: z.string(),
  name: z.string(),
  description: z.string(),
  sourceObjectId: z.string(),
  targetObjectId: z.string(),
  status: mappingDefinitionStatusSchema,
  mappings: z.array(mappingDefinitionRowSchema),
  createdAt: z.string().nullable(),
  updatedAt: z.string().nullable()
});

export type MappingDefinition = z.infer<typeof mappingDefinitionSchema>;

export const mappingDefinitionUpsertRequestSchema = z.object({
  mappingId: z.string().min(3).max(96),
  name: z.string().min(3).max(120),
  description: z.string().min(10).max(500),
  sourceObjectId: z.string().min(3).max(80),
  targetObjectId: z.string().min(3).max(80),
  status: mappingDefinitionStatusSchema,
  mappings: z.array(mappingDefinitionRowSchema).min(1).max(50)
});

export type MappingDefinitionUpsertRequest = z.infer<
  typeof mappingDefinitionUpsertRequestSchema
>;

export const mappingLifecycleRequestSchema = z.object({
  action: mappingLifecycleActionSchema,
  note: z.string().max(300).nullable().optional()
});

export type MappingLifecycleRequest = z.infer<typeof mappingLifecycleRequestSchema>;

export const mappingLifecycleResponseSchema = z.object({
  mapping: mappingDefinitionSchema,
  action: mappingLifecycleActionSchema,
  message: z.string()
});

export type MappingLifecycleResponse = z.infer<typeof mappingLifecycleResponseSchema>;

export const mappingSimulationResponseSchema = z.object({
  mappingId: z.string(),
  status: mappingDefinitionStatusSchema,
  sourceObjectId: z.string(),
  targetObjectId: z.string(),
  sourcePayload: z.record(z.string(), z.unknown()),
  targetPayload: z.record(z.string(), z.unknown()),
  warnings: z.array(z.string()),
  transformsApplied: z.array(z.string()),
  simulatedAt: z.string()
});

export type MappingSimulationResponse = z.infer<typeof mappingSimulationResponseSchema>;

export const flowRunTimelineStepSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: flowRunStepStatusSchema,
  startedAt: z.string(),
  completedAt: z.string(),
  latencyMs: z.number(),
  approvedTool: z.string().nullable(),
  mappingDefinitionId: z.string().nullable(),
  warnings: z.array(z.string())
});

export type FlowRunTimelineStep = z.infer<typeof flowRunTimelineStepSchema>;

export const flowLifecycleRequestSchema = z.object({
  action: flowLifecycleActionSchema,
  note: z.string().max(300).nullable().optional()
});

export type FlowLifecycleRequest = z.infer<typeof flowLifecycleRequestSchema>;

export const flowLifecycleResponseSchema = z.object({
  flow: flowDefinitionSchema,
  action: flowLifecycleActionSchema,
  message: z.string()
});

export type FlowLifecycleResponse = z.infer<typeof flowLifecycleResponseSchema>;

export const flowRunResponseSchema = z.object({
  requestId: z.string(),
  flowId: flowIdSchema,
  status: flowRunStatusSchema,
  startedAt: z.string(),
  completedAt: z.string(),
  toolsUsed: z.array(z.string()),
  message: z.string(),
  data: z.unknown(),
  executionTimeline: z.array(flowRunTimelineStepSchema)
});

export type FlowRunResponse = z.infer<typeof flowRunResponseSchema>;

export const userRoleSchema = z.enum([
  "CFO",
  "Finance Controller",
  "Integration Admin",
  "Viewer",
  "Developer"
]);

export type UserRole = z.infer<typeof userRoleSchema>;

export const authUserSchema = z.object({
  userId: z.string(),
  email: z.string(),
  role: userRoleSchema
});

export type AuthUser = z.infer<typeof authUserSchema>;

export const loginResponseSchema = z.object({
  accessToken: z.string(),
  tokenType: z.literal("bearer"),
  user: authUserSchema
});

export type LoginResponse = z.infer<typeof loginResponseSchema>;
