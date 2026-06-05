import { FlowDetailPanel } from "@/components/flow-detail-panel";
import { PlatformShell } from "@/components/platform-shell";
import { getFlow, getFlowRunsForFlow } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowDetailPage({
  params
}: {
  params: Promise<{ flowId: string }>;
}) {
  const { flowId } = await params;
  const [flowResult, runsResult] = await Promise.all([
    getFlow(flowId),
    getFlowRunsForFlow(flowId, 10)
  ]);

  return (
    <PlatformShell
      active="/flows"
      subtitle={flowResult.data.description ?? "Integration detail and run history."}
      title={flowResult.data.name}
    >
      <FlowDetailPanel
        initialFlow={flowResult.data}
        initialRuns={runsResult.data}
        isFallback={flowResult.isFallback}
      />
    </PlatformShell>
  );
}
