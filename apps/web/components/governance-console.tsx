"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Filter,
  Loader2,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Webhook,
  Zap,
  ZapOff,
} from "lucide-react";
import type { AuditLogEntry, FlowDefinition } from "@ai-integration-cloud/shared";

import { EmptyState } from "@/components/empty-state";
import {
  type AuditLogsFilter,
  type AuditMetrics,
  type WebhookDelivery,
  type WebhookDeliveryStats,
  auditExportUrl,
  getAuditLogs,
  getAuditMetrics,
  getWebhookDeliveries,
  getWebhookDeliveryStats,
  retryWebhookDelivery,
  transitionFlowLifecycle,
} from "@/lib/api";

type Tab = "approvals" | "audit" | "webhooks";
type StatusFilter = "all" | "succeeded" | "failed";

interface GovernanceConsoleProps {
  initialFlows: FlowDefinition[];
  initialAuditLogs: AuditLogEntry[];
  initialMetrics?: AuditMetrics;
  initialWebhookStats?: WebhookDeliveryStats;
}

// ---------------------------------------------------------------------------
// Metric strip card
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "emerald" | "rose" | "teal" | "amber";
}) {
  const accentMap = {
    emerald: "text-emerald-600",
    rose: "text-rose-600",
    teal: "text-teal-600",
    amber: "text-amber-600",
  };
  const color = accent ? accentMap[accent] : "text-slate-900";
  return (
    <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-card">
      <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums leading-none ${color}`}>{value}</p>
      {sub && <p className="mt-1 text-[11px] text-slate-400">{sub}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mini bar chart for events-per-day
// ---------------------------------------------------------------------------

function SparkBar({ data }: { data: AuditMetrics["eventsPerDay"] }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.total), 1);
  const recent = data.slice(-14); // last 14 days

  return (
    <div className="flex h-10 items-end gap-0.5">
      {recent.map((d) => (
        <div key={d.date} className="group relative flex-1" title={`${d.date}: ${d.total} events`}>
          <div
            className="w-full rounded-sm bg-teal-500/70 transition-all group-hover:bg-teal-500"
            style={{ height: `${Math.max((d.total / max) * 100, 4)}%` }}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pending approvals tab
// ---------------------------------------------------------------------------

function ApprovalsTab({ flows }: { flows: FlowDefinition[] }) {
  const [localFlows, setLocalFlows] = useState(flows);
  const [busyKey, setBusyKey]       = useState<string | null>(null);
  const [error, setError]           = useState<string | null>(null);

  const pending = localFlows.filter((f) => f.status === "pending_approval");

  async function act(flow: FlowDefinition, action: "approve" | "reject") {
    setBusyKey(`${flow.flowId}:${action}`);
    setError(null);
    const result = await transitionFlowLifecycle(flow.flowId, action);
    setBusyKey(null);
    if (!result.ok) {
      setError(result.error ?? "Action failed.");
      return;
    }
    setLocalFlows((prev) =>
      prev.map((f) => (f.flowId === flow.flowId ? result.data.flow : f))
    );
  }

  if (pending.length === 0) {
    return (
      <EmptyState
        icon={<ShieldCheck className="h-10 w-10 text-teal-400" />}
        title="No pending approvals"
        description="All integrations are either approved, published, or in draft."
      />
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {error}
        </p>
      )}
      {pending.map((flow) => {
        const approveBusy = busyKey === `${flow.flowId}:approve`;
        const rejectBusy  = busyKey === `${flow.flowId}:reject`;
        return (
          <div
            key={flow.flowId}
            className="flex items-start justify-between gap-4 rounded-xl border border-amber-100 bg-white p-4 shadow-card"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">
                  pending
                </span>
                <p className="text-sm font-semibold text-slate-900">{flow.name}</p>
              </div>
              <p className="mt-0.5 truncate text-xs text-slate-500">{flow.description}</p>
              <div className="mt-1.5 flex items-center gap-3 text-[11px] text-slate-400">
                <span>
                  Source:{" "}
                  <span className="font-mono text-slate-600">{flow.sourceConnector}</span>
                </span>
                <span>
                  Trigger:{" "}
                  <span className="capitalize text-slate-600">{flow.triggerType}</span>
                </span>
              </div>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                disabled={!!busyKey}
                onClick={() => act(flow, "reject")}
                className="flex items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 transition-colors hover:bg-rose-50 disabled:opacity-50"
              >
                {rejectBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ZapOff className="h-3.5 w-3.5" />}
                Reject
              </button>
              <button
                type="button"
                disabled={!!busyKey}
                onClick={() => act(flow, "approve")}
                className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-teal-700 disabled:opacity-50"
              >
                {approveBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                Approve
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audit log row — expandable to show tools + question
// ---------------------------------------------------------------------------

function AuditRow({ log }: { log: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);

  const intentLabel = (log.detectedIntent ?? "").replace(/_/g, " ").toLowerCase();
  const toolsShort  = (log.toolsUsed ?? []).slice(0, 2);
  const moreTools   = (log.toolsUsed ?? []).length - 2;

  return (
    <>
      <tr
        className="cursor-pointer border-b border-slate-100 text-xs transition-colors hover:bg-slate-50/70"
        onClick={() => setExpanded((v) => !v)}
      >
        {/* Expand */}
        <td className="w-6 py-3 pl-4 pr-0 text-slate-300">
          {expanded
            ? <ChevronDown className="h-3.5 w-3.5" />
            : <ChevronRight className="h-3.5 w-3.5" />}
        </td>
        {/* Request ID */}
        <td className="max-w-[180px] truncate py-3 pl-2 font-mono text-slate-600">
          {log.requestId ?? "—"}
        </td>
        {/* Intent */}
        <td className="py-3 pr-3">
          <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium capitalize text-slate-600">
            {intentLabel || "—"}
          </span>
        </td>
        {/* Tools used */}
        <td className="py-3 pr-3">
          <div className="flex flex-wrap gap-1">
            {toolsShort.map((t) => (
              <span key={t} className="rounded bg-teal-50 px-1.5 py-0.5 font-mono text-[10px] text-teal-700">
                {t.split(".").slice(-1)[0]}
              </span>
            ))}
            {moreTools > 0 && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                +{moreTools}
              </span>
            )}
          </div>
        </td>
        {/* Status */}
        <td className="py-3 pr-3">
          {log.success ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
              <CheckCircle2 className="h-2.5 w-2.5" /> ok
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700 ring-1 ring-inset ring-rose-200">
              <AlertCircle className="h-2.5 w-2.5" /> fail
            </span>
          )}
        </td>
        {/* Latency */}
        <td className="py-3 pr-3 tabular-nums text-slate-500">
          {log.latencyMs != null ? `${log.latencyMs}ms` : "—"}
        </td>
        {/* Timestamp */}
        <td className="py-3 pr-4 tabular-nums text-slate-400">
          {log.timestamp
            ? new Date(log.timestamp).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "—"}
        </td>
      </tr>
      {/* Expanded detail row */}
      {expanded && (
        <tr className="border-b border-slate-100 bg-slate-50/50">
          <td colSpan={7} className="px-4 py-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Question / Action
                </p>
                <p className="mt-0.5 text-xs text-slate-700">{log.question || "—"}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Endpoint
                </p>
                <p className="mt-0.5 font-mono text-xs text-slate-600">{log.endpointCalled || "—"}</p>
              </div>
              {(log.toolsUsed ?? []).length > 0 && (
                <div className="sm:col-span-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    All Tools Used
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(log.toolsUsed ?? []).map((t) => (
                      <span key={t} className="rounded bg-teal-50 px-2 py-0.5 font-mono text-[10px] text-teal-700 ring-1 ring-inset ring-teal-200">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {log.failureReason && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Failure Reason
                  </p>
                  <p className="mt-0.5 text-xs text-rose-600">{log.failureReason}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Audit tab — filters, metrics strip, log table
// ---------------------------------------------------------------------------

function AuditTab({
  initialLogs,
  initialMetrics,
}: {
  initialLogs: AuditLogEntry[];
  initialMetrics?: AuditMetrics;
}) {
  const [logs, setLogs]           = useState<AuditLogEntry[]>(initialLogs);
  const [metrics, setMetrics]     = useState<AuditMetrics | undefined>(initialMetrics);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [intentFilter, setIntentFilter] = useState("");
  const [dateFrom, setDateFrom]   = useState("");
  const [dateTo, setDateTo]       = useState("");
  const [loading, setLoading]     = useState(false);

  const distinctIntents = useMemo(
    () => metrics?.distinctIntents ?? [],
    [metrics]
  );

  const buildFilter = useCallback((): AuditLogsFilter => {
    const f: AuditLogsFilter = { limit: 200 };
    if (statusFilter === "succeeded") f.success = true;
    if (statusFilter === "failed")    f.success = false;
    if (intentFilter)                 f.intent  = intentFilter;
    if (dateFrom)                     f.since   = dateFrom;
    if (dateTo)                       f.until   = dateTo;
    return f;
  }, [statusFilter, intentFilter, dateFrom, dateTo]);

  async function refresh() {
    setLoading(true);
    const [logsResult, metricsResult] = await Promise.all([
      getAuditLogs(buildFilter()),
      getAuditMetrics(30),
    ]);
    setLogs(logsResult.data);
    setMetrics(metricsResult.data);
    setLoading(false);
  }

  // Re-fetch when filters change (debounce date changes via useEffect dependency)
  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, intentFilter]);

  // For date inputs, only re-fetch when both are set or both are cleared
  useEffect(() => {
    if (dateFrom || dateTo) void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo]);

  const successRate = metrics?.successRate ?? 0;
  const successPct  = `${Math.round(successRate * 100)}%`;
  const avgLatency  = metrics ? `${Math.round(metrics.averageLatencyMs)}ms` : "—";
  const p95         = metrics ? `${metrics.p95LatencyMs}ms` : "—";

  return (
    <div className="space-y-5">
      {/* ── Metric strip ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          label="Total Events"
          value={(metrics?.totalEvents ?? 0).toLocaleString()}
          sub="last 30 days"
          accent="teal"
        />
        <MetricCard
          label="Success Rate"
          value={successPct}
          sub={`${metrics?.totalEvents ?? 0} events`}
          accent={successRate >= 0.95 ? "emerald" : successRate >= 0.8 ? "amber" : "rose"}
        />
        <MetricCard
          label="Avg Latency"
          value={avgLatency}
          sub={`p95 ${p95}`}
          accent="teal"
        />
        <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-card">
          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Activity (14d)
          </p>
          <div className="mt-2">
            {metrics?.eventsPerDay.length ? (
              <SparkBar data={metrics.eventsPerDay} />
            ) : (
              <p className="text-xs text-slate-300">No data</p>
            )}
          </div>
        </div>
      </div>

      {/* ── Filter bar ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Filter className="h-3.5 w-3.5" />
          <span className="font-medium text-slate-500">Filters</span>
        </div>

        {/* Status pills */}
        {(["all", "succeeded", "failed"] as StatusFilter[]).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors ${
              statusFilter === s
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-slate-200 text-slate-600 hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
            }`}
          >
            {s}
          </button>
        ))}

        {/* Intent dropdown */}
        <select
          value={intentFilter}
          onChange={(e) => setIntentFilter(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
        >
          <option value="">All intents</option>
          {distinctIntents.map((i) => (
            <option key={i} value={i}>
              {i.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        {/* Date range */}
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
          title="From date"
        />
        <span className="text-xs text-slate-400">→</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
          title="To date"
        />

        {/* Spacer + actions */}
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={refresh}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50"
          >
            {loading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </button>

          <a
            href={auditExportUrl(buildFilter())}
            download
            className="flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 transition-colors hover:bg-teal-100"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {/* ── Log table ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : logs.length === 0 ? (
        <EmptyState
          icon={<Activity className="h-10 w-10 text-slate-300" />}
          title="No audit entries match"
          description="Try adjusting the filters or date range, or trigger some connector / flow actions."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="w-6 py-2.5 pl-4 pr-0" />
                <th className="py-2.5 pl-2 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Request ID
                </th>
                <th className="py-2.5 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Intent
                </th>
                <th className="py-2.5 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Tools
                </th>
                <th className="py-2.5 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Status
                </th>
                <th className="py-2.5 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" /> Latency
                  </span>
                </th>
                <th className="py-2.5 pr-4 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Timestamp
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 200).map((log, i) => (
                <AuditRow key={log.requestId ?? i} log={log} />
              ))}
            </tbody>
          </table>
          {logs.length > 200 && (
            <p className="border-t border-slate-100 py-2.5 text-center text-xs text-slate-400">
              Showing 200 of {logs.length} entries. Export CSV for the full dataset.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Webhooks tab — delivery log, stats, retry
// ---------------------------------------------------------------------------

const _STATUS_COLORS: Record<string, string> = {
  succeeded:   "bg-emerald-50 text-emerald-700 ring-emerald-200",
  processing:  "bg-blue-50 text-blue-700 ring-blue-200",
  failed:      "bg-amber-50 text-amber-700 ring-amber-200",
  dead_letter: "bg-rose-50 text-rose-700 ring-rose-200",
};

function DeliveryStatusBadge({ status }: { status: string }) {
  const cls = _STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function WebhooksTab({ initialStats }: { initialStats?: WebhookDeliveryStats }) {
  const [deliveries, setDeliveries]   = useState<WebhookDelivery[]>([]);
  const [stats, setStats]             = useState<WebhookDeliveryStats | undefined>(initialStats);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading]         = useState(false);
  const [retryingId, setRetryingId]   = useState<string | null>(null);
  const [banner, setBanner]           = useState<{ type: "success"|"error"; msg: string } | null>(null);

  async function refresh() {
    setLoading(true);
    const [dResult, sResult] = await Promise.all([
      getWebhookDeliveries({ status: statusFilter === "all" ? undefined : statusFilter, limit: 200 }),
      getWebhookDeliveryStats(),
    ]);
    setDeliveries(dResult.data);
    setStats(sResult.data);
    setLoading(false);
  }

  useEffect(() => { void refresh(); }, [statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleRetry(delivery: WebhookDelivery) {
    setRetryingId(delivery.deliveryId);
    const result = await retryWebhookDelivery(delivery.deliveryId);
    setRetryingId(null);
    if (result.ok) {
      setBanner({ type: "success", msg: `Delivery ${delivery.deliveryId.slice(0, 8)}… re-queued successfully.` });
      void refresh();
    } else {
      setBanner({ type: "error", msg: result.error ?? "Retry failed." });
    }
  }

  const deadLetterCount = stats?.deadLetter ?? 0;

  return (
    <div className="space-y-5">
      {/* Stats strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          { label: "Total",       value: stats?.total ?? 0,       accent: "teal"    },
          { label: "Succeeded",   value: stats?.succeeded ?? 0,   accent: "emerald" },
          { label: "Processing",  value: stats?.processing ?? 0,  accent: "blue"    },
          { label: "Failed",      value: stats?.failed ?? 0,      accent: "amber"   },
          { label: "Dead Letter", value: stats?.deadLetter ?? 0,  accent: "rose"    },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-card">
            <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
            <p className={`mt-1 text-2xl font-bold tabular-nums leading-none text-${accent}-600`}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Banner */}
      {banner && (
        <div className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-2.5 text-xs ${
          banner.type === "success"
            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
            : "border-rose-200 bg-rose-50 text-rose-800"
        }`}>
          <span>{banner.msg}</span>
          <button type="button" onClick={() => setBanner(null)} className="opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2.5">
        <Filter className="h-3.5 w-3.5 text-slate-400" />
        {(["all", "processing", "succeeded", "failed", "dead_letter"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors ${
              statusFilter === s
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-slate-200 text-slate-600 hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
            }`}
          >
            {s.replace("_", " ")}
            {s === "dead_letter" && deadLetterCount > 0 && (
              <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
                {deadLetterCount}
              </span>
            )}
          </button>
        ))}
        <button
          type="button"
          disabled={loading}
          onClick={refresh}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Refresh
        </button>
      </div>

      {/* Deliveries table */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : deliveries.length === 0 ? (
        <EmptyState
          icon={<Webhook className="h-10 w-10 text-slate-300" />}
          title="No webhook deliveries yet"
          description="Once a webhook-triggered flow receives a POST, deliveries will appear here."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {["Delivery ID", "Flow", "Status", "Attempts", "Received", "Next Retry / Completed", ""].map((h) => (
                  <th key={h} className="py-2.5 pl-4 pr-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deliveries.map((d) => (
                <tr key={d.deliveryId} className="border-b border-slate-100 text-xs transition-colors hover:bg-slate-50/70">
                  <td className="max-w-[120px] truncate py-3 pl-4 pr-3 font-mono text-slate-600">
                    {d.deliveryId.slice(0, 12)}…
                  </td>
                  <td className="py-3 pr-3">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700">
                      {d.flowId}
                    </span>
                  </td>
                  <td className="py-3 pr-3">
                    <DeliveryStatusBadge status={d.status} />
                  </td>
                  <td className="py-3 pr-3 tabular-nums text-slate-500">
                    {d.attemptCount} / {d.maxAttempts}
                  </td>
                  <td className="py-3 pr-3 tabular-nums text-slate-400">
                    {d.receivedAt
                      ? new Date(d.receivedAt).toLocaleString(undefined, {
                          month: "short", day: "numeric",
                          hour: "2-digit", minute: "2-digit",
                        })
                      : "—"}
                  </td>
                  <td className="py-3 pr-3 text-slate-400">
                    {d.nextRetryAt
                      ? <span className="text-amber-600">{new Date(d.nextRetryAt).toLocaleString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>
                      : d.completedAt
                        ? new Date(d.completedAt).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                        : "—"}
                  </td>
                  <td className="py-3 pr-4">
                    {(d.status === "failed" || d.status === "dead_letter") && (
                      <button
                        type="button"
                        disabled={retryingId === d.deliveryId}
                        onClick={() => handleRetry(d)}
                        className="flex items-center gap-1 rounded-lg border border-teal-200 bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-700 transition-colors hover:bg-teal-100 disabled:opacity-50"
                      >
                        {retryingId === d.deliveryId
                          ? <Loader2 className="h-3 w-3 animate-spin" />
                          : <RotateCcw className="h-3 w-3" />}
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main governance console
// ---------------------------------------------------------------------------

export function GovernanceConsole({
  initialFlows,
  initialAuditLogs,
  initialMetrics,
  initialWebhookStats,
}: GovernanceConsoleProps) {
  const [tab, setTab] = useState<Tab>("approvals");

  const pendingCount    = initialFlows.filter((f) => f.status === "pending_approval").length;

  return (
    <div className="space-y-5 px-5 py-6 lg:px-8">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {(["approvals", "audit", "webhooks"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === t
                ? "border-teal-600 text-teal-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "approvals" ? (
              <span className="flex items-center gap-1.5">
                Pending Approvals
                {pendingCount > 0 && (
                  <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-white">
                    {pendingCount}
                  </span>
                )}
              </span>
            ) : t === "audit" ? (
              <span className="flex items-center gap-1.5">
                Audit Log
                <Activity className="h-3.5 w-3.5 opacity-60" />
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                Webhooks
                <Webhook className="h-3.5 w-3.5 opacity-60" />
                {(initialWebhookStats?.deadLetter ?? 0) > 0 && (
                  <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
                    {initialWebhookStats!.deadLetter}
                  </span>
                )}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "approvals" && <ApprovalsTab flows={initialFlows} />}
      {tab === "audit" && (
        <AuditTab initialLogs={initialAuditLogs} initialMetrics={initialMetrics} />
      )}
      {tab === "webhooks" && (
        <WebhooksTab initialStats={initialWebhookStats} />
      )}
    </div>
  );
}
