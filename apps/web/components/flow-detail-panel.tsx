"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  Hand,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  ShieldCheck,
  Webhook,
  XCircle,
  Zap
} from "lucide-react";
import type { FlowDefinition, FlowLifecycleAction, FlowRunResponse } from "@ai-integration-cloud/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SkeletonTile, SkeletonRow } from "@/components/ui/skeleton";
import { runFlow, transitionFlowLifecycle } from "@/lib/api";

// ── Lifecycle pipeline ──────────────────────────────────────────────────────

const PIPELINE_STEPS: Array<{ key: string; label: string }> = [
  { key: "draft", label: "Draft" },
  { key: "pending_approval", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "published", label: "Live" }
];

const PIPELINE_ORDER: Record<string, number> = {
  draft: 0,
  pending_approval: 1,
  approved: 2,
  published: 3,
  paused: 3
};

function LifecyclePipeline({ status }: { status: FlowDefinition["status"] }) {
  const currentIndex = PIPELINE_ORDER[status] ?? 0;

  return (
    <div className="flex items-center gap-0">
      {PIPELINE_STEPS.map((step, i) => {
        const reached = i <= currentIndex && status !== "paused";
        const isLast = i === PIPELINE_STEPS.length - 1;
        const isPausedAtLive = status === "paused" && i === PIPELINE_STEPS.length - 1;

        return (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={`
                h-7 w-7 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors
                ${isPausedAtLive
                  ? "border-slate-400 bg-slate-200 text-slate-500"
                  : reached
                  ? "border-sky-500 bg-sky-500 text-white"
                  : "border-slate-300 bg-white text-slate-400"
                }
              `}>
                {isPausedAtLive ? (
                  <Pause className="h-3 w-3" />
                ) : reached ? (
                  <CheckCircle2 className="h-3 w-3" />
                ) : (
                  i + 1
                )}
              </div>
              <span className={`text-[10px] font-medium ${reached ? "text-sky-700" : "text-slate-400"}`}>
                {isPausedAtLive ? "Paused" : step.label}
              </span>
            </div>
            {!isLast && (
              <div className={`h-0.5 w-10 mx-1 mb-4 ${i < currentIndex ? "bg-sky-400" : "bg-slate-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function runStatusClass(status: string): string {
  if (status === "succeeded") return "border-emerald-200 text-emerald-700 bg-emerald-50";
  if (status === "failed") return "border-rose-200 text-rose-700 bg-rose-50";
  if (status === "running") return "border-sky-200 text-sky-700 bg-sky-50";
  return "border-slate-200 text-slate-500 bg-white";
}

function durationMs(run: FlowRunResponse): string {
  if (!run.startedAt || !run.completedAt) return "—";
  const ms = new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function TriggerIcon({ type }: { type: string }) {
  if (type === "schedule") return <Calendar className="h-4 w-4 text-sky-500" />;
  if (type === "webhook") return <Webhook className="h-4 w-4 text-violet-500" />;
  return <Hand className="h-4 w-4 text-slate-500" />;
}

function statusFlowClass(status: FlowDefinition["status"]): string {
  if (status === "published") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (status === "pending_approval") return "text-amber-700 bg-amber-50 border-amber-200";
  if (status === "paused") return "text-slate-600 bg-slate-100 border-slate-300";
  return "text-slate-600 bg-white border-slate-200";
}

// ── Main component ───────────────────────────────────────────────────────────

interface FlowDetailPanelProps {
  initialFlow: FlowDefinition;
  initialRuns: FlowRunResponse[];
  isFallback: boolean;
}

export function FlowDetailPanel({ initialFlow, initialRuns, isFallback }: FlowDetailPanelProps) {
  const [flow, setFlow] = useState(initialFlow);
  const [runs, setRuns] = useState(initialRuns);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [runLoading, setRunLoading] = useState(false);

  async function handleLifecycle(action: FlowLifecycleAction) {
    setActionLoading(action);
    setActionError(null);
    const result = await transitionFlowLifecycle(flow.flowId, action);
    setActionLoading(null);
    if (!result.ok) {
      setActionError(result.error ?? "Action failed.");
      return;
    }
    setFlow(result.data.flow);
  }

  async function handleRun() {
    setRunLoading(true);
    const result = await runFlow(flow.flowId);
    setRunLoading(false);
    if (result.ok) {
      setRuns((prev) => [result.data, ...prev]);
    }
  }

  if (isFallback) {
    return (
      <div className="px-5 lg:px-8 py-6 space-y-4">
        {[...Array(3)].map((_, i) => <SkeletonTile key={i} />)}
        {[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}
      </div>
    );
  }

  const availableActions: FlowLifecycleAction[] = (() => {
    if (flow.status === "draft") return ["submit_for_approval"];
    if (flow.status === "pending_approval") return ["approve", "reject"];
    if (flow.status === "approved") return ["publish", "reject"];
    if (flow.status === "published") return ["pause"];
    if (flow.status === "paused") return ["unpause"];
    return [];
  })();

  const actionLabels: Record<string, string> = {
    submit_for_approval: "Submit for Approval",
    approve: "Approve",
    reject: "Reject",
    publish: "Publish",
    pause: "Pause",
    unpause: "Restore to Live"
  };

  return (
    <div className="px-5 lg:px-8 py-6">
      {/* Back link */}
      <div className="mb-5">
        <Link
          href="/flows"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-sky-600 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> All Integrations
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left column: config + lifecycle */}
        <div className="lg:col-span-2 space-y-5">
          {/* Config card */}
          <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur p-5 space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold text-slate-900">{flow.name}</h2>
                {flow.description && (
                  <p className="text-sm text-slate-500 mt-0.5">{flow.description}</p>
                )}
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <TriggerIcon type={flow.triggerType} />
                <span className="inline-flex items-center rounded-md border border-slate-200 bg-muted px-2 py-1 text-xs font-medium capitalize">
                  {flow.triggerType}
                </span>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-slate-400">Status</dt>
              <dd>
                <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${statusFlowClass(flow.status)}`}>
                  {flow.status.replace("_", " ")}
                </span>
              </dd>

              <dt className="text-slate-400">Source</dt>
              <dd className="font-mono text-xs text-slate-700">{flow.sourceConnector}</dd>

              <dt className="text-slate-400">Target</dt>
              <dd className="font-mono text-xs text-slate-700">{flow.targetModule}</dd>

              {flow.triggerCron && (
                <>
                  <dt className="text-slate-400">Schedule</dt>
                  <dd className="font-mono text-xs text-slate-700">{flow.triggerCron}</dd>
                </>
              )}

              <dt className="text-slate-400">Last run</dt>
              <dd className="text-xs text-slate-600">
                {flow.lastRunAt ? new Date(flow.lastRunAt).toLocaleString() : "Never"}
              </dd>
            </dl>
          </Card>

          {/* Lifecycle pipeline card */}
          <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur p-5 space-y-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Approval Pipeline</h3>
            <LifecyclePipeline status={flow.status} />

            {actionError && (
              <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded px-2 py-1">{actionError}</p>
            )}

            <div className="flex flex-wrap gap-2 pt-1">
              {flow.status === "published" && (
                <Button
                  variant="default"
                  onClick={handleRun}
                  disabled={runLoading}
                  className="gap-1.5 h-8 px-3 text-xs"
                >
                  {runLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  Run Now
                </Button>
              )}
              {availableActions.map((action) => (
                <Button
                  key={action}
                  variant={action === "reject" ? "default" : "secondary"}
                  onClick={() => handleLifecycle(action)}
                  disabled={actionLoading !== null}
                  className={`gap-1.5 h-8 px-3 text-xs ${action === "reject" ? "bg-rose-600 hover:bg-rose-700 text-white" : ""}`}
                >
                  {actionLoading === action ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : action === "pause" ? (
                    <Pause className="h-3.5 w-3.5" />
                  ) : action === "unpause" ? (
                    <RefreshCw className="h-3.5 w-3.5" />
                  ) : action === "approve" ? (
                    <ShieldCheck className="h-3.5 w-3.5" />
                  ) : null}
                  {actionLabels[action]}
                </Button>
              ))}
            </div>
          </Card>
        </div>

        {/* Right column: run history */}
        <div className="lg:col-span-3">
          <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-700">Run History</h3>
              <span className="text-xs text-slate-400">{runs.length} run{runs.length !== 1 ? "s" : ""}</span>
            </div>

            {runs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                <Zap className="h-8 w-8 opacity-30" />
                <p className="text-sm">No runs yet. Trigger the flow to see history.</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {runs.map((run) => (
                  <li key={run.requestId} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors">
                    <div className="shrink-0">
                      {run.status === "succeeded" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : run.status === "failed" ? (
                        <XCircle className="h-4 w-4 text-rose-500" />
                      ) : (
                        <Clock className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-slate-600 truncate">
                        {run.requestId.slice(0, 12)}…
                      </p>
                      <p className="text-xs text-slate-400">
                        {run.startedAt ? new Date(run.startedAt).toLocaleString() : "—"}
                      </p>
                    </div>
                    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${runStatusClass(run.status)}`}>
                      {run.status.replace("_", " ")}
                    </span>
                    <span className="text-xs text-slate-400 tabular-nums shrink-0">{durationMs(run)}</span>
                    <Link
                      href={`/flows/runs/${run.requestId}`}
                      className="shrink-0 text-slate-400 hover:text-sky-500 transition-colors"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
