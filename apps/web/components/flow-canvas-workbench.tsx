"use client";

import { useMemo, useState } from "react";
import type { DragEvent } from "react";
import {
  CalendarClock,
  CheckCircle2,
  DatabaseZap,
  FileCheck2,
  GitBranch,
  GripVertical,
  Sparkles,
  Save,
  ShieldCheck,
  Workflow
} from "lucide-react";
import type {
  ApprovedFlowTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowSuggestionResponse,
  FlowStep
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { type ApiResult, saveFlowDefinition, suggestFlowDefinition } from "@/lib/api";

type PaletteItem = {
  description: string;
  id: string;
  label: string;
  tool: ApprovedFlowTool;
};

const palette: PaletteItem[] = [
  {
    description: "Load cash, receivables, revenue, and KPI summary.",
    id: "dashboard-summary",
    label: "CFO summary",
    tool: "cfo.dashboard_summary"
  },
  {
    description: "Compare P/L actuals against approved budget.",
    id: "pl-budget",
    label: "P/L vs budget",
    tool: "cfo.pl_vs_budget"
  },
  {
    description: "Inspect subsidiary operating performance.",
    id: "subsidiary",
    label: "Subsidiary drilldown",
    tool: "cfo.subsidiary_drilldown"
  },
  {
    description: "Summarize overdue project exposure.",
    id: "overdue",
    label: "Overdue projects",
    tool: "cfo.overdue_projects_by_account_manager"
  },
  {
    description: "Route an approved CFO question through governance.",
    id: "orchestrator",
    label: "AI query route",
    tool: "orchestrator.query"
  }
];

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
  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>({
    description: "Visual CFO orchestration draft using approved actions only.",
    flowId: "visual-cfo-orchestration",
    name: "Visual CFO orchestration",
    sourceConnector: "netsuite",
    status: "draft",
    steps: [stepFromPalette(palette[0], 0), stepFromPalette(palette[1], 1)],
    targetModule: "cfo_dashboard",
    triggerType: "manual"
  });
  const [message, setMessage] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);
  const [flowPrompt, setFlowPrompt] = useState(
    "Create a monthly CFO dashboard refresh flow from NetSuite that compares P/L vs budget, highlights overdue projects, and records a CFO summary."
  );
  const [suggestion, setSuggestion] = useState<FlowSuggestionResponse | undefined>();
  const [isSuggesting, setIsSuggesting] = useState(false);

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const tool = event.dataTransfer.getData("application/x-approved-tool") as ApprovedFlowTool;
    const item = palette.find((candidate) => candidate.tool === tool);
    if (!item) {
      return;
    }

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
        ? `${response.data.name} saved. Custom execution remains guarded until mapped.`
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
          <aside className="border-b border-border bg-slate-950 p-4 text-white lg:border-b-0 lg:border-r">
            <div className="flex items-center gap-2">
              <GripVertical className="h-4 w-4 text-sky-300" />
              <p className="text-sm font-semibold">Node palette</p>
            </div>
            <div className="mt-4 space-y-2">
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <CalendarClock className="h-4 w-4 text-sky-300" />
                <p className="mt-2 text-sm font-medium">Manual trigger</p>
                <p className="mt-1 text-xs leading-5 text-slate-300">Fixed start node</p>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <DatabaseZap className="h-4 w-4 text-sky-300" />
                <p className="mt-2 text-sm font-medium">NetSuite connector</p>
                <p className="mt-1 text-xs leading-5 text-slate-300">Approved access only</p>
              </div>
              {palette.map((item) => (
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
              ))}
            </div>
          </aside>

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
                <Badge className="bg-white">Drop approved action nodes here</Badge>
                <Badge className="bg-white">No arbitrary execution</Badge>
                <Badge className="bg-white">AI drafts stay unpublished</Badge>
              </div>
              <div className="grid gap-4 xl:grid-cols-[220px_1fr_180px]">
                <CanvasNode icon="trigger" title="Manual trigger" detail={draft.triggerType} />
                <div className="grid gap-3">
                  <CanvasNode icon="connector" title="NetSuite" detail="sandbox/mock governed connector" />
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
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    status: event.target.value as FlowDefinitionUpsertRequest["status"]
                  }))
                }
                value={draft.status}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
              </select>
              <div className="rounded-md border border-border bg-muted/50 p-3">
                <p className="text-sm font-medium">Current draft</p>
                <p className="mt-1 text-sm text-muted-foreground">{draft.steps.length} approved steps</p>
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
                  <Badge key={step.id}>{step.approvedTool}</Badge>
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
