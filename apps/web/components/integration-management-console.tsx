"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  CircleDot,
  FilePenLine,
  Link2,
  PauseCircle,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Workflow
} from "lucide-react";
import type {
  ApprovedFlowTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowLifecycleAction,
  FlowRunResponse,
  MappingDefinition,
  MappingLifecycleAction,
  MappingSimulationResponse
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  type ApiResult,
  deleteFlowDefinition,
  deleteMappingDefinition,
  getFlowRun,
  getMappingDefinitions,
  runFlow,
  saveFlowDefinition,
  simulateMappingDefinition,
  transitionFlowLifecycle,
  transitionMappingLifecycle
} from "@/lib/api";

const builtInFlowIds = new Set([
  "netsuite-cfo-dashboard-refresh",
  "netsuite-project-risk-refresh",
  "netsuite-subsidiary-drilldown-refresh"
]);

const approvedTools: ApprovedFlowTool[] = [
  "cfo.dashboard_summary",
  "cfo.pl_vs_budget",
  "cfo.yoy_comparison",
  "cfo.subsidiary_drilldown",
  "cfo.running_projects",
  "cfo.overdue_projects_by_account_manager",
  "orchestrator.query"
];

type Filter = "all" | FlowDefinition["status"];

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function flowActionsForStatus(status: FlowDefinition["status"]): FlowLifecycleAction[] {
  if (status === "draft") return ["submit_for_approval"];
  if (status === "pending_approval") return ["approve", "reject"];
  if (status === "approved") return ["publish", "reject"];
  if (status === "published") return ["pause"];
  return ["submit_for_approval"];
}

function mappingActionsForStatus(status: MappingDefinition["status"]): MappingLifecycleAction[] {
  if (status === "draft") return ["submit_for_approval"];
  if (status === "pending_approval") return ["approve", "reject"];
  if (status === "approved") return ["publish", "reject"];
  if (status === "published") return ["pause"];
  return ["submit_for_approval"];
}

function statusBadgeClass(status: string) {
  if (status === "published") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (status === "approved") return "border-sky-200 bg-sky-50 text-sky-900";
  if (status === "pending_approval") return "border-amber-200 bg-amber-50 text-amber-900";
  if (status === "paused") return "border-slate-300 bg-slate-100 text-slate-800";
  return "border-violet-200 bg-violet-50 text-violet-900";
}

function emptyDraft(): FlowDefinitionUpsertRequest {
  return {
    description: "Preview an approved integration using governed actions and an optional published mapping.",
    flowId: "customer-event-to-salesforce-opportunity",
    mappingDefinitionId: null,
    name: "Customer Event to Salesforce Opportunity",
    sourceConnector: "netsuite",
    status: "draft",
    steps: [
      {
        approvedTool: "orchestrator.query",
        description: "Route the approved business request through governed orchestration.",
        id: "governed-orchestration",
        name: "Governed orchestration"
      }
    ],
    targetModule: "salesforce_opportunity",
    triggerType: "manual"
  };
}

