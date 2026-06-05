"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle2,
  Download,
  Filter,
  Loader2,
  ShieldCheck,
  XCircle
} from "lucide-react";
import type { AuditLogEntry, FlowDefinition } from "@netsuite-cfo/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { transitionFlowLifecycle } from "@/lib/api";

type Tab = "approvals" | "audit";

interface GovernanceConsoleProps {
  initialFlows: FlowDefinition[];
  initialAuditLogs: AuditLogEntry[];
}

// ── CSV export ────────────────────────────────────────────────────────────────

function exportCsv(logs: AuditLogEntry[]) {
  const headers = ["requestId", "detectedIntent", "aiProvider", "success", "latencyMs", "timestamp"];
  const rows = logs.map((l) =>
    [
      l.requestId ?? "",
      l.detectedIntent ?? "",
      l.aiProvider ?? "",
      String(l.success),
      String(l.latencyMs ?? ""),
      l.timestamp ?? ""
    ].map((v) => `"${v.replace(/"/g, '""')}"`).join(",")
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Pending Approvals tab ─────────────────────────────────────────────────────

function ApprovalsTab({ flows }: { flows: FlowDefinition[] }) {
  const [localFlows, setLocalFlows] = useState(flows);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        icon={<ShieldCheck className="h-10 w-10" />}
        title="No pending approvals"
        description="All integrations are either approved, published, or in draft."
      />
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded px-3 py-2">{error}</p>
      )}
      {pending.map((flow) => (
        <Card key={flow.flowId} className="bg-white border border-amber-100 p-4 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-900">{flow.name}</p>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{flow.description}</p>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
              <span>Source: <span className="font-mono">{flow.sourceConnector}</span></span>
              <span>Trigger: <span className="capitalize">{flow.triggerType}</span></span>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button
              onClick={() => act(flow, "reject")}
              disabled={busyKey !== null}
              variant="secondary"
              className="gap-1.5 h-8 px-3 text-xs text-rose-700 border-rose-200 hover:bg-rose-50"
            >
              {busyKey === `${flow.flowId}:reject` ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <XCircle className="h-3.5 w-3.5" />
              )}
              Reject
            </Button>
            <Button
              onClick={() => act(flow, "approve")}
              disabled={busyKey !== null}
              className="gap-1.5 h-8 px-3 text-xs"
            >
              {busyKey === `${flow.flowId}:approve` ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5" />
              )}
              Approve
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ── Audit Log tab ─────────────────────────────────────────────────────────────

type StatusFilter = "all" | "succeeded" | "failed";

function AuditTab({ logs }: { logs: AuditLogEntry[] }) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const filtered = useMemo(() => {
    return logs.filter((l) => {
      if (statusFilter === "succeeded" && !l.success) return false;
      if (statusFilter === "failed" && l.success) return false;
      if (dateFrom && l.timestamp && l.timestamp < dateFrom) return false;
      if (dateTo && l.timestamp && l.timestamp > dateTo + "T23:59:59") return false;
      return true;
    });
  }, [logs, statusFilter, dateFrom, dateTo]);

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Filter className="h-3.5 w-3.5" />
          <span className="font-medium">Filters</span>
        </div>
        {(["all", "succeeded", "failed"] as StatusFilter[]).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full border text-xs font-medium transition-colors capitalize ${
              statusFilter === s
                ? "bg-sky-500 border-sky-500 text-white"
                : "border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {s}
          </button>
        ))}
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="px-2 py-1 rounded border border-slate-200 text-xs text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
          title="From date"
        />
        <span className="text-xs text-slate-400">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="px-2 py-1 rounded border border-slate-200 text-xs text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
          title="To date"
        />
        <Button
          variant="secondary"
          onClick={() => exportCsv(filtered)}
          className="gap-1.5 h-8 px-3 text-xs ml-auto"
        >
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </Button>
      </div>

      {/* Log table */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No audit entries match"
          description="Try adjusting the filters or date range."
        />
      ) : (
        <Card className="overflow-hidden bg-white border border-slate-200">
          <div className="grid grid-cols-[1fr_100px_80px_120px] bg-slate-50 px-4 py-2 text-xs font-semibold uppercase text-slate-500 border-b border-slate-100">
            <span>Request</span>
            <span>Intent</span>
            <span>Status</span>
            <span>Time</span>
          </div>
          <ul className="divide-y divide-slate-100">
            {filtered.slice(0, 100).map((log, i) => (
              <li
                key={log.requestId ?? i}
                className="grid grid-cols-[1fr_100px_80px_120px] items-center gap-2 px-4 py-3 text-xs hover:bg-slate-50 transition-colors"
              >
                <span className="font-mono text-slate-600 truncate">{log.requestId ?? "—"}</span>
                <span className="text-slate-700 truncate capitalize">{log.detectedIntent ?? "—"}</span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                  log.success
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                    : "bg-rose-50 border-rose-200 text-rose-700"
                }`}>
                  {log.success ? "succeeded" : "failed"}
                </span>
                <span className="text-slate-400 tabular-nums">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                </span>
              </li>
            ))}
          </ul>
          {filtered.length > 100 && (
            <p className="text-xs text-slate-400 text-center py-2 border-t border-slate-100">
              Showing 100 of {filtered.length} entries. Export CSV for full data.
            </p>
          )}
        </Card>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function GovernanceConsole({ initialFlows, initialAuditLogs }: GovernanceConsoleProps) {
  const [tab, setTab] = useState<Tab>("approvals");

  const pendingCount = initialFlows.filter((f) => f.status === "pending_approval").length;

  return (
    <div className="px-5 lg:px-8 py-6 space-y-5">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {(["approvals", "audit"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px capitalize ${
              tab === t
                ? "border-sky-500 text-sky-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "approvals" ? (
              <span className="flex items-center gap-1.5">
                Pending Approvals
                {pendingCount > 0 && (
                  <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-amber-500 text-white text-[10px] font-bold">
                    {pendingCount}
                  </span>
                )}
              </span>
            ) : (
              "Audit Log"
            )}
          </button>
        ))}
      </div>

      {tab === "approvals" && <ApprovalsTab flows={initialFlows} />}
      {tab === "audit" && <AuditTab logs={initialAuditLogs} />}
    </div>
  );
}
