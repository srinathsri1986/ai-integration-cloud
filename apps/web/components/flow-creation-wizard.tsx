"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Eye,
  Hand,
  Loader2,
  Plus,
  RefreshCw,
  Webhook,
  Zap,
} from "lucide-react";
import type {
  ConnectorDefinition,
  FieldInfo,
  InlineFieldMapping,
} from "@ai-integration-cloud/shared";
import type { FlowDefinitionUpsertRequest, FlowTriggerType } from "@ai-integration-cloud/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CronPreview } from "@/components/cron-preview";
import { FieldMapper } from "@/components/field-mapper";
import {
  createCustomEndpoint,
  discoverCustomEndpointSchema,
  getConnectors,
  getCustomEndpointSchema,
  saveFlowDefinition,
  testCustomEndpointConnection,
} from "@/lib/api";

// --- Trigger type cards ---

interface TriggerCardProps {
  selected: boolean;
  onSelect: () => void;
  icon: React.ReactNode;
  label: string;
  description: string;
}

function TriggerCard({ selected, onSelect, icon, label, description }: TriggerCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`
        relative flex flex-col gap-3 p-5 rounded-xl border-2 text-left transition-all
        hover:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-400
        ${selected
          ? "border-sky-500 bg-sky-50 ring-2 ring-sky-400"
          : "border-slate-200 bg-white hover:bg-sky-50/40"
        }
      `}
    >
      {selected && (
        <div className="absolute top-3 right-3">
          <Check className="h-4 w-4 text-sky-600" />
        </div>
      )}
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${selected ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600"}`}>
        {icon}
      </div>
      <div>
        <p className={`text-sm font-semibold ${selected ? "text-sky-700" : "text-slate-800"}`}>{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </div>
    </button>
  );
}

// --- Connector picker card ---

const AUTH_SCHEME_COLORS: Record<string, string> = {
  oauth2:       "bg-sky-100 text-sky-700",
  api_key:      "bg-violet-100 text-violet-700",
  basic:        "bg-amber-100 text-amber-700",
  token_based:  "bg-indigo-100 text-indigo-700",
  none:         "bg-slate-100 text-slate-600",
};

function ConnectorCard({
  connector,
  selected,
  onSelect,
}: {
  connector: ConnectorDefinition;
  selected: boolean;
  onSelect: () => void;
}) {
  const colorClass = AUTH_SCHEME_COLORS[connector.authScheme] ?? AUTH_SCHEME_COLORS.none;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`
        relative flex flex-col gap-2 p-4 rounded-xl border-2 text-left transition-all
        hover:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-400
        ${selected
          ? "border-sky-500 bg-sky-50 ring-2 ring-sky-400"
          : "border-slate-200 bg-white hover:bg-sky-50/40"
        }
      `}
    >
      {selected && (
        <div className="absolute top-2 right-2">
          <Check className="h-3.5 w-3.5 text-sky-600" />
        </div>
      )}
      <p className={`text-sm font-semibold leading-tight ${selected ? "text-sky-700" : "text-slate-800"}`}>
        {connector.name}
      </p>
      <p className="font-mono text-[11px] text-slate-400">{connector.connectorId}</p>
      <span className={`self-start rounded-full px-2 py-0.5 text-[10px] font-medium ${colorClass}`}>
        {connector.authScheme}
      </span>
    </button>
  );
}

// --- Step progress bar ---

function StepBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`
            h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors
            ${i + 1 < current ? "bg-emerald-500 text-white" : i + 1 === current ? "bg-sky-500 text-white" : "bg-slate-200 text-slate-400"}
          `}>
            {i + 1 < current ? <Check className="h-3.5 w-3.5" /> : i + 1}
          </div>
          {i < total - 1 && (
            <div className={`h-0.5 flex-1 w-16 ${i + 1 < current ? "bg-emerald-400" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom API form (inline, appears when "+ Custom API" card is clicked)
// ---------------------------------------------------------------------------

interface CustomApiFormProps {
  role: "source" | "target";
  onCreated: (endpointId: string, fields: FieldInfo[]) => void;
  onCancel: () => void;
}

function CustomApiForm({ role, onCreated, onCancel }: CustomApiFormProps) {
  const [apiName, setApiName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [authScheme, setAuthScheme] = useState<"none" | "api_key" | "bearer" | "basic">("none");
  const [apiKey, setApiKey] = useState("");
  const [bearerToken, setBearerToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [defaultPath, setDefaultPath] = useState("/");
  const [httpMethod, setHttpMethod] = useState<"GET" | "POST">("GET");
  const [saving, setSaving] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [discoveredFields, setDiscoveredFields] = useState<FieldInfo[]>([]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    const result = await createCustomEndpoint({
      name: apiName.trim(),
      baseUrl,
      authScheme,
      defaultPath,
      httpMethod,
      ...(authScheme === "api_key" ? { apiKey } : {}),
      ...(authScheme === "bearer" ? { bearerToken } : {}),
      ...(authScheme === "basic" ? { username, password } : {}),
    });
    setSaving(false);
    if (!result.ok) {
      setError(result.error ?? "Failed to register endpoint.");
      return;
    }
    setCreatedId(result.data.endpointId);
  }

  async function handleTest() {
    if (!createdId) return;
    setTesting(true);
    const result = await testCustomEndpointConnection(createdId);
    setTesting(false);
    setTestResult(result.ok ? result.data : { ok: false, message: result.error ?? "Test failed." });
  }

  async function handleDiscover() {
    if (!createdId) return;
    setDiscovering(true);
    setError(null);
    const result = await discoverCustomEndpointSchema(createdId, { path: defaultPath });
    setDiscovering(false);
    if (!result.ok || result.data.fieldCount === 0) {
      setError(result.error ?? "No fields discovered. Check the endpoint path and authentication.");
      return;
    }
    setDiscoveredFields(result.data.fields);
  }

  const canSave = apiName.trim().length >= 2 && baseUrl.startsWith("http");
  const canUse = createdId && discoveredFields.length > 0;

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50/40 p-4 space-y-4">
      <p className="text-sm font-semibold text-sky-800">Register {role} API</p>

      {/* Basic info */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Name <span className="text-rose-500">*</span></label>
          <input
            value={apiName}
            onChange={(e) => setApiName(e.target.value)}
            placeholder="My CRM API"
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Base URL <span className="text-rose-500">*</span></label>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.example.com"
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
          />
        </div>
      </div>

      {/* Endpoint path + method */}
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 mb-1">Endpoint path</label>
          <input
            value={defaultPath}
            onChange={(e) => setDefaultPath(e.target.value)}
            placeholder="/api/records"
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Method</label>
          <select
            value={httpMethod}
            onChange={(e) => setHttpMethod(e.target.value as "GET" | "POST")}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-400"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
          </select>
        </div>
      </div>

      {/* Auth */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Authentication</label>
        <select
          value={authScheme}
          onChange={(e) => setAuthScheme(e.target.value as typeof authScheme)}
          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-400"
        >
          <option value="none">None</option>
          <option value="api_key">API Key (header)</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
        </select>
      </div>
      {authScheme === "api_key" && (
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          type="password"
          placeholder="API key — encrypted at rest"
          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
        />
      )}
      {authScheme === "bearer" && (
        <input
          value={bearerToken}
          onChange={(e) => setBearerToken(e.target.value)}
          type="password"
          placeholder="Bearer token — encrypted at rest"
          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
        />
      )}
      {authScheme === "basic" && (
        <div className="grid grid-cols-2 gap-3">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Password — encrypted at rest"
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
          />
        </div>
      )}

      {error && (
        <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-2">
        {!createdId ? (
          <>
            <Button onClick={handleSave} disabled={!canSave || saving} className="gap-1.5">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              {saving ? "Registering…" : "Register endpoint"}
            </Button>
            <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          </>
        ) : (
          <>
            <Button
              variant="secondary"
              onClick={handleTest}
              disabled={testing}
             
              className="gap-1.5"
            >
              {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              Test connection
            </Button>
            {testResult && (
              <span className={`text-xs font-medium flex items-center gap-1 ${testResult.ok ? "text-emerald-600" : "text-rose-600"}`}>
                {testResult.ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                {testResult.message}
              </span>
            )}
            <Button
              onClick={handleDiscover}
              disabled={discovering}
             
              className="gap-1.5"
            >
              {discovering ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              {discovering ? "Discovering…" : "Discover fields"}
            </Button>
            {discoveredFields.length > 0 && (
              <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {discoveredFields.length} fields discovered
              </span>
            )}
          </>
        )}
        {canUse && (
          <Button
            onClick={() => onCreated(createdId!, discoveredFields)}
           
            className="gap-1.5 bg-emerald-500 hover:bg-emerald-600 ml-auto"
          >
            <Check className="h-3.5 w-3.5" />
            Use this endpoint
          </Button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main wizard (4 steps)
// ---------------------------------------------------------------------------

type WizardStep = 1 | 2 | 3 | 4;

export function FlowCreationWizard() {
  const router = useRouter();
  const [step, setStep] = useState<WizardStep>(1);

  // Step 1
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<FlowTriggerType>("manual");
  const [cronExpression, setCronExpression] = useState("0 9 * * 1-5");
  const [webhookSecret, setWebhookSecret] = useState("");

  // Step 2 (source)
  const [sourceConnector, setSourceConnector] = useState<string>("");
  const [sourceCustomId, setSourceCustomId] = useState<string | null>(null);
  const [sourceFields, setSourceFields] = useState<FieldInfo[]>([]);
  const [showSourceCustomForm, setShowSourceCustomForm] = useState(false);

  // Step 3 (target)
  const [targetConnector, setTargetConnector] = useState<string>("");
  const [targetCustomId, setTargetCustomId] = useState<string | null>(null);
  const [targetFields, setTargetFields] = useState<FieldInfo[]>([]);
  const [showTargetCustomForm, setShowTargetCustomForm] = useState(false);

  // Step 4 (field mappings)
  const [fieldMappings, setFieldMappings] = useState<InlineFieldMapping[]>([]);

  // Shared
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>([]);
  const [loadingConnectors, setLoadingConnectors] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch connectors once when entering step 2
  const hasFetchedConnectors = useRef(false);
  useEffect(() => {
    if ((step === 2 || step === 3) && !hasFetchedConnectors.current) {
      hasFetchedConnectors.current = true;
      setLoadingConnectors(true);
      getConnectors().then((result) => {
        setConnectors(result.data);
        setLoadingConnectors(false);
      });
    }
  }, [step]);

  // When user picks a pre-built connector, try to load its schema for the mapper
  useEffect(() => {
    if (!sourceConnector || sourceCustomId) return;
    getCustomEndpointSchema(sourceConnector)
      .then((r) => { if (r.data.fieldCount > 0) setSourceFields(r.data.fields); })
      .catch(() => {});
  }, [sourceConnector, sourceCustomId]);

  useEffect(() => {
    if (!targetConnector || targetCustomId) return;
    getCustomEndpointSchema(targetConnector)
      .then((r) => { if (r.data.fieldCount > 0) setTargetFields(r.data.fields); })
      .catch(() => {});
  }, [targetConnector, targetCustomId]);

  const canProceedStep1 = name.trim().length >= 3 && (
    triggerType !== "schedule" || cronExpression.trim().split(/\s+/).length === 5
  );
  const canProceedStep2 = sourceConnector.length > 0 && !showSourceCustomForm;
  const canProceedStep3 = targetConnector.length > 0 && !showTargetCustomForm;

  const selectedConnector = connectors.find((c) => c.connectorId === sourceConnector);
  const selectedTargetConnector = connectors.find((c) => c.connectorId === targetConnector);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);

    const flowId = name.trim().toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 96);

    const descriptionValue = description.trim().length >= 10
      ? description.trim()
      : `${name.trim()} — integration draft created via wizard.`;

    const effectiveSourceConnector = sourceCustomId ? `custom:${sourceCustomId}` : sourceConnector;
    const effectiveTargetConnector = targetCustomId ? `custom:${targetCustomId}` : targetConnector;

    const payload: FlowDefinitionUpsertRequest = {
      flowId,
      name: name.trim(),
      description: descriptionValue,
      sourceConnector: effectiveSourceConnector,
      targetModule: effectiveTargetConnector || effectiveSourceConnector.replace(/[:/]/g, "_"),
      targetConnector: effectiveTargetConnector || undefined,
      fieldMappings,
      status: "draft",
      triggerType,
      steps: [
        {
          id: "step-1",
          name: "Fetch source data",
          description: "Pull data from the source connector.",
          approvedTool: "orchestrator.query",
        },
      ],
      ...(triggerType === "schedule" ? { triggerCron: cronExpression.trim() } : {}),
    };

    const result = await saveFlowDefinition(payload);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error ?? "Failed to create integration.");
      return;
    }
    router.push(`/flows/${result.data.flowId}`);
  }

  return (
    <div className="px-5 lg:px-8 py-6 max-w-2xl mx-auto">
      <StepBar current={step} total={4} />

      {/* Step 1 — Trigger & Name */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Integration name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Salesforce opportunity sync"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What does this integration do?"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Trigger type <span className="text-rose-500">*</span>
            </label>
            <div className="grid grid-cols-3 gap-3">
              <TriggerCard
                selected={triggerType === "manual"}
                onSelect={() => setTriggerType("manual")}
                icon={<Hand className="h-5 w-5" />}
                label="Manual"
                description="Run on demand from the dashboard."
              />
              <TriggerCard
                selected={triggerType === "schedule"}
                onSelect={() => setTriggerType("schedule")}
                icon={<Calendar className="h-5 w-5" />}
                label="Schedule"
                description="Run automatically on a cron schedule."
              />
              <TriggerCard
                selected={triggerType === "webhook"}
                onSelect={() => setTriggerType("webhook")}
                icon={<Webhook className="h-5 w-5" />}
                label="Webhook"
                description="Run when an HTTP event arrives."
              />
            </div>
          </div>

          {triggerType === "schedule" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Cron expression{" "}
                <span className="text-xs text-slate-400 font-normal ml-1">(minute hour dom month dow)</span>
              </label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                placeholder="0 9 * * 1-5"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
              />
              <CronPreview expression={cronExpression} count={3} />
            </div>
          )}

          {triggerType === "webhook" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Webhook HMAC secret{" "}
                <span className="text-xs text-slate-400 font-normal ml-1">(optional — used to sign incoming requests)</span>
              </label>
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                placeholder="Leave blank to auto-generate"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
              />
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              disabled={!canProceedStep1}
              onClick={() => setStep(2)}
              className="gap-2"
            >
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2 — Source Connector ────────────────────────────────────── */}
      {step === 2 && (
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Source connector <span className="text-rose-500">*</span>
              <span className="ml-2 text-xs text-slate-400 font-normal">where data comes FROM</span>
            </label>

            {loadingConnectors ? (
              <div className="flex items-center gap-2 text-sm text-slate-500 py-6">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading connectors…
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-3">
                  {connectors.map((connector) => (
                    <ConnectorCard
                      key={connector.connectorId}
                      connector={connector}
                      selected={sourceConnector === connector.connectorId}
                      onSelect={() => {
                        setSourceConnector(connector.connectorId);
                        setSourceCustomId(null);
                        setShowSourceCustomForm(false);
                      }}
                    />
                  ))}

                  {/* Custom API card */}
                  <button
                    type="button"
                    onClick={() => {
                      setSourceConnector("custom");
                      setShowSourceCustomForm(true);
                    }}
                    className={`
                      relative flex flex-col gap-2 p-4 rounded-xl border-2 text-left transition-all
                      hover:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-400
                      ${showSourceCustomForm
                        ? "border-sky-500 bg-sky-50 ring-2 ring-sky-400"
                        : "border-dashed border-slate-300 bg-white hover:bg-sky-50/40"
                      }
                    `}
                  >
                    <p className="text-sm font-semibold text-slate-800">+ Custom API</p>
                    <p className="font-mono text-[11px] text-slate-400">any REST endpoint</p>
                    <span className="self-start rounded-full px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600">
                      api_key / bearer / basic
                    </span>
                  </button>
                </div>

                {showSourceCustomForm && (
                  <CustomApiForm
                    role="source"
                    onCreated={(id, fields) => {
                      setSourceCustomId(id);
                      setSourceConnector(`custom:${id}`);
                      setSourceFields(fields);
                      setShowSourceCustomForm(false);
                    }}
                    onCancel={() => {
                      setShowSourceCustomForm(false);
                      setSourceConnector("");
                      setSourceCustomId(null);
                    }}
                  />
                )}

                {sourceCustomId && !showSourceCustomForm && (
                  <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2 flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Custom source API registered — {sourceFields.length} fields discovered.
                    <button
                      type="button"
                      onClick={() => setShowSourceCustomForm(true)}
                      className="ml-auto underline text-emerald-700"
                    >Edit</button>
                  </p>
                )}
              </>
            )}
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(1)} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button disabled={!canProceedStep2} onClick={() => setStep(3)} className="gap-2">
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 3 — Target Connector ─────────────────────────────────────── */}
      {step === 3 && (
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Target connector <span className="text-rose-500">*</span>
              <span className="ml-2 text-xs text-slate-400 font-normal">where data goes TO</span>
            </label>

            {loadingConnectors ? (
              <div className="flex items-center gap-2 text-sm text-slate-500 py-6">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading connectors…
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-3">
                  {connectors.map((connector) => (
                    <ConnectorCard
                      key={connector.connectorId}
                      connector={connector}
                      selected={targetConnector === connector.connectorId}
                      onSelect={() => {
                        setTargetConnector(connector.connectorId);
                        setTargetCustomId(null);
                        setShowTargetCustomForm(false);
                      }}
                    />
                  ))}

                  <button
                    type="button"
                    onClick={() => {
                      setTargetConnector("custom");
                      setShowTargetCustomForm(true);
                    }}
                    className={`
                      relative flex flex-col gap-2 p-4 rounded-xl border-2 text-left transition-all
                      hover:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-400
                      ${showTargetCustomForm
                        ? "border-sky-500 bg-sky-50 ring-2 ring-sky-400"
                        : "border-dashed border-slate-300 bg-white hover:bg-sky-50/40"
                      }
                    `}
                  >
                    <p className="text-sm font-semibold text-slate-800">+ Custom API</p>
                    <p className="font-mono text-[11px] text-slate-400">any REST endpoint</p>
                    <span className="self-start rounded-full px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600">
                      api_key / bearer / basic
                    </span>
                  </button>
                </div>

                {showTargetCustomForm && (
                  <CustomApiForm
                    role="target"
                    onCreated={(id, fields) => {
                      setTargetCustomId(id);
                      setTargetConnector(`custom:${id}`);
                      setTargetFields(fields);
                      setShowTargetCustomForm(false);
                    }}
                    onCancel={() => {
                      setShowTargetCustomForm(false);
                      setTargetConnector("");
                      setTargetCustomId(null);
                    }}
                  />
                )}

                {targetCustomId && !showTargetCustomForm && (
                  <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2 flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Custom target API registered — {targetFields.length} fields discovered.
                    <button
                      type="button"
                      onClick={() => setShowTargetCustomForm(true)}
                      className="ml-auto underline text-emerald-700"
                    >Edit</button>
                  </p>
                )}
              </>
            )}
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(2)} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button disabled={!canProceedStep3} onClick={() => setStep(4)} className="gap-2">
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 4 — Field Mapping + Review ──────────────────────────────── */}
      {step === 4 && (
        <div className="space-y-6">

          {/* Field mapper */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-medium text-slate-700">
                Map fields
                <span className="ml-2 text-xs text-slate-400 font-normal">optional — skipped fields pass through unchanged</span>
              </label>
            </div>
            <FieldMapper
              sourceFields={sourceFields}
              targetFields={targetFields}
              initialMappings={fieldMappings}
              onChange={setFieldMappings}
              sourceLabel={selectedConnector?.name ?? "Source"}
              targetLabel={selectedTargetConnector?.name ?? "Target"}
            />
          </div>

          {/* Review card */}
          <Card className="bg-slate-50 border border-slate-200 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Review your integration</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium text-slate-800">{name}</dd>

              <dt className="text-slate-500">Trigger</dt>
              <dd>
                <span className="inline-flex items-center rounded-md border border-slate-200 bg-muted px-2 py-1 text-xs font-medium capitalize">
                  {triggerType}
                </span>
              </dd>

              {triggerType === "schedule" && (
                <>
                  <dt className="text-slate-500">Schedule</dt>
                  <dd className="font-mono text-xs text-slate-700">{cronExpression}</dd>
                </>
              )}

              <dt className="text-slate-500">Source</dt>
              <dd className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-slate-800">
                  {sourceCustomId ? `Custom API (${sourceFields.length} fields)` : (selectedConnector?.name ?? sourceConnector)}
                </span>
                {selectedConnector && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${AUTH_SCHEME_COLORS[selectedConnector.authScheme] ?? AUTH_SCHEME_COLORS.none}`}>
                    {selectedConnector.authScheme}
                  </span>
                )}
              </dd>

              <dt className="text-slate-500">Target</dt>
              <dd className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-slate-800">
                  {targetCustomId ? `Custom API (${targetFields.length} fields)` : (selectedTargetConnector?.name ?? targetConnector)}
                </span>
                {selectedTargetConnector && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${AUTH_SCHEME_COLORS[selectedTargetConnector.authScheme] ?? AUTH_SCHEME_COLORS.none}`}>
                    {selectedTargetConnector.authScheme}
                  </span>
                )}
              </dd>

              <dt className="text-slate-500">Field mappings</dt>
              <dd className="font-medium text-slate-800">{fieldMappings.length} mapping{fieldMappings.length !== 1 ? "s" : ""}</dd>
            </dl>
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mt-2">
              This integration will be created as a <strong>draft</strong>. Submit it for approval before it can run.
            </p>
          </Card>

          {error && (
            <div className="flex items-start gap-2 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(3)} disabled={submitting} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button onClick={handleSubmit} disabled={submitting} className="gap-2">
              {submitting ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Creating…</>
              ) : (
                <><Check className="h-4 w-4" /> Create Integration</>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
