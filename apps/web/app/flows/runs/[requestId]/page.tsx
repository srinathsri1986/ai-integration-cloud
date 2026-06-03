import { FlowRunDetail } from "@/components/flow-run-detail";
import { PlatformShell } from "@/components/platform-shell";
import { getFlowRun } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowRunDetailPage({
  params
}: {
  params: Promise<{ requestId: string }>;
}) {
  const { requestId } = await params;
  const runResult = await getFlowRun(requestId);

  return (
    <PlatformShell
      active="/flows"
      subtitle="Inspect each integration run with step status, payload previews, warnings, and audit trace identifiers."
      title="Run Detail"
    >
      <div className="-mx-5 lg:-mx-8">
        <FlowRunDetail runResult={runResult} />
      </div>
    </PlatformShell>
  );
}
