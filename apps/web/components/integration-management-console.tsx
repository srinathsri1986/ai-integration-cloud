"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar,
  CheckCircle2,
  CircleDot,
  ClipboardCopy,
  FilePenLine,
  Hand,
  Link2,
  Loader2,
  PauseCircle,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Webhook,
  Workflow
} from "lucide-react";
import type {
  ApprovedFlowTool,
  ConnectorDefinition,
  ConnectorTool,
  FlowDefinition,
  FlowDefinitionUpsertRequest,
  FlowLifecycleAction,
  FlowRunResponse,
  MappingDefinition,
  MappingLifecycleAction,
  MappingSimulationResponse
} from "@ai-integration-cloud/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DeleteFlowModal } from "@/components/delete-flow-modal";
import {
  type ApiResult,
  deleteFlowDefinition,
  deleteMappingDefinition,
  getConnectors,
  getConnectorTools,
  getFlowRun,
  getMappingDefinitions,
  runFlow,
  saveFlowDefinition,
  simulateMappingDefinition,
  transitionFlowLifecycle,
  transitionMappingLifecycle
} from "@/lib/api";

const builtInFlowIds = new Set([
  "demo-netsuite-cfo-dashboard",
  "demo-salesforce-opportunity-sync",
  "demo-sap-journal-post",
  "demo-oracle-financial-report",
  "demo-hcm-headcount-snapshot",
  "demo-postgres-analytics-pull",
  "demo-rest-api-webhook-relay",
  "demo-slack-alert-dispatch",
]);

type Filter = "all" | FlowDefinition["status"];

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function flowActionsForStatus(status: FlowDefinition["status"]): FlowLifecycleAction[] {
  if (status === "draft") return ["submit_for_approval"];
  if (status === "pending_approval") return ["approve", "reject"];
  if (status === "approved") return ["publish", "reject"];
  if (status === "published") return ["pause"];
  if (status === "paused") return ["unpause"];
  return ["submit_for_approval"];
}

function mappingActionsForStatus(status: MappingDefinition["status"]): MappingLifecycleAction[] {
  if (status === "draft") return ["submit_for_approval"];
  if (status === "pending_approval") return ["approve", "reject"];
  if (status === "approved") return ["publish", "reject"];
  if (status === "published") return ["pause"];
  return ["submit_for_approval"];
}

function TriggerBadge({ triggerType, cronValue }: { triggerType: string; cronValue?: string | null }) {
  if (triggerType === "schedule") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[10px] font-medium text-sky-700">
        <Calendar className="h-3 w-3" />
        {cronValue ? cronValue : "schedule"}
      </span>
    );
  }
  if (triggerType === "webhook") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-700">
        <Webhook className="h-3 w-3" />
        webhook
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-500">
      <Hand className="h-3 w-3" />
      manual
    </span>
  );
}

function statusBadgeClass(status: string) {
  if (status === "published") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (status === "approved") return "border-sky-200 bg-sky-50 text-sky-900";
  if (status === "pending_approval") return "border-amber-200 bg-amber-50 text-amber-900";
  if (status === "paused") return "border-slate-300 bg-slate-100 text-slate-800";
  return "border-violet-200 bg-violet-50 text-violet-900";
}

function emptyDraft(connectorId = "netsuite", firstTool = "cfo.dashboard_summary"): FlowDefinitionUpsertRequest {
  return {
    description: "Integration draft — configure approved actions and publish to run.",
    flowId: `${connectorId}-integration-draft`,
    mappingDefinitionId: null,
    name: `${connectorId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Integration`,
    sourceConnector: connectorId,
    status: "draft",
    steps: [
      {
        approvedTool: firstTool as ApprovedFlowTool,
        description: `Run approved action ${firstTool}.`,
        id: firstTool.replaceAll(".", "-"),
        name: firstTool
      }
    ],
    targetModule: connectorId.replace(/-/g, "_"),
    triggerCron: null,
    triggerType: "manual"
  };
}

