"use client";

import { useState } from "react";
import { GitBranch, Play, Save, Workflow } from "lucide-react";
import type {
  ApprovedFlowTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowLifecycleAction,
  FlowRunResponse
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ApiResult,
  runFlow,
  saveFlowDefinition,
  transitionFlowLifecycle
} from "@/lib/api";

const approvedTools: ApprovedFlowTool[] = [
  "cfo.dashboard_summary",
  "cfo.pl_vs_budget",
  "cfo.yoy_comparison",
  "cfo.subsidiary_drilldown",
  "cfo.running_projects",
  "cfo.overdue_projects_by_account_manager",
  "orchestrator.query"
];

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function lifecycleActionsForStatus(status: FlowDefinition["status"]): FlowLifecycleAction[] {
  if (status === "draft") {
    return ["submit_for_approval"];
  }

  if (status === "pending_approval") {
    return ["approve", "reject"];
  }

  if (status === "approved") {
    return ["publish", "reject"];
  }

  if (status === "published") {
    return ["pause"];
  }

  return ["submit_for_approval"];
}

export function FlowCatalog({ initialFlows }: { initialFlows: ApiResult<FlowDefinition[]> }) {
  const [flows, setFlows] = useState(initialFlows.data);
  const [error, setError] = useState<string | undefined>(
    initialFlows.isFallback ? initialFlows.error : undefined
  );
  const [runningFlowId, setRunningFlowId] = useState<string | undefined>();
  const [transitioningFlowId, setTransitioningFlowId] = useState<string | undefined>();
  const [lastRun, setLastRun] = useState<Record<string, FlowRunResponse>>({});
  const [designerMessage, setDesignerMessage] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);
  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>({
    description: "Refresh CFO dashboard data through approved NetSuite CFO actions.",
    flowId: "custom-cfo-refresh",
    name: "Custom CFO refresh",
    sourceConnector: "netsuite",
    status: "draft",
    steps: [
      {
        approvedTool: "cfo.dashboard_summary",
        description: "Load approved CFO dashboard summary data.",
        id: "load-summary",
        name: "Load CFO summary"
      }
    ],
    targetModule: "cfo_dashboard",
    triggerType: "manual"
  });

  async function onRun(flow: FlowDefinition) {
    setError(undefined);
    setRunningFlowId(flow.flowId);

    const response = await runFlow(flow.flowId);
    setLastRun((current) => ({ ...current, [flow.flowId]: response.data }));
    if (response.ok) {
      setFlows((current) =>
        current.map((item) =>
          item.flowId === flow.flowId
            ? {
                ...item,
                lastRunAt: response.data.completedAt,
                lastRunStatus: response.data.status
              }
            : item
        )
      );
    } else {
      setError(response.error ?? "Unable to run flow.");
    }
    setRunningFlowId(undefined);
  }

  async function onTransition(flow: FlowDefinition, action: FlowLifecycleAction) {
    setError(undefined);
    setTransitioningFlowId(`${flow.flowId}:${action}`);
    const response = await transitionFlowLifecycle(flow.flowId, action);

    if (response.ok) {
      setFlows((current) =>
        current.map((item) =>
          item.flowId === response.data.flow.flowId ? response.data.flow : item
        )
      );
      setDesignerMessage(response.data.message);
    } else {
      setError(response.error ?? "Unable to update flow lifecycle.");
    }

    setTransitioningFlowId(undefined);
  }

  async function onSaveDesigner() {
    setDesignerMessage(undefined);
    setIsSaving(true);

    const response = await saveFlowDefinition(draft);
    if (response.ok) {
      setFlows((current) => {
        const existing = current.some((flow) => flow.flowId === response.data.flowId);
        return existing
          ? current.map((flow) => (flow.flowId === response.data.flowId ? response.data : flow))
          : [...current, response.data];
      });
      setDesignerMessage(`${response.data.name} saved as ${statusLabel(response.data.status)}.`);
    } else {
      setDesignerMessage(response.error ?? "Unable to save flow definition.");
    }
    setIsSaving(false);
  }

  return (
    <section className="mx-auto max-w-7xl px-6 pb-12">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Flow Catalog</p>
          <h2 className="mt-1 text-xl font-semibold">Mock integration flows</h2>
        </div>
        <Badge className="border-emerald-300 bg-emerald-50 text-emerald-900">
          <Workflow className="mr-1 h-3.5 w-3.5" />
          Approved tools only
        </Badge>
      </div>

      {error ? (
        <p className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          {error}
        </p>
      ) : null}

      <Card className="mb-4 border-sky-200 bg-sky-50/70">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <div>
            <CardHeader>
              <CardTitle>Flow Designer Lite</CardTitle>
            </CardHeader>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                maxLength={96}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, flowId: event.target.value }))
                }
                placeholder="flow-id"
                value={draft.flowId}
              />
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                maxLength={120}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="Flow name"
                value={draft.name}
              />
              <select
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                disabled
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    status: event.target.value as FlowDefinitionUpsertRequest["status"]
                  }))
                }
                value={draft.status}
              >
                <option value="draft">Draft</option>
              </select>
              <select
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    triggerType: event.target.value as FlowDefinitionUpsertRequest["triggerType"]
                  }))
                }
                value={draft.triggerType}
              >
                <option value="manual">Manual trigger</option>
                <option value="schedule_placeholder">Schedule placeholder</option>
              </select>
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary md:col-span-2"
                maxLength={500}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, description: event.target.value }))
                }
                placeholder="Description"
                value={draft.description}
              />
              <select
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary md:col-span-2"
                onChange={(event) => {
                  const tool = event.target.value as ApprovedFlowTool;
                  setDraft((current) => ({
                    ...current,
                    steps: [
                      {
                        approvedTool: tool,
                        description: `Run approved action ${tool}.`,
                        id: tool.replaceAll(".", "-"),
                        name: statusLabel(tool)
                      }
                    ]
                  }));
                }}
                value={draft.steps[0]?.approvedTool}
              >
                {approvedTools.map((tool) => (
                  <option key={tool} value={tool}>
                    {tool}
                  </option>
                ))}
              </select>
            </div>
            {designerMessage ? (
              <p className="mt-3 rounded-md border border-sky-200 bg-white px-3 py-2 text-sm text-sky-950">
                {designerMessage}
              </p>
            ) : null}
          </div>
          <div className="rounded-md border border-sky-200 bg-white p-4">
            <p className="text-sm font-medium">Designer guardrails</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge>No raw SQL</Badge>
              <Badge>No SuiteQL input</Badge>
              <Badge>Approved tools only</Badge>
              <Badge>Human save required</Badge>
            </div>
            <Button className="mt-4 w-full" disabled={isSaving} onClick={onSaveDesigner} type="button">
              <Save className="h-4 w-4" />
              {isSaving ? "Saving" : "Save flow"}
            </Button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {flows.map((flow) => {
          const result = lastRun[flow.flowId];
          return (
            <Card key={flow.flowId}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardHeader>
                    <CardTitle>{flow.name}</CardTitle>
                  </CardHeader>
                  <p className="text-sm leading-6 text-muted-foreground">{flow.description}</p>
                </div>
                <GitBranch className="h-5 w-5 shrink-0 text-primary" />
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <Badge>{statusLabel(flow.status)}</Badge>
                <Badge>{flow.sourceConnector}</Badge>
                <Badge>{flow.targetModule}</Badge>
                {flow.status !== "published" ? <Badge>approval required</Badge> : <Badge>runnable</Badge>}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Last status</p>
                  <p className="font-medium">{statusLabel(flow.lastRunStatus)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Last run</p>
                  <p className="font-medium">
                    {flow.lastRunAt ? new Date(flow.lastRunAt).toLocaleString() : "Never"}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <p className="text-sm font-medium">Steps</p>
                <div className="mt-2 space-y-2">
                  {flow.steps.map((step) => (
                    <div key={step.id} className="rounded-md border border-border bg-muted/50 p-3">
                      <p className="text-sm font-medium">{step.name}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {step.description}
                      </p>
                      <Badge className="mt-2">{step.approvedTool}</Badge>
                    </div>
                  ))}
                </div>
              </div>

              {result ? (
                <p className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950">
                  {result.message} Request {result.requestId}.
                </p>
              ) : null}

              <div className="mt-4 grid gap-2">
                <div className="grid gap-2 sm:grid-cols-2">
                  {lifecycleActionsForStatus(flow.status).map((action) => (
                    <Button
                      disabled={transitioningFlowId === `${flow.flowId}:${action}`}
                      key={action}
                      onClick={() => onTransition(flow, action)}
                      type="button"
                      variant="secondary"
                    >
                      {statusLabel(action)}
                    </Button>
                  ))}
                </div>
                <Button
                  className="w-full"
                  disabled={runningFlowId === flow.flowId || flow.status !== "published"}
                  onClick={() => onRun(flow)}
                  type="button"
                >
                  <Play className="h-4 w-4" />
                  {runningFlowId === flow.flowId ? "Running" : "Run published flow"}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
