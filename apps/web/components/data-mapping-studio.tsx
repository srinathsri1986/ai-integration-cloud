"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Archive,
  ArrowRightLeft,
  BrainCircuit,
  CheckCircle2,
  DatabaseZap,
  FileJson2,
  Link2,
  ListChecks,
  MousePointerClick,
  PlayCircle,
  Rocket,
  ShieldCheck,
  Sparkles,
  Unlink,
  XCircle
} from "lucide-react";
import type {
  MappingDefinition,
  MappingLifecycleAction,
  MappingSimulationResponse,
  MappingSuggestionItem,
  RestApiSchemaDiscoveryResponse
} from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { integrationSystems } from "@/lib/integration-catalog";
import {
  discoverRestApiSchema,
  getMappingDefinitions,
  saveMappingDefinition,
  simulateMappingDefinition,
  suggestMappingDefinition,
  transitionMappingLifecycle
} from "@/lib/api";
import {
  mappingObjects,
  mappingTransforms,
  objectsForSystem,
  samplePayload
} from "@/lib/mapping-catalog";
import type { MappingField, MappingTransform } from "@/lib/mapping-catalog";

type MappingRow = {
  id: string;
  sourceField: string;
  targetField: string;
  transform: MappingTransform;
  confidence?: number;
  rationale?: string;
};

const initialMappings: MappingRow[] = [
  {
    id: "map-customer",
    sourceField: "customer_name",
    targetField: "AccountName",
    transform: "direct"
  },
  {
    id: "map-budget",
    sourceField: "budget_amount",
    targetField: "Amount",
    transform: "direct"
  },
  {
    id: "map-date",
    sourceField: "due_date",
    targetField: "CloseDate",
    transform: "format_date"
  }
];

