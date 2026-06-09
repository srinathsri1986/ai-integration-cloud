"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  BarChart3,
  Bell,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Database,
  Download,
  FileText,
  Loader2,
  RotateCcw,
  Search,
  Shuffle,
  Sparkles,
  TriangleAlert,
  Wand2,
  XCircle,
  Zap,
} from "lucide-react";
import type {
  FlowDefinitionUpsertRequest,
  FlowStep,
  FlowSuggestionResponse,
} from "@ai-integration-cloud/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { saveFlowDefinition, suggestFlowDefinition } from "@/lib/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const SESSION_KEY_DRAFT = "askAI_suggestedFlow";
const SESSION_KEY_BUILDER = "aiBuilderDraft";

const KNOWN_CONNECTORS = new Set([
  "netsuite", "salesforce", "sap", "oracle", "servicenow",
  "hubspot", "workday", "slack", "sftp", "rest-api", "postgres", "mysql",
]);

const CONNECTOR_LABELS: Record<string, string> = {
  netsuite: "NetSuite",
  salesforce: "Salesforce",
  sap: "SAP",
  oracle: "Oracle",
  servicenow: "ServiceNow",
  hubspot: "HubSpot",
  workday: "Workday",
  slack: "Slack",
  sftp: "SFTP",
  "rest-api": "REST API",
  postgres: "PostgreSQL",
  mysql: "MySQL",
};

const EXAMPLE_PROMPTS = [
  "Sync NetSuite customers to Salesforce every hour",
  "Push SAP vendors to ServiceNow daily",
  "When an order is created in NetSuite, sync it to HubSpot",
  "Sync NetSuite contacts to Salesforce every 15 min",
];

// ── Tool helpers ──────────────────────────────────────────────────────────────

function StepIcon({ tool, className = "h-4 w-4" }: { tool: string; className?: string }) {
  if (tool === "connector.schedule_trigger") return <Clock className={className} />;
  if (tool === "connector.webhook_trigger") return <Zap className={className} />;
  if (tool === "connector.fetch_records") return <Download className={className} />;
  if (tool === "connector.search_records") return <Search className={className} />;
  if (
    tool === "connector.upsert_record" ||
    tool === "connector.create_record" ||
    tool === "connector.update_record"
  )
    return <Database className={className} />;
  if (tool === "connector.transform_payload") return <Shuffle className={className} />;
  if (tool === "connector.send_notification") return <Bell className={className} />;
  if (tool === "connector.audit_log") return <FileText className={className} />;
  if (tool === "connector.retry_handler") return <RotateCcw className={className} />;
  if (tool.startsWith("cfo.")) return <BarChart3 className={className} />;
  if (tool === "orchestrator.query") return <Bot className={className} />;
  return <Sparkles className={className} />;
}

function stepCardTheme(tool: string): { card: string; icon: string } {
  if (
    tool === "connector.schedule_trigger" ||
    tool === "connector.webhook_trigger"
  )
    return { card: "border-teal-200 bg-teal-50", icon: "bg-teal-100 text-teal-700" };
  if (tool === "connector.fetch_records" || tool === "connector.search_records")
    return { card: "border-sky-200 bg-sky-50", icon: "bg-sky-100 text-sky-700" };
  if (tool === "connector.transform_payload")
    return { card: "border-amber-200 bg-amber-50", icon: "bg-amber-100 text-amber-700" };
  if (
    tool === "connector.upsert_record" ||
    tool === "connector.create_record" ||
    tool === "connector.update_record"
  )
    return { card: "border-emerald-200 bg-emerald-50", icon: "bg-emerald-100 text-emerald-700" };
  if (tool === "connector.audit_log" || tool === "connector.retry_handler")
    return { card: "border-slate-200 bg-slate-50", icon: "bg-slate-200 text-slate-600" };
  if (tool === "connector.send_notification")
    return { card: "border-purple-200 bg-purple-50", icon: "bg-purple-100 text-purple-700" };
  // CFO / orchestrator
  return { card: "border-blue-200 bg-blue-50", icon: "bg-blue-100 text-blue-700" };
}

function toolLabel(tool: string): string {
  return tool.replace("connector.", "").replace("cfo.", "cfo: ").replace("_", " ").replace(/_/g, " ");
}

// ── Validation ────────────────────────────────────────────────────────────────

type ValidationStatus = "ok" | "warning" | "review" | "block";

interface ValidationItem {
  label: string;
  value: string;
  status: ValidationStatus;
  note?: string;
}

