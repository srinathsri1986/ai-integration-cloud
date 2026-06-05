import { DashboardConsole } from "@/components/dashboard-console";
import { PlatformShell } from "@/components/platform-shell";
import { getFlows, getFlowRunsForFlow } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const flowsResult = await getFlows();
  // Fetch recent runs for the first few flows to power the activity feed
  const topFlowIds = flowsResult.data.items.slice(0, 5).map((f) => f.flowId);
  const runResults = await Promise.all(
    topFlowIds.map((id) => getFlowRunsForFlow(id, 10))
  );
  const allRuns = runResults.flatMap((r) => r.data);

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
