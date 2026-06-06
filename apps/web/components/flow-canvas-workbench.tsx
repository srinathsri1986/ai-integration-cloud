"use client";

import { useEffect, useMemo, useState } from "react";
import type { DragEvent } from "react";
import {
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  DatabaseZap,
  FileCheck2,
  GitBranch,
  GripVertical,
  Loader2,
  Sparkles,
  Save,
  ShieldCheck,
  Workflow
} from "lucide-react";
import type {
  ConnectorDefinition,
  ConnectorTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowStep,
  FlowSuggestionResponse
} from "@ai-integration-cloud/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { type ApiResult, getConnectors, getConnectorTools, saveFlowDefinition, suggestFlowDefinition } from "@/lib/api";

type PaletteItem = {
  description: string;
  id: string;
  label: string;
  tool: string;
};

function toolToPaletteItem(t: ConnectorTool): PaletteItem {
  return { description: t.description, id: t.toolId.replace(/\./g, "-"), label: t.label, tool: t.toolId };
}

function stepFromPalette(item: PaletteItem, index: number): FlowStep {
  return {
    approvedTool: item.tool,
    description: item.description,
    id: `${item.id}-${index + 1}`,
    name: item.label
  };
}

export function FlowCanvasWorkbench({
  initialFlows
}: {
  initialFlows: ApiResult<FlowDefinition[]>;
}) {
  const firstFlow = initialFlows.data[0];
  const [selectedFlowId, setSelectedFlowId] = useState<string>(firstFlow?.flowId ?? "");
  const selectedFlow = useMemo(
    () => initialFlows.data.find((flow) => flow.flowId === selectedFlowId) ?? firstFlow,
    [firstFlow, initialFlows.data, selectedFlowId]
  );

  // Connector state
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>([]);
  const [selectedConnectorId, setSelectedConnectorId] = useState<string>("netsuite");
  const [palette, setPalette] = useState<PaletteItem[]>([]);
  const [loadingPalette, setLoadingPalette] = useState(false);

  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>({
    description: "Visual integration draft using governed, approved actions only.",
    flowId: "visual-integration-draft",
    name: "Visual Integration Draft",
    sourceConnector: "netsuite",
    status: "draft",
    steps: [],
    targetModule: "netsuite",
    triggerType: "manual"
  });
  const [message, setMessage] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);
  const [flowPrompt, setFlowPrompt] = useState(
    "Create a monthly financial dashboard refresh that pulls summary data and compares actuals against budget."
  );
  const [suggestion, setSuggestion] = useState<FlowSuggestionResponse | undefined>();
  const [isSuggesting, setIsSuggesting] = useState(false);

  // Load connectors on mount
  useEffect(() => {
    getConnectors().then((result) => {
      if (!result.isFallback && result.data.length > 0) {
        setConnectors(result.data);
        const defaultId = result.data[0].connectorId;
        setSelectedConnectorId(defaultId);
        loadPaletteForConnector(defaultId);
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPaletteForConnector(connectorId: string) {
    setLoadingPalette(true);
    const result = await getConnectorTools(connectorId);
    if (!result.isFallback) {
      const items = result.data.map(toolToPaletteItem);
      setPalette(items);
      // Seed the draft with the first two tools from the new connector
      setDraft((current) => ({
        ...current,
        sourceConnector: connectorId,
        targetModule: connectorId.replace(/-/g, "_"),
        flowId: `visual-${connectorId}-draft`,
        name: `Visual ${connectorId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Draft`,
        steps: items.slice(0, 2).map((item, i) => stepFromPalette(item, i))
      }));
    }
    setLoadingPalette(false);
  }

  async function handleConnectorChange(connectorId: string) {
    setSelectedConnectorId(connectorId);
    await loadPaletteForConnector(connectorId);
  }

  const selectedConnector = connectors.find((c) => c.connectorId === selectedConnectorId);

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const tool = event.dataTransfer.getData("application/x-approved-tool");
    const item = palette.find((candidate) => candidate.tool === tool);
    if (!item) return;
    setDraft((current) => ({
      ...current,
      steps: [...current.steps, stepFromPalette(item, current.steps.length)]
    }));
  }

  async function onSave() {
    setIsSaving(true);
    setMessage(undefined);
    const response = await saveFlowDefinition(draft);
    setMessage(
      response.ok
        ? `${response.data.name} saved. Governed flow — submit for approval before running.`
        : response.error ?? "Unable to save visual flow."
    );
    setIsSaving(false);
  }

  async function onSuggestFlow() {
    setIsSuggesting(true);
    setMessage(undefined);
    const response = await suggestFlowDefinition({ prompt: flowPrompt });
    setSuggestion(response.data);

    if (response.ok) {
      setDraft(response.data.suggestedFlow);
      setMessage(
        response.data.suggestionFallbackUsed
          ? "Template fallback drafted a governed flow for review."
          : "AI drafted a governed flow for review."
      );
    } else {
      setDraft(response.data.suggestedFlow);
      setMessage(response.error ?? "Unable to generate flow suggestion.");
    }

    setIsSuggesting(false);
  }

  const previewSteps = selectedFlow?.steps ?? [];

  return (
    <section className="mx-auto max-w-7xl px-6 pb-12">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Visual Flow Designer</p>
          <h2 className="mt-1 text-xl font-semibold">Governed orchestration canvas</h2>
        </div>
        <Badge className="border-sky-300 bg-sky-50 text-sky-950">
          <Workflow className="mr-1 h-3.5 w-3.5" />
          Visual shell
        </Badge>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="grid min-h-[560px] lg:grid-cols-[260px_minmax(0,1fr)_320px]">
          {/* ── Left palette ── */}
          <aside className="border-b border-border bg-slate-950 p-4 text-white lg:border-b-0 lg:border-r">
            <div className="flex items-center gap-2">
              <GripVertical className="h-4 w-4 text-sky-300" />
              <p className="text-sm font-semibold">Node palette</p>
            </div>

            {/* Connector selector */}
            <div className="mt-3 relative">
              <select
                className="w-full appearance-none rounded-md border border-slate-700 bg-slate-800 px-3 py-2 pr-8 text-xs text-slate-100 outline-none focus:border-sky-400"
                value={selectedConnectorId}
                onChange={(e) => handleConnectorChange(e.target.value)}
              >
                {connectors.length === 0 ? (
                  <option value="netsuite">netsuite</option>
                ) : connectors.map((c) => (
                  <option key={c.connectorId} value={c.connectorId}>{c.name}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-2.5 h-3.5 w-3.5 text-slate-400" />
            </div>

            <div className="mt-3 space-y-2">
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <CalendarClock className="h-4 w-4 text-sky-300" />
                <p className="mt-2 text-sm font-medium">Manual trigger</p>
                <p className="mt-1 text-xs leading-5 text-slate-300">Fixed start node</p>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <DatabaseZap className="h-4 w-4 text-sky-300" />
                <p className="mt-2 text-sm font-medium">
                  {selectedConnector?.name ?? selectedConnectorId}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-300">
                  {selectedConnector?.authScheme ?? "mock"} · governed
                </p>
              </div>

              {loadingPalette ? (
                <div className="flex items-center gap-2 py-3 text-xs text-slate-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading tools…
                </div>
              ) : palette.length === 0 ? (
                <p className="py-3 text-xs text-slate-500">No tools available.</p>
              ) : (
                palette.map((item) => (
                  <button
                    className="w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-left transition-colors hover:border-sky-300"
                    draggable
                    key={item.tool}
                    onDragStart={(event) =>
                      event.dataTransfer.setData("application/x-approved-tool", item.tool)
                    }
                    type="button"
                  >
                    <FileCheck2 className="h-4 w-4 text-sky-300" />
                    <p className="mt-2 text-sm font-medium">{item.label}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-300">{item.tool}</p>
                  </button>
                ))
              )}
            </div>
          </aside>

          {/* ── Centre canvas ── */}
          <div className="grid bg-slate-100 xl:grid-rows-[auto_1fr]">
            <div className="border-b border-slate-200 bg-white p-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold">Describe a flow</p>
              </div>
              <textarea
                className="mt-3 min-h-24 w-full resize-none rounded-md border border-border bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-primary"
                onChange={(event) => setFlowPrompt(event.target.value)}
                value={flowPrompt}
              />
              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs leading-5 text-muted-foreground">
                  Drafts only. Human review is required before save, run, or publish.
                </p>
                <Button disabled={isSuggesting || flowPrompt.length < 10} onClick={onSuggestFlow} type="button">
                  <Sparkles className="h-4 w-4" />
                  {isSuggesting ? "Drafting" : "Generate draft"}
                </Button>
              </div>
              {suggestion ? (
                <div className="mt-3 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-950">
                  <p className="font-medium">
                    {suggestion.suggestionProvider}
                    {suggestion.suggestionModel ? ` / ${suggestion.suggestionModel}` : ""}
                  </p>
                  <p className="mt-1 leading-6">{suggestion.rationale}</p>
                </div>
              ) : null}
            </div>

            <div
              className="relative overflow-hidden p-5"
              onDragOver={(event) => event.preventDefault()}
              onDrop={onDrop}
            >
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#cbd5e1_1px,transparent_1px),linear-gradient(to_bottom,#cbd5e1_1px,transparent_1px)] bg-[size:28px_28px] opacity-50" />
              <div className="relative grid gap-4">
                <div className="flex flex-wrap gap-2">
                  <Badge className="bg-white">Drag tool nodes onto canvas</Badge>
                  <Badge className="bg-white">No arbitrary execution</Badge>
                  <Badge className="bg-white">AI drafts stay unpublished</Badge>
                </div>
                <div className="grid gap-4 xl:grid-cols-[220px_1fr_180px]">
                  <CanvasNode icon="trigger" title="Manual trigger" detail={draft.triggerType} />
                  <div className="grid gap-3">
                    <CanvasNode
                      icon="connector"
                      title={selectedConnector?.name ?? selectedConnectorId}
                      detail={`${selectedConnector?.authScheme ?? "mock"} · governed connector`}
                    />
                    {draft.steps.map((step, index) => (
                      <CanvasNode
                        detail={step.approvedTool}
                        icon="action"
                        key={step.id}
                        title={`${index + 1}. ${step.name}`}
                      />
                    ))}
                  </div>
                  <CanvasNode icon="audit" title="Audit event" detail="record model, tool, and flow metadata" />
                </div>
              </div>
            </div>
          </div>

          {/* ── Right properties panel ── */}
          <aside className="border-t border-border bg-white p-4 lg:border-l lg:border-t-0">
            <CardHeader>
              <CardTitle>Properties</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              <input
                className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                onChange={(event) => setDraft((current) => ({ ...current, flowId: event.target.value }))}
                value={draft.flowId}
              />
              <input
                className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
                value={draft.name}
              />
              <select
                className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                disabled
                value={draft.status}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    status: event.target.value as FlowDefinitionUpsertRequest["status"]
                  }))
                }
              >
                <option value="draft">Draft</option>
              </select>
              <div className="rounded-md border border-border bg-muted/50 p-3">
                <p className="text-sm font-medium">Current draft</p>
                <p className="mt-1 text-sm text-muted-foreground">{draft.steps.length} approved steps</p>
                <p className="mt-0.5 font-mono text-xs text-muted-foreground">{draft.sourceConnector}</p>
              </div>
              <Button className="w-full" disabled={isSaving} onClick={onSave} type="button">
                <Save className="h-4 w-4" />
                {isSaving ? "Saving" : "Validate and save"}
              </Button>
              {message ? (
                <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950">
                  {message}
                </p>
              ) : null}
            </div>

            <div className="mt-5 border-t border-border pt-4">
              <p className="text-sm font-medium">Preview saved flow</p>
              <select
                className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                onChange={(event) => setSelectedFlowId(event.target.value)}
                value={selectedFlowId}
              >
                {initialFlows.data.map((flow) => (
                  <option key={flow.flowId} value={flow.flowId}>
                    {flow.name}
                  </option>
                ))}
              </select>
              <div className="mt-3 space-y-2">
                {previewSteps.map((step) => (
                  <div key={step.id} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5">
                    <p className="font-mono text-xs text-slate-700">{step.approvedTool}</p>
                    <p className="text-xs text-slate-500">{step.name}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </Card>
    </section>
  );
}

function CanvasNode({
  detail,
  icon,
  title
}: {
  detail: string;
  icon: "action" | "audit" | "connector" | "trigger";
  title: string;
}) {
  const Icon =
    icon === "trigger"
      ? CalendarClock
      : icon === "connector"
        ? DatabaseZap
        : icon === "audit"
          ? ShieldCheck
          : CheckCircle2;

  return (
    <div className="rounded-md border border-slate-300 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 break-words text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
        <Icon className="h-4 w-4 shrink-0 text-primary" />
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <GitBranch className="h-3.5 w-3.5" />
        governed edge
      </div>
    </div>
  );
}
