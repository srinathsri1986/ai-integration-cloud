"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { ConnectorDefinition, ConnectorTool } from "@ai-integration-cloud/shared";
import type { ApiResult } from "@/lib/api";
import { testConnector, getConnectorTools } from "@/lib/api";
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Link2Off,
  Loader2,
  RefreshCw,
  Settings2,
  Wrench,
  XCircle,
  Zap,
} from "lucide-react";

const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
    : "http://localhost:8000";

interface ConnectorCatalogProps {
  initialConnectors: ApiResult<ConnectorDefinition[]>;
}

// Per-connector category color mapping
const connectorColors: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  netsuite:   { bg: "bg-cyan-50",    text: "text-cyan-700",    border: "border-cyan-200",   dot: "bg-cyan-500"    },
  salesforce: { bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-200",   dot: "bg-blue-500"    },
  sap:        { bg: "bg-violet-50",  text: "text-violet-700",  border: "border-violet-200", dot: "bg-violet-500"  },
  oracle:     { bg: "bg-orange-50",  text: "text-orange-700",  border: "border-orange-200", dot: "bg-orange-500"  },
  hcm:        { bg: "bg-green-50",   text: "text-green-700",   border: "border-green-200",  dot: "bg-green-500"   },
  postgres:   { bg: "bg-indigo-50",  text: "text-indigo-700",  border: "border-indigo-200", dot: "bg-indigo-500"  },
  "rest-api": { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",  dot: "bg-amber-500"   },
  slack:      { bg: "bg-rose-50",    text: "text-rose-700",    border: "border-rose-200",   dot: "bg-rose-500"    },
};

const defaultColor = { bg: "bg-slate-50", text: "text-slate-700", border: "border-slate-200", dot: "bg-slate-400" };

function getColor(connectorId: string) {
  return connectorColors[connectorId] ?? defaultColor;
}

function connectorInitials(name: string) {
  return name
    .split(/[\s/]+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

function StatusBadge({ status, mode }: { status: string; mode: string }) {
  if (mode === "live" || status === "test_passed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Live
      </span>
    );
  }
  if (status === "test_failed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-inset ring-rose-200">
        <XCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
      Mock
    </span>
  );
}

function AuthBadge({ scheme }: { scheme: string }) {
  const map: Record<string, string> = {
    oauth2:      "bg-teal-50 text-teal-700 ring-teal-200",
    api_key:     "bg-violet-50 text-violet-700 ring-violet-200",
    basic:       "bg-amber-50 text-amber-700 ring-amber-200",
    token_based: "bg-indigo-50 text-indigo-700 ring-indigo-200",
    none:        "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${map[scheme] ?? map.none}`}>
      {scheme}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Config modal — REST API (base_url + api_key) and PostgreSQL (connection_string)
// ---------------------------------------------------------------------------

interface ConfigModalProps {
  connectorId: string;
  authScheme: string;
  onClose: () => void;
  onSuccess: (connectorId: string) => void;
}

function ConfigModal({ connectorId, authScheme, onClose, onSuccess }: ConfigModalProps) {
  const [baseUrl, setBaseUrl]           = useState("");
  const [apiKey, setApiKey]             = useState("");
  const [connStr, setConnStr]           = useState("");
  const [saving, setSaving]             = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const isRestApi = connectorId === "rest-api";
  const isPostgres = connectorId === "postgres";

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      let endpoint = "";
      let body: Record<string, string> = {};

      if (isRestApi) {
        endpoint = `${API_BASE}/api/v1/connectors/rest-api/live-config`;
        body = { base_url: baseUrl, api_key: apiKey };
      } else if (isPostgres) {
        endpoint = `${API_BASE}/api/v1/connectors/postgres/live-config`;
        body = { connection_string: connStr };
      }

      const resp = await fetch(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${_getToken()}` },
        body: JSON.stringify(body),
        credentials: "include",
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data?.detail ?? `HTTP ${resp.status}`);
      }

      onSuccess(connectorId);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Configure {isRestApi ? "REST API" : "PostgreSQL"} Connector
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          {isRestApi && (
            <>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Base URL <span className="text-rose-500">*</span>
                </label>
                <input
                  type="url"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.yourservice.com"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-100"
                />
                <p className="mt-1 text-[11px] text-slate-400">
                  Must start with https://. This is the root URL for all approved templates.
                </p>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                  API Key <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-••••••••••••••••"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-100"
                />
                <p className="mt-1 text-[11px] text-slate-400">
                  Encrypted at rest. Sent as <code className="font-mono">Authorization: Bearer …</code>
                </p>
              </div>
            </>
          )}

          {isPostgres && (
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                Connection String <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                value={connStr}
                onChange={(e) => setConnStr(e.target.value)}
                placeholder="postgresql://user:password@host:5432/dbname"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-900 placeholder-slate-400 focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-100"
              />
              <p className="mt-1 text-[11px] text-slate-400">
                Encrypted at rest. Only pre-approved parameterised query templates are executed — no raw SQL.
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              {error}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-teal-700 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Save & Activate
          </button>
        </div>
      </div>
    </div>
  );
}

function _getToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("auth_token") ?? "";
}

// ---------------------------------------------------------------------------
// Main catalog component
// ---------------------------------------------------------------------------

export function ConnectorCatalog({ initialConnectors }: ConnectorCatalogProps) {
  const searchParams = useSearchParams();
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>(initialConnectors.data);
  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; message: string; mode?: string } | null>
  >({});
  const [testingId, setTestingId]           = useState<string | null>(null);
  const [expandedId, setExpandedId]         = useState<string | null>(null);
  const [tools, setTools]                   = useState<Record<string, ConnectorTool[]>>({});
  const [loadingTools, setLoadingTools]     = useState<string | null>(null);
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const [banner, setBanner]                 = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [configModal, setConfigModal]       = useState<{ connectorId: string; authScheme: string } | null>(null);

  useEffect(() => {
    // Handle OAuth2 callback redirects from multiple connectors
    const slackConnected   = searchParams.get("slack_connected");
    const slackWorkspace   = searchParams.get("workspace");
    const slackError       = searchParams.get("slack_error");
    const sfConnected      = searchParams.get("salesforce_connected");
    const sfInstanceUrl    = searchParams.get("instance_url");
    const sfError          = searchParams.get("salesforce_error");

    if (slackConnected === "1") {
      setBanner({
        type: "success",
        message: `Slack connected${slackWorkspace ? ` to workspace "${slackWorkspace}"` : ""}. Connector is now live.`,
      });
      _setLive("slack");
    } else if (slackError) {
      setBanner({ type: "error", message: `Slack OAuth error: ${slackError}` });
    }

    if (sfConnected === "1") {
      setBanner({
        type: "success",
        message: `Salesforce connected${sfInstanceUrl ? ` to ${sfInstanceUrl}` : ""}. Connector is now live.`,
      });
      _setLive("salesforce");
    } else if (sfError) {
      setBanner({ type: "error", message: `Salesforce OAuth error: ${sfError}` });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function _setLive(connectorId: string) {
    setConnectors((prev) =>
      prev.map((c) =>
        c.connectorId === connectorId ? { ...c, mode: "live" as const, status: "configured" } : c
      )
    );
  }

  async function handleTest(connectorId: string) {
    setTestingId(connectorId);
    const result = await testConnector(connectorId);
    setTestResults((prev) => ({ ...prev, [connectorId]: result.data }));
    setTestingId(null);
  }

  async function handleExpand(connectorId: string) {
    if (expandedId === connectorId) { setExpandedId(null); return; }
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

  async function handleDisconnect(connectorId: string, authScheme: string) {
    setDisconnectingId(connectorId);
    try {
      // OAuth2 connectors → /oauth/disconnect  |  form connectors → /live-config/disconnect
      const path = authScheme === "oauth2"
        ? `/api/v1/connectors/${connectorId}/oauth/disconnect`
        : `/api/v1/connectors/${connectorId}/live-config/disconnect`;

      const resp = await fetch(`${API_BASE}${path}`, {
        method: "DELETE",
        credentials: "include",
        headers: { Authorization: `Bearer ${_getToken()}` },
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
        setBanner({ type: "success", message: `${connectorId} disconnected and reset to mock mode.` });
      }
    } catch {
      setBanner({ type: "error", message: `Failed to disconnect ${connectorId}.` });
    }
    setDisconnectingId(null);
  }

  function handleConfigSaved(connectorId: string) {
    _setLive(connectorId);
    setBanner({ type: "success", message: `${connectorId} connector activated in live mode.` });
  }

  return (
    <section>
      {/* Config modal */}
      {configModal && (
        <ConfigModal
          connectorId={configModal.connectorId}
          authScheme={configModal.authScheme}
          onClose={() => setConfigModal(null)}
          onSuccess={handleConfigSaved}
        />
      )}

      {/* Banner */}
      {banner && (
        <div
          className={`mb-6 flex items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm ${
            banner.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {banner.type === "success"
              ? <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              : <XCircle className="h-4 w-4 text-rose-600 shrink-0" />}
            <span>{banner.message}</span>
          </div>
          <button
            type="button"
            className="shrink-0 text-xs font-medium opacity-70 hover:opacity-100 underline"
            onClick={() => setBanner(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {connectors.map((c) => {
          const testResult      = testResults[c.connectorId];
          const isTesting       = testingId === c.connectorId;
          const isExpanded      = expandedId === c.connectorId;
          const connectorTools  = tools[c.connectorId] ?? [];
          const isLoadingTools  = loadingTools === c.connectorId;
          const isLive          = c.mode === "live";
          const isDisconnecting = disconnectingId === c.connectorId;
          const supportsOAuth   = c.authScheme === "oauth2";
          const supportsForm    = c.authScheme === "api_key" || c.authScheme === "basic";
          const color           = getColor(c.connectorId);

          return (
            <div
              key={c.connectorId}
              className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-card overflow-hidden"
            >
              {/* Colored top bar */}
              <div className={`h-1 w-full ${color.dot}`} />

              {/* Header */}
              <div className="p-4 pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${color.bg} ${color.text}`}>
                      {connectorInitials(c.name)}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{c.name}</p>
                      <p className="font-mono text-[11px] text-slate-400">{c.connectorId}</p>
                    </div>
                  </div>
                  <StatusBadge status={c.status} mode={c.mode ?? "mock"} />
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <AuthBadge scheme={c.authScheme} />
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                    {c.toolCount} {c.toolCount === 1 ? "tool" : "tools"}
                  </span>
                </div>
              </div>

              {/* Test result */}
              {testResult && (
                <div className={`mx-4 mb-3 rounded-lg px-3 py-2 text-xs ${
                  testResult.ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                }`}>
                  {testResult.mode && (
                    <span className="mr-1.5 rounded bg-white/60 px-1 py-0.5 font-mono text-[10px]">
                      {testResult.mode}
                    </span>
                  )}
                  {testResult.message}
                </div>
              )}

              {/* Actions */}
              <div className="mt-auto space-y-2 p-4 pt-0">
                {/* OAuth2 connectors (Slack, Salesforce) */}
                {supportsOAuth && (
                  isLive ? (
                    <button
                      type="button"
                      disabled={isDisconnecting}
                      onClick={() => handleDisconnect(c.connectorId, c.authScheme)}
                      className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-50"
                    >
                      {isDisconnecting
                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        : <Link2Off className="h-3.5 w-3.5" />}
                      Disconnect
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleConnect(c.connectorId)}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white shadow-sm shadow-teal-900/20 transition-colors hover:bg-teal-700"
                    >
                      <Zap className="h-3.5 w-3.5" />
                      Connect
                      <ExternalLink className="h-3 w-3 opacity-60" />
                    </button>
                  )
                )}

                {/* Form-based connectors (REST API, PostgreSQL) */}
                {supportsForm && (
                  isLive ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setConfigModal({ connectorId: c.connectorId, authScheme: c.authScheme })}
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-xs font-medium text-teal-700 transition-colors hover:border-teal-300 hover:bg-teal-100"
                      >
                        <Settings2 className="h-3.5 w-3.5" />
                        Edit Config
                      </button>
                      <button
                        type="button"
                        disabled={isDisconnecting}
                        onClick={() => handleDisconnect(c.connectorId, c.authScheme)}
                        className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-50"
                      >
                        {isDisconnecting
                          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          : <Link2Off className="h-3.5 w-3.5" />}
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfigModal({ connectorId: c.connectorId, authScheme: c.authScheme })}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white shadow-sm shadow-teal-900/20 transition-colors hover:bg-teal-700"
                    >
                      <Settings2 className="h-3.5 w-3.5" />
                      Configure
                    </button>
                  )
                )}

                {/* Test + Tools */}
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={isTesting}
                    onClick={() => handleTest(c.connectorId)}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50"
                  >
                    {isTesting
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <RefreshCw className="h-3.5 w-3.5" />}
                    Test
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExpand(c.connectorId)}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <Wrench className="h-3.5 w-3.5" />
                    {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    Tools
                  </button>
                </div>

                {/* Tool list */}
                {isExpanded && (
                  <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    {isLoadingTools ? (
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading tools…
                      </div>
                    ) : connectorTools.length === 0 ? (
                      <p className="text-xs text-slate-400">No tools found.</p>
                    ) : (
                      <ul className="space-y-2">
                        {connectorTools.map((t) => (
                          <li key={t.toolId} className="flex items-start gap-2">
                            <span className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${color.dot}`} />
                            <div>
                              <p className="font-mono text-[11px] font-semibold text-slate-700">{t.toolId}</p>
                              <p className="text-[11px] leading-4 text-slate-400">{t.description}</p>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
