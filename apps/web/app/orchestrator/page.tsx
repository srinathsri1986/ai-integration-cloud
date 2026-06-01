import { AiQueryConsole } from "@/components/ai-query-console";
import { PlatformShell } from "@/components/platform-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default function OrchestratorPage() {
  return (
    <PlatformShell
      active="/orchestrator"
      subtitle="Ask CFO questions through governed intent extraction, approved tools, validated narratives, and safe fallback routing."
      title="AI Orchestration Workbench"
    >
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-white/90">
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Governed</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Intent extraction only</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Models classify supported CFO intents. They do not call tools or generate raw ERP queries.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">Model agnostic</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Mock, Ollama, OpenAI</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Local Ollama remains the preferred provider, with deterministic routing as the safe fallback.
            </p>
          </Card>
          <Card className="bg-white/90">
            <Badge className="border-amber-200 bg-amber-50 text-amber-900">Audited</Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Traceable results</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Every query records intent, provider, model call status, tools used, and fallback behavior.
            </p>
          </Card>
        </section>
        <div className="-mx-5 lg:-mx-8">
          <AiQueryConsole />
        </div>
      </div>
    </PlatformShell>
  );
}
