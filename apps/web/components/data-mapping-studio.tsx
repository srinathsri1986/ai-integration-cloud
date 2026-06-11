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
} from "@ai-integration-cloud/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { integrationSystems } from "@/lib/integration-catalog";
import {
  discoverRestApiSchema,
  getMappingDefinitions,
  promoteRestApiSchema,
  saveMappingDefinition,
  simulateMappingDefinition,
  suggestMappingDefinition,
  transitionMappingLifecycle
} from "@/lib/api";
import {
  mappingObjects,
  mappingTransforms,
  samplePayload
} from "@/lib/mapping-catalog";
import type { MappingField, MappingObject, MappingTransform } from "@/lib/mapping-catalog";
import type { ConnectorSchema } from "@/lib/api";
import { getConnectorSchema } from "@/lib/api";
import { MappingCanvas } from "@/components/mapping-canvas";
import type { CanvasMappingRow } from "@/components/mapping-canvas";

type MappingRow = {
  id: string;
  sourceField: string;
  targetField: string;
  transform: MappingTransform;
  confidence?: number;
  rationale?: string;
};

type WizardStep = "describe" | "discover" | "map" | "review";

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
  const [activeStep, setActiveStep] = useState<WizardStep>("discover");
  const [sourceSystemId, setSourceSystemId] = useState("netsuite");
  const [targetSystemId, setTargetSystemId] = useState("salesforce");
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
  const [lastSavedMappingId, setLastSavedMappingId] = useState<string | undefined>();
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
  const [discoveredSourceObject, setDiscoveredSourceObject] = useState<MappingObject | undefined>();
  const [discoveredTargetObject, setDiscoveredTargetObject] = useState<MappingObject | undefined>();
  const [promotedRestObjects, setPromotedRestObjects] = useState<MappingObject[]>([]);
  const [isPromotingSchema, setIsPromotingSchema] = useState(false);
  // R14 canvas: tracks whether the drag-and-drop canvas reports all required target fields mapped
  const [canvasAllRequiredMapped, setCanvasAllRequiredMapped] = useState(false);
  // R22a: live schema from GET /connectors/{id}/schema — replaces hardcoded catalog entries
  const [liveSchemaObjects, setLiveSchemaObjects] = useState<MappingObject[]>([]);
  // Set to true by the Ask-AI mount effect when the AI detected both source + target objects.
  // A separate useEffect watches this flag and fires suggestMappings() once state has settled.
  const [pendingAutoSuggest, setPendingAutoSuggest] = useState(false);

  const allMappingObjects = useMemo(
    () => {
      const liveIds = new Set(liveSchemaObjects.map((o) => o.id));
      return [
        ...liveSchemaObjects,
        // keep static catalog entries that have no live equivalent (e.g. rest-api, sftp-csv)
        ...mappingObjects.filter((o) => !liveIds.has(o.id)),
        ...promotedRestObjects,
        ...(discoveredSourceObject ? [discoveredSourceObject] : []),
        ...(discoveredTargetObject ? [discoveredTargetObject] : [])
      ];
    },
    [liveSchemaObjects, discoveredSourceObject, discoveredTargetObject, promotedRestObjects]
  );
  const sourceObjects = useMemo(
    () => objectsForSystemFrom(allMappingObjects, sourceSystemId),
    [allMappingObjects, sourceSystemId]
  );
  const targetObjects = useMemo(
    () => objectsForSystemFrom(allMappingObjects, targetSystemId),
    [allMappingObjects, targetSystemId]
  );

  const sourceObject = useMemo(
    () => allMappingObjects.find((object) => object.id === sourceObjectId) ?? sourceObjects[0],
    [allMappingObjects, sourceObjectId, sourceObjects]
  );
  const targetObject = useMemo(
    () => allMappingObjects.find((object) => object.id === targetObjectId) ?? targetObjects[0],
    [allMappingObjects, targetObjectId, targetObjects]
  );
  const mappedTargetFields = new Set(mappings.map((mapping) => mapping.targetField));
  const missingRequiredTargets = targetObject.fields.filter(
    (field) => field.required && !mappedTargetFields.has(field.name)
  );
  const usesSessionDiscoveredObject =
    sourceObjectId.startsWith("rest-discovered-") || targetObjectId.startsWith("rest-discovered-");
  // canReview: allow navigation to Review if there are any mappings.
  // Required-field validation is surfaced as a warning in the Review step itself
  // (on Save) so the user is never silently blocked with no explanation.
  const canReview = mappings.length > 0;
  const canSimulateCurrentMapping =
    lastSavedMappingId === mappingId || savedMappings.some((mapping) => mapping.mappingId === mappingId);

  // --- R14: canvas-driven mappings (drag-and-drop) ---
  // canvasInitialMappings: seeded from AI suggestions AND kept in sync with every canvas change so
  // that navigating away from the "map" step and back does NOT lose manually dragged mappings.
  const [canvasInitialMappings, setCanvasInitialMappings] = useState<CanvasMappingRow[]>([]);
  // canvasResetKey: increment to hard-reset the canvas (wipe all mappings + re-pick connectors).
  // Only changes when the user deliberately starts a fresh canvas; NOT on every mapping change.
  const [canvasResetKey, setCanvasResetKey] = useState(0);

  function handleCanvasChange(
    newMappings: CanvasMappingRow[],
    srcConnId: string,
    srcObjId: string,
    tgtConnId: string,
    tgtObjId: string,
    allRequiredMapped: boolean,
  ) {
    // Mirror canvas state back into studio so Review / Save steps work
    setMappings(
      newMappings.map((m) => ({
        id: m.id,
        sourceField: m.sourceField,
        targetField: m.targetField,
        transform: m.transform,
      })),
    );
    setCanvasAllRequiredMapped(allRequiredMapped);

    // Persist the full mapping list so navigating away and back restores it.
    // (canvasResetKey is NOT changed here — only explicit resets increment it)
    setCanvasInitialMappings(newMappings);

    // Convert canvas object IDs → backend catalog format
    // e.g.  "salesforce" + "Opportunity"  →  "salesforce-opportunity"
    //        "sap"        + "cost_center"  →  "sap-cost-center"
    const toCatalogId = (connId: string, objId: string) =>
      `${connId}-${objId.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;

    const newId   = `${srcConnId}-${srcObjId}--${tgtConnId}-${tgtObjId}`.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    const newName = `${srcConnId} ${srcObjId} → ${tgtConnId} ${tgtObjId}`;
    setMappingId(newId);
    setMappingName(newName);
    setSourceObjectId(toCatalogId(srcConnId, srcObjId));
    setTargetObjectId(toCatalogId(tgtConnId, tgtObjId));
    setSimulation(undefined);
    setLastSavedMappingId(undefined);
  }

  // Pick up pre-fill context injected by the Ask AI panel.
  //
  // Two-tier behaviour:
  //   • System + Object detected  → set both; will auto-trigger AI suggestions if autoSuggest=true
  //   • System only detected      → call onSourceSystemChange / onTargetSystemChange so the
  //                                  component resets to the system's first available object,
  //                                  leaving the user free to choose a different one.
  useEffect(() => {
    const stored = sessionStorage.getItem("askAI_mappingSuggestion");
    if (!stored) return;
    try {
      const hint = JSON.parse(stored) as {
        sourceSystemId?: string;
        sourceObjectId?: string | null;
        targetSystemId?: string;
        targetObjectId?: string | null;
        mappingPrompt?: string;
        autoSuggest?: boolean;
      };

      // Source side
      if (hint.sourceSystemId) {
        if (hint.sourceObjectId) {
          // Explicit object — set both directly so the exact catalog entry is selected
          setSourceSystemId(hint.sourceSystemId);
          setSourceObjectId(hint.sourceObjectId);
        } else {
          // System only — reset to that system's first object (user will pick the exact object)
          onSourceSystemChange(hint.sourceSystemId);
        }
      }

      // Target side
      if (hint.targetSystemId) {
        if (hint.targetObjectId) {
          setTargetSystemId(hint.targetSystemId);
          setTargetObjectId(hint.targetObjectId);
        } else {
          onTargetSystemChange(hint.targetSystemId);
        }
      }

      if (hint.mappingPrompt) setMappingPrompt(hint.mappingPrompt);

      // Navigate to the right wizard step regardless of prior React state:
      //   • autoSuggest=true  → suggestMappings() will call setActiveStep("map") once done
      //   • autoSuggest=false → land on "discover" so the user can choose the objects
      if (hint.autoSuggest) {
        setPendingAutoSuggest(true);
      } else {
        // Land on "describe" (step 1) so the user sees the pre-selected systems
        // and only needs to choose the specific objects before hitting Suggest.
        setActiveStep("describe");
      }

      sessionStorage.removeItem("askAI_mappingSuggestion");
    } catch {
      // Silently ignore malformed data
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // When both source + target objects were pre-filled by Ask AI, automatically
  // fire the AI field-mapping suggestion so the user sees results right away.
  useEffect(() => {
    if (!pendingAutoSuggest) return;
    setPendingAutoSuggest(false);
    suggestMappings();
  }, [pendingAutoSuggest]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadSavedMappings();
  }, []);

  // R22a: fetch live schema whenever source or target connector changes
  useEffect(() => {
    const connectorIds = Array.from(new Set([sourceSystemId, targetSystemId]));
    Promise.all(connectorIds.map((id) => getConnectorSchema(id))).then((results) => {
      const objects: MappingObject[] = results.flatMap((res) =>
        !res.error && res.data.objects.length > 0 ? connectorSchemaToMappingObjects(res.data) : []
      );
      if (objects.length > 0) {
        setLiveSchemaObjects((prev) => {
          // Merge: replace any object with the same id, keep others
          const incoming = new Map(objects.map((o) => [o.id, o]));
          const kept = prev.filter((o) => !incoming.has(o.id));
          return [...kept, ...objects];
        });
      }
    });
  }, [sourceSystemId, targetSystemId]);

  async function loadSavedMappings() {
    setIsLoadingMappings(true);
    const response = await getMappingDefinitions();
    setSavedMappings(response.data);
    setIsLoadingMappings(false);
  }

  function onSourceSystemChange(systemId: string) {
    const objects = objectsForSystemFrom(allMappingObjects, systemId);
    setSourceSystemId(systemId);
    setSourceObjectId(objects[0]?.id ?? sourceObjectId);
    setSelectedSourceField(objects[0]?.fields[0]?.name);
    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
    setLastSavedMappingId(undefined);
  }

  function onTargetSystemChange(systemId: string) {
    const objects = objectsForSystemFrom(allMappingObjects, systemId);
    setTargetSystemId(systemId);
    setTargetObjectId(objects[0]?.id ?? targetObjectId);
    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
    setLastSavedMappingId(undefined);
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

    // R22b: resolve live schema fields from the already-fetched allMappingObjects.
    // Passing real field names, types, and samples lets Qwen3 reason semantically
    // (e.g. SAP_Vendor_ID__c → vendorId) instead of guessing from catalog templates.
    const sourceObject = allMappingObjects.find((o) => o.id === sourceObjectId);
    const targetObject = allMappingObjects.find((o) => o.id === targetObjectId);

    const response = await suggestMappingDefinition({
      prompt: mappingPrompt,
      // requireLiveAi intentionally omitted (defaults false) — if the LLM is
      // unavailable or returns invalid output the service falls back to
      // field-name-similarity template suggestions instead of hard-failing.
      sourceObjectId,
      targetObjectId,
      ...(sourceObject && {
        sourceFields: sourceObject.fields.map((f) => ({
          name: f.name,
          label: f.description,
          type: f.type,
          required: f.required ?? false,
          sample: f.sample != null ? String(f.sample) : null,
        })),
      }),
      ...(targetObject && {
        targetFields: targetObject.fields.map((f) => ({
          name: f.name,
          label: f.description,
          type: f.type,
          required: f.required ?? false,
          sample: f.sample != null ? String(f.sample) : null,
        })),
      }),
    });

    if (response.ok) {
      setSuggestions(response.data.suggestions);
      if (!response.data.suggestionFallbackUsed) {
        setSuggestionStatus(
          `${response.data.suggestionProvider} / ${
            response.data.suggestionModel ?? "live model"
          } suggested ${response.data.suggestions.length} reviewed draft matches.`
        );
      } else if (response.data.suggestions.length > 0) {
        setSuggestionStatus(
          `Template suggestions (AI model unavailable) — ${response.data.suggestions.length} ` +
          `draft matches from field-name similarity. Review carefully before accepting.`
        );
      } else {
        setSuggestionStatus(
          "No automatic matches found. Map fields manually or refine the mapping prompt."
        );
      }
    } else {
      setSuggestions([]);
      setSuggestionStatus(response.error ?? "Suggestion service unavailable.");
    }
    setIsSuggesting(false);
    setActiveStep("map");
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
    // Seed into canvas — update initialMappings AND bump resetKey so canvas picks up new seeds
    setCanvasInitialMappings((current) => {
      const withoutTarget = current.filter((m) => m.targetField !== suggestion.targetField);
      return [
        ...withoutTarget,
        {
          id: `ai-${suggestion.sourceField}-to-${suggestion.targetField}`,
          sourceField: suggestion.sourceField,
          targetField: suggestion.targetField,
          transform: suggestion.transform,
        },
      ];
    });
    setCanvasResetKey((k) => k + 1); // force canvas to re-read the new initialMappings
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
    if (usesSessionDiscoveredObject) {
      setMessage(
        "Discovered REST schemas are session-scoped. Map them visually now; promote them to a governed catalog object before saving a persistent mapping."
      );
      setActiveStep("discover");
      return;
    }

    setIsSaving(true);
    // Description uses mappingName when catalog objects aren't loaded for the canvas selection.
    const description = `Maps ${mappingName} fields with governed transforms.`;
    const response = await saveMappingDefinition({
      description,
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

    setMessage(`${response.data.name} saved as a governed draft. You can now simulate it.`);
    setLastSavedMappingId(response.data.mappingId);
    setSavedMappings((current) => [
      response.data,
      ...current.filter((mapping) => mapping.mappingId !== response.data.mappingId)
    ]);
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
    setSourceSystemId(allMappingObjects.find((object) => object.id === mapping.sourceObjectId)?.systemId ?? sourceSystemId);
    setTargetSystemId(allMappingObjects.find((object) => object.id === mapping.targetObjectId)?.systemId ?? targetSystemId);
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
    setLastSavedMappingId(mapping.mappingId);
    setActiveStep("map");
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

  async function promoteDiscoveredSchema() {
    if (!discoveredSchema || discoveredSchema.fields.length === 0) {
      setSchemaDiscoveryStatus("Discover at least one safe field before promoting the schema.");
      return;
    }

    setIsPromotingSchema(true);
    const response = await promoteRestApiSchema({
      fields: discoveredSchema.fields,
      objectId: discoveredSchema.objectId,
      objectLabel: discoveredSchema.objectLabel
    });
    setIsPromotingSchema(false);

    if (!response.ok || !response.data.promoted) {
      setSchemaDiscoveryStatus(response.error ?? response.data.message);
      return;
    }

    const promotedObject = normalizeMappingObject(response.data.mappingObject);
    setPromotedRestObjects((current) => [
      ...current.filter((object) => object.id !== promotedObject.id),
      promotedObject
    ]);
    setDiscoveredSourceObject(undefined);
    setDiscoveredTargetObject(undefined);
    setSourceSystemId("rest-api");
    setSourceObjectId(promotedObject.id);
    setSelectedSourceField(promotedObject.fields[0]?.name);
    setMappingId(`${promotedObject.id}-to-${targetObject.id}`);
    setMappingName(`${promotedObject.displayName} to ${targetObject.displayName}`);
    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
    setLastSavedMappingId(undefined);
    setMessage(response.data.message);
    setSchemaDiscoveryStatus(response.data.message);
    setActiveStep("map");
  }

  function useDiscoveredSchema(role: "source" | "target") {
    if (!discoveredSchema || discoveredSchema.fields.length === 0) {
      setSchemaDiscoveryStatus("Discover at least one safe field before using the schema.");
      return;
    }

    const mappingObject = mappingObjectFromDiscoveredSchema(discoveredSchema, role);
    if (role === "source") {
      setDiscoveredSourceObject(mappingObject);
      setSourceSystemId("rest-api");
      setSourceObjectId(mappingObject.id);
      setSelectedSourceField(mappingObject.fields[0]?.name);
      setMappingPrompt(`Map ${mappingObject.displayName} fields into ${targetObject.displayName}.`);
    } else {
      setDiscoveredTargetObject(mappingObject);
      setTargetSystemId("rest-api");
      setTargetObjectId(mappingObject.id);
      setMappingPrompt(`Map ${sourceObject.displayName} fields into ${mappingObject.displayName}.`);
    }

    setMappings([]);
    setSuggestions([]);
    setSimulation(undefined);
    setLastSavedMappingId(undefined);
    setMessage(`${mappingObject.displayName} is ready in the ${role} tray.`);
    setActiveStep("map");
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

      <WizardProgress
        activeStep={activeStep}
        onStepChange={(step) => {
          setMessage(undefined);
          setActiveStep(step);
        }}
      />

      {/* Global status banner — visible on every step */}
      {message ? (
        <div className={`rounded-md border px-4 py-3 text-sm ${
          message.toLowerCase().includes("error") ||
          message.toLowerCase().includes("required") ||
          message.toLowerCase().includes("could not") ||
          message.toLowerCase().includes("cannot") ||
          message.toLowerCase().includes("failed") ||
          message.toLowerCase().includes("missing")
            ? "border-rose-200 bg-rose-50 text-rose-900"
            : "border-emerald-200 bg-emerald-50 text-emerald-900"
        }`}>
          {message}
        </div>
      ) : null}

      {activeStep === "describe" ? (
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

            {/* ── Source → Target system + object selectors ───────────────── */}
            <div className="mt-5 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[1fr_auto_1fr]">
              {/* Source */}
              <div className="grid gap-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Source</p>
                <select
                  className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
                  value={sourceSystemId}
                  onChange={(e) => onSourceSystemChange(e.target.value)}
                >
                  {integrationSystems
                    .filter((s) => objectsForSystemFrom(allMappingObjects, s.id).length > 0)
                    .map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                </select>
                <select
                  className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
                  value={sourceObjectId}
                  onChange={(e) => { setSourceObjectId(e.target.value); setMappings([]); setSuggestions([]); }}
                >
                  {sourceObjects.map((o) => (
                    <option key={o.id} value={o.id}>{o.displayName}</option>
                  ))}
                </select>
              </div>

              {/* Arrow divider */}
              <div className="flex items-center justify-center py-2 text-slate-400">
                <ArrowRightLeft className="h-4 w-4" />
              </div>

              {/* Target */}
              <div className="grid gap-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Target</p>
                <select
                  className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
                  value={targetSystemId}
                  onChange={(e) => onTargetSystemChange(e.target.value)}
                >
                  {integrationSystems
                    .filter((s) => objectsForSystemFrom(allMappingObjects, s.id).length > 0)
                    .map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                </select>
                <select
                  className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
                  value={targetObjectId}
                  onChange={(e) => { setTargetObjectId(e.target.value); setMappings([]); setSuggestions([]); }}
                >
                  {targetObjects.map((o) => (
                    <option key={o.id} value={o.id}>{o.displayName}</option>
                  ))}
                </select>
              </div>
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
      ) : null}

      {activeStep === "discover" ? (
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

                <div className="grid gap-2 sm:grid-cols-2">
                  <button
                    className="inline-flex h-10 items-center justify-center rounded-md bg-amber-300 px-3 text-sm font-semibold text-slate-950 hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={discoveredSchema.fields.length === 0}
                    onClick={() => useDiscoveredSchema("source")}
                    type="button"
                  >
                    Use as Source
                  </button>
                  <button
                    className="inline-flex h-10 items-center justify-center rounded-md border border-white/15 px-3 text-sm font-semibold text-white hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={discoveredSchema.fields.length === 0}
                    onClick={() => useDiscoveredSchema("target")}
                    type="button"
                  >
                    Use as Target
                  </button>
                </div>
                <button
                  className="inline-flex h-10 w-full items-center justify-center rounded-md bg-emerald-400 px-3 text-sm font-semibold text-slate-950 hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={discoveredSchema.fields.length === 0 || isPromotingSchema}
                  onClick={promoteDiscoveredSchema}
                  type="button"
                >
                  {isPromotingSchema ? "Promoting..." : "Promote to governed catalog"}
                </button>
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
      ) : null}

      {activeStep === "review" ? (
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
              {/* Required-field validation — shown as warning before Save */}
              {missingRequiredTargets.length > 0 && (
                <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  <ListChecks className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <span>
                    <span className="font-semibold">Missing required fields: </span>
                    {missingRequiredTargets.map((f) => f.name).join(", ")}.
                    {" "}Go back to Map and connect them before saving.
                  </span>
                </div>
              )}
              <Button disabled={isSaving || mappings.length === 0} onClick={saveDraft} type="button">
                <ListChecks className="h-4 w-4" />
                {isSaving ? "Saving..." : "Save mapping draft"}
              </Button>
              {/* Simulate is enabled only after the mapping has been saved */}
              {!canSimulateCurrentMapping && (
                <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-muted-foreground">
                  Save the mapping draft above — then simulate it.
                </p>
              )}
              <Button
                disabled={isSimulating || !canSimulateCurrentMapping}
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
      ) : null}

      {activeStep === "review" && simulation ? (
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

      {activeStep === "map" ? (
      <Card className="border-slate-200 bg-white/95 p-5 shadow-sm lg:p-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Badge className="border-teal-200 bg-teal-50 text-teal-900">
              <ArrowRightLeft className="mr-1 h-3.5 w-3.5" />
              Drag-and-drop field mapper
            </Badge>
            <h2 className="mt-3 text-xl font-semibold text-slate-950">Map fields between systems</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Drag a source field onto a target field. SVG lines show live connections.
              Accepted AI suggestions from the previous step are pre-loaded.
            </p>
          </div>
          <Button
            className="shrink-0 bg-slate-950 text-white hover:bg-slate-800"
            disabled={!canReview}
            onClick={() => setActiveStep("review")}
            type="button"
          >
            Review integration →
          </Button>
        </div>

        <MappingCanvas
          key={canvasResetKey}
          initialMappings={canvasInitialMappings}
          onMappingsChange={handleCanvasChange}
        />

        {/* Required-field hint — shown whenever required targets are not yet covered */}
        {missingRequiredTargets.length > 0 && (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <ListChecks className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <span>
              <span className="font-semibold">Required target fields not yet mapped: </span>
              {missingRequiredTargets.map((f) => f.name).join(", ")}.
              {" "}Map these before saving the definition.
            </span>
          </div>
        )}

      </Card>
      ) : null}

      {activeStep === "review" ? (
      <section className="grid gap-4 lg:grid-cols-2">
        <PayloadPreview fields={sourceObject.fields} title="Source sample payload" />
        <PayloadPreview fields={targetObject.fields} title="Target sample payload" />
      </section>
      ) : null}
    </div>
  );
}

function WizardProgress({
  activeStep,
  onStepChange
}: {
  activeStep: WizardStep;
  onStepChange: (step: WizardStep) => void;
}) {
  const steps: Array<{ id: WizardStep; label: string; summary: string }> = [
    {
      id: "describe",
      label: "Describe",
      summary: "Optional AI help"
    },
    {
      id: "discover",
      label: "Choose data",
      summary: "Discover or select fields"
    },
    {
      id: "map",
      label: "Map fields",
      summary: "Match source to target"
    },
    {
      id: "review",
      label: "Review",
      summary: "Save or simulate"
    }
  ];

  return (
    <Card className="border-slate-200 bg-white/95 p-4 shadow-sm">
      <div className="grid gap-3 md:grid-cols-4">
        {steps.map((step, index) => {
          const isActive = step.id === activeStep;
          return (
            <button
              className={`rounded-lg border p-4 text-left transition-colors ${
                isActive
                  ? "border-slate-950 bg-slate-950 text-white"
                  : "border-slate-200 bg-slate-50 text-slate-950 hover:border-primary"
              }`}
              key={step.id}
              onClick={() => onStepChange(step.id)}
              type="button"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                    isActive ? "bg-white text-slate-950" : "bg-white text-slate-700"
                  }`}
                >
                  {index + 1}
                </span>
                <span className="text-sm font-semibold">{step.label}</span>
              </div>
              <p className={isActive ? "mt-2 text-xs text-slate-300" : "mt-2 text-xs text-muted-foreground"}>
                {step.summary}
              </p>
            </button>
          );
        })}
      </div>
    </Card>
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

