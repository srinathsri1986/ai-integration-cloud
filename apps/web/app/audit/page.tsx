import { AuditLogPanel } from "@/components/audit-log-panel";
import { PlatformShell } from "@/components/platform-shell";

export const dynamic = "force-dynamic";

export default function AuditPage() {
  return (
    <PlatformShell
      active="/audit"
      subtitle="Review every governed AI call, tool call, fallback event, flow run, and connector action from a single control surface."
      title="Governance Center"
    >
      <div className="-mx-5 lg:-mx-8">
        <AuditLogPanel />
      </div>
    </PlatformShell>
  );
}
