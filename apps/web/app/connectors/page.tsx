import { ConnectorCatalog } from "@/components/connector-catalog";
import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getConnectors } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ConnectorsPage() {
  const connectorsResult = await getConnectors();

  return (
    <PlatformShell
      active="/connectors"
      subtitle="Manage approved systems, APIs, auth posture, and connector readiness without exposing credentials or raw system access."
      title="Connector Registry"
    >
      <div className="space-y-8">
        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-white/90">
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Mock first</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Safe local connectors</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              All connectors use approved tool templates and placeholder settings. Secrets never touch source code.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">8 connectors</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">System-agnostic registry</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              NetSuite, Salesforce, SAP, Oracle, HCM, PostgreSQL, REST API, and Slack — all pluggable.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-amber-200 bg-amber-50 text-amber-900">No raw access</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Template-only execution</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Users and AI models cannot submit arbitrary SQL, SuiteQL, URLs, headers, or payloads.
            </p>
          </Card>
        </section>

        {/* All 8 registered connectors — configure, test, browse tools and fields */}
        <ConnectorCatalog initialConnectors={connectorsResult} />
      </div>
    </PlatformShell>
  );
}
