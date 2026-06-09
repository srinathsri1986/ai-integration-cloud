"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRightLeft,
  Calendar,
  CheckCircle2,
  CircleDot,
  ClipboardCopy,
  Hand,
  Link2,
  Loader2,
  Map,
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
  FlowDefinition,
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
  deleteMappingDefinition,
  getFlowRun,
  getMappingDefinitions,
  linkMappingToFlow,
  runFlow,
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


export function IntegrationManagementConsole({
  initialFlows,
  createdFlowId = null,
}: {
  initialFlows: ApiResult<{ items: FlowDefinition[]; total: number; limit: number; offset: number }>;
  createdFlowId?: string | null;
}) {
  const router = useRouter();
  const [flows, setFlows] = useState(initialFlows.data.items);
  const [selectedFlowId, setSelectedFlowId] = useState(
    createdFlowId ?? initialFlows.data.items[0]?.flowId
  );
  const [showCreatedBanner, setShowCreatedBanner] = useState(!!createdFlowId);
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

  const selectedFlow = flows.find((flow) => flow.flowId === selectedFlowId) ?? flows[0];
  const linkedMapping = mappings.find(
    (mapping) => mapping.mappingId === selectedFlow?.mappingDefinitionId
  );
  const filteredFlows = useMemo(
    () => (filter === "all" ? flows : flows.filter((flow) => flow.status === filter)),
    [filter, flows]
  );
  const userFlows = useMemo(
    () => filteredFlows.filter((flow) => !builtInFlowIds.has(flow.flowId)),
    [filteredFlows]
  );
  const demoFlows = useMemo(
    () => filteredFlows.filter((flow) => builtInFlowIds.has(flow.flowId)),
    [filteredFlows]
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

  async function linkMapping(flow: FlowDefinition, mappingDefinitionId: string | null) {
    setBusyKey(`${flow.flowId}:link_mapping`);
    setMessage(undefined);
    setMessageIsError(false);

    // If the chosen mapping is only "approved" (not yet published), auto-promote it
    // to "published" first. This is the most common reason linking silently fails —
    // users save a mapping but don't realise they must also publish it before linking.
    if (mappingDefinitionId) {
      const chosen = mappings.find((m) => m.mappingId === mappingDefinitionId);
      if (chosen && chosen.status === "approved") {
        const promoteResponse = await transitionMappingLifecycle(mappingDefinitionId, "publish");
        if (promoteResponse.ok) {
          // Keep local state in sync so the badge updates immediately
          setMappings((current) =>
            current.map((item) =>
              item.mappingId === promoteResponse.data.mapping.mappingId
                ? promoteResponse.data.mapping
                : item
            )
          );
        } else {
          setMessage(promoteResponse.error ?? "Could not publish mapping before linking.");
          setMessageIsError(true);
          setBusyKey(undefined);
          return;
        }
      }
    }

    const response = await linkMappingToFlow(flow.flowId, mappingDefinitionId);
    if (response.ok) {
      setFlows((current) =>
        current.map((item) => (item.flowId === response.data.flowId ? response.data : item))
      );
      const label = mappingDefinitionId ? `Mapping linked to "${flow.name}".` : `Mapping detached from "${flow.name}".`;
      setMessage(label);
      setMessageIsError(false);
    } else {
      setMessage(response.error ?? "Unable to link mapping.");
      setMessageIsError(true);
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
      {/* Delete confirmation modal */}
      {deleteModalFlow && (
        <DeleteFlowModal
          flow={deleteModalFlow}
          open={deleteModalFlow !== null}
          onClose={() => setDeleteModalFlow(null)}
          onDeleted={handleFlowDeleted}
        />
      )}

      {/* AI Builder success banner */}
      {showCreatedBanner && createdFlowId && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-teal-200 bg-teal-50 px-5 py-3">
          <div className="flex items-center gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-teal-500">
              <svg className="h-3.5 w-3.5 text-white" viewBox="0 0 16 16" fill="none">
                <path d="M3 8l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </span>
            <div>
              <p className="text-sm font-semibold text-teal-900">
                Flow draft saved by AI Builder
              </p>
              <p className="text-[12px] text-teal-700">
                <span className="font-mono">{createdFlowId}</span> is saved as a draft — submit for approval when ready to publish.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowCreatedBanner(false)}
            className="shrink-0 rounded-md p-1 text-teal-500 hover:bg-teal-100 hover:text-teal-700"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
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

            {/* User-created integrations */}
            <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
              <div className="grid min-w-[920px] grid-cols-[1.3fr_110px_110px_120px_150px] bg-slate-50 px-4 py-3 text-xs font-semibold uppercase text-muted-foreground">
                <span>Integration</span>
                <span>Status</span>
                <span>Run</span>
                <span>Mapping</span>
                <span>Actions</span>
              </div>
              {userFlows.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-10 text-center text-sm text-muted-foreground">
                  <Workflow className="h-8 w-8 text-slate-300" />
                  <p className="font-medium text-slate-700">No integrations yet</p>
                  <p className="max-w-xs text-xs">
                    Use the wizard to configure connectors, approved actions, and triggers for each
                    integration you need.
                  </p>
                  <Button onClick={() => router.push("/flows/new")} type="button">
                    <Plus className="h-4 w-4" />
                    Create your first integration
                  </Button>
                </div>
              ) : (
                userFlows.map((flow) => (
                  <FlowRow
                    flow={flow}
                    isSelected={selectedFlow?.flowId === flow.flowId}
                    isBuiltIn={false}
                    busyKey={busyKey}
                    key={flow.flowId}
                    onSelect={setSelectedFlowId}
                    onDelete={deleteFlow}
                  />
                ))
              )}
            </div>

            {/* Built-in demo integrations — collapsible */}
            <details className="group mt-4" open={userFlows.length === 0}>
              <summary className="flex cursor-pointer select-none items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-slate-100">
                <span className="flex-1">
                  Demo integrations
                  <span className="ml-2 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs">
                    {demoFlows.length}
                  </span>
                </span>
                <span className="text-xs text-slate-400 group-open:hidden">Show</span>
                <span className="hidden text-xs text-slate-400 group-open:inline">Hide</span>
              </summary>
              <div className="mt-2 overflow-x-auto rounded-xl border border-slate-200">
                <div className="grid min-w-[920px] grid-cols-[1.3fr_110px_110px_120px_150px] bg-slate-50 px-4 py-2 text-xs font-semibold uppercase text-muted-foreground">
                  <span>Demo Integration</span>
                  <span>Status</span>
                  <span>Run</span>
                  <span>Mapping</span>
                  <span>Actions</span>
                </div>
                {demoFlows.map((flow) => (
                  <FlowRow
                    flow={flow}
                    isSelected={selectedFlow?.flowId === flow.flowId}
                    isBuiltIn
                    busyKey={busyKey}
                    key={flow.flowId}
                    onSelect={setSelectedFlowId}
                    onDelete={deleteFlow}
                  />
                ))}
              </div>
            </details>
          </Card>
        </div>

        <IntegrationReviewPane
          busyKey={busyKey}
          flow={selectedFlow}
          linkedMapping={linkedMapping}
          mappingSimulation={mappingSimulation}
          publishedMappings={mappings.filter((m) => m.status === "published" || m.status === "approved")}
          onDeleteFlow={deleteFlow}
          onDeleteMapping={deleteMapping}
          onFlowAction={applyFlowAction}
          onLinkMapping={linkMapping}
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

function FlowRow({
  flow,
  isSelected,
  isBuiltIn,
  busyKey,
  onSelect,
  onDelete
}: {
  flow: FlowDefinition;
  isSelected: boolean;
  isBuiltIn: boolean;
  busyKey?: string;
  onSelect: (id: string) => void;
  onDelete: (flow: FlowDefinition) => void;
}) {
  return (
    <div
      className={`grid min-w-[920px] w-full grid-cols-[1.3fr_110px_110px_120px_150px] items-center gap-3 border-t border-slate-200 px-4 py-4 text-left transition hover:bg-slate-50 cursor-pointer ${
        isSelected ? "bg-sky-50/60" : "bg-white"
      }`}
      key={flow.flowId}
      onClick={() => onSelect(flow.flowId)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(flow.flowId)}
      role="button"
      tabIndex={0}
    >
      <span>
        <span className="flex items-center gap-2">
          <span className="block text-sm font-semibold text-slate-950">{flow.name}</span>
          <TriggerBadge triggerType={flow.triggerType} cronValue={flow.triggerCron} />
          {isBuiltIn && (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
              demo
            </span>
          )}
        </span>
        <span className="mt-1 flex items-center gap-1 text-xs leading-5 text-muted-foreground">
          <span className="capitalize">{flow.sourceConnector}</span>
          {flow.targetModule && flow.targetModule !== flow.sourceConnector && (
            <>
              <ArrowRightLeft className="h-3 w-3 shrink-0 text-muted-foreground/60" />
              <span className="capitalize">{flow.targetModule.replace(/_/g, " ")}</span>
            </>
          )}
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
          disabled={isBuiltIn || busyKey === `${flow.flowId}:delete`}
          onClick={(event) => {
            event.stopPropagation();
            onDelete(flow);
          }}
          title={isBuiltIn ? "Built-in demo integrations are protected" : "Delete integration"}
          type="button"
          variant="secondary"
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </Button>
      </span>
    </div>
  );
}

function IntegrationReviewPane({
  busyKey,
  flow,
  linkedMapping,
  mappingSimulation,
  publishedMappings,
  onDeleteFlow,
  onDeleteMapping,
  onFlowAction,
  onLinkMapping,
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
  publishedMappings: MappingDefinition[];
  onDeleteFlow: (flow: FlowDefinition) => void;
  onDeleteMapping: (mapping: MappingDefinition) => void;
  onFlowAction: (flow: FlowDefinition, action: FlowLifecycleAction) => void;
  onLinkMapping: (flow: FlowDefinition, mappingDefinitionId: string | null) => void;
  onMappingAction: (mapping: MappingDefinition, action: MappingLifecycleAction) => void;
  onRefreshMappings: () => void;
  onRun: (flow: FlowDefinition) => void;
  onSimulateMapping: (mapping: MappingDefinition) => void;
  run?: FlowRunResponse;
}) {
  const [selectedMappingId, setSelectedMappingId] = useState<string>("");
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
          <div className="mt-4 space-y-3">
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-muted-foreground">
              No data mapping is linked to this integration.
            </div>

            {/* Link an existing mapping (published or approved) -------------------------------- */}
            {publishedMappings.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-600">
                  Link a mapping:
                </p>
                <div className="flex gap-2">
                  <select
                    className="flex-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={selectedMappingId}
                    onChange={(e) => setSelectedMappingId(e.target.value)}
                  >
                    <option value="">— choose a mapping —</option>
                    {publishedMappings.map((m) => (
                      <option key={m.mappingId} value={m.mappingId}>
                        {m.name}{m.status === "approved" ? " (will be published on link)" : ""}
                      </option>
                    ))}
                  </select>
                  <Button
                    disabled={!selectedMappingId || busyKey === `${flow.flowId}:link_mapping`}
                    onClick={() => {
                      if (selectedMappingId) onLinkMapping(flow, selectedMappingId);
                    }}
                    type="button"
                  >
                    {busyKey === `${flow.flowId}:link_mapping` ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Link2 className="h-4 w-4" />
                    )}
                    Link
                  </Button>
                </div>
              </div>
            ) : null}

            <Link
              className="flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-800 transition hover:bg-sky-100"
              href="/mapping"
            >
              <Map className="h-4 w-4 shrink-0" />
              Create a new data mapping →
            </Link>
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

