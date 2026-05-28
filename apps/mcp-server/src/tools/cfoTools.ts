import type { CfoDashboardSummary, NetSuiteQueryResult } from "@netsuite-cfo/shared";

import { postJson, getJson } from "./apiClient.js";
import type { ApprovedNetSuiteQueryTemplateId } from "../schemas/netsuite.js";

export async function getCfoDashboardSummary() {
  const summary = await getJson<CfoDashboardSummary>("/api/v1/cfo/dashboard-summary");

  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(summary, null, 2)
      }
    ]
  };
}

export async function runApprovedNetSuiteTemplate(input: {
  templateId: ApprovedNetSuiteQueryTemplateId;
}) {
  const result = await postJson<NetSuiteQueryResult>(
    `/api/v1/cfo/netsuite/templates/${input.templateId}/run`
  );

  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(result, null, 2)
      }
    ]
  };
}
