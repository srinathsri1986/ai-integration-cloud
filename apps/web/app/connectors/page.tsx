import { ConnectorStudio } from "@/components/connector-studio";
import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  getNetSuiteConnectorConfig,
  getRestApiConnectorConfig,
  getRestApiObjects
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ConnectorsPage() {
  const connectorResult = await getNetSuiteConnectorConfig();
  const restApiConnectorResult = await getRestApiConnectorConfig();
  const restApiObjectsResult = await getRestApiObjects();

  return (
    <PlatformShell
      active="/connectors"
      subtitle="Manage approved systems, APIs, auth posture, and connector readiness without exposing credentials or raw system access."
      title="Systems and Connector Studio"
    >
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-white/90">
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Mock first</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Safe local connector</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              The current NetSuite adapter uses approved templates and placeholder local settings.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">Sandbox ready</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Controlled path to real ERP</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Sandbox wiring is prepared, but secrets stay in local environment files only.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-amber-200 bg-amber-50 text-amber-900">No raw access</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Template-only access</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Users and models cannot submit arbitrary SQL, SuiteQL, URLs, headers, or payloads.
            </p>
          </Card>
        </section>
        <div className="-mx-5 lg:-mx-8">
          <ConnectorStudio
            initialConfig={connectorResult}
            initialRestApiConfig={restApiConnectorResult}
            initialRestApiObjects={restApiObjectsResult}
          />
        </div>
      </div>
    </PlatformShell>
  );
}
