import { CheckCircle2, Clock3, ListChecks, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { getAuditLogs, getAuditSummary } from "@/lib/api";

function StatCard({
  icon: Icon,
  label,
  value
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <div className="flex items-end justify-between gap-4">
        <p className="text-2xl font-semibold">{value}</p>
        <Icon className="h-5 w-5 text-primary" />
      </div>
    </Card>
  );
}

export async function AuditLogPanel() {
  const [logsResult, summaryResult] = await Promise.all([getAuditLogs(), getAuditSummary()]);
  const logs = logsResult.data.slice(0, 5);
  const summary = summaryResult.data;
  const isFallback = logsResult.isFallback || summaryResult.isFallback;

  return (
    <section className="mx-auto max-w-7xl px-6 pb-12">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Audit log</p>
          <h2 className="mt-1 text-xl font-semibold">Tool execution monitoring</h2>
        </div>
        {isFallback ? (
          <Badge className="border-amber-300 bg-amber-50 text-amber-900">Audit unavailable</Badge>
        ) : (
          <Badge className="border-emerald-300 bg-emerald-50 text-emerald-900">In memory</Badge>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <StatCard icon={ListChecks} label="Total calls" value={summary.total} />
        <StatCard icon={CheckCircle2} label="Successes" value={summary.successes} />
        <StatCard icon={XCircle} label="Failures" value={summary.failures} />
        <StatCard icon={Clock3} label="Avg latency" value={`${summary.averageLatencyMs} ms`} />
      </div>

      <div className="mt-4 grid gap-4">
        {logs.length > 0 ? (
          logs.map((log) => (
            <Card key={log.requestId}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{log.detectedIntent}</Badge>
                    <Badge>{log.success ? "success" : "failure"}</Badge>
                    {log.fallbackUsed ? <Badge>fallback</Badge> : null}
                  </div>
                  <p className="mt-3 text-sm font-medium">{log.question}</p>
                  <p className="mt-1 break-all text-xs leading-5 text-muted-foreground">
                    {log.requestId} | {log.endpointCalled} | {log.latencyMs} ms
                  </p>
                </div>
                <div className="flex max-w-xl flex-wrap gap-2">
                  {log.toolsUsed.length > 0 ? (
                    log.toolsUsed.map((tool) => <Badge key={tool}>{tool}</Badge>)
                  ) : (
                    <Badge>no tool</Badge>
                  )}
                </div>
              </div>
            </Card>
          ))
        ) : (
          <Card>
            <p className="text-sm text-muted-foreground">
              No orchestrator executions have been recorded in memory yet.
            </p>
          </Card>
        )}
      </div>
    </section>
  );
}
