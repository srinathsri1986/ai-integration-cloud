import { TeamManagementPanel } from "@/components/team-management-panel";
import { PlatformShell } from "@/components/platform-shell";

export const dynamic = "force-dynamic";

export default function AdminTeamPage() {
  return (
    <PlatformShell
      active="/admin"
      subtitle="Manage workspace members, invite colleagues, and control role-based access for your team."
      title="Team & Access"
    >
      <TeamManagementPanel />
    </PlatformShell>
  );
}