function buildValidation(response: FlowSuggestionResponse): ValidationItem[] {
  const flow = response.suggestedFlow;
  const srcKnown = KNOWN_CONNECTORS.has(flow.sourceConnector);
  const tgtKnown = flow.targetConnector
    ? KNOWN_CONNECTORS.has(flow.targetConnector)
    : false;

  let credStatus: ValidationStatus;
  let credValue: string;
  if (srcKnown && tgtKnown) {
    credStatus = "ok";
    credValue = "Both connectors configured";
  } else if (srcKnown) {
    credStatus = "warning";
    credValue = "Target connector needs setup";
  } else {
    credStatus = "block";
    credValue = "Connector credentials required";
  }

  const isLive =
    response.suggestionProvider === "ollama" ||
    response.suggestionProvider === "openai";

  return [
    {
      label: "Connector Credentials",
      value: credValue,
      status: credStatus,
      note: srcKnown
        ? `${connectorLabel(flow.sourceConnector)} → ${connectorLabel(flow.targetConnector ?? "target")}`
        : undefined,
    },
    {
      label: "Mapping Confidence",
      value: isLive ? "AI-generated (high)" : "Template (deterministic)",
      status: isLive ? "ok" : "warning",
      note: isLive
        ? (response.suggestionModel ?? response.suggestionProvider)
        : "Connect Qwen3 for semantic field matching",
    },
    {
      label: "Requires Approval",
      value: "Review before publish",
      status: "review",
      note: "Governance policy: admin sign-off required",
    },
    {
      label: "Sandbox Test",
      value: "Not run yet",
      status: "block",
      note: "Run sandbox to validate end-to-end",
    },
  ];
}

