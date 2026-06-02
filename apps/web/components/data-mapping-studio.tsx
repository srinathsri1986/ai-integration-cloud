"use client";

import { useMemo, useState } from "react";
import {
  ArrowRightLeft,
  CheckCircle2,
  DatabaseZap,
  FileJson2,
  Link2,
  ListChecks,
  MousePointerClick,
  ShieldCheck,
  Sparkles,
  Unlink
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { integrationSystems } from "@/lib/integration-catalog";
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

  function onSourceSystemChange(systemId: string) {
    const objects = objectsForSystem(systemId);
    setSourceSystemId(systemId);
    setSourceObjectId(objects[0]?.id ?? sourceObjectId);
    setSelectedSourceField(objects[0]?.fields[0]?.name);
    setMappings([]);
  }

  function onTargetSystemChange(systemId: string) {
    const objects = objectsForSystem(systemId);
    setTargetSystemId(systemId);
    setTargetObjectId(objects[0]?.id ?? targetObjectId);
    setMappings([]);
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

  function saveDraft() {
    if (missingRequiredTargets.length > 0) {
      setMessage(`Map required fields first: ${missingRequiredTargets.map((field) => field.name).join(", ")}.`);
      return;
    }

    setMessage("Mapping draft validated locally. Persistence and AI suggestions come next.");
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
              <Guardrail label="AI suggestions planned next" />
            </div>
          </div>
        </div>
      </Card>

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
            Validate mapping draft
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
