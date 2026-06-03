import { GuidedIntegrationWizard } from "@/components/guided-integration-wizard";
import { PlatformShell } from "@/components/platform-shell";
import { getMappingDefinitions } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function NewFlowPage() {
  const mappingsResult = await getMappingDefinitions();

  return (
    <PlatformShell
      active="/flows"
      subtitle="Create a governed integration one decision at a time, with live AI assistance and human review."
      title="Create Integration"
    >
      <div className="-mx-5 lg:-mx-8">
        <GuidedIntegrationWizard initialMappings={mappingsResult} />
      </div>
    </PlatformShell>
  );
}