// ---------------------------------------------------------------------------
// R22a: Convert live ConnectorSchema → MappingObject[] for the studio trays
// ---------------------------------------------------------------------------

function connectorSchemaToMappingObjects(schema: ConnectorSchema): MappingObject[] {
  const _VALID_TYPES = new Set(["string", "number", "date", "boolean"]);
  return schema.objects.map((obj) => ({
    id: `${schema.connectorId}-${obj.objectId.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
    displayName: obj.label,
    systemId: schema.connectorId,
    fields: obj.fields.map((f) => ({
      name: f.name,
      description: f.label || f.name,
      type: (_VALID_TYPES.has(f.type) ? f.type : "string") as MappingField["type"],
      required: f.required,
      sample: f.sample ?? null,
    })),
  }));
}

function objectsForSelect(systemId: string) {
  return mappingObjects.filter((object) => object.systemId === systemId);
}

function objectsForSystemFrom(objects: MappingObject[], systemId: string) {
  return objects.filter((object) => object.systemId === systemId);
}

function mappingObjectFromDiscoveredSchema(
  schema: RestApiSchemaDiscoveryResponse,
  role: "source" | "target"
): MappingObject {
  return {
    displayName: `${schema.objectLabel} (${role})`,
    fields: schema.fields.map((field) => ({
      description: `Discovered from REST sample payload as ${field.type}.`,
      name: field.name,
      required: field.required,
      sample: field.sample ?? null,
      type: field.type
    })),
    id: `${schema.objectId}-${role}`,
    systemId: "rest-api"
  };
}

function normalizeMappingObject(object: {
  displayName: string;
  fields: Array<{
    description: string;
    name: string;
    required?: boolean;
    sample?: string | number | boolean | null;
    type: MappingField["type"];
  }>;
  id: string;
  systemId: string;
}): MappingObject {
  return {
    ...object,
    fields: object.fields.map((field) => ({
      ...field,
      sample: field.sample ?? null
    }))
  };
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