function connectorLabel(id: string): string {
  return CONNECTOR_LABELS[id] ?? id.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Small UI atoms ────────────────────────────────────────────────────────────

function ValidationStatusIcon({ status }: { status: ValidationStatus }) {
  if (status === "ok")
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />;
  if (status === "warning")
    return <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />;
  if (status === "review")
    return <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />;
  return <XCircle className="h-4 w-4 shrink-0 text-rose-500" />;
}

function ValidationStatusBadge({ status }: { status: ValidationStatus }) {
  const map: Record<ValidationStatus, string> = {
    ok: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    review: "border-amber-200 bg-amber-50 text-amber-700",
    block: "border-rose-200 bg-rose-50 text-rose-700",
  };
  const label: Record<ValidationStatus, string> = {
    ok: "OK",
    warning: "Warning",
    review: "Review",
    block: "Required",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${map[status]}`}
    >
      {label[status]}
    </span>
  );
}

function TriggerBadge({
  triggerType,
  triggerCron,
}: {
  triggerType: string;
  triggerCron?: string | null;
}) {
  if (triggerType === "schedule")
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-700">
        <Clock className="h-3 w-3" />
        {triggerCron}
      </span>
    );
  if (triggerType === "webhook")
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
        <Zap className="h-3 w-3" />
        Webhook
      </span>
    );
  return (
    <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500">
      Manual
    </span>
  );
}

// ── Canvas step card ──────────────────────────────────────────────────────────

function StepCard({ step, index }: { step: FlowStep; index: number }) {
  const theme = stepCardTheme(step.approvedTool);
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-full rounded-xl border px-4 py-3 transition-shadow hover:shadow-sm ${theme.card}`}
      >
        <div className="flex items-start gap-3">
          {/* Step number + icon */}
          <div className="flex flex-col items-center gap-1">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${theme.icon}`}
            >
              <StepIcon tool={step.approvedTool} />
            </div>
            <span className="text-[10px] font-semibold text-slate-400">
              {String(index + 1).padStart(2, "0")}
            </span>
          </div>
          {/* Content */}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold leading-5 text-slate-900">{step.name}</p>
            <p className="mt-0.5 text-[12px] leading-4 text-slate-500">{step.description}</p>
            <span className="mt-1.5 inline-flex items-center rounded-full border border-slate-200 bg-white/70 px-2 py-0.5 text-[10px] font-mono font-medium text-slate-500">
              {toolLabel(step.approvedTool)}
            </span>
          </div>
        </div>
      </div>
      {/* Connector arrow — omit after last card */}
    </div>
  );
}

// ── Empty canvas ─────────────────────────────────────────────────────────────

function EmptyCanvas() {
  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 p-10 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50">
        <Wand2 className="h-7 w-7 text-teal-500" />
      </div>
      <p className="text-sm font-semibold text-slate-700">No flow generated yet</p>
      <p className="mt-1.5 max-w-xs text-[13px] leading-5 text-slate-400">
        Describe your integration on the left and click{" "}
        <span className="font-medium text-teal-600">Generate Flow</span> to see
        the step-by-step canvas here.
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function AIWorkflowBuilder() {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FlowSuggestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedFlowId, setSavedFlowId] = useState<string | null>(null);

  // Pick up draft injected by Ask AI panel via sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem(SESSION_KEY_DRAFT);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as FlowSuggestionResponse;
        setResult(parsed);
        setPrompt(parsed.prompt);
        sessionStorage.removeItem(SESSION_KEY_DRAFT);
      } catch {
        // Silently ignore malformed data
      }
    }
  }, []);

  async function handleGenerate() {
    const q = prompt.trim();
    if (!q || q.length < 10) return;
    setLoading(true);
    setError(null);

    const res = await suggestFlowDefinition({ prompt: q });
    setLoading(false);

    if (res.ok) {
      setResult(res.data);
    } else {
      setError(res.error ?? "Flow generation failed. Check the API server and try again.");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleGenerate();
    }
  }

  async function handleCreateFlow() {
    if (!flow) return;
    setSaving(true);
    setSaveError(null);
    setSavedFlowId(null);

    // Make the flowId unique so re-generating the same prompt doesn't conflict
    const uniqueId = `${flow.flowId}-${Date.now().toString(36)}`;
    const draftToSave: FlowDefinitionUpsertRequest = { ...flow, flowId: uniqueId };

    const res = await saveFlowDefinition(draftToSave);
    setSaving(false);

    if (res.ok) {
      // Navigate straight to the integration studio — draft appears at the top of the list
      router.push(`/flows?created=${res.data.flowId}`);
    } else {
      setSaveError(res.error ?? "Failed to save the flow draft. Please try again.");
    }
  }

  const flow = result?.suggestedFlow ?? null;
  const validation = result ? buildValidation(result) : null;
  const allValidationOk = validation?.every((v) => v.status === "ok") ?? false;
  const hasBlocker = validation?.some((v) => v.status === "block") ?? false;

  return (
    <div className="flex min-h-0 flex-col gap-6 lg:flex-row lg:items-start">

      {/* ── LEFT PANEL — Input ───────────────────────────────────────────── */}
      <div className="shrink-0 lg:w-[360px] xl:w-[400px]">
        <Card className="overflow-hidden rounded-2xl border border-slate-100 p-0 shadow-card">
          {/* Header */}
          <div className="border-b border-slate-100 px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500 shadow-sm shadow-teal-900/20">
                <Wand2 className="h-4 w-4 text-white" />
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">Describe Your Workflow</p>
                <p className="text-[11px] text-slate-400">Natural language → governed integration</p>
              </div>
            </div>
          </div>

          {/* Textarea */}
          <div className="px-5 pt-4 pb-3">
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. Sync NetSuite customers to Salesforce every hour, or: When a vendor is updated in SAP push changes to ServiceNow"
              rows={5}
              className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 transition-colors focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-400/20"
            />
            <div className="mt-2 flex items-center justify-between">
              <p className="text-[11px] text-slate-400">
                <kbd className="rounded border border-slate-200 bg-slate-100 px-1 py-0.5 text-[10px] font-mono">
                  ⌘ Enter
                </kbd>{" "}
                to generate
              </p>
              <Button
                onClick={handleGenerate}
                disabled={loading || prompt.trim().length < 10}
                className="h-9 gap-2 rounded-lg px-4 text-sm"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                {loading ? "Generating…" : "Generate Flow"}
              </Button>
            </div>
          </div>

          {/* Example prompts */}
          {!result && !loading && (
            <div className="border-t border-slate-100 px-5 pb-4 pt-3">
              <p className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Examples
              </p>
              <div className="flex flex-col gap-1.5">
                {EXAMPLE_PROMPTS.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setPrompt(ex)}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="border-t border-slate-100 px-5 pb-5 pt-4">
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            </div>
          )}

          {/* Rationale — shown after generation */}
          {result && (
            <div className="border-t border-slate-100 px-5 pb-5 pt-4">
              <div className="flex items-start gap-2.5 rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3">
                <BrainCircuit className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
                <div className="min-w-0">
                  <p className="text-[12px] font-medium text-teal-800">AI Rationale</p>
                  <p className="mt-0.5 text-[12px] leading-5 text-teal-700">{result.rationale}</p>
                  {result.suggestionProvider !== "template" && (
                    <span className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-teal-200 bg-white px-2 py-0.5 text-[10px] font-medium text-teal-700">
                      <BrainCircuit className="h-3 w-3" />
                      {result.suggestionModel ?? result.suggestionProvider}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* ── MIDDLE PANEL — Canvas ────────────────────────────────────────── */}
      <div className="min-w-0 flex-1">
        <Card className="overflow-hidden rounded-2xl border border-slate-100 p-0 shadow-card">
          {/* Header */}
          <div className="border-b border-slate-100 px-5 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">Generated Workflow Canvas</p>
                <p className="text-[11px] text-slate-400">
                  {flow
                    ? `${flow.steps.length} steps · ${flow.sourceConnector} → ${flow.targetConnector ?? flow.targetModule}`
                    : "Step-by-step integration visualised here"}
                </p>
              </div>
              {flow && (
                <div className="flex items-center gap-2">
                  <TriggerBadge
                    triggerType={flow.triggerType}
                    triggerCron={flow.triggerCron}
                  />
                  <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-500">
                    draft
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="px-5 py-5">
            {!flow ? (
              <EmptyCanvas />
            ) : (
              <>
                {/* Flow name + description */}
                <div className="mb-5">
                  <h2 className="text-base font-bold text-slate-900">{flow.name}</h2>
                  <p className="mt-1 text-[13px] leading-5 text-slate-500">{flow.description}</p>
                </div>

                {/* Step cards with connecting lines */}
                <div className="space-y-0">
                  {flow.steps.map((step, idx) => (
                    <div key={step.id}>
                      <StepCard step={step} index={idx} />
                      {idx < flow.steps.length - 1 && (
                        <div className="flex justify-center py-1.5">
                          <ArrowDown className="h-4 w-4 text-slate-300" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* ── RIGHT PANEL — Validation ─────────────────────────────────────── */}
      <div className="shrink-0 lg:w-[300px] xl:w-[320px]">
        <Card className="overflow-hidden rounded-2xl border border-slate-100 p-0 shadow-card">
          {/* Header */}
          <div className="border-b border-slate-100 px-5 py-4">
            <div className="flex items-center gap-3">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                  !validation
                    ? "bg-slate-100"
                    : allValidationOk
                    ? "bg-emerald-500"
                    : hasBlocker
                    ? "bg-rose-500"
                    : "bg-amber-500"
                } shadow-sm`}
              >
                <CheckCircle2
                  className={`h-4 w-4 ${
                    !validation
                      ? "text-slate-400"
                      : "text-white"
                  }`}
                />
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">Validation</p>
                <p className="text-[11px] text-slate-400">
                  {!validation
                    ? "Generate a flow to see checks"
                    : allValidationOk
                    ? "All checks passed"
                    : hasBlocker
                    ? "Blockers need attention"
                    : "Review required"}
                </p>
              </div>
            </div>
          </div>

          {/* Validation items */}
          <div className="divide-y divide-slate-50 px-5 py-2">
            {!validation ? (
              /* Empty state */
              <div className="py-8 text-center">
                <div className="mb-3 flex justify-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100">
                    <CheckCircle2 className="h-6 w-6 text-slate-300" />
                  </div>
                </div>
                <p className="text-[13px] text-slate-400">
                  Validation runs after you generate a flow
                </p>
              </div>
            ) : (
              validation.map((item) => (
                <div key={item.label} className="py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <ValidationStatusIcon status={item.status} />
                      <span className="text-[13px] font-medium text-slate-700">{item.label}</span>
                    </div>
                    <ValidationStatusBadge status={item.status} />
                  </div>
                  <p className="mt-1 pl-6 text-[12px] text-slate-500">{item.value}</p>
                  {item.note && (
                    <p className="mt-0.5 pl-6 text-[11px] text-slate-400">{item.note}</p>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Action buttons */}
          <div className="border-t border-slate-100 px-5 pb-5 pt-4 space-y-2">
            {/* Run Sandbox Test */}
            <button
              type="button"
              disabled
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-400 cursor-not-allowed"
              title="Sandbox testing coming in the next release"
            >
              Run Sandbox Test
            </button>

            {/* Create Flow — saves draft directly, no wizard */}
            <Button
              onClick={handleCreateFlow}
              disabled={!flow || saving}
              className="w-full h-10 rounded-xl gap-2 text-sm font-semibold"
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Wand2 className="h-3.5 w-3.5" />
              )}
              {saving ? "Saving draft…" : "Create Flow"}
            </Button>

            {/* Save error */}
            {saveError && (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-center text-[11px] text-rose-600">
                {saveError}
              </p>
            )}

            {/* Governance note */}
            <p className="text-center text-[11px] text-slate-400">
              Saved as draft · requires approval before publish
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
