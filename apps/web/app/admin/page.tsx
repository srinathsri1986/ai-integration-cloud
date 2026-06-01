import { AccessControlPanel } from "@/components/access-control-panel";
import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default function AdminPage() {
  return (
    <PlatformShell
      active="/admin"
      subtitle="Local development controls for persona testing, placeholder RBAC, runtime posture, and future tenant administration."
      title="Admin Settings"
    >
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-white/90">
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">Placeholder</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Local RBAC</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Switch roles locally to test persona-aware navigation and protected browser actions.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Runtime</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Safe configuration</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Runtime validation and redaction keep secrets out of logs and committed files.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-amber-200 bg-amber-50 text-amber-900">Future</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Enterprise policies</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              This space will grow into provider, connector, approval, and governance settings.
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
