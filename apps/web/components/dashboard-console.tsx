"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  XCircle,
  Zap
} from "lucide-react";
import type { FlowDefinition, FlowRunResponse } from "@ai-integration-cloud/shared";

import { Card } from "@/components/ui/card";
import { getFlows, getRecentFlowRuns } from "@/lib/api";

const POLL_INTERVAL_MS = 5_000;

interface DashboardConsoleProps {
  initialFlows: FlowDefinition[];
  initialRuns: FlowRunResponse[];
  isFallback: boolean;
}

function timeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

function RunStatusDot({ status }: { status: string }) {
  if (status === "succeeded") return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
  if (status === "failed")    return <XCircle      className="h-4 w-4 text-rose-500 shrink-0" />;
  if (status === "running")   return <Activity     className="h-4 w-4 text-sky-500 shrink-0 animate-pulse" />;
  return <Clock className="h-4 w-4 text-slate-400 shrink-0" />;
}

interface KpiTileProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent?: "emerald" | "sky" | "rose" | "amber";
}

function KpiTile({ icon, label, value, sub, accent = "sky" }: KpiTileProps) {
  const accentMap = {
    emerald: "bg-emerald-50 text-emerald-600",
    sky:     "bg-sky-50 text-sky-600",
    rose:    "bg-rose-50 text-rose-600",
    amber:   "bg-amber-50 text-amber-600",
  };
  return (
    <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur p-5 flex flex-col gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${accentMap[accent]}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900 tabular-nums">{value}</p>
        <p className="text-sm font-medium text-slate-600 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </Card>
  );
}

function runStatusClass(status: string): string {
  if (status === "succeeded") return "border-emerald-200 text-emerald-700 bg-emerald-50";
  if (status === "failed")    return "border-rose-200 text-rose-700 bg-rose-50";
  if (status === "running")   return "border-sky-200 text-sky-700 bg-sky-50";
  return "border-slate-200 text-slate-500 bg-white";
}

function flowStatusClass(status: FlowDefinition["status"]): string {
  if (status === "published")        return "border-emerald-200 text-emerald-700 bg-emerald-50";
  if (status === "pending_approval") return "border-amber-200 text-amber-700 bg-amber-50";
  if (status === "paused")           return "border-slate-300 text-slate-500 bg-slate-100";
  return "border-slate-200 text-slate-500 bg-white";
}

