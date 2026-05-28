import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { createCfoMcpServer } from "./server.js";

const server = createCfoMcpServer();
const transport = new StdioServerTransport();

await server.connect(transport);
