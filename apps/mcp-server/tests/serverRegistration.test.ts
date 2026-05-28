import assert from "node:assert/strict";
import test from "node:test";

import { cfoToolDefinitions } from "../src/server.js";

test("registers the required CFO tools only", () => {
  const toolNames = cfoToolDefinitions.map((tool) => tool.name).sort();

  assert.deepEqual(toolNames, [
    "get_cfo_dashboard_summary",
    "get_overdue_projects_by_account_manager",
    "get_pl_vs_budget",
    "get_running_projects",
    "get_subsidiary_drilldown",
    "get_yoy_comparison"
  ]);
});

test("does not expose raw NetSuite or template execution tools", () => {
  const toolNames = cfoToolDefinitions.map((tool) => tool.name);

  assert.equal(toolNames.includes("run_approved_netsuite_template"), false);
  assert.equal(toolNames.some((name) => name.toLowerCase().includes("sql")), false);
  assert.equal(toolNames.some((name) => name.toLowerCase().includes("suiteql")), false);
});