export function DashboardConsole({ initialFlows, initialRuns, isFallback }: DashboardConsoleProps) {
  const [flows, setFlows] = useState<FlowDefinition[]>(initialFlows);
  const [runs, setRuns]   = useState<FlowRunResponse[]>(initialRuns);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const cancelledRef = useRef(false);

  // Poll every 5 s — stops if the component unmounts
  useEffect(() => {
    cancelledRef.current = false;

    async function tick() {
      if (cancelledRef.current) return;
      setIsRefreshing(true);
      const [flowsResult, runsResult] = await Promise.all([
        getFlows(),
        getRecentFlowRuns(50),
      ]);
      if (cancelledRef.current) return;
      if (!flowsResult.isFallback) setFlows(flowsResult.data.items ?? []);
      if (!runsResult.isFallback)  setRuns(runsResult.data ?? []);
      setLastRefresh(new Date());
      setIsRefreshing(false);
    }

    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelledRef.current = true;
      clearInterval(id);
    };
  }, []);

  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const kpis = useMemo(() => {
    const runsToday = runs.filter((r) => {
      const d = r.startedAt ? new Date(r.startedAt) : null;
      return d && d >= today;
    });
    const successToday = runsToday.filter((r) => r.status === "succeeded").length;
    const failedToday  = runsToday.filter((r) => r.status === "failed").length;
    const successRate  = runsToday.length > 0
      ? Math.round((successToday / runsToday.length) * 100)
      : 100;
    const pendingApprovals = flows.filter((f) => f.status === "pending_approval").length;
    return { runsToday: runsToday.length, successRate, pendingApprovals, errors: failedToday };
  }, [flows, runs, today]);

  const activityFeed = useMemo(() =>
    [...runs]
      .filter((r) => r.startedAt)
      .sort((a, b) => new Date(b.startedAt!).getTime() - new Date(a.startedAt!).getTime())
      .slice(0, 10),
    [runs],
  );

  const hasActiveRuns = runs.some((r) => r.status === "running");

  return (
    <div className="px-5 lg:px-8 py-6 space-y-8">
      {isFallback && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>Live data unavailable</strong> — showing last known state. Check that the API
          service is running and refresh the page.
        </div>
      )}

      {/* Live indicator */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <RefreshCw className={`h-3 w-3 ${isRefreshing ? "animate-spin text-sky-500" : ""}`} />
        {hasActiveRuns
          ? <span className="text-sky-600 font-medium">Live — polling every 5 s</span>
          : <span>Auto-refreshing every 5 s · last updated {timeAgo(lastRefresh.toISOString())}</span>
        }
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiTile icon={<TrendingUp   className="h-5 w-5" />} label="Runs Today"        value={kpis.runsToday}            sub="across all flows"   accent="sky" />
        <KpiTile icon={<CheckCircle2 className="h-5 w-5" />} label="Success Rate"      value={`${kpis.successRate}%`}    sub="today"              accent="emerald" />
        <KpiTile icon={<ShieldCheck  className="h-5 w-5" />} label="Pending Approvals" value={kpis.pendingApprovals}     sub="awaiting review"    accent="amber" />
        <KpiTile icon={<AlertCircle  className="h-5 w-5" />} label="Errors Today"      value={kpis.errors}               sub="failed runs"        accent="rose" />
      </div>

      {/* Activity Feed */}
      <div>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Recent Activity
        </h2>
        <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur overflow-hidden">
          {activityFeed.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
              <Zap className="h-8 w-8 opacity-30" />
              <p className="text-sm">No runs recorded yet. Trigger a flow to see activity.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {activityFeed.map((run) => (
                <li key={`${run.requestId}`} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors">
                  <RunStatusDot status={run.status} />
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/flows/${run.flowId}`}
                      className="text-sm font-medium text-slate-800 hover:text-sky-600 truncate block"
                    >
                      {run.flowId}
                    </Link>
                    <p className="text-xs text-slate-400 truncate">
                      Run {run.requestId.slice(0, 8)}…
                    </p>
                  </div>
                  <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${runStatusClass(run.status)}`}>
                    {run.status.replace("_", " ")}
                  </span>
                  <span className="text-xs text-slate-400 shrink-0 tabular-nums">
                    {timeAgo(run.startedAt!)}
                  </span>
                  <Link
                    href={`/flows/runs/${run.requestId}`}
                    className="text-xs text-slate-400 hover:text-sky-500 transition-colors shrink-0"
                  >
                    →
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Integration Status */}
      <div>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Integration Status
        </h2>
        <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur overflow-hidden">
          {flows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
              <Activity className="h-8 w-8 opacity-30" />
              <p className="text-sm">No integrations yet.</p>
              <Link href="/flows/new" className="text-xs text-sky-500 hover:underline">
                Create your first integration
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {flows.map((flow) => {
                const latestRun = runs
                  .filter((r) => r.flowId === flow.flowId)
                  .sort((a, b) => new Date(b.startedAt ?? 0).getTime() - new Date(a.startedAt ?? 0).getTime())[0];
                return (
                  <li key={flow.flowId} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors">
                    <span className={`h-2 w-2 rounded-full shrink-0 ${
                      flow.status === "published"        ? "bg-emerald-400" :
                      flow.status === "pending_approval" ? "bg-amber-400 animate-pulse" :
                      flow.status === "paused"           ? "bg-slate-400" :
                      "bg-sky-300"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/flows/${flow.flowId}`}
                        className="text-sm font-medium text-slate-800 hover:text-sky-600 truncate block"
                      >
                        {flow.name}
                      </Link>
                      <p className="text-xs text-slate-400 truncate">
                        {latestRun
                          ? `Last run ${timeAgo(latestRun.startedAt!)} — ${latestRun.status}`
                          : flow.description ?? "No runs yet"}
                      </p>
                    </div>
                    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${flowStatusClass(flow.status)}`}>
                      {flow.status.replace("_", " ")}
                    </span>
                    {latestRun?.status === "running" && (
                      <Activity className="h-3.5 w-3.5 text-sky-500 animate-pulse shrink-0" />
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
