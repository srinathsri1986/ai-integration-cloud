import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ZodRawShape } from "zod";

import {
  overdueProjectsByAccountManagerInputSchema,
  plVsBudgetInputSchema,
  runningProjectsInputSchema,
  subsidiaryDrilldownInputSchema,
  yoyComparisonInputObjectSchema
} from "./schemas/cfo.js";
import {
  getCfoDashboardSummary,
  getOverdueProjectsByAccountManager,
  getPlVsBudget,
  getRunningProjects,
  getSubsidiaryDrilldown,
  getYoyComparison
} from "./tools/cfoTools.js";

type ToolHandler = (input: unknown) => Promise<{
  content: Array<{ type: "text"; text: string }>;
}>;

export type CfoToolDefinition = {
  description: string;
  handler: ToolHandler;
  inputShape: ZodRawShape;
  name: string;
};

export const cfoToolDefinitions: CfoToolDefinition[] = [
  {
    name: "get_cfo_dashboard_summary",
    description: "Return the mock CFO dashboard summary from the orchestrator API.",
    inputShape: {},
    handler: getCfoDashboardSummary
  },
  {
    name: "get_pl_vs_budget",
    description: "Return approved mock P/L actuals vs budget from the CFO API.",
    inputShape: plVsBudgetInputSchema.shape,
    handler: getPlVsBudget
  },
  {
    name: "get_yoy_comparison",
    description: "Return approved mock year-over-year CFO comparison from the CFO API.",
    inputShape: yoyComparisonInputObjectSchema.shape,
    handler: getYoyComparison
  },
  {
    name: "get_subsidiary_drilldown",
    description: "Return approved mock subsidiary drilldown from the CFO API.",
    inputShape: subsidiaryDrilldownInputSchema.shape,
    handler: getSubsidiaryDrilldown
  },
  {
    name: "get_running_projects",
    description: "Return approved mock running project financials from the CFO API.",
    inputShape: runningProjectsInputSchema.shape,
    handler: getRunningProjects
  },
  {
    name: "get_overdue_projects_by_account_manager",
    description: "Return approved mock overdue project aging by account manager from the CFO API.",
    inputShape: overdueProjectsByAccountManagerInputSchema.shape,
    handler: getOverdueProjectsByAccountManager
  }
];

export function createCfoMcpServer() {
  const server = new McpServer({
    name: process.env.MCP_SERVER_NAME ?? "netsuite-cfo-intelligence",
    version: "0.4.0"
  });

  for (const tool of cfoToolDefinitions) {
    server.tool(tool.name, tool.description, tool.inputShape, tool.handler);
  }

  return server;
}
