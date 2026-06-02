import { FlowCanvasWorkbench } from "@/components/flow-canvas-workbench";
import { FlowCatalog } from "@/components/flow-catalog";
import { IntegrationWorkbench } from "@/components/integration-workbench";
import { PlatformShell } from "@/components/platform-shell";
import { getFlows } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowsPage() {
  const flowsResult = await getFlows();

  return (
    <PlatformShell
      active="/flows"
      subtitle="Choose systems, pick data, match fields, add governed AI help, review controls, and publish approved integrations."
      title="Integration Studio"
    >
      <div className="-mx-5 space-y-2 lg:-mx-8">
        <IntegrationWorkbench />
        <FlowCanvasWorkbench initialFlows={flowsResult} />
        <FlowCatalog initialFlows={flowsResult} />
      </div>
    </PlatformShell>
  );
}
