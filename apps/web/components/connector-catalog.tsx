"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { ConnectorDefinition, ConnectorTool } from "@ai-integration-cloud/shared";
import type { ApiResult } from "@/lib/api";
import { testConnector, getConnectorTools } from "@/lib/api";
import { CheckCircle2, ExternalLink, Link2Off, Loader2, RefreshCw, Wrench, XCircle, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
    : "http://localhost:8000";

interface ConnectorCatalogProps {
  initialConnectors: ApiResult<ConnectorDefinition[]>;
}

function statusBadge(status: string, mode: string) {
  if (mode === "live" || status === "test_passed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
        <CheckCircle2 className="h-3 w-3" />
        Live
      </span>
    );
  }
  if (status === "test_failed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-400">
        <XCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-500/10 px-2 py-0.5 text-xs font-medium text-slate-400">
      Mock
    </span>
  );
}

function authSchemeBadge(scheme: string) {
  const colors: Record<string, string> = {
    oauth2:      "bg-sky-500/10 text-sky-400",
    api_key:     "bg-violet-500/10 text-violet-400",
    basic:       "bg-amber-500/10 text-amber-400",
    token_based: "bg-indigo-500/10 text-indigo-400",
    none:        "bg-slate-500/10 text-slate-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[scheme] ?? colors.none}`}>
      {scheme}
    </span>
  );
}

export function ConnectorCatalog({ initialConnectors }: ConnectorCatalogProps) {
  const searchParams = useSearchParams();
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>(initialConnectors.data);
  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; message: string; mode?: string } | null>
  >({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [tools, setTools] = useState<Record<string, ConnectorTool[]>>({});
  const [loadingTools, setLoadingTools] = useState<string | null>(null);
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Show banner if redirected back from OAuth callback
  useEffect(() => {
    const connected = searchParams.get("slack_connected");
    const workspace = searchParams.get("workspace");
    const slackError = searchParams.get("slack_error");
    if (connected === "1") {
      setBanner({
        type: "success",
        message: `Slack connected${workspace ? ` to workspace "${workspace}"` : ""}. Connector is now live.`,
      });
      setConnectors((prev) =>
        prev.map((c) =>
          c.connectorId === "slack" ? { ...c, mode: "live" as const, status: "configured" } : c
        )
      );
    } else if (slackError) {
      setBanner({ type: "error", message: `Slack OAuth error: ${slackError}` });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  function handleConnect(connectorId: string) {
    window.location.href = `${API_BASE}/api/v1/connectors/${connectorId}/oauth/authorize`;
  }

  async function handleDisconnect(connectorId: string) {
    setDisconnectingId(connectorId);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/connectors/${connectorId}/oauth/disconnect`, {
        method: "DELETE",
        credentials: "include",
      });
      if (resp.ok) {
        setConnectors((prev) =>
          prev.map((c) =>
            c.connectorId === connectorId
              ? { ...c, mode: "mock" as const, status: "not_configured" }
              : c
          )
        );
        setTestResults((prev) => ({ ...prev, [connectorId]: null }));
        setBanner({
          type: "success",
          message: `${connectorId} disconnected and reset to mock mode.`,
        });
      }
    } catch {
      setBanner({ type: "error", message: `Failed to disconnect ${connectorId}.` });
    }
    setDisconnectingId(null);
  }

  return (
    <section>
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Registered Connectors
      </h2>

      {banner && (
        <div
          className={`mb-4 flex items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
            banner.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          <span>{banner.message}</span>
          <button
            type="button"
            className="shrink-0 text-xs underline opacity-70 hover:opacity-100"
            onClick={() => setBanner(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {connectors.map((c) => {
          const testResult = testResults[c.connectorId];
          const isTesting = testingId === c.connectorId;
          const isExpanded = expandedId === c.connectorId;
          const connectorTools = tools[c.connectorId] ?? [];
          const isLoadingTools = loadingTools === c.connectorId;
          const isLive = c.mode === "live";
          const isDisconnecting = disconnectingId === c.connectorId;
          const supportsOAuth = c.authScheme === "oauth2";

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
                  {statusBadge(c.status, c.mode ?? "mock")}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {authSchemeBadge(c.authScheme)}
                  <span className="rounded-full bg-slate-700/60 px-2 py-0.5 text-xs text-slate-400">
                    {c.toolCount} tool{c.toolCount !== 1 ? "s" : ""}
                  </span>
                </div>
              </CardHeader>

              <div className="space-y-2 px-4 pb-4">
                {testResult && (
                  <p className={`text-xs ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
                    {testResult.mode && (
                      <span className="mr-1 rounded bg-slate-700 px-1 py-0.5 font-mono text-[10px] text-slate-300">
                        {testResult.mode}
                      </span>
                    )}
                    {testResult.message}
                  </p>
                )}

                {/* OAuth Connect / Disconnect for oauth2 connectors */}
                {supportsOAuth &&
                  (isLive ? (
                    <Button
                      className="h-7 w-full text-xs"
                      variant="secondary"
                      disabled={isDisconnecting}
                      onClick={() => handleDisconnect(c.connectorId)}
                    >
                      {isDisconnecting ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : (
                        <Link2Off className="mr-1 h-3 w-3" />
                      )}
                      Disconnect
                    </Button>
                  ) : (
                    <Button
                      className="h-7 w-full text-xs"
                      onClick={() => handleConnect(c.connectorId)}
                    >
                      <Zap className="mr-1 h-3 w-3" />
                      Connect
                      <ExternalLink className="ml-1 h-3 w-3 opacity-60" />
                    </Button>
                  ))}

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
