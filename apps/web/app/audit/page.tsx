import { GovernanceConsole } from "@/components/governance-console";
import { PlatformShell } from "@/components/platform-shell";
import { getAuditLogs, getAuditMetrics, getFlows } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const [flowsResult, auditResult, metricsResult] = await Promise.all([
    getFlows(),
    getAuditLogs({ limit: 200 }),
    getAuditMetrics(30),
  ]);

  return (
    <PlatformShell
      active="/audit"
      subtitle="Approve pending integrations, review every governed tool call, and export audit trails."
      title="Governance Center"
    >
      <div className="-mx-5 lg:-mx-8">
        <GovernanceConsole
          initialFlows={flowsResult.data.items}
          initialAuditLogs={auditResult.data}
          initialMetrics={metricsResult.data}
        />
      </div>
    </PlatformShell>
  );
}
