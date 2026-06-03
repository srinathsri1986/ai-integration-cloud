"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Database,
  FileJson,
  Loader2,
  ShieldCheck,
  TriangleAlert,
  Workflow,
  XCircle
} from "lucide-react";
import type { FlowRunResponse } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ApiResult } from "@/lib/api";

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function statusBadgeClass(status: string) {
  if (status === "succeeded") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (status === "failed") return "border-rose-200 bg-rose-50 text-rose-900";
  if (status === "running") return "border-sky-200 bg-sky-50 text-sky-900";
  return "border-slate-200 bg-slate-50 text-slate-800";
}

function jsonBlock(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function mappingSimulation(run: FlowRunResponse) {
  if (run.data && typeof run.data === "object" && "mappingSimulation" in run.data) {
    return (run.data as { mappingSimulation?: unknown }).mappingSimulation;
  }

  return undefined;
}

export function FlowRunDetail({ runResult }: { runResult: ApiResult<FlowRunResponse> }) {
  const router = useRouter();
  const run = runResult.data;
  const inspection = run.inspection;
  const simulation = mappingSimulation(run) as
    | {
        sourcePayload?: unknown;
        targetPayload?: unknown;
        warnings?: string[];
        transformsApplied?: string[];
      }
    | undefined;

  const isRunning = run.status === "running";

  return (
    <section className="space-y-6 px-6 pb-12">
      {isRunning ? (
        <div className="flex items-center gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
          <Loader2 className="h-4 w-4 animate-spin" />
          Flow is executing — refreshing automatically every 3 seconds…
        </div>
      ) : null}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <Badge className={statusBadgeClass(run.status)}>
              {isRunning ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : null}
              {statusLabel(run.status)}
            </Badge>
            <h2 className="mt-4 max-w-4xl text-3xl font-semibold tracking-normal text-slate-950">
              {run.flowId}
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">{run.message}</p>
            <p className="mt-2 text-xs text-muted-foreground">Request {run.requestId}</p>
          </div>
          <Button onClick={() => router.push("/flows")} type="button" variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Back to integrations
          </Button>
        </div>
      </div>

      {runResult.isFallback ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          {runResult.error ?? "The run detail API was unavailable."}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric icon={<Clock3 className="h-4 w-4" />} label="Duration" value={`${inspection?.durationMs ?? 0}ms`} />
        <Metric icon={<Workflow className="h-4 w-4" />} label="Steps" value={String(inspection?.stepCount ?? 0)} />
        <Metric icon={<TriangleAlert className="h-4 w-4" />} label="Warnings" value={String(inspection?.warningCount ?? 0)} />
        <Metric
          icon={<ShieldCheck className="h-4 w-4" />}
          label="Audit trace"
          value={inspection?.auditRequestId ?? run.requestId}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="bg-white">
          <div className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-primary" />
            <h3 className="text-xl font-semibold text-slate-950">Execution timeline</h3>
          </div>
          <div className="mt-5 space-y-3">
            {run.executionTimeline.map((step, index) => (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4" key={step.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-semibold text-slate-950">
                      {index + 1}
                    </span>
                    <div>
                      <p className="font-semibold text-slate-950">{step.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {step.approvedTool ?? "Runtime validation"} · {step.latencyMs}ms
                      </p>
                      {step.mappingDefinitionId ? (
                        <p className="mt-1 text-xs text-sky-900">Mapping {step.mappingDefinitionId}</p>
                      ) : null}
                    </div>
                  </div>
                  <Badge className={statusBadgeClass(step.status)}>
                    {step.status === "succeeded" ? <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> : null}
                    {step.status === "failed" ? <XCircle className="mr-1 h-3.5 w-3.5" /> : null}
                    {statusLabel(step.status)}
                  </Badge>
                </div>
                {step.warnings.length ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950">
                    {step.warnings.join(" ")}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="bg-white">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              <h3 className="text-xl font-semibold text-slate-950">Run metadata</h3>
            </div>
            <div className="mt-5 space-y-3 text-sm">
              <Fact label="Started" value={new Date(run.startedAt).toLocaleString()} />
              <Fact label="Completed" value={run.completedAt ? new Date(run.completedAt).toLocaleString() : "In progress…"} />
              <Fact label="Tools" value={run.toolsUsed.join(", ") || "None"} />
              <Fact label="Mapping" value={inspection?.mappingDefinitionId ?? "None"} />
              <Fact
                label="Payloads"
                value={
                  inspection?.hasSourcePayload || inspection?.hasTargetPayload
                    ? "Source and target preview available"
                    : "No mapped payload preview"
                }
              />
            </div>
          </Card>

          <Card className="bg-white">
            <div className="flex items-center gap-2">
              <FileJson className="h-5 w-5 text-primary" />
              <h3 className="text-xl font-semibold text-slate-950">Payload preview</h3>
            </div>
            <div className="mt-4 space-y-4">
              <Payload title="Source payload" value={simulation?.sourcePayload ?? {}} />
              <Payload title="Target payload" value={simulation?.targetPayload ?? run.data} />
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <Card className="bg-white">
      <div className="flex items-center gap-2 text-primary">{icon}</div>
      <p className="mt-3 text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 truncate text-xl font-semibold text-slate-950">{value}</p>
    </Card>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 break-words font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function Payload({ title, value }: { title: string; value: unknown }) {
  return (
    <div>
      <p className="text-sm font-semibold text-slate-950">{title}</p>
      <pre className="mt-2 max-h-72 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">
        {jsonBlock(value)}
      </pre>
    </div>
  );
}