export function IntegrationManagementConsole({
  initialFlows
}: {
  initialFlows: ApiResult<FlowDefinition[]>;
}) {
  const router = useRouter();
  const [flows, setFlows] = useState(initialFlows.data);
  const [selectedFlowId, setSelectedFlowId] = useState(initialFlows.data[0]?.flowId);
  const [filter, setFilter] = useState<Filter>("all");
  const [message, setMessage] = useState<string | undefined>(
    initialFlows.isFallback ? initialFlows.error : undefined
  );
  const [busyKey, setBusyKey] = useState<string | undefined>();
  const [lastRuns, setLastRuns] = useState<Record<string, FlowRunResponse>>({});
  const [mappings, setMappings] = useState<MappingDefinition[]>([]);
  const [mappingSimulation, setMappingSimulation] = useState<MappingSimulationResponse | undefined>();
  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>(emptyDraft());

  const selectedFlow = flows.find((flow) => flow.flowId === selectedFlowId) ?? flows[0];
  const linkedMapping = mappings.find(
    (mapping) => mapping.mappingId === selectedFlow?.mappingDefinitionId
  );
  const publishedMappings = mappings.filter((mapping) => mapping.status === "published");
  const filteredFlows = useMemo(
    () => (filter === "all" ? flows : flows.filter((flow) => flow.status === filter)),
    [filter, flows]
  );
  const counts = useMemo(
    () =>
      flows.reduce<Record<string, number>>(
        (current, flow) => ({ ...current, [flow.status]: (current[flow.status] ?? 0) + 1 }),
        {}
      ),
    [flows]
  );

  useEffect(() => {
    refreshMappings();
  }, []);

  async function refreshMappings() {
    const response = await getMappingDefinitions();
    setMappings(response.data);
    if (!response.ok) setMessage(response.error ?? "Unable to load mapping definitions.");
  }

  async function saveDraft() {
    setBusyKey("save-draft");
    setMessage(undefined);
    const response = await saveFlowDefinition(draft);
    if (response.ok) {
      setFlows((current) => {
        const exists = current.some((flow) => flow.flowId === response.data.flowId);
        return exists
          ? current.map((flow) => (flow.flowId === response.data.flowId ? response.data : flow))
          : [response.data, ...current];
      });
      setSelectedFlowId(response.data.flowId);
      setMessage(`${response.data.name} saved as a draft integration.`);
    } else {
      setMessage(response.error ?? "Unable to save draft integration.");
    }
    setBusyKey(undefined);
  }

  async function applyFlowAction(flow: FlowDefinition, action: FlowLifecycleAction) {
    setBusyKey(`${flow.flowId}:${action}`);
    setMessage(undefined);
    const response = await transitionFlowLifecycle(flow.flowId, action);
    if (response.ok) {
      setFlows((current) =>
        current.map((item) => (item.flowId === response.data.flow.flowId ? response.data.flow : item))
      );
      setSelectedFlowId(response.data.flow.flowId);
      setMessage(response.data.message);
    } else {
      setMessage(response.error ?? "Unable to update integration.");
    }
    setBusyKey(undefined);
  }

  async function applyMappingAction(mapping: MappingDefinition, action: MappingLifecycleAction) {
    setBusyKey(`${mapping.mappingId}:${action}`);
    setMessage(undefined);
    const response = await transitionMappingLifecycle(mapping.mappingId, action);
    if (response.ok) {
      setMappings((current) =>
        current.map((item) =>
          item.mappingId === response.data.mapping.mappingId ? response.data.mapping : item
        )
      );
      setMessage(response.data.message);
    } else {
      setMessage(response.error ?? "Unable to update mapping.");
    }
    setBusyKey(undefined);
  }

  async function runSelectedFlow(flow: FlowDefinition) {
    setBusyKey(`${flow.flowId}:run`);
    setMessage(undefined);
    const response = await runFlow(flow.flowId);
    let detail = response.data;
    if (response.ok) {
      const detailResponse = await getFlowRun(response.data.requestId);
      if (detailResponse.ok) detail = detailResponse.data;
      setFlows((current) =>
        current.map((item) =>
          item.flowId === flow.flowId
            ? { ...item, lastRunAt: response.data.completedAt, lastRunStatus: response.data.status }
            : item
        )
      );
      setMessage(response.data.message);
    } else {
      setMessage(response.error ?? "Unable to run integration.");
    }
    setLastRuns((current) => ({ ...current, [flow.flowId]: detail }));
    setBusyKey(undefined);
  }

  async function simulateLinkedMapping(mapping: MappingDefinition) {
    setBusyKey(`${mapping.mappingId}:simulate`);
    setMessage(undefined);
    const response = await simulateMappingDefinition(mapping.mappingId);
    if (response.ok) {
      setMappingSimulation(response.data);
      setMessage(`${mapping.name} simulation completed.`);
    } else {
      setMessage(response.error ?? "Unable to simulate mapping.");
    }
    setBusyKey(undefined);
  }

  async function deleteFlow(flow: FlowDefinition) {
    const confirmed = window.confirm(`Delete ${flow.name}? This removes the saved integration.`);
    if (!confirmed) return;

    setBusyKey(`${flow.flowId}:delete`);
    setMessage(undefined);
    const response = await deleteFlowDefinition(flow.flowId);
    if (response.ok) {
      const nextFlows = flows.filter((item) => item.flowId !== flow.flowId);
      setFlows(nextFlows);
      setSelectedFlowId(nextFlows[0]?.flowId);
      setMessage(response.data.message);
    } else {
      setMessage(response.error ?? "Unable to delete integration.");
    }
    setBusyKey(undefined);
  }

  async function deleteMapping(mapping: MappingDefinition) {
    const confirmed = window.confirm(`Delete ${mapping.name}? This removes the saved mapping.`);
    if (!confirmed) return;

    setBusyKey(`${mapping.mappingId}:delete`);
    setMessage(undefined);
    const response = await deleteMappingDefinition(mapping.mappingId);
    if (response.ok) {
      setMappings((current) => current.filter((item) => item.mappingId !== mapping.mappingId));
      setMappingSimulation(undefined);
      setMessage(response.data.message);
    } else {
      setMessage(response.error ?? "Unable to delete mapping.");
    }
    setBusyKey(undefined);
  }

  return (
    <section className="space-y-6 px-6 pb-12">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
          <div>
            <Badge className="border-slate-200 bg-slate-50 text-slate-900">
              <Workflow className="mr-1 h-3.5 w-3.5" />
              Active Integrations
            </Badge>
            <h2 className="mt-4 max-w-3xl text-3xl font-semibold tracking-normal text-slate-950">
              Manage drafts, approvals, published integrations, and runtime previews in one place.
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              Every row below is backed by the API: save, review, run, lifecycle, and delete actions
              operate on persisted integration or mapping definitions.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="Published" value={counts.published ?? 0} />
            <Metric label="Drafts" value={counts.draft ?? 0} />
            <Metric label="Review" value={counts.pending_approval ?? 0} />
            <Metric label="Mappings" value={mappings.length} />
          </div>
        </div>
      </div>

      {message ? (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
          {message}
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-5">
          <Card className="bg-white">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Integration list</p>
                <h3 className="mt-1 text-xl font-semibold text-slate-950">
                  Active and draft integrations
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => router.push("/flows/new")} type="button">
                  <Plus className="h-4 w-4" />
                  New integration
                </Button>
                {(["all", "draft", "pending_approval", "approved", "published", "paused"] as Filter[]).map(
                  (item) => (
                    <Button
                      key={item}
                      onClick={() => setFilter(item)}
                      type="button"
                      variant={filter === item ? "default" : "secondary"}
                    >
                      {statusLabel(item)}
                    </Button>
                  )
                )}
              </div>
            </div>

            <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
              <div className="grid min-w-[920px] grid-cols-[1.3fr_110px_110px_120px_150px] bg-slate-50 px-4 py-3 text-xs font-semibold uppercase text-muted-foreground">
                <span>Integration</span>
                <span>Status</span>
                <span>Run</span>
                <span>Mapping</span>
                <span>Actions</span>
              </div>
              {filteredFlows.map((flow) => (
                <button
                  className={`grid min-w-[920px] w-full grid-cols-[1.3fr_110px_110px_120px_150px] items-center gap-3 border-t border-slate-200 px-4 py-4 text-left transition hover:bg-slate-50 ${
                    selectedFlow?.flowId === flow.flowId ? "bg-sky-50/60" : "bg-white"
                  }`}
                  key={flow.flowId}
                  onClick={() => setSelectedFlowId(flow.flowId)}
                  type="button"
                >
                  <span>
                    <span className="block text-sm font-semibold text-slate-950">{flow.name}</span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      {flow.sourceConnector} to {flow.targetModule}
                    </span>
                  </span>
                  <Badge className={statusBadgeClass(flow.status)}>{statusLabel(flow.status)}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {flow.lastRunStatus === "never_run" ? "Never run" : statusLabel(flow.lastRunStatus)}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {flow.mappingDefinitionId ?? "None"}
                  </span>
                  <span className="flex justify-end gap-1">
                    <Button
                      disabled={builtInFlowIds.has(flow.flowId)}
                      onClick={(event) => {
                        event.stopPropagation();
                        deleteFlow(flow);
                      }}
                      title={
                        builtInFlowIds.has(flow.flowId)
                          ? "Built-in demo integrations are protected"
                          : "Delete integration"
                      }
                      type="button"
                      variant="secondary"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  </span>
                </button>
              ))}
            </div>
          </Card>

          <Card className="bg-white">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Create draft</p>
                <h3 className="mt-1 text-xl font-semibold text-slate-950">
                  Save a new integration draft
                </h3>
              </div>
              <Badge className="border-violet-200 bg-violet-50 text-violet-900">
                <Plus className="mr-1 h-3.5 w-3.5" />
                Real save
              </Badge>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <TextInput
                label="Integration ID"
                onChange={(value) => setDraft((current) => ({ ...current, flowId: value }))}
                value={draft.flowId}
              />
              <TextInput
                label="Name"
                onChange={(value) => setDraft((current) => ({ ...current, name: value }))}
                value={draft.name}
              />
              <TextInput
                label="Target area"
                onChange={(value) => setDraft((current) => ({ ...current, targetModule: value }))}
                value={draft.targetModule}
              />
              <label className="text-sm font-medium text-slate-900">
                Published mapping
                <select
                  className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      mappingDefinitionId: event.target.value || null
                    }))
                  }
                  value={draft.mappingDefinitionId ?? ""}
                >
                  <option value="">No mapping attached</option>
                  {publishedMappings.map((mapping) => (
                    <option key={mapping.mappingId} value={mapping.mappingId}>
                      {mapping.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-900 md:col-span-2">
                Approved action
                <select
                  className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  onChange={(event) => {
                    const tool = event.target.value as ApprovedFlowTool;
                    setDraft((current) => ({
                      ...current,
                      steps: [
                        {
                          approvedTool: tool,
                          description: `Run approved action ${tool}.`,
                          id: tool.replaceAll(".", "-"),
                          name: statusLabel(tool)
                        }
                      ]
                    }));
                  }}
                  value={draft.steps[0]?.approvedTool}
                >
                  {approvedTools.map((tool) => (
                    <option key={tool} value={tool}>
                      {tool}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-900 md:col-span-2">
                Description
                <textarea
                  className="mt-2 min-h-20 w-full rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-primary"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, description: event.target.value }))
                  }
                  value={draft.description}
                />
              </label>
            </div>

            <Button className="mt-4 w-full" disabled={busyKey === "save-draft"} onClick={saveDraft} type="button">
              <FilePenLine className="h-4 w-4" />
              {busyKey === "save-draft" ? "Saving draft" : "Save draft integration"}
            </Button>
          </Card>
        </div>

        <IntegrationReviewPane
          busyKey={busyKey}
          flow={selectedFlow}
          linkedMapping={linkedMapping}
          mappingSimulation={mappingSimulation}
          onDeleteFlow={deleteFlow}
          onDeleteMapping={deleteMapping}
          onFlowAction={applyFlowAction}
          onMappingAction={applyMappingAction}
          onRefreshMappings={refreshMappings}
          onRun={runSelectedFlow}
          onSimulateMapping={simulateLinkedMapping}
          run={selectedFlow ? lastRuns[selectedFlow.flowId] : undefined}
        />
      </div>
    </section>
  );
}

function IntegrationReviewPane({
  busyKey,
  flow,
  linkedMapping,
  mappingSimulation,
  onDeleteFlow,
  onDeleteMapping,
  onFlowAction,
  onMappingAction,
  onRefreshMappings,
  onRun,
  onSimulateMapping,
  run
}: {
  busyKey?: string;
  flow?: FlowDefinition;
  linkedMapping?: MappingDefinition;
  mappingSimulation?: MappingSimulationResponse;
  onDeleteFlow: (flow: FlowDefinition) => void;
  onDeleteMapping: (mapping: MappingDefinition) => void;
  onFlowAction: (flow: FlowDefinition, action: FlowLifecycleAction) => void;
  onMappingAction: (mapping: MappingDefinition, action: MappingLifecycleAction) => void;
  onRefreshMappings: () => void;
  onRun: (flow: FlowDefinition) => void;
  onSimulateMapping: (mapping: MappingDefinition) => void;
  run?: FlowRunResponse;
}) {
  const router = useRouter();
  if (!flow) {
    return (
      <Card className="bg-white">
        <p className="text-sm text-muted-foreground">No integration selected.</p>
      </Card>
    );
  }

  const isBuiltIn = builtInFlowIds.has(flow.flowId);

  return (
    <aside className="sticky top-5 h-fit space-y-4">
      <Card className="border-slate-900 bg-slate-950 text-white shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Badge className="border-white/15 bg-white/10 text-white">Review pane</Badge>
            <h3 className="mt-4 text-2xl font-semibold tracking-normal">{flow.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{flow.description}</p>
          </div>
          <Badge className={statusBadgeClass(flow.status)}>{statusLabel(flow.status)}</Badge>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
          <DarkMetric label="Source" value={flow.sourceConnector} />
          <DarkMetric label="Target" value={flow.targetModule} />
          <DarkMetric label="Trigger" value={statusLabel(flow.triggerType)} />
          <DarkMetric label="Last run" value={statusLabel(flow.lastRunStatus)} />
        </div>

        <div className="mt-5 grid gap-2">
          <Button
            disabled={flow.status !== "published" || busyKey === `${flow.flowId}:run`}
            onClick={() => onRun(flow)}
            type="button"
          >
            <Play className="h-4 w-4" />
            {busyKey === `${flow.flowId}:run` ? "Running" : "Run integration"}
          </Button>
          <div className="grid grid-cols-2 gap-2">
            {flowActionsForStatus(flow.status).map((action) => (
              <Button
                disabled={busyKey === `${flow.flowId}:${action}`}
                key={action}
                onClick={() => onFlowAction(flow, action)}
                type="button"
                variant="secondary"
              >
                {statusLabel(action)}
              </Button>
            ))}
          </div>
          <Button
            disabled={isBuiltIn || busyKey === `${flow.flowId}:delete`}
            onClick={() => onDeleteFlow(flow)}
            title={isBuiltIn ? "Built-in demo integrations are protected" : "Delete integration"}
            type="button"
            variant="secondary"
          >
            <Trash2 className="h-4 w-4" />
            {isBuiltIn ? "Protected demo integration" : "Delete integration"}
          </Button>
        </div>
      </Card>

      <Card className="bg-white">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Linked mapping</p>
            <h3 className="mt-1 text-lg font-semibold text-slate-950">
              {linkedMapping ? linkedMapping.name : "No mapping attached"}
            </h3>
          </div>
          <Button onClick={onRefreshMappings} type="button" variant="secondary">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {linkedMapping ? (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge className={statusBadgeClass(linkedMapping.status)}>
                {statusLabel(linkedMapping.status)}
              </Badge>
              <Badge className="border-sky-200 bg-sky-50 text-sky-900">
                <Link2 className="mr-1 h-3.5 w-3.5" />
                {linkedMapping.mappings.length} fields
              </Badge>
            </div>
            <div className="space-y-2">
              {linkedMapping.mappings.slice(0, 5).map((mapping) => (
                <div
                  className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                  key={mapping.id}
                >
                  <span className="font-medium text-slate-950">{mapping.sourceField}</span>
                  <span className="text-muted-foreground">to</span>
                  <span className="font-medium text-slate-950">{mapping.targetField}</span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {mappingActionsForStatus(linkedMapping.status).map((action) => (
                <Button
                  disabled={busyKey === `${linkedMapping.mappingId}:${action}`}
                  key={action}
                  onClick={() => onMappingAction(linkedMapping, action)}
                  type="button"
                  variant="secondary"
                >
                  {statusLabel(action)}
                </Button>
              ))}
            </div>
            <Button
              className="w-full"
              disabled={busyKey === `${linkedMapping.mappingId}:simulate`}
              onClick={() => onSimulateMapping(linkedMapping)}
              type="button"
            >
              <ShieldCheck className="h-4 w-4" />
              Simulate mapping
            </Button>
            <Button
              className="w-full"
              disabled={busyKey === `${linkedMapping.mappingId}:delete`}
              onClick={() => onDeleteMapping(linkedMapping)}
              type="button"
              variant="secondary"
            >
              <Trash2 className="h-4 w-4" />
              Delete mapping
            </Button>
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-muted-foreground">
            Attach a published mapping when creating or editing an integration draft.
          </div>
        )}
      </Card>

      {run ? (
        <Card className="bg-white">
          <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Runtime preview</p>
            <h3 className="mt-1 text-lg font-semibold text-slate-950">{run.message}</h3>
          </div>
            <Badge className={statusBadgeClass(run.status)}>{statusLabel(run.status)}</Badge>
          </div>
          <div className="mt-4 space-y-2">
            {run.executionTimeline.map((step) => (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={step.id}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-950">{step.name}</p>
                  {step.status === "succeeded" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : step.status === "failed" ? (
                    <PauseCircle className="h-4 w-4 text-rose-600" />
                  ) : (
                    <CircleDot className="h-4 w-4 text-slate-500" />
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {step.approvedTool ?? "Runtime check"}
                </p>
              </div>
            ))}
          </div>
          <Button className="mt-4 w-full" onClick={() => router.push(`/flows/runs/${run.requestId}`)} type="button">
            Open run detail
          </Button>
        </Card>
      ) : null}

      {mappingSimulation ? (
        <Card className="bg-white">
          <p className="text-sm font-medium text-muted-foreground">Simulation output</p>
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
            {JSON.stringify(mappingSimulation.targetPayload, null, 2)}
          </pre>
        </Card>
      ) : null}
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function DarkMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/10 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 truncate font-semibold text-white">{value}</p>
    </div>
  );
}

function TextInput({
  label,
  onChange,
  value
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label className="text-sm font-medium text-slate-900">
      {label}
      <input
        className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}
