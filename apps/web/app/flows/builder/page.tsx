import { AIWorkflowBuilder } from "@/components/ai-workflow-builder";
import { PlatformShell } from "@/components/platform-shell";

export const dynamic = "force-dynamic";

export default function AIBuilderPage() {
  return (
    <PlatformShell
      active="/flows/builder"
      subtitle="Describe an integration in plain language — AI generates a governed, step-by-step workflow ready for sandbox and approval."
      title="AI Flow Builder"
    >
      <AIWorkflowBuilder />
    </PlatformShell>
  );
}
