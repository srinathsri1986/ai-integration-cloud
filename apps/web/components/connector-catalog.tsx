"use client";

import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { ConnectorDefinition, ConnectorTool } from "@ai-integration-cloud/shared";
import type { ApiResult, ConnectorSchema } from "@/lib/api";
import { LOCAL_AUTH_TOKEN_KEY, testConnector, getConnectorTools, getConnectorSchema, getConnectors } from "@/lib/api";
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
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
// Schema Viewer — renders objects + fields fetched from GET /connectors/{id}/schema
// ---------------------------------------------------------------------------

function SchemaViewer({ schema }: { schema: ConnectorSchema }) {
  const [openObject, setOpenObject] = useState<string | null>(
    schema.objects.length === 1 ? schema.objects[0]?.objectId ?? null : null,
  );

  const typeColor = (t: string) => {
    if (t === "string")  return "bg-sky-100 text-sky-700";
    if (t === "number")  return "bg-amber-100 text-amber-700";
    if (t === "boolean") return "bg-violet-100 text-violet-700";
    if (t === "date" || t === "datetime") return "bg-teal-100 text-teal-700";
    if (t === "id")      return "bg-rose-100 text-rose-700";
    return "bg-slate-100 text-slate-500";
  };

  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      {/* Schema header */}
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          {schema.objects.length} {schema.objects.length === 1 ? "object" : "objects"}
        </span>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
            schema.mode === "live"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-slate-200 text-slate-500"
          }`}
        >
          {schema.mode}
        </span>
      </div>

      {schema.objects.length === 0 ? (
        <p className="text-[11px] text-slate-400">No schema objects available.</p>
      ) : (
        <div className="space-y-1">
          {schema.objects.map((obj) => {
            const isOpen = openObject === obj.objectId;
            return (
              <div key={obj.objectId} className="overflow-hidden rounded-md border border-slate-100 bg-white">
                <button
                  type="button"
                  onClick={() => setOpenObject(isOpen ? null : obj.objectId)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-slate-50"
                >
                  <div className="flex items-center gap-2">
                    <Database className="h-3 w-3 text-slate-400 shrink-0" />
                    <span className="text-[11px] font-semibold text-slate-800">{obj.label}</span>
                    <span className="font-mono text-[10px] text-slate-400">{obj.objectId}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400">{obj.fields.length} fields</span>
                    {isOpen
                      ? <ChevronUp className="h-3 w-3 text-slate-400" />
                      : <ChevronDown className="h-3 w-3 text-slate-400" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-100 px-3 py-2">
                    <table className="w-full text-left">
                      <thead>
                        <tr>
                          <th className="pb-1.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">Field</th>
                          <th className="pb-1.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">Type</th>
                          <th className="pb-1.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">Sample</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {obj.fields.map((f) => (
                          <tr key={f.name} className="group">
                            <td className="py-1 pr-2">
                              <div className="flex items-center gap-1">
                                <span className="font-mono text-[10px] font-medium text-slate-700">{f.name}</span>
                                {f.required && (
                                  <span className="rounded bg-rose-50 px-0.5 text-[8px] font-bold text-rose-500">req</span>
                                )}
                              </div>
                              {f.label !== f.name && (
                                <p className="text-[10px] text-slate-400">{f.label}</p>
                              )}
                            </td>
                            <td className="py-1 pr-2">
                              <span className={`rounded px-1.5 py-0.5 text-[9px] font-medium ${typeColor(f.type)}`}>
                                {f.type}
                              </span>
                            </td>
                            <td className="py-1 max-w-[90px]">
                              {f.sample ? (
                                <span className="truncate font-mono text-[10px] text-slate-400" title={f.sample}>
                                  {f.sample}
                                </span>
                              ) : (
                                <span className="text-[10px] text-slate-300">—</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function _getToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(LOCAL_AUTH_TOKEN_KEY) ?? "";
}

function Field({
  label, hint, required = false, children,
}: { label: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold text-slate-700">
        {label} {required && <span className="text-rose-500">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-[11px] text-slate-400">{hint}</p>}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-100";

// ---------------------------------------------------------------------------
// Credential modal — full forms for every connector type
// ---------------------------------------------------------------------------

interface ConfigModalProps {
  connectorId: string;
  connectorName: string;
  authScheme: string;
  onClose: () => void;
  onSuccess: (connectorId: string) => void;
}

function ConfigModal({ connectorId, connectorName, authScheme, onClose, onSuccess }: ConfigModalProps) {
  // ── OAuth2 App setup (Salesforce, Slack) ──────────────────────────────────
  const [oauthClientId,     setOauthClientId]     = useState("");
  const [oauthClientSecret, setOauthClientSecret] = useState("");
  const [loginUrl,          setLoginUrl]          = useState("https://login.salesforce.com");
  // Whether the OAuth app creds have been saved (step 1 done → show Authorize button)
  const [oauthAppSaved,     setOauthAppSaved]     = useState(false);

  // ── NetSuite ──────────────────────────────────────────────────────────────
  const [nsAccountId,      setNsAccountId]      = useState("");
  const [nsConsumerKey,    setNsConsumerKey]     = useState("");
  const [nsConsumerSecret, setNsConsumerSecret] = useState("");
  const [nsTokenId,        setNsTokenId]        = useState("");
  const [nsTokenSecret,    setNsTokenSecret]    = useState("");

  // ── SAP ───────────────────────────────────────────────────────────────────
  // Two connection modes mirror the live connector's two auth schemes:
  //   "production" → Basic Auth + sap-client (real S/4HANA Cloud / on-prem Gateway)
  //   "sandbox"    → APIKey header (free SAP Business Accelerator Hub Sandbox —
  //                  self-service key from api.sap.com, no real SAP system needed)
  const [sapMode,         setSapMode]         = useState<"production" | "sandbox">("production");
  const [sapHost,         setSapHost]         = useState("");
  const [sapClient,       setSapClient]       = useState("100");
  const [sapUsername,     setSapUsername]     = useState("");
  const [sapPassword,     setSapPassword]     = useState("");
  const [sapSystemNumber, setSapSystemNumber] = useState("00");
  const [sapApiKey,       setSapApiKey]       = useState("");
  const [sapApiBasePath,  setSapApiBasePath]  = useState("s4hanacloud");

  // ── Oracle ────────────────────────────────────────────────────────────────
  const [oraHost,        setOraHost]        = useState("");
  const [oraPort,        setOraPort]        = useState("1521");
  const [oraService,     setOraService]     = useState("");
  const [oraUsername,    setOraUsername]    = useState("");
  const [oraPassword,    setOraPassword]    = useState("");

  // ── HCM (Workday) ─────────────────────────────────────────────────────────
  const [hcmTenantUrl,    setHcmTenantUrl]    = useState("");
  const [hcmClientId,     setHcmClientId]     = useState("");
  const [hcmClientSecret, setHcmClientSecret] = useState("");
  const [hcmUsername,     setHcmUsername]     = useState("");
  const [hcmPassword,     setHcmPassword]     = useState("");

  // ── REST API ──────────────────────────────────────────────────────────────
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey,  setApiKey]  = useState("");

  // ── PostgreSQL ────────────────────────────────────────────────────────────
  const [connStr, setConnStr] = useState("");

  // ── Shared state ─────────────────────────────────────────────────────────
  const [saving,     setSaving]     = useState(false);
  const [testing,    setTesting]    = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [error,      setError]      = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const isSalesforce = connectorId === "salesforce";
  const isSlack      = connectorId === "slack";
  const isOAuth2App  = isSalesforce || isSlack;   // two-step: save app creds → then OAuth
  const isNetSuite   = connectorId === "netsuite";
  const isSAP        = connectorId === "sap";
  const isOracle     = connectorId === "oracle";
  const isHCM        = connectorId === "hcm";
  const isRestApi    = connectorId === "rest-api";
  const isPostgres   = connectorId === "postgres";
  const hasForm      = isOAuth2App || isNetSuite || isSAP || isOracle || isHCM || isRestApi || isPostgres;

  // ── Helpers ───────────────────────────────────────────────────────────────

  function require(val: string, label: string): boolean {
    if (!val.trim()) { setError(`${label} is required.`); return false; }
    return true;
  }

  async function apiCall(method: string, path: string, body?: Record<string, string>): Promise<void> {
    const resp = await fetch(`${API_BASE}/api/v1/connectors/${path}`, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${_getToken()}` },
      body: body ? JSON.stringify(body) : undefined,
      credentials: "include",
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data?.detail ?? `HTTP ${resp.status}`);
    }
  }

  async function handleTestInline() {
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/connectors/${connectorId}/test`, {
        method: "POST",
        credentials: "include",
        headers: { Authorization: `Bearer ${_getToken()}` },
      });
      const data = await resp.json().catch(() => ({}));
      setTestResult({ ok: data?.ok ?? resp.ok, message: data?.message ?? `HTTP ${resp.status}` });
    } catch (e: unknown) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : "Connection failed" });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      if (isOAuth2App) {
        if (!require(oauthClientId,     "Client ID"))     return;
        if (!require(oauthClientSecret, "Client Secret")) return;
        const extra: Record<string, string> = {
          client_id:     oauthClientId,
          client_secret: oauthClientSecret,
        };
        if (isSalesforce && loginUrl) extra.login_url = loginUrl;
        await apiCall("PUT", `${connectorId}/oauth-app-config`, extra);
        setOauthAppSaved(true);
        // Don't close — show the "Authorize" button now
        return;
      }

      if (isNetSuite) {
        if (!require(nsAccountId,      "Account ID"))      return;
        if (!require(nsConsumerKey,    "Consumer Key"))    return;
        if (!require(nsConsumerSecret, "Consumer Secret")) return;
        if (!require(nsTokenId,        "Token ID"))        return;
        if (!require(nsTokenSecret,    "Token Secret"))    return;
        await apiCall("PUT", "netsuite/live-config", {
          account_id:      nsAccountId,
          consumer_key:    nsConsumerKey,
          consumer_secret: nsConsumerSecret,
          token_id:        nsTokenId,
          token_secret:    nsTokenSecret,
        });
      } else if (isSAP) {
        if (!require(sapHost, "Host")) return;
        if (sapMode === "sandbox") {
          if (!require(sapApiKey, "API Key")) return;
          await apiCall("PUT", "sap/live-config", {
            host:           sapHost,
            api_key:        sapApiKey,
            api_base_path:  sapApiBasePath,
          });
        } else {
          if (!require(sapUsername, "Username")) return;
          if (!require(sapPassword, "Password")) return;
          await apiCall("PUT", "sap/live-config", {
            host:          sapHost,
            client:        sapClient,
            username:      sapUsername,
            password:      sapPassword,
            system_number: sapSystemNumber,
          });
        }
      } else if (isOracle) {
        if (!require(oraHost,     "Host"))         return;
        if (!require(oraService,  "Service Name")) return;
        if (!require(oraUsername, "Username"))     return;
        if (!require(oraPassword, "Password"))     return;
        await apiCall("PUT", "oracle/live-config", {
          host:         oraHost,
          port:         oraPort,
          service_name: oraService,
          username:     oraUsername,
          password:     oraPassword,
        });
      } else if (isHCM) {
        if (!require(hcmTenantUrl,    "Tenant URL"))    return;
        if (!require(hcmClientId,     "Client ID"))     return;
        if (!require(hcmClientSecret, "Client Secret")) return;
        await apiCall("PUT", "hcm/live-config", {
          tenant_url:    hcmTenantUrl,
          client_id:     hcmClientId,
          client_secret: hcmClientSecret,
          username:      hcmUsername,
          password:      hcmPassword,
        });
      } else if (isRestApi) {
        if (!require(baseUrl, "Base URL")) return;
        if (!require(apiKey,  "API Key"))  return;
        await apiCall("PUT", "rest-api/live-config", { base_url: baseUrl, api_key: apiKey });
      } else if (isPostgres) {
        if (!require(connStr, "Connection String")) return;
        await apiCall("PUT", "postgres/live-config", { connection_string: connStr });
      }

      onSuccess(connectorId);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  function handleOAuthRedirect() {
    window.location.href = `${API_BASE}/api/v1/connectors/${connectorId}/oauth/authorize`;
  }

  // ── Subtitle text ─────────────────────────────────────────────────────────
  const subtitle = isOAuth2App
    ? `Step 1 — enter your ${connectorName} Connected App credentials. Step 2 — click Authorize to complete OAuth.`
    : isNetSuite
    ? "Token-based OAuth credentials from your NetSuite integration record."
    : isSAP
    ? "Connect a production SAP system (Basic Auth) or the free SAP Sandbox (API key)."
    : isOracle
    ? "Oracle DB connection details — host, service name, and credentials."
    : isHCM
    ? "Workday HCM tenant URL and OAuth client credentials."
    : isRestApi
    ? "Base URL and API key — encrypted at rest."
    : isPostgres
    ? "PostgreSQL connection string — encrypted at rest."
    : "Configure this connector.";

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Configure {connectorName}</h2>
            <p className="mt-0.5 text-[11px] text-slate-400">{subtitle}</p>
          </div>
          <button type="button" onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
            <XCircle className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[65vh] overflow-y-auto px-6 py-5 space-y-4">

          {/* ── OAuth2 App (Salesforce / Slack) ── */}
          {isOAuth2App && !oauthAppSaved && (
            <>
              {isSalesforce && (
                <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2.5 text-xs text-sky-800">
                  <p className="font-semibold">Create a Connected App first</p>
                  <p className="mt-0.5">In Salesforce: Setup → App Manager → New Connected App.<br />
                  Set callback URL to: <code className="font-mono">{API_BASE}/api/v1/connectors/salesforce/oauth/callback</code><br />
                  Scopes: <code className="font-mono">api, refresh_token, offline_access</code></p>
                </div>
              )}
              {isSlack && (
                <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2.5 text-xs text-sky-800">
                  <p className="font-semibold">Create a Slack App first</p>
                  <p className="mt-0.5">Go to <strong>api.slack.com/apps</strong> → Create New App → From scratch.<br />
                  Add redirect URI: <code className="font-mono">{API_BASE}/api/v1/connectors/slack/oauth/callback</code><br />
                  Bot token scopes: <code className="font-mono">chat:write, channels:read, channels:join</code></p>
                </div>
              )}
              <Field label="Client ID" required>
                <input type="text" value={oauthClientId} onChange={e => setOauthClientId(e.target.value)}
                  placeholder={isSalesforce ? "3MVG9..." : "1234567890.apps.abc123"}
                  className={inputCls} autoComplete="off" />
              </Field>
              <Field label="Client Secret" required>
                <input type="password" value={oauthClientSecret} onChange={e => setOauthClientSecret(e.target.value)}
                  placeholder="••••••••••••••••••••"
                  className={inputCls} autoComplete="new-password" />
              </Field>
              {isSalesforce && (
                <Field
                  label="Login URL"
                  hint="If your org blocks login.salesforce.com (Setup → My Domain → Login Policy), choose Custom and enter your My Domain URL, e.g. https://yourcompany-dev-ed.develop.my.salesforce.com"
                >
                  <select
                    value={["https://login.salesforce.com", "https://test.salesforce.com"].includes(loginUrl) ? loginUrl : "custom"}
                    onChange={e => {
                      if (e.target.value === "custom") setLoginUrl("");
                      else setLoginUrl(e.target.value);
                    }}
                    className={inputCls}
                  >
                    <option value="https://login.salesforce.com">Production (login.salesforce.com)</option>
                    <option value="https://test.salesforce.com">Sandbox (test.salesforce.com)</option>
                    <option value="custom">Custom — My Domain URL…</option>
                  </select>
                  {!["https://login.salesforce.com", "https://test.salesforce.com"].includes(loginUrl) && (
                    <input
                      type="text"
                      value={loginUrl}
                      onChange={e => setLoginUrl(e.target.value)}
                      placeholder="https://yourcompany-dev-ed.develop.my.salesforce.com"
                      className={`${inputCls} mt-2`}
                      autoComplete="off"
                    />
                  )}
                </Field>
              )}
            </>
          )}

          {/* After OAuth app creds saved — show Authorize CTA */}
          {isOAuth2App && oauthAppSaved && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-center">
              <CheckCircle2 className="mx-auto mb-2 h-6 w-6 text-emerald-500" />
              <p className="text-sm font-semibold text-emerald-800">App credentials saved</p>
              <p className="mt-1 text-xs text-emerald-700">
                Click below to open {connectorName}&apos;s login page and grant access.
                You&apos;ll be redirected back automatically.
              </p>
              <button type="button" onClick={handleOAuthRedirect}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-700">
                <Zap className="h-4 w-4" />
                Authorize with {connectorName}
                <ExternalLink className="h-3.5 w-3.5 opacity-70" />
              </button>
            </div>
          )}

          {/* ── NetSuite ── */}
          {isNetSuite && (
            <>
              <Field label="Account ID" required hint="e.g. TSTDRV1234567 or 1234567_SB1 for sandbox">
                <input type="text" value={nsAccountId} onChange={e => setNsAccountId(e.target.value)}
                  placeholder="TSTDRV1234567" className={inputCls} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Consumer Key" required>
                  <input type="password" value={nsConsumerKey} onChange={e => setNsConsumerKey(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
                <Field label="Consumer Secret" required>
                  <input type="password" value={nsConsumerSecret} onChange={e => setNsConsumerSecret(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Token ID" required>
                  <input type="password" value={nsTokenId} onChange={e => setNsTokenId(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
                <Field label="Token Secret" required>
                  <input type="password" value={nsTokenSecret} onChange={e => setNsTokenSecret(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-400">
                Find these in NetSuite: Setup → Integration → Manage Integrations → Token-Based Authentication.
              </div>
            </>
          )}

          {/* ── SAP ── */}
          {isSAP && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => setSapMode("production")}
                  className={`rounded-lg border px-3 py-2 text-left text-xs transition ${sapMode === "production" ? "border-teal-500 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-500 hover:border-slate-300"}`}>
                  <div className="font-medium">Production system</div>
                  <div className="mt-0.5 text-[11px] opacity-80">Basic Auth — your S/4HANA Cloud or on-prem Gateway</div>
                </button>
                <button type="button" onClick={() => setSapMode("sandbox")}
                  className={`rounded-lg border px-3 py-2 text-left text-xs transition ${sapMode === "sandbox" ? "border-teal-500 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-500 hover:border-slate-300"}`}>
                  <div className="font-medium">SAP Sandbox</div>
                  <div className="mt-0.5 text-[11px] opacity-80">API key — free Business Accelerator Hub Sandbox</div>
                </button>
              </div>

              {sapMode === "production" ? (
                <>
                  <Field label="Application Server Host" required hint="IP or hostname of your SAP application server">
                    <input type="text" value={sapHost} onChange={e => setSapHost(e.target.value)}
                      placeholder="192.168.1.100 or sapserver.company.com" className={inputCls} />
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="System Number" hint="Usually 00">
                      <input type="text" value={sapSystemNumber} onChange={e => setSapSystemNumber(e.target.value)}
                        placeholder="00" className={inputCls} />
                    </Field>
                    <Field label="Client" hint="Usually 100">
                      <input type="text" value={sapClient} onChange={e => setSapClient(e.target.value)}
                        placeholder="100" className={inputCls} />
                    </Field>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Username" required>
                      <input type="text" value={sapUsername} onChange={e => setSapUsername(e.target.value)}
                        placeholder="SAPUSER" className={inputCls} autoComplete="username" />
                    </Field>
                    <Field label="Password" required>
                      <input type="password" value={sapPassword} onChange={e => setSapPassword(e.target.value)}
                        placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                    </Field>
                  </div>
                </>
              ) : (
                <>
                  <Field label="Sandbox Host" required hint="The Business Accelerator Hub sandbox gateway">
                    <input type="text" value={sapHost} onChange={e => setSapHost(e.target.value)}
                      placeholder="sandbox.api.sap.com" className={inputCls} />
                  </Field>
                  <Field label="API Key" required hint="From api.sap.com → open an API → 'Show API Key' (free SAP Community signup, no real SAP system needed)">
                    <input type="password" value={sapApiKey} onChange={e => setSapApiKey(e.target.value)}
                      placeholder="••••••••••••••••" className={inputCls} autoComplete="new-password" />
                  </Field>
                  <Field label="API Base Path" hint="The sandbox proxy prefix shown in the API's endpoint URL, e.g. 's4hanacloud'">
                    <input type="text" value={sapApiBasePath} onChange={e => setSapApiBasePath(e.target.value)}
                      placeholder="s4hanacloud" className={inputCls} />
                  </Field>
                  <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-400">
                    Get a free key: api.sap.com → sign in with an SAP Community account → open any API
                    (e.g. API_BUSINESS_PARTNER) → "Show API Key". No real SAP system required.
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Oracle ── */}
          {isOracle && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <Field label="Host" required>
                    <input type="text" value={oraHost} onChange={e => setOraHost(e.target.value)}
                      placeholder="oracle.company.com" className={inputCls} />
                  </Field>
                </div>
                <Field label="Port" hint="Default 1521">
                  <input type="text" value={oraPort} onChange={e => setOraPort(e.target.value)}
                    placeholder="1521" className={inputCls} />
                </Field>
              </div>
              <Field label="Service Name" required hint="e.g. ORCL or XEPDB1">
                <input type="text" value={oraService} onChange={e => setOraService(e.target.value)}
                  placeholder="ORCL" className={inputCls} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Username" required>
                  <input type="text" value={oraUsername} onChange={e => setOraUsername(e.target.value)}
                    placeholder="system" className={inputCls} autoComplete="username" />
                </Field>
                <Field label="Password" required>
                  <input type="password" value={oraPassword} onChange={e => setOraPassword(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
              </div>
            </>
          )}

          {/* ── HCM (Workday) ── */}
          {isHCM && (
            <>
              <Field label="Tenant URL" required hint="Your Workday tenant base URL">
                <input type="url" value={hcmTenantUrl} onChange={e => setHcmTenantUrl(e.target.value)}
                  placeholder="https://wd2.myworkday.com/yourcompany"
                  className={inputCls} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Client ID" required hint="ISU / API client">
                  <input type="text" value={hcmClientId} onChange={e => setHcmClientId(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="off" />
                </Field>
                <Field label="Client Secret" required>
                  <input type="password" value={hcmClientSecret} onChange={e => setHcmClientSecret(e.target.value)}
                    placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                </Field>
              </div>
              <details className="text-xs text-slate-400">
                <summary className="cursor-pointer hover:text-slate-600">Basic auth fallback (optional)</summary>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <Field label="Username">
                    <input type="text" value={hcmUsername} onChange={e => setHcmUsername(e.target.value)}
                      placeholder="svc_account@tenant" className={inputCls} autoComplete="username" />
                  </Field>
                  <Field label="Password">
                    <input type="password" value={hcmPassword} onChange={e => setHcmPassword(e.target.value)}
                      placeholder="••••••••" className={inputCls} autoComplete="new-password" />
                  </Field>
                </div>
              </details>
            </>
          )}

          {/* ── REST API ── */}
          {isRestApi && (
            <>
              <Field label="Base URL" required hint="Root URL — must start with https://.">
                <input type="url" value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                  placeholder="https://api.yourservice.com" className={inputCls} />
              </Field>
              <Field label="API Key" required hint="Sent as Authorization: Bearer …">
                <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
                  placeholder="sk-••••••••••••••••" className={inputCls} autoComplete="new-password" />
              </Field>
            </>
          )}

          {/* ── PostgreSQL ── */}
          {isPostgres && (
            <Field label="Connection String" required
              hint="Encrypted at rest. Only pre-approved query templates are executed — no raw SQL.">
              <input type="password" value={connStr} onChange={e => setConnStr(e.target.value)}
                placeholder="postgresql://user:password@host:5432/dbname"
                className={`${inputCls} font-mono`} autoComplete="new-password" />
            </Field>
          )}

          {/* Feedback */}
          {testResult && (
            <div className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
              testResult.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                            : "border-rose-200 bg-rose-50 text-rose-800"}`}>
              {testResult.ok
                ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-600" />}
              <span>{testResult.message}</span>
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 border-t border-slate-100 px-6 py-4">
          <button type="button" disabled={testing} onClick={handleTestInline}
            title="Saves your credentials first, then tests the connection against the saved state."
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50">
            {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Test Saved Credentials
          </button>

          <div className="flex gap-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50">
              Cancel
            </button>
            {/* Show Save button for all non-OAuth2-app connectors, or step 1 of OAuth2 */}
            {hasForm && !(isOAuth2App && oauthAppSaved) && (
              <button type="button" disabled={saving} onClick={handleSave}
                className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-teal-700 disabled:opacity-50">
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {isOAuth2App ? "Save & Continue" : "Save & Activate"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main catalog component
// ---------------------------------------------------------------------------

type PanelView = "tools" | "schema";

export function ConnectorCatalog({ initialConnectors }: ConnectorCatalogProps) {
  const searchParams = useSearchParams();

  const [connectors, setConnectors] = useState<ConnectorDefinition[]>(initialConnectors.data);
  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; message: string; mode?: string } | null>
  >({});
  const [testingId, setTestingId]             = useState<string | null>(null);

  // Expanded drawer state: which connector is open + which view (tools | schema)
  const [expandedId, setExpandedId]           = useState<string | null>(null);
  const [panelView, setPanelView]             = useState<Record<string, PanelView>>({});

  // Tools cache
  const [tools, setTools]                     = useState<Record<string, ConnectorTool[]>>({});
  const [loadingTools, setLoadingTools]       = useState<string | null>(null);

  // Schema cache
  const [schemas, setSchemas]                 = useState<Record<string, ConnectorSchema>>({});
  const [loadingSchema, setLoadingSchema]     = useState<string | null>(null);

  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const [banner, setBanner]                   = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [configModal, setConfigModal]         = useState<{
    connectorId: string;
    connectorName: string;
    authScheme: string;
  } | null>(null);

  // -------------------------------------------------------------------------
  // OAuth2 redirect handling
  // -------------------------------------------------------------------------

  useEffect(() => {
    const slackConnected = searchParams.get("slack_connected");
    const slackWorkspace = searchParams.get("workspace");
    const slackError     = searchParams.get("slack_error");
    const sfConnected    = searchParams.get("salesforce_connected");
    const sfInstanceUrl  = searchParams.get("instance_url");
    const sfError        = searchParams.get("salesforce_error");

    if (slackConnected === "1") {
      setBanner({
        type: "success",
        message: `Slack connected${slackWorkspace ? ` to workspace "${slackWorkspace}"` : ""}. Connector is now live.`,
      });
      _setLive("slack");
      void _fetchSchema("slack");
    } else if (slackError) {
      setBanner({ type: "error", message: `Slack OAuth error: ${slackError}` });
    }

    if (sfConnected === "1") {
      setBanner({
        type: "success",
        message: `Salesforce connected${sfInstanceUrl ? ` to ${sfInstanceUrl}` : ""}. Connector is now live.`,
      });
      _setLive("salesforce");
      void _fetchSchema("salesforce");
    } else if (sfError) {
      setBanner({ type: "error", message: `Salesforce OAuth error: ${sfError}` });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Client-side refresh: SSR fetches connectors without auth (no cookie available
  // server-side), so badges always start as "mock". After hydration we re-fetch
  // with the user's auth token so live connectors show the correct Live badge.
  useEffect(() => {
    async function refreshConnectorModes() {
      const result = await getConnectors();
      if (result.data && result.data.length > 0) {
        setConnectors(result.data);
      }
    }
    void refreshConnectorModes();
  }, []);

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  function _setLive(connectorId: string) {
    setConnectors((prev) =>
      prev.map((c) =>
        c.connectorId === connectorId ? { ...c, mode: "live" as const, status: "configured" } : c,
      ),
    );
  }

  async function _fetchSchema(connectorId: string) {
    if (schemas[connectorId]) return; // already cached
    setLoadingSchema(connectorId);
    const result = await getConnectorSchema(connectorId);
    setSchemas((prev) => ({ ...prev, [connectorId]: result.data }));
    setLoadingSchema(null);
  }

  // -------------------------------------------------------------------------
  // Card actions
  // -------------------------------------------------------------------------

  async function handleTest(connectorId: string) {
    setTestingId(connectorId);
    const result = await testConnector(connectorId);
    setTestResults((prev) => ({ ...prev, [connectorId]: result.data }));
    setTestingId(null);
  }

  function openPanel(connectorId: string, view: PanelView) {
    const alreadyOpen = expandedId === connectorId && panelView[connectorId] === view;
    if (alreadyOpen) {
      setExpandedId(null);
      return;
    }
    setExpandedId(connectorId);
    setPanelView((prev) => ({ ...prev, [connectorId]: view }));
  }

  async function handleExpandTools(connectorId: string) {
    openPanel(connectorId, "tools");
    if (!tools[connectorId]) {
      setLoadingTools(connectorId);
      const result = await getConnectorTools(connectorId);
      setTools((prev) => ({ ...prev, [connectorId]: result.data }));
      setLoadingTools(null);
    }
  }

  async function handleExpandSchema(connectorId: string) {
    openPanel(connectorId, "schema");
    await _fetchSchema(connectorId);
  }

  function handleConnect(connectorId: string) {
    window.location.href = `${API_BASE}/api/v1/connectors/${connectorId}/oauth/authorize`;
  }

  async function handleDisconnect(connectorId: string, authScheme: string) {
    setDisconnectingId(connectorId);
    try {
      const path =
        authScheme === "oauth2"
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
              : c,
          ),
        );
        setTestResults((prev) => ({ ...prev, [connectorId]: null }));
        // Clear cached schema so it re-fetches in mock mode
        setSchemas((prev) => { const next = { ...prev }; delete next[connectorId]; return next; });
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
    // Invalidate cached schema and re-fetch (live schema may differ from mock)
    setSchemas((prev) => { const next = { ...prev }; delete next[connectorId]; return next; });
    void _fetchSchema(connectorId);
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <section>
      {/* Credential modal */}
      {configModal && (
        <ConfigModal
          connectorId={configModal.connectorId}
          connectorName={configModal.connectorName}
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
          const currentView     = panelView[c.connectorId] ?? "tools";
          const connectorTools  = tools[c.connectorId] ?? [];
          const connectorSchema = schemas[c.connectorId];
          const isLoadingTools  = loadingTools === c.connectorId;
          const isLoadingSchema = loadingSchema === c.connectorId;
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
                {/* Every connector: Configure / Edit Config + Disconnect when live */}
                {isLive ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setConfigModal({ connectorId: c.connectorId, connectorName: c.name, authScheme: c.authScheme })}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-xs font-medium text-teal-700 transition-colors hover:border-teal-300 hover:bg-teal-100"
                    >
                      <Settings2 className="h-3.5 w-3.5" />
                      Edit Credentials
                    </button>
                    <button
                      type="button"
                      disabled={isDisconnecting}
                      onClick={() => handleDisconnect(c.connectorId, c.authScheme)}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-50"
                    >
                      {isDisconnecting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Link2Off className="h-3.5 w-3.5" />}
                      Disconnect
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfigModal({ connectorId: c.connectorId, connectorName: c.name, authScheme: c.authScheme })}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white shadow-sm shadow-teal-900/20 transition-colors hover:bg-teal-700"
                  >
                    <Settings2 className="h-3.5 w-3.5" />
                    {supportsOAuth ? "Set Up & Connect" : "Enter Credentials"}
                  </button>
                )}

                {/* Test + Tools + Fields row */}
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    disabled={isTesting}
                    onClick={() => handleTest(c.connectorId)}
                    className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 disabled:opacity-50"
                  >
                    {isTesting
                      ? <Loader2 className="h-3 w-3 animate-spin" />
                      : <RefreshCw className="h-3 w-3" />}
                    Test
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExpandTools(c.connectorId)}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition-colors ${
                      isExpanded && currentView === "tools"
                        ? "border-slate-300 bg-slate-100 text-slate-800"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <Wrench className="h-3 w-3" />
                    Tools
                    {isExpanded && currentView === "tools"
                      ? <ChevronUp className="h-3 w-3" />
                      : <ChevronDown className="h-3 w-3" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExpandSchema(c.connectorId)}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition-colors ${
                      isExpanded && currentView === "schema"
                        ? "border-slate-300 bg-slate-100 text-slate-800"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <Database className="h-3 w-3" />
                    Fields
                    {isExpanded && currentView === "schema"
                      ? <ChevronUp className="h-3 w-3" />
                      : <ChevronDown className="h-3 w-3" />}
                  </button>
                </div>

                {/* Expanded panel */}
                {isExpanded && currentView === "tools" && (
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

                {isExpanded && currentView === "schema" && (
                  isLoadingSchema ? (
                    <div className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-400">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Fetching schema…
                    </div>
                  ) : connectorSchema ? (
                    <SchemaViewer schema={connectorSchema} />
                  ) : (
                    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-400">
                      No schema available.
                    </div>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
