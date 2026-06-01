import { FlowCanvasWorkbench } from "@/components/flow-canvas-workbench";
import { FlowCatalog } from "@/components/flow-catalog";
import { PlatformShell } from "@/components/platform-shell";
import { getFlows } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowsPage() {
  const flowsResult = await getFlows();

  return (
    <PlatformShell
      active="/flows"
      subtitle="Design governed NetSuite CFO flows, generate AI-assisted drafts, and keep custom execution fail-closed until runtime mappings are approved."
      title="Flow Design Studio"
    >
      <div className="-mx-5 space-y-2 lg:-mx-8">
        <FlowCanvasWorkbench initialFlows={flowsResult} />
        <FlowCatalog initialFlows={flowsResult} />
      </div>
    </PlatformShell>
  );
}
