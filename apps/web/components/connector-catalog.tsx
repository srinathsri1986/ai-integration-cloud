"use client";

import { useState } from "react";
import type { ConnectorDefinition, ConnectorTool } from "@ai-integration-cloud/shared";
import type { ApiResult } from "@/lib/api";
import { testConnector, getConnectorTools } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Loader2, RefreshCw, Wrench, XCircle } from "lucide-react";

interface ConnectorCatalogProps {
  initialConnectors: ApiResult<ConnectorDefinition[]>;
}

function statusBadge(status: string) {
  if (status === "test_passed" || status === "configured")
    return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400"><CheckCircle2 className="h-3 w-3" />Live</span>;
  if (status === "test_failed")
    return <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-400"><XCircle className="h-3 w-3" />Failed</span>;
  return <span className="inline-flex items-center gap-1 rounded-full bg-slate-500/10 px-2 py-0.5 text-xs font-medium text-slate-400">Mock</span>;
}

function authSchemeBadge(scheme: string) {
  const colors: Record<string, string> = {
    oauth2: "bg-sky-500/10 text-sky-400",
    api_key: "bg-violet-500/10 text-violet-400",
    basic: "bg-amber-500/10 text-amber-400",
    token_based: "bg-indigo-500/10 text-indigo-400",
    none: "bg-slate-500/10 text-slate-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[scheme] ?? colors.none}`}>
      {scheme}
    </span>
  );
}

export function ConnectorCatalog({ initialConnectors }: ConnectorCatalogProps) {
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>(initialConnectors.data);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string } | null>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [tools, setTools] = useState<Record<string, ConnectorTool[]>>({});
  const [loadingTools, setLoadingTools] = useState<string | null>(null);

  async function handleTest(connectorId: string) {
    setTestingId(connectorId);
    const result = await testConnector(connectorId);
    setTestResults((prev) => ({ ...prev, [connectorId]: result.data }));
    setTestingId(null);
  }

  async function handleExpand(connectorId: string) {
    if (expandedId === connectorId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(connectorId);
    if (!tools[connectorId]) {
      setLoadingTools(connectorId);
      const result = await getConnectorTools(connectorId);
      setTools((prev) => ({ ...prev, [connectorId]: result.data }));
      setLoadingTools(null);
    }
  }

  return (
    <section>
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Registered Connectors
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {connectors.map((c) => {
          const testResult = testResults[c.connectorId];
          const isTesting = testingId === c.connectorId;
          const isExpanded = expandedId === c.connectorId;
          const connectorTools = tools[c.connectorId] ?? [];
          const isLoadingTools = loadingTools === c.connectorId;

          return (
            <Card
              key={c.connectorId}
              className="border-white/10 bg-slate-800/60 text-slate-100"
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-sm font-semibold">{c.name}</CardTitle>
                    <p className="mt-0.5 font-mono text-xs text-slate-500">{c.connectorId}</p>
                  </div>
                  {statusBadge(c.status)}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {authSchemeBadge(c.authScheme)}
                  <span className="rounded-full bg-slate-700/60 px-2 py-0.5 text-xs text-slate-400">
                    {c.toolCount} tool{c.toolCount !== 1 ? "s" : ""}
                  </span>
                </div>
              </CardHeader>
              <div className="space-y-2">
                {testResult && (
                  <p className={`text-xs ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
                    {testResult.message}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button
                    className="h-7 flex-1 text-xs"
                    disabled={isTesting}
                    variant="secondary"
                    onClick={() => handleTest(c.connectorId)}
                  >
                    {isTesting ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-1 h-3 w-3" />
                    )}
                    Test
                  </Button>
                  <Button
                    className="h-7 flex-1 text-xs"
                    variant="secondary"
                    onClick={() => handleExpand(c.connectorId)}
                  >
                    <Wrench className="mr-1 h-3 w-3" />
                    {isExpanded ? "Hide" : "Tools"}
                  </Button>
                </div>

                {isExpanded && (
                  <div className="mt-2 rounded-md border border-white/10 bg-slate-900/40 p-2">
                    {isLoadingTools ? (
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <Loader2 className="h-3 w-3 animate-spin" /> Loading tools…
                      </div>
                    ) : connectorTools.length === 0 ? (
                      <p className="text-xs text-slate-500">No tools found.</p>
                    ) : (
                      <ul className="space-y-1.5">
                        {connectorTools.map((t) => (
                          <li key={t.toolId}>
                            <p className="font-mono text-xs font-medium text-slate-200">{t.toolId}</p>
                            <p className="text-xs text-slate-500">{t.description}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
