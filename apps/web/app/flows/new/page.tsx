import { FlowCreationWizard } from "@/components/flow-creation-wizard";
import { PlatformShell } from "@/components/platform-shell";

export const dynamic = "force-dynamic";

export default function NewFlowPage() {
  return (
    <PlatformShell
      active="/flows"
      subtitle="Create a governed integration one decision at a time."
      title="Create Integration"
    >
      <FlowCreationWizard />
    </PlatformShell>
  );
}
