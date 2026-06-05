"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  TrendingUp,
  XCircle,
  Zap
} from "lucide-react";
import type { FlowDefinition, FlowRunResponse } from "@netsuite-cfo/shared";

import { Card } from "@/components/ui/card";
import { SkeletonTile, SkeletonRow } from "@/components/ui/skeleton";

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
  if (status === "succeeded") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
  }
  if (status === "failed") {
    return <XCircle className="h-4 w-4 text-rose-500 shrink-0" />;
  }
  if (status === "running") {
    return <Activity className="h-4 w-4 text-sky-500 shrink-0 animate-pulse" />;
  }
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
    sky: "bg-sky-50 text-sky-600",
    rose: "bg-rose-50 text-rose-600",
    amber: "bg-amber-50 text-amber-600"
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
  if (status === "failed") return "border-rose-200 text-rose-700 bg-rose-50";
  if (status === "running") return "border-sky-200 text-sky-700 bg-sky-50";
  return "border-slate-200 text-slate-500 bg-white";
}

export function DashboardConsole({ initialFlows, initialRuns, isFallback }: DashboardConsoleProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const kpis = useMemo(() => {
    const runsToday = initialRuns.filter((r) => {
      const d = r.startedAt ? new Date(r.startedAt) : null;
      return d && d >= today;
    });
    const successToday = runsToday.filter((r) => r.status === "succeeded").length;
    const failedToday = runsToday.filter((r) => r.status === "failed").length;
    const successRate =
      runsToday.length > 0
        ? Math.round((successToday / runsToday.length) * 100)
        : 100;
    const pendingApprovals = initialFlows.filter((f) => f.status === "pending_approval").length;

    return { runsToday: runsToday.length, successRate, pendingApprovals, errors: failedToday };
  }, [initialFlows, initialRuns]);

  const activityFeed = useMemo(() => {
    return [...initialRuns]
      .filter((r) => r.startedAt)
      .sort((a, b) => new Date(b.startedAt!).getTime() - new Date(a.startedAt!).getTime())
      .slice(0, 10);
  }, [initialRuns]);

  if (isFallback) {
    return (
      <div className="px-5 lg:px-8 py-6 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <SkeletonTile key={i} />)}
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="px-5 lg:px-8 py-6 space-y-8">
      {/* KPI Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiTile
          icon={<TrendingUp className="h-5 w-5" />}
          label="Runs Today"
          value={kpis.runsToday}
          sub="across all flows"
          accent="sky"
        />
        <KpiTile
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Success Rate"
          value={`${kpis.successRate}%`}
          sub="today"
          accent="emerald"
        />
        <KpiTile
          icon={<ShieldCheck className="h-5 w-5" />}
          label="Pending Approvals"
          value={kpis.pendingApprovals}
          sub="awaiting review"
          accent="amber"
        />
        <KpiTile
          icon={<AlertCircle className="h-5 w-5" />}
          label="Errors Today"
          value={kpis.errors}
          sub="failed runs"
          accent="rose"
        />
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
                <li key={run.requestId} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors">
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
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Flow Status Overview */}
      <div>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Integration Status
        </h2>
        <Card className="bg-white/85 border border-white/70 shadow-xl shadow-slate-200/60 backdrop-blur overflow-hidden">
          {initialFlows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
              <Activity className="h-8 w-8 opacity-30" />
              <p className="text-sm">No integrations yet.</p>
              <Link href="/flows/new" className="text-xs text-sky-500 hover:underline">
                Create your first integration
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {initialFlows.map((flow) => (
                <li key={flow.flowId} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${
                    flow.status === "published" ? "bg-emerald-400" :
                    flow.status === "pending_approval" ? "bg-amber-400" :
                    flow.status === "paused" ? "bg-slate-400" :
                    "bg-sky-300"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <Link
                      href={`/flows/${flow.flowId}`}
                      className="text-sm font-medium text-slate-800 hover:text-sky-600 truncate block"
                    >
                      {flow.name}
                    </Link>
                    <p className="text-xs text-slate-400 truncate">{flow.description}</p>
                  </div>
                  <span className="inline-flex items-center rounded-md border border-slate-200 bg-muted px-2 py-1 text-xs font-medium capitalize">
                    {flow.status.replace("_", " ")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
