import { IntegrationManagementConsole } from "@/components/integration-management-console";
import { PlatformShell } from "@/components/platform-shell";
import { getFlows } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowsPage({
  searchParams,
}: {
  searchParams: Promise<{ created?: string }>;
}) {
  const [flowsResult, params] = await Promise.all([getFlows(), searchParams]);
  const createdFlowId = params.created ?? null;

  return (
    <PlatformShell
      active="/flows"
      subtitle="Choose systems, pick data, match fields, add governed AI help, review controls, and publish approved integrations."
      title="Integration Studio"
    >
      <div className="-mx-5 lg:-mx-8">
        <IntegrationManagementConsole
          initialFlows={flowsResult}
          createdFlowId={createdFlowId}
        />
      </div>
    </PlatformShell>
  );
}