export function DataMappingStudio() {
  const [sourceSystemId, setSourceSystemId] = useState("netsuite");
  const [targetSystemId, setTargetSystemId] = useState("salesforce");
  const sourceObjects = objectsForSystem(sourceSystemId);
  const targetObjects = objectsForSystem(targetSystemId);
  const [sourceObjectId, setSourceObjectId] = useState("netsuite-project");
  const [targetObjectId, setTargetObjectId] = useState("salesforce-opportunity");
  const [selectedSourceField, setSelectedSourceField] = useState<string | undefined>("project_id");
  const [mappings, setMappings] = useState<MappingRow[]>(initialMappings);
  const [message, setMessage] = useState<string | undefined>();
  const [mappingPrompt, setMappingPrompt] = useState(
    "Map NetSuite project customer, budget, due date, and owner fields into Salesforce opportunity fields."
  );
  const [suggestions, setSuggestions] = useState<MappingSuggestionItem[]>([]);
  const [suggestionStatus, setSuggestionStatus] = useState<string | undefined>();
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [mappingId, setMappingId] = useState("netsuite-project-to-salesforce-opportunity");
  const [mappingName, setMappingName] = useState("NetSuite Project to Salesforce Opportunity");
  const [savedMappings, setSavedMappings] = useState<MappingDefinition[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingMappings, setIsLoadingMappings] = useState(false);
  const [simulation, setSimulation] = useState<MappingSimulationResponse | undefined>();
  const [isSimulating, setIsSimulating] = useState(false);
  const [restObjectLabel, setRestObjectLabel] = useState("Customer Event");
  const [restSampleJson, setRestSampleJson] = useState(
    JSON.stringify(
      {
        externalId: "CUST-100",
        displayName: "Acme Manufacturing",
        amount: 2500.75,
        invoiceDate: "2026-06-02",
        isActive: true
      },
      null,
      2
    )
  );
  const [discoveredSchema, setDiscoveredSchema] = useState<
    RestApiSchemaDiscoveryResponse | undefined
  >();
  const [isDiscoveringSchema, setIsDiscoveringSchema] = useState(false);
  const [schemaDiscoveryStatus, setSchemaDiscoveryStatus] = useState<string | undefined>();

  const sourceObject = useMemo(
    () => mappingObjects.find((object) => object.id === sourceObjectId) ?? sourceObjects[0],
    [sourceObjectId, sourceObjects]
  );
  const targetObject = useMemo(
    () => mappingObjects.find((object) => object.id === targetObjectId) ?? targetObjects[0],
    [targetObjectId, targetObjects]
  );
  const mappedTargetFields = new Set(mappings.map((mapping) => mapping.targetField));
  const missingRequiredTargets = targetObject.fields.filter(
    (field) => field.required && !mappedTargetFields.has(field.name)
  );

  useEffect(() => {
    loadSavedMappings();
  }, []);

  async function loadSavedMappings() {
    setIsLoadingMappings(true);
    const response = await getMappingDefinitions();
    setSavedMappings(response.data);
    setIsLoadingMappings(false);
  }

  function onSourceSystemChange(systemId: string) {
    const objects = objectsForSystem(systemId);
    setSourceSystemId(systemId);
    setSourceObjectId(objects[0]?.id ?? sourceObjectId);
    setSelectedSourceField(objects[0]?.fields[0]?.name);
    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
  }

  function onTargetSystemChange(systemId: string) {
    const objects = objectsForSystem(systemId);
    setTargetSystemId(systemId);
    setTargetObjectId(objects[0]?.id ?? targetObjectId);
    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
  }

  function mapToTarget(targetField: MappingField) {
    if (!selectedSourceField) {
      setMessage("Select a source field first, then choose the target field.");
      return;
    }

    setMappings((current) => {
      const withoutTarget = current.filter((mapping) => mapping.targetField !== targetField.name);
      return [
        ...withoutTarget,
        {
          id: `${selectedSourceField}-to-${targetField.name}`,
          sourceField: selectedSourceField,
          targetField: targetField.name,
          transform: targetField.type === "date" ? "format_date" : "direct"
        }
      ];
    });
    setMessage(`${selectedSourceField} mapped to ${targetField.name}.`);
  }

  function updateTransform(mappingId: string, transform: MappingTransform) {
    setMappings((current) =>
      current.map((mapping) => (mapping.id === mappingId ? { ...mapping, transform } : mapping))
    );
  }

  function removeMapping(mappingId: string) {
    setMappings((current) => current.filter((mapping) => mapping.id !== mappingId));
  }

  async function suggestMappings() {
    setIsSuggesting(true);
    setSuggestionStatus("Asking the governed model for field matches.");

    const response = await suggestMappingDefinition({
      prompt: mappingPrompt,
      sourceObjectId,
      targetObjectId
    });

    setSuggestions(response.data.suggestions);
    setSuggestionStatus(
      response.isFallback
        ? "Template suggestions are shown because the model path fell back safely."
        : `${response.data.suggestionProvider} suggested ${response.data.suggestions.length} reviewed draft matches.`
    );
    setIsSuggesting(false);
  }

  function acceptSuggestion(suggestion: MappingSuggestionItem) {
    setMappings((current) => {
      const withoutTarget = current.filter((mapping) => mapping.targetField !== suggestion.targetField);
      return [
        ...withoutTarget,
        {
          id: `ai-${suggestion.sourceField}-to-${suggestion.targetField}`,
          sourceField: suggestion.sourceField,
          targetField: suggestion.targetField,
          transform: suggestion.transform,
          confidence: suggestion.confidence,
          rationale: suggestion.rationale
        }
      ];
    });
    setSuggestions((current) =>
      current.filter(
        (candidate) =>
          candidate.sourceField !== suggestion.sourceField || candidate.targetField !== suggestion.targetField
      )
    );
    setMessage(`${suggestion.sourceField} accepted for ${suggestion.targetField}.`);
    setSimulation(undefined);
  }

  function rejectSuggestion(suggestion: MappingSuggestionItem) {
    setSuggestions((current) =>
      current.filter(
        (candidate) =>
          candidate.sourceField !== suggestion.sourceField || candidate.targetField !== suggestion.targetField
      )
    );
    setMessage(`${suggestion.sourceField} to ${suggestion.targetField} rejected.`);
  }

  async function saveDraft() {
    if (missingRequiredTargets.length > 0) {
      setMessage(`Map required fields first: ${missingRequiredTargets.map((field) => field.name).join(", ")}.`);
      return;
    }

    setIsSaving(true);
    const response = await saveMappingDefinition({
      description: `Maps ${sourceObject.displayName} fields into ${targetObject.displayName} fields with governed transforms.`,
      mappingId,
      mappings: mappings.map((mapping) => ({
        confidence: mapping.confidence ?? null,
        id: mapping.id,
        rationale: mapping.rationale ?? null,
        sourceField: mapping.sourceField,
        targetField: mapping.targetField,
        transform: mapping.transform
      })),
      name: mappingName,
      sourceObjectId,
      status: "draft",
      targetObjectId
    });

    setIsSaving(false);
    if (!response.ok) {
      setMessage(response.error ?? "Mapping draft could not be saved.");
      return;
    }

    setMessage(`${response.data.name} saved as a governed draft.`);
    await loadSavedMappings();
  }

  async function simulateCurrentMapping() {
    setIsSimulating(true);
    const response = await simulateMappingDefinition(mappingId);
    setSimulation(response.data);
    setIsSimulating(false);
    setMessage(
      response.ok
        ? `${response.data.mappingId} simulated with ${response.data.transformsApplied.length} transforms.`
        : response.error ?? "Mapping simulation could not be run."
    );
  }

  async function applyLifecycle(mapping: MappingDefinition, action: MappingLifecycleAction) {
    const response = await transitionMappingLifecycle(mapping.mappingId, action);
    setMessage(response.data.message);
    await loadSavedMappings();
  }

  function openSavedMapping(mapping: MappingDefinition) {
    setMappingId(mapping.mappingId);
    setMappingName(mapping.name);
    setSourceObjectId(mapping.sourceObjectId);
    setTargetObjectId(mapping.targetObjectId);
    setSourceSystemId(mappingObjects.find((object) => object.id === mapping.sourceObjectId)?.systemId ?? sourceSystemId);
    setTargetSystemId(mappingObjects.find((object) => object.id === mapping.targetObjectId)?.systemId ?? targetSystemId);
    setMappings(
      mapping.mappings.map((row) => ({
        confidence: row.confidence ?? undefined,
        id: row.id,
        rationale: row.rationale ?? undefined,
        sourceField: row.sourceField,
        targetField: row.targetField,
        transform: row.transform
      }))
    );
    setSuggestions([]);
    setSimulation(undefined);
    setMessage(`${mapping.name} opened in the mapping grid.`);
  }

  async function discoverSchema() {
    setIsDiscoveringSchema(true);
    setSchemaDiscoveryStatus(undefined);

    try {
      const parsed = JSON.parse(restSampleJson) as unknown;
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
        setSchemaDiscoveryStatus("Sample must be a single JSON object.");
        setIsDiscoveringSchema(false);
        return;
      }

      const response = await discoverRestApiSchema({
        objectLabel: restObjectLabel,
        samplePayload: parsed as Record<string, unknown>
      });

      setDiscoveredSchema(response.data);
      setSchemaDiscoveryStatus(
        response.ok
          ? `${response.data.fields.length} safe fields discovered for ${response.data.objectLabel}.`
          : response.error ?? "REST schema discovery could not be completed."
      );
    } catch {
      setSchemaDiscoveryStatus("Sample JSON is not valid.");
    } finally {
      setIsDiscoveringSchema(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-white/80 bg-slate-950 p-0 text-white shadow-xl shadow-slate-300/40">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_340px] lg:p-8">
          <div>
            <Badge className="border-white/15 bg-white/10 text-white">
              <ArrowRightLeft className="mr-1 h-3.5 w-3.5" />
              Data Mapping Studio Lite
            </Badge>
            <h2 className="mt-5 max-w-4xl text-3xl font-semibold leading-tight tracking-normal">
              Match fields visually between approved systems.
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
              Pick a source object, choose a target object, map fields, select governed
              transforms, and validate required fields before any integration can use the mapping.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/10 p-4">
            <p className="text-sm font-semibold">Guardrails</p>
            <div className="mt-4 grid gap-3 text-sm text-slate-300">
              <Guardrail label="No arbitrary code transforms" />
              <Guardrail label="No SQL or SuiteQL mapping logic" />
              <Guardrail label="Human-reviewed mappings only" />
              <Guardrail label="Ollama suggestions validated before display" />
            </div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden border-slate-200 bg-white/95 p-0 shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[1fr_380px]">
          <div className="p-5 lg:p-6">
            <div className="flex items-center gap-2">
              <Badge className="border-sky-200 bg-sky-50 text-sky-900">
                <BrainCircuit className="mr-1 h-3.5 w-3.5" />
                Natural language mapping
              </Badge>
              <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">
                Human approval required
              </Badge>
            </div>
            <label className="mt-5 block text-sm font-semibold text-slate-950" htmlFor="mapping-prompt">
              Describe the integration mapping
            </label>
            <textarea
              className="mt-2 min-h-28 w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-950 outline-none transition-colors focus:border-primary focus:bg-white"
              id="mapping-prompt"
              onChange={(event) => setMappingPrompt(event.target.value)}
              value={mappingPrompt}
            />
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm leading-6 text-muted-foreground">
                The model sees only selected object names, field metadata, allowed transforms, and this goal.
              </p>
              <Button disabled={isSuggesting || mappingPrompt.length < 10} onClick={suggestMappings} type="button">
                <Sparkles className="h-4 w-4" />
                {isSuggesting ? "Suggesting..." : "Suggest mappings"}
              </Button>
            </div>
          </div>

          <div className="border-t border-slate-200 bg-slate-950 p-5 text-white lg:border-l lg:border-t-0 lg:p-6">
            <p className="text-sm font-semibold">Suggestion queue</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Suggestions are draft matches. Accepting one adds it to the mapping grid; rejecting it removes it from this queue.
            </p>
            {suggestionStatus ? (
              <p className="mt-4 rounded-md border border-white/10 bg-white/10 px-3 py-2 text-sm text-slate-200">
                {suggestionStatus}
              </p>
            ) : null}
            <div className="mt-4 space-y-3">
              {suggestions.length > 0 ? (
                suggestions.map((suggestion) => (
                  <div
                    className="rounded-lg border border-white/10 bg-white/10 p-3"
                    key={`${suggestion.sourceField}-${suggestion.targetField}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">
                          {suggestion.sourceField} {"->"} {suggestion.targetField}
                        </p>
                        <p className="mt-1 text-xs leading-5 text-slate-300">{suggestion.rationale}</p>
                      </div>
                      <Badge className="border-white/10 bg-white text-slate-950">
                        {Math.round(suggestion.confidence * 100)}%
                      </Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Badge className="border-white/10 bg-white/10 text-white">{suggestion.transform}</Badge>
                      <button
                        className="inline-flex h-8 items-center gap-1 rounded-md bg-emerald-400 px-3 text-xs font-semibold text-slate-950 hover:bg-emerald-300"
                        onClick={() => acceptSuggestion(suggestion)}
                        type="button"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Accept
                      </button>
                      <button
                        className="inline-flex h-8 items-center gap-1 rounded-md border border-white/15 px-3 text-xs font-semibold text-white hover:bg-white/10"
                        onClick={() => rejectSuggestion(suggestion)}
                        type="button"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-white/15 p-6 text-center">
                  <Sparkles className="mx-auto h-6 w-6 text-sky-300" />
                  <p className="mt-3 text-sm font-medium">No AI suggestions queued.</p>
                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    Describe the mapping and ask the model to propose safe matches.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden border-slate-200 bg-white/95 p-0 shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[1fr_420px]">
          <div className="p-5 lg:p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-amber-200 bg-amber-50 text-amber-900">
                <FileJson2 className="mr-1 h-3.5 w-3.5" />
                REST schema discovery
              </Badge>
              <Badge className="border-slate-200 bg-white text-slate-700">Design-time only</Badge>
            </div>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Sample payload field tray</h2>
            <div className="mt-4 grid gap-3">
              <label className="text-sm font-semibold text-slate-950" htmlFor="rest-object-label">
                Object label
              </label>
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                id="rest-object-label"
                maxLength={80}
                minLength={3}
                onChange={(event) => setRestObjectLabel(event.target.value)}
                value={restObjectLabel}
              />
              <label className="text-sm font-semibold text-slate-950" htmlFor="rest-sample-json">
                Sample JSON
              </label>
              <textarea
                className="min-h-56 rounded-lg border border-slate-200 bg-slate-950 px-4 py-3 font-mono text-xs leading-6 text-slate-100 outline-none focus:border-amber-300"
                id="rest-sample-json"
                onChange={(event) => setRestSampleJson(event.target.value)}
                spellCheck={false}
                value={restSampleJson}
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm leading-6 text-muted-foreground">
                  Discovery reads pasted sample structure only. It does not call external APIs.
                </p>
                <Button
                  disabled={isDiscoveringSchema || restObjectLabel.length < 3}
                  onClick={discoverSchema}
                  type="button"
                >
                  <Sparkles className="h-4 w-4" />
                  {isDiscoveringSchema ? "Discovering..." : "Discover schema"}
                </Button>
              </div>
              {schemaDiscoveryStatus ? (
                <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950">
                  {schemaDiscoveryStatus}
                </p>
              ) : null}
            </div>
          </div>

          <div className="border-t border-slate-200 bg-slate-950 p-5 text-white lg:border-l lg:border-t-0 lg:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">Discovered fields</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Safe scalar fields appear here for mapping review.
                </p>
              </div>
              <Badge className="border-white/10 bg-white/10 text-white">
                {discoveredSchema?.executable === false ? "Not executable" : "Waiting"}
              </Badge>
            </div>

            {discoveredSchema ? (
              <div className="mt-4 space-y-3">
                <div className="rounded-lg border border-white/10 bg-white/10 p-3">
                  <p className="text-sm font-semibold">{discoveredSchema.objectLabel}</p>
                  <p className="mt-1 text-xs text-slate-400">{discoveredSchema.objectId}</p>
                </div>
                {discoveredSchema.fields.length > 0 ? (
                  discoveredSchema.fields.map((field) => (
                    <div className="rounded-lg border border-white/10 bg-white/10 p-3" key={field.name}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold">{field.label}</p>
                          <p className="mt-1 text-xs text-slate-400">{field.name}</p>
                        </div>
                        {field.required ? (
                          <Badge className="border-white/10 bg-white text-slate-950">Required</Badge>
                        ) : null}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Badge className="border-white/10 bg-white/10 text-white">{field.type}</Badge>
                        <Badge className="border-white/10 bg-white/10 text-white">
                          {String(field.sample ?? "null")}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="rounded-lg border border-dashed border-white/15 p-5 text-center text-sm text-slate-300">
                    No safe scalar fields discovered.
                  </p>
                )}

                {discoveredSchema.warnings.length > 0 ? (
                  <div className="rounded-lg border border-amber-300/30 bg-amber-300/10 p-3">
                    <p className="text-sm font-semibold text-amber-100">Warnings</p>
                    <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100">
                      {discoveredSchema.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="mt-4 rounded-lg border border-dashed border-white/15 p-8 text-center">
                <FileJson2 className="mx-auto h-7 w-7 text-amber-300" />
                <p className="mt-3 text-sm font-medium">No sample schema discovered yet.</p>
              </div>
            )}
          </div>
        </div>
      </Card>

      <Card className="border-slate-200 bg-white/95 shadow-sm">
        <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <Badge className="border-indigo-200 bg-indigo-50 text-indigo-900">
              <Archive className="mr-1 h-3.5 w-3.5" />
              Mapping definition
            </Badge>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Save a governed mapping draft</h2>
            <div className="mt-4 grid gap-3">
              <label className="text-sm font-semibold text-slate-950" htmlFor="mapping-id">
                Mapping ID
              </label>
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                id="mapping-id"
                onChange={(event) => setMappingId(event.target.value)}
                value={mappingId}
              />
              <label className="text-sm font-semibold text-slate-950" htmlFor="mapping-name">
                Display name
              </label>
              <input
                className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                id="mapping-name"
                onChange={(event) => setMappingName(event.target.value)}
                value={mappingName}
              />
              <Button disabled={isSaving || mappings.length === 0} onClick={saveDraft} type="button">
                <ListChecks className="h-4 w-4" />
                {isSaving ? "Saving..." : "Save mapping draft"}
              </Button>
              <Button
                disabled={isSimulating || !savedMappings.some((mapping) => mapping.mappingId === mappingId)}
                onClick={simulateCurrentMapping}
                type="button"
                variant="secondary"
              >
                <PlayCircle className="h-4 w-4" />
                {isSimulating ? "Simulating..." : "Simulate saved mapping"}
              </Button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-950">Saved mappings</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Drafts can be submitted, approved, and published by explicit human action.
                </p>
              </div>
              <Button className="bg-white" onClick={loadSavedMappings} type="button" variant="secondary">
                Refresh
              </Button>
            </div>
            <div className="mt-4 space-y-3">
              {isLoadingMappings ? (
                <p className="rounded-md border border-slate-200 bg-white p-4 text-sm text-muted-foreground">
                  Loading saved mappings...
                </p>
              ) : savedMappings.length > 0 ? (
                savedMappings.map((mapping) => (
                  <div className="rounded-lg border border-slate-200 bg-white p-3" key={mapping.mappingId}>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-950">{mapping.name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{mapping.mappingId}</p>
                      </div>
                      <Badge className={statusBadgeClass(mapping.status)}>{mapping.status}</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        className="inline-flex h-8 items-center rounded-md border border-border px-3 text-xs font-semibold hover:bg-muted"
                        onClick={() => openSavedMapping(mapping)}
                        type="button"
                      >
                        Open
                      </button>
                      {lifecycleActionsForStatus(mapping.status).map((action) => (
                        <button
                          className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-3 text-xs font-semibold hover:bg-muted"
                          key={action}
                          onClick={() => applyLifecycle(mapping, action)}
                          type="button"
                        >
                          {action === "publish" ? <Rocket className="h-3.5 w-3.5" /> : null}
                          {actionLabel(action)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-md border border-dashed border-slate-300 bg-white p-5 text-center text-sm text-muted-foreground">
                  No saved mapping definitions yet.
                </p>
              )}
            </div>
          </div>
        </div>
      </Card>

      {simulation ? (
        <Card className="border-slate-200 bg-white/95 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">
                <PlayCircle className="mr-1 h-3.5 w-3.5" />
                Runtime simulation
              </Badge>
              <h2 className="mt-4 text-xl font-semibold text-slate-950">Preview mapped sample output</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Simulation uses approved sample payloads only. It does not call external systems or execute arbitrary code.
              </p>
            </div>
            <Badge className={simulation.warnings.length ? "border-amber-200 bg-amber-50 text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-900"}>
              {simulation.warnings.length ? `${simulation.warnings.length} warnings` : "No warnings"}
            </Badge>
          </div>

          {simulation.warnings.length ? (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-950">Validation warnings</p>
              <ul className="mt-2 space-y-1 text-sm text-amber-900">
                {simulation.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <section className="mt-5 grid gap-4 lg:grid-cols-2">
            <SimulationPreview payload={simulation.sourcePayload} title="Source sample" />
            <SimulationPreview payload={simulation.targetPayload} title="Mapped target output" />
          </section>
        </Card>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1fr_1.1fr_1fr]">
        <FieldTray
          fields={sourceObject.fields}
          objectId={sourceObjectId}
          objects={sourceObjects}
          onFieldSelect={setSelectedSourceField}
          onObjectChange={(objectId) => {
            setSourceObjectId(objectId);
            setSelectedSourceField(mappingObjects.find((object) => object.id === objectId)?.fields[0]?.name);
            setMappings([]);
          }}
          onSystemChange={onSourceSystemChange}
          selectedField={selectedSourceField}
          systemId={sourceSystemId}
          title="Source"
        />

        <Card className="bg-white/90">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Mapping grid</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">Approved field matches</h2>
            </div>
            <Badge className={missingRequiredTargets.length ? "border-amber-200 bg-amber-50 text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-900"}>
              {missingRequiredTargets.length ? `${missingRequiredTargets.length} required missing` : "Valid"}
            </Badge>
          </div>

          <div className="mt-5 space-y-3">
            {mappings.length > 0 ? (
              mappings.map((mapping) => (
                <div
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                  key={mapping.id}
                >
                  <div className="grid items-center gap-3 lg:grid-cols-[1fr_auto_1fr_auto]">
                    <FieldPill label={mapping.sourceField} />
                    <Link2 className="mx-auto h-4 w-4 text-primary" />
                    <FieldPill label={mapping.targetField} />
                    <button
                      className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-white px-3 text-sm text-muted-foreground hover:bg-muted"
                      onClick={() => removeMapping(mapping.id)}
                      type="button"
                    >
                      <Unlink className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-3">
                    <label className="text-xs font-medium text-muted-foreground" htmlFor={`${mapping.id}-transform`}>
                      Transformation
                    </label>
                    <select
                      className="mt-1 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                      id={`${mapping.id}-transform`}
                      onChange={(event) =>
                        updateTransform(mapping.id, event.target.value as MappingTransform)
                      }
                      value={mapping.transform}
                    >
                      {mappingTransforms.map((transform) => (
                        <option key={transform.value} value={transform.value}>
                          {transform.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  {typeof mapping.confidence === "number" || mapping.rationale ? (
                    <div className="mt-3 rounded-md border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-950">
                      {typeof mapping.confidence === "number" ? (
                        <span className="font-semibold">{Math.round(mapping.confidence * 100)}% AI confidence. </span>
                      ) : null}
                      {mapping.rationale}
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
                <MousePointerClick className="mx-auto h-6 w-6 text-primary" />
                <p className="mt-3 text-sm font-medium text-slate-950">Select a source field, then click a target field.</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Mappings stay in draft until they pass validation.
                </p>
              </div>
            )}
          </div>

          <div className="mt-5 rounded-md border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Required target fields</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {targetObject.fields
                .filter((field) => field.required)
                .map((field) => (
                  <Badge
                    className={
                      mappedTargetFields.has(field.name)
                        ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                        : "border-amber-200 bg-amber-50 text-amber-900"
                    }
                    key={field.name}
                  >
                    {field.name}
                  </Badge>
                ))}
            </div>
          </div>

          {message ? (
            <p className="mt-4 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950">
              {message}
            </p>
          ) : null}

          <Button className="mt-5 w-full" onClick={saveDraft} type="button">
            <ListChecks className="h-4 w-4" />
            Save mapping draft
          </Button>
        </Card>

        <FieldTray
          fields={targetObject.fields}
          objectId={targetObjectId}
          objects={targetObjects}
          onFieldSelect={(fieldName) => {
            const field = targetObject.fields.find((candidate) => candidate.name === fieldName);
            if (field) {
              mapToTarget(field);
            }
          }}
          onObjectChange={(objectId) => {
            setTargetObjectId(objectId);
            setMappings([]);
          }}
          onSystemChange={onTargetSystemChange}
          selectedField={undefined}
          systemId={targetSystemId}
          title="Target"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <PayloadPreview fields={sourceObject.fields} title="Source sample payload" />
        <PayloadPreview fields={targetObject.fields} title="Target sample payload" />
      </section>
    </div>
  );
}

function Guardrail({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <ShieldCheck className="h-4 w-4 text-emerald-300" />
      {label}
    </div>
  );
}

function FieldTray({
  fields,
  objectId,
  objects,
  onFieldSelect,
  onObjectChange,
  onSystemChange,
  selectedField,
  systemId,
  title
}: {
  fields: MappingField[];
  objectId: string;
  objects: Array<{ displayName: string; id: string }>;
  onFieldSelect: (fieldName: string) => void;
  onObjectChange: (objectId: string) => void;
  onSystemChange: (systemId: string) => void;
  selectedField?: string;
  systemId: string;
  title: "Source" | "Target";
}) {
  return (
    <Card className="bg-white/90">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title} tray</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">Pick data fields</h2>
        </div>
        <DatabaseZap className="h-5 w-5 text-primary" />
      </div>

      <div className="mt-5 grid gap-3">
        <select
          className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
          onChange={(event) => onSystemChange(event.target.value)}
          value={systemId}
        >
          {integrationSystems
            .filter((system) => objectsForSelect(system.id).length > 0)
            .map((system) => (
              <option key={system.id} value={system.id}>
                {system.name}
              </option>
            ))}
        </select>
        <select
          className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
          onChange={(event) => onObjectChange(event.target.value)}
          value={objectId}
        >
          {objects.map((object) => (
            <option key={object.id} value={object.id}>
              {object.displayName}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-5 space-y-2">
        {fields.map((field) => (
          <button
            className={`w-full rounded-md border p-3 text-left transition-colors ${
              selectedField === field.name
                ? "border-slate-950 bg-slate-950 text-white"
                : "border-slate-200 bg-slate-50 hover:border-primary"
            }`}
            key={field.name}
            onClick={() => onFieldSelect(field.name)}
            type="button"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">{field.name}</p>
                <p className={selectedField === field.name ? "mt-1 text-xs leading-5 text-slate-300" : "mt-1 text-xs leading-5 text-muted-foreground"}>
                  {field.description}
                </p>
              </div>
              {field.required ? <Badge className="bg-white text-slate-700">Required</Badge> : null}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge className={selectedField === field.name ? "border-white/20 bg-white/10 text-white" : ""}>
                {field.type}
              </Badge>
              <Badge className={selectedField === field.name ? "border-white/20 bg-white/10 text-white" : ""}>
                {String(field.sample)}
              </Badge>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}

function objectsForSelect(systemId: string) {
  return mappingObjects.filter((object) => object.systemId === systemId);
}

function lifecycleActionsForStatus(status: MappingDefinition["status"]): MappingLifecycleAction[] {
  if (status === "draft") {
    return ["submit_for_approval"];
  }
  if (status === "pending_approval") {
    return ["approve", "reject"];
  }
  if (status === "approved") {
    return ["publish", "reject"];
  }
  if (status === "published") {
    return ["pause"];
  }
  if (status === "paused") {
    return ["submit_for_approval"];
  }

  return [];
}

function actionLabel(action: MappingLifecycleAction) {
  const labels: Record<MappingLifecycleAction, string> = {
    approve: "Approve",
    pause: "Pause",
    publish: "Publish",
    reject: "Reject",
    submit_for_approval: "Submit"
  };

  return labels[action];
}

function statusBadgeClass(status: MappingDefinition["status"]) {
  if (status === "published") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (status === "approved") {
    return "border-sky-200 bg-sky-50 text-sky-900";
  }
  if (status === "pending_approval") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  if (status === "paused") {
    return "border-slate-200 bg-slate-100 text-slate-700";
  }

  return "border-slate-200 bg-white text-slate-700";
}

function FieldPill({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-950">
      {label}
    </div>
  );
}

function PayloadPreview({ fields, title }: { fields: MappingField[]; title: string }) {
  return (
    <Card className="bg-white/90">
      <div className="flex items-center gap-2">
        <FileJson2 className="h-4 w-4 text-primary" />
        <p className="text-sm font-semibold text-slate-950">{title}</p>
      </div>
      <pre className="mt-4 max-h-72 overflow-auto rounded-md border border-border bg-slate-950 p-4 text-xs leading-6 text-slate-100">
        {JSON.stringify(samplePayload(fields), null, 2)}
      </pre>
    </Card>
  );
}

function SimulationPreview({ payload, title }: { payload: Record<string, unknown>; title: string }) {
  return (
    <Card className="bg-white">
      <div className="flex items-center gap-2">
        <FileJson2 className="h-4 w-4 text-primary" />
        <p className="text-sm font-semibold text-slate-950">{title}</p>
      </div>
      <pre className="mt-4 max-h-80 overflow-auto rounded-md border border-border bg-slate-950 p-4 text-xs leading-6 text-slate-100">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </Card>
  );
}
