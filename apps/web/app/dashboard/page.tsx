import { DashboardConsole } from "@/components/dashboard-console";
import { PlatformShell } from "@/components/platform-shell";
import { getFlows, getRecentFlowRuns } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [flowsResult, runsResult] = await Promise.all([
    getFlows(),
    getRecentFlowRuns(20)
  ]);
  const allRuns = runsResult.data;

  return (
    <PlatformShell
      active="/dashboard"
      subtitle="Live status of your integration estate — runs, approvals, and recent activity."
      title="Dashboard"
    >
      <DashboardConsole
        initialFlows={flowsResult.data.items}
        initialRuns={allRuns}
        isFallback={flowsResult.isFallback}
      />
    </PlatformShell>
  );
}
