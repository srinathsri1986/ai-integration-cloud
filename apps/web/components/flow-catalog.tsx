"use client";

import { useState } from "react";
import { GitBranch, Play, Workflow } from "lucide-react";
import type { FlowDefinition, FlowRunResponse } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { type ApiResult, runFlow } from "@/lib/api";

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export function FlowCatalog({ initialFlows }: { initialFlows: ApiResult<FlowDefinition[]> }) {
  const [flows, setFlows] = useState(initialFlows.data);
  const [error, setError] = useState<string | undefined>(
    initialFlows.isFallback ? initialFlows.error : undefined
  );
  const [runningFlowId, setRunningFlowId] = useState<string | undefined>();
  const [lastRun, setLastRun] = useState<Record<string, FlowRunResponse>>({});

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

              <Button
                className="mt-4 w-full"
                disabled={runningFlowId === flow.flowId}
                onClick={() => onRun(flow)}
                type="button"
              >
                <Play className="h-4 w-4" />
                {runningFlowId === flow.flowId ? "Running" : "Run flow"}
              </Button>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
