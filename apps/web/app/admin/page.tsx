import Link from "next/link";
import { AccessControlPanel } from "@/components/access-control-panel";
import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default function AdminPage() {
  return (
    <PlatformShell
      active="/admin"
      subtitle="Workspace settings, team management, and runtime controls."
      title="Admin"
    >
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-white/90">
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Team</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Team & Access</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Invite colleagues, manage roles, and view pending invitations.
            </p>
            <Link className="mt-4 block" href="/admin/team">
              <Button className="w-full" type="button" variant="secondary">Manage team</Button>
            </Link>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">Runtime</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Safe configuration</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Runtime validation and redaction keep secrets out of logs and committed files.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-amber-200 bg-amber-50 text-amber-900">Coming soon</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Billing & Plan</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Usage meters, plan tiers, and subscription management arrive in Release 7.0.
            </p>
          </Card>
        </section>
        <div className="-mx-5 lg:-mx-8">
          <AccessControlPanel />
        </div>
      </div>
    </PlatformShell>
  );
}
