import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { approvedNetSuiteQueryTemplateIdSchema } from "./schemas/netsuite.js";
import { getCfoDashboardSummary, runApprovedNetSuiteTemplate } from "./tools/cfoTools.js";

const server = new McpServer({
  name: process.env.MCP_SERVER_NAME ?? "netsuite-cfo-intelligence",
  version: "0.1.0"
});

server.tool(
  "get_cfo_dashboard_summary",
  "Return the mock CFO dashboard summary from the orchestrator API.",
  {},
  getCfoDashboardSummary
);

server.tool(
  "run_approved_netsuite_template",
  "Run one approved mock NetSuite query template. Arbitrary SQL or SuiteQL is not accepted.",
  {
    templateId: approvedNetSuiteQueryTemplateIdSchema
  },
  runApprovedNetSuiteTemplate
);

const transport = new StdioServerTransport();
await server.connect(transport);