export function IntegrationManagementConsole({
  initialFlows
}: {
  initialFlows: ApiResult<{ items: FlowDefinition[]; total: number; limit: number; offset: number }>;
}) {
  const router = useRouter();
  const [flows, setFlows] = useState(initialFlows.data.items);
  const [selectedFlowId, setSelectedFlowId] = useState(initialFlows.data.items[0]?.flowId);
  const [filter, setFilter] = useState<Filter>("all");
  const [message, setMessage] = useState<string | undefined>(
    initialFlows.isFallback ? initialFlows.error : undefined
  );
  const [messageIsError, setMessageIsError] = useState(initialFlows.isFallback);
  const [busyKey, setBusyKey] = useState<string | undefined>();
  const [lastRuns, setLastRuns] = useState<Record<string, FlowRunResponse>>({});
  const [mappings, setMappings] = useState<MappingDefinition[]>([]);
  const [deleteModalFlow, setDeleteModalFlow] = useState<FlowDefinition | null>(null);
  const [mappingSimulation, setMappingSimulation] = useState<MappingSimulationResponse | undefined>();
  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>(emptyDraft());
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>([]);
  const [draftConnectorTools, setDraftConnectorTools] = useState<ConnectorTool[]>([]);
  const [loadingTools, setLoadingTools] = useState(false);

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

  const loadToolsForConnector = useCallback(async (connectorId: string) => {
    setLoadingTools(true);
    const result = await getConnectorTools(connectorId);
    if (!result.isFallback) setDraftConnectorTools(result.data);
    setLoadingTools(false);
  }, []);

  useEffect(() => {
    refreshMappings();
    // Load connectors list and tools for the default connector
    getConnectors().then((result) => {
      if (!result.isFallback) {
        setConnectors(result.data);
        const defaultId = result.data[0]?.connectorId ?? "netsuite";
        setDraft(emptyDraft(defaultId));
        void loadToolsForConnector(defaultId);
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshMappings() {
    const response = await getMappingDefinitions();
    setMappings(response.data);
    if (!response.ok) {
      setMessage(response.error ?? "Unable to load mapping definitions.");
      setMessageIsError(true);
    }
  }

  async function saveDraft() {
    setBusyKey("save-draft");
    setMessage(undefined);
    setMessageIsError(false);
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
      setMessageIsError(false);
    } else {
      setMessage(response.error ?? "Unable to save draft integration.");
      setMessageIsError(true);
    }
    setBusyKey(undefined);
  }

  async function applyFlowAction(flow: FlowDefinition, action: FlowLifecycleAction) {
    setBusyKey(`${flow.flowId}:${action}`);
    setMessage(undefined);
    setMessageIsError(false);
    const response = await transitionFlowLifecycle(flow.flowId, action);
    if (response.ok && response.data.flow) {
      setFlows((current) =>
        current.map((item) => (item.flowId === response.data.flow.flowId ? response.data.flow : item))
      );
      setSelectedFlowId(response.data.flow.flowId);
      setMessage(response.data.message);
      setMessageIsError(false);
    } else {
      setMessage(response.error ?? "Unable to update integration.");
      setMessageIsError(true);
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
    setMessageIsError(false);
    const response = await runFlow(flow.flowId);
    if (!response.ok) {
      setMessage(response.error ?? "Unable to run integration.");
      setMessageIsError(true);
      setBusyKey(undefined);
      return;
    }

    // Poll every 3s while the async task is running.
    let detail = response.data;
    while (detail.status === "running") {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const detailResponse = await getFlowRun(response.data.requestId);
      if (detailResponse.ok) detail = detailResponse.data;
      else break;
    }

    setFlows((current) =>
      current.map((item) =>
        item.flowId === flow.flowId
          ? { ...item, lastRunAt: detail.completedAt ?? item.lastRunAt, lastRunStatus: detail.status }
          : item
      )
    );
    setMessage(detail.message);
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

  function deleteFlow(flow: FlowDefinition) {
    setDeleteModalFlow(flow);
  }

  function handleFlowDeleted(flowId: string) {
    const nextFlows = flows.filter((item) => item.flowId !== flowId);
    setFlows(nextFlows);
    setSelectedFlowId(nextFlows[0]?.flowId);
    setMessage("Integration deleted.");
    setDeleteModalFlow(null);
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
      {/* Delete confirmation modal */}
      {deleteModalFlow && (
        <DeleteFlowModal
          flow={deleteModalFlow}
          open={deleteModalFlow !== null}
          onClose={() => setDeleteModalFlow(null)}
          onDeleted={handleFlowDeleted}
        />
      )}

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
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          messageIsError
            ? "border-rose-200 bg-rose-50 text-rose-900"
            : "border-emerald-200 bg-emerald-50 text-emerald-900"
        }`}>
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
                <div
                  className={`grid min-w-[920px] w-full grid-cols-[1.3fr_110px_110px_120px_150px] items-center gap-3 border-t border-slate-200 px-4 py-4 text-left transition hover:bg-slate-50 cursor-pointer ${
                    selectedFlow?.flowId === flow.flowId ? "bg-sky-50/60" : "bg-white"
                  }`}
                  key={flow.flowId}
                  onClick={() => setSelectedFlowId(flow.flowId)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setSelectedFlowId(flow.flowId)}
                >
                  <span>
                    <span className="flex items-center gap-2">
                      <span className="block text-sm font-semibold text-slate-950">{flow.name}</span>
                      <TriggerBadge triggerType={flow.triggerType} cronValue={flow.triggerCron} />
                    </span>
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
                </div>
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
                Source connector
                <select
                  className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  value={draft.sourceConnector}
                  onChange={async (event) => {
                    const connectorId = event.target.value;
                    const result = await getConnectorTools(connectorId);
                    const firstTool = !result.isFallback && result.data[0] ? result.data[0].toolId : "orchestrator.query";
                    if (!result.isFallback) setDraftConnectorTools(result.data);
                    setDraft((current) => ({
                      ...current,
                      sourceConnector: connectorId,
                      targetModule: connectorId.replace(/-/g, "_"),
                      steps: [{
                        approvedTool: firstTool as ApprovedFlowTool,
                        description: `Run approved action ${firstTool}.`,
                        id: firstTool.replaceAll(".", "-"),
                        name: firstTool
                      }]
                    }));
                  }}
                >
                  {connectors.length === 0 ? (
                    <option value="netsuite">netsuite</option>
                  ) : connectors.map((c) => (
                    <option key={c.connectorId} value={c.connectorId}>
                      {c.name} ({c.connectorId})
                    </option>
                  ))}
                </select>
              </label>
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
                  disabled={loadingTools}
                  onChange={(event) => {
                    const tool = event.target.value as ApprovedFlowTool;
                    setDraft((current) => ({
                      ...current,
                      steps: [
                        {
                          approvedTool: tool,
                          description: `Run approved action ${tool}.`,
                          id: tool.replaceAll(".", "-"),
                          name: tool
                        }
                      ]
                    }));
                  }}
                  value={draft.steps[0]?.approvedTool}
                >
                  {loadingTools ? (
                    <option value="">Loading tools…</option>
                  ) : draftConnectorTools.length === 0 ? (
                    <option value="orchestrator.query">orchestrator.query</option>
                  ) : draftConnectorTools.map((t) => (
                    <option key={t.toolId} value={t.toolId}>
                      {t.toolId} — {t.label}
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
              <label className="text-sm font-medium text-slate-900 md:col-span-2">
                Trigger type
                <select
                  className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                  onChange={(event) => {
                    const t = event.target.value as FlowDefinitionUpsertRequest["triggerType"];
                    setDraft((current) => ({
                      ...current,
                      triggerType: t,
                      triggerCron: t === "schedule" ? (current.triggerCron ?? "0 9 * * 1") : null
                    }));
                  }}
                  value={draft.triggerType}
                >
                  <option value="manual">Manual — run on demand</option>
                  <option value="schedule">Schedule — cron</option>
                  <option value="webhook">Webhook — inbound HTTP</option>
                </select>
              </label>
              {draft.triggerType === "schedule" && (
                <div className="md:col-span-2 space-y-2">
                  <label className="text-sm font-medium text-slate-900">
                    Cron expression
                    <input
                      className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 font-mono text-sm outline-none focus:border-primary"
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, triggerCron: event.target.value || null }))
                      }
                      placeholder="0 9 * * 1"
                      type="text"
                      value={draft.triggerCron ?? ""}
                    />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { label: "Every Monday 9am", cron: "0 9 * * 1" },
                      { label: "Daily midnight", cron: "0 0 * * *" },
                      { label: "1st of month", cron: "0 0 1 * *" },
                      { label: "Hourly", cron: "0 * * * *" }
                    ].map(({ label, cron }) => (
                      <button
                        className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                        key={cron}
                        onClick={() => setDraft((current) => ({ ...current, triggerCron: cron }))}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Format: <code className="font-mono">minute hour day-of-month month day-of-week</code>
                  </p>
                </div>
              )}
              {draft.triggerType === "webhook" && (
                <p className="md:col-span-2 text-xs text-muted-foreground">
                  A webhook URL and secret will be generated when this integration is published.
                </p>
              )}
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
      <Card className="border-l-4 border-l-teal-500 bg-white shadow-card-md">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Badge className="border-teal-200 bg-teal-50 text-teal-700">Review pane</Badge>
            <h3 className="mt-4 text-xl font-bold tracking-tight text-slate-900">{flow.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-500">{flow.description}</p>
          </div>
          <Badge className={statusBadgeClass(flow.status)}>{statusLabel(flow.status)}</Badge>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
          <DarkMetric label="Source" value={flow.sourceConnector} />
          <DarkMetric label="Target" value={flow.targetModule} />
          <DarkMetric label="Trigger" value={statusLabel(flow.triggerType)} />
          <DarkMetric label="Last run" value={statusLabel(flow.lastRunStatus)} />
          {flow.triggerType === "schedule" && flow.triggerCron && (
            <div className="col-span-2 rounded-md border border-white/10 bg-white/5 px-3 py-2">
              <p className="text-xs text-slate-400 mb-1">Cron schedule</p>
              <code className="font-mono text-xs text-slate-200">{flow.triggerCron}</code>
            </div>
          )}
          {flow.triggerType === "webhook" && flow.status === "published" && (
            <WebhookUrlBlock flowId={flow.flowId} />
          )}
        </div>

        {isBuiltIn && (
          <p className="mt-4 rounded-md border border-amber-300/50 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Demo integration — runs only. Lifecycle changes and deletion are disabled.
          </p>
        )}
        <div className="mt-5 grid gap-2">
          <Button
            disabled={flow.status !== "published" || busyKey === `${flow.flowId}:run`}
            onClick={() => onRun(flow)}
            type="button"
          >
            {busyKey === `${flow.flowId}:run` ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {busyKey === `${flow.flowId}:run` ? "Running…" : "Run integration"}
          </Button>
          <div className="grid grid-cols-2 gap-2">
            {flowActionsForStatus(flow.status).map((action) => {
              const isBusy = busyKey === `${flow.flowId}:${action}`;
              return (
                <Button
                  disabled={isBuiltIn || isBusy}
                  key={action}
                  onClick={() => onFlowAction(flow, action)}
                  title={isBuiltIn ? "Demo integrations cannot be modified" : undefined}
                  type="button"
                  variant="secondary"
                >
                  {isBusy ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : null}
                  {statusLabel(action)}
                </Button>
              );
            })}
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

function WebhookUrlBlock({ flowId }: { flowId: string; webhookSecret?: string }) {
  const apiBase =
    typeof window !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
      : "http://localhost:8000";
  // HMAC-secured endpoint — secret travels in X-Hub-Signature-256 header, not the URL
  const url = `${apiBase}/api/v1/webhooks/${flowId}`;
  const [copiedId, setCopiedId] = useState<string | null>(null);

  function handleCopy() {
    void navigator.clipboard.writeText(url).then(() => {
      setCopiedId(flowId);
      setTimeout(() => setCopiedId(null), 2500);
    });
  }

  return (
    <div className="col-span-2 rounded-md border border-white/10 bg-white/5 px-3 py-2">
      <p className="text-xs text-slate-400 mb-1">Webhook URL</p>
      <div className="flex items-center gap-2">
        <code className="flex-1 truncate font-mono text-xs text-slate-200">{url}</code>
        <button
          className="shrink-0 inline-flex items-center gap-1 rounded border border-white/15 bg-white/10 px-2 py-1 text-xs hover:bg-white/20 transition-colors"
          onClick={handleCopy}
          title="Copy webhook URL"
          type="button"
        >
          {copiedId === flowId ? (
            <><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /><span className="text-emerald-400">Copied!</span></>
          ) : (
            <><ClipboardCopy className="h-3.5 w-3.5 text-slate-300" /><span className="text-slate-300">Copy</span></>
          )}
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        POST to this URL with <code className="font-mono">X-Hub-Signature-256</code> header to trigger.
      </p>
    </div>
  );
}

function DarkMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-800">{value}</p>
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
