"use client";

/**
 * FieldMapper — R18a
 *
 * Visual column-to-column mapping UI for the flow creation wizard.
 *
 * Left panel:  source fields (from pre-built connector schema or custom endpoint)
 * Right panel: target fields (same)
 * Middle:      current mapping rows with transform selector and remove button
 *
 * Features:
 * - Add mapping by selecting source field + target field from dropdowns
 * - Per-mapping transform selector (direct / uppercase / lowercase / to_string / to_number / format_date)
 * - Auto-suggest by name similarity (levenshtein-light)
 * - Remove individual mapping
 * - Visual field badges showing type
 * - "No schema yet" state with a nudge to discover fields
 *
 * Props:
 *   sourceFields   — discovered FieldInfo[] for the source
 *   targetFields   — discovered FieldInfo[] for the target
 *   initialMappings — pre-seeded mappings (editing flow)
 *   onChange       — called whenever mappings change
 */

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Plus, RotateCcw, Trash2, Wand2 } from "lucide-react";
import type { FieldInfo, InlineFieldMapping } from "@ai-integration-cloud/shared";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MappingTransform =
  | "direct"
  | "uppercase"
  | "lowercase"
  | "to_string"
  | "to_number"
  | "format_date";

const TRANSFORMS: { value: MappingTransform; label: string }[] = [
  { value: "direct",      label: "Direct copy"    },
  { value: "uppercase",   label: "Uppercase"      },
  { value: "lowercase",   label: "Lowercase"      },
  { value: "to_string",   label: "→ String"       },
  { value: "to_number",   label: "→ Number"       },
  { value: "format_date", label: "Format date"    },
];

const TYPE_COLORS: Record<string, string> = {
  string:  "bg-sky-100 text-sky-700",
  number:  "bg-violet-100 text-violet-700",
  boolean: "bg-amber-100 text-amber-700",
  date:    "bg-emerald-100 text-emerald-700",
  object:  "bg-slate-100 text-slate-600",
  array:   "bg-orange-100 text-orange-700",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function similarity(a: string, b: string): number {
  // Simple Jaccard similarity on character trigrams — fast, no library needed
  const trigrams = (s: string) => {
    const t = new Set<string>();
    const n = s.toLowerCase().replace(/[^a-z0-9]/g, "");
    for (let i = 0; i < n.length - 2; i++) t.add(n.slice(i, i + 3));
    return t;
  };
  const ta = trigrams(a);
  const tb = trigrams(b);
  const inter = [...ta].filter((x) => tb.has(x)).length;
  const union = new Set([...ta, ...tb]).size;
  return union === 0 ? 0 : inter / union;
}

function autoSuggest(sources: FieldInfo[], targets: FieldInfo[]): InlineFieldMapping[] {
  const suggestions: InlineFieldMapping[] = [];
  const usedTargets = new Set<string>();
  for (const src of sources) {
    let best: FieldInfo | null = null;
    let bestScore = 0;
    for (const tgt of targets) {
      if (usedTargets.has(tgt.name)) continue;
      const score = similarity(src.name, tgt.name);
      if (score > bestScore && score > 0.4) {
        bestScore = score;
        best = tgt;
      }
    }
    if (best) {
      usedTargets.add(best.name);
      suggestions.push({
        sourceField: src.name,
        targetField: best.name,
        transform: "direct",
        sourceType: src.type,
        targetType: best.type,
      });
    }
  }
  return suggestions;
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

function FieldBadge({ field }: { field: FieldInfo }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[field.type] ?? "bg-slate-100 text-slate-600"}`}>
      {field.label || field.name.split(".").pop()}
      <span className="opacity-60 text-[10px]">{field.type}</span>
    </span>
  );
}

function FieldSelect({
  fields,
  value,
  onChange,
  placeholder,
}: {
  fields: FieldInfo[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="flex-1 min-w-0 px-2 py-1.5 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-400 text-slate-700"
    >
      <option value="">{placeholder}</option>
      {fields.map((f) => (
        <option key={f.name} value={f.name}>
          {f.label || f.name} ({f.type})
        </option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface FieldMapperProps {
  sourceFields: FieldInfo[];
  targetFields: FieldInfo[];
  initialMappings?: InlineFieldMapping[];
  onChange?: (mappings: InlineFieldMapping[]) => void;
  sourceLabel?: string;
  targetLabel?: string;
}

export function FieldMapper({
  sourceFields,
  targetFields,
  initialMappings = [],
  onChange,
  sourceLabel = "Source",
  targetLabel = "Target",
}: FieldMapperProps) {
  const [mappings, setMappings] = useState<InlineFieldMapping[]>(initialMappings);
  const [newSrc, setNewSrc] = useState("");
  const [newTgt, setNewTgt] = useState("");
  const [newTransform, setNewTransform] = useState<MappingTransform>("direct");

  // Notify parent whenever mappings change
  useEffect(() => {
    onChange?.(mappings);
  }, [mappings]); // eslint-disable-line react-hooks/exhaustive-deps

  function addMapping() {
    if (!newSrc || !newTgt) return;
    const srcField = sourceFields.find((f) => f.name === newSrc);
    const tgtField = targetFields.find((f) => f.name === newTgt);
    const next: InlineFieldMapping = {
      sourceField: newSrc,
      targetField: newTgt,
      transform: newTransform,
      sourceType: srcField?.type ?? "string",
      targetType: tgtField?.type ?? "string",
    };
    setMappings((prev) => [...prev, next]);
    setNewSrc("");
    setNewTgt("");
    setNewTransform("direct");
  }

  function removeMapping(idx: number) {
    setMappings((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateTransform(idx: number, transform: MappingTransform) {
    setMappings((prev) =>
      prev.map((m, i) => (i === idx ? { ...m, transform } : m))
    );
  }

  function handleAutoSuggest() {
    const suggested = autoSuggest(sourceFields, targetFields);
    if (suggested.length === 0) return;
    // Merge with existing — don't overwrite already-mapped source fields
    const usedSources = new Set(mappings.map((m) => m.sourceField));
    const toAdd = suggested.filter((s) => !usedSources.has(s.sourceField));
    setMappings((prev) => [...prev, ...toAdd]);
  }

  const hasFields = sourceFields.length > 0 && targetFields.length > 0;
  const canAdd = newSrc.length > 0 && newTgt.length > 0;

  const sourceFieldMap = useMemo(
    () => Object.fromEntries(sourceFields.map((f) => [f.name, f])),
    [sourceFields]
  );
  const targetFieldMap = useMemo(
    () => Object.fromEntries(targetFields.map((f) => [f.name, f])),
    [targetFields]
  );

  if (!hasFields) {
    return (
      <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center">
        <p className="text-sm text-slate-500 font-medium">
          {sourceFields.length === 0 && targetFields.length === 0
            ? "Discover fields for both source and target to enable mapping."
            : sourceFields.length === 0
            ? "Source fields not yet discovered — click "Discover fields" above."
            : "Target fields not yet discovered — click "Discover fields" above."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">
          {mappings.length} field mapping{mappings.length !== 1 ? "s" : ""}
        </p>
        <button
          type="button"
          onClick={handleAutoSuggest}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-sky-200 bg-sky-50 text-sky-700 text-xs font-medium hover:bg-sky-100 transition-colors"
        >
          <Wand2 className="h-3.5 w-3.5" />
          Auto-suggest
        </button>
      </div>

      {/* Existing mapping rows */}
      {mappings.length > 0 && (
        <div className="rounded-xl border border-slate-200 overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_1fr_auto_auto] gap-0 text-xs font-semibold text-slate-500 bg-slate-50 px-3 py-2 border-b border-slate-200">
            <span>{sourceLabel} field</span>
            <span />
            <span>{targetLabel} field</span>
            <span className="px-2">Transform</span>
            <span />
          </div>
          {mappings.map((m, idx) => {
            const srcField = sourceFieldMap[m.sourceField];
            const tgtField = targetFieldMap[m.targetField];
            return (
              <div
                key={`${m.sourceField}-${m.targetField}-${idx}`}
                className="grid grid-cols-[1fr_auto_1fr_auto_auto] items-center gap-2 px-3 py-2.5 border-b border-slate-100 last:border-0 hover:bg-slate-50/60"
              >
                {/* Source */}
                <div className="min-w-0">
                  {srcField ? (
                    <FieldBadge field={srcField} />
                  ) : (
                    <span className="text-xs text-rose-600 font-mono">{m.sourceField}</span>
                  )}
                </div>
                {/* Arrow */}
                <ArrowRight className="h-3.5 w-3.5 text-slate-300 flex-shrink-0" />
                {/* Target */}
                <div className="min-w-0">
                  {tgtField ? (
                    <FieldBadge field={tgtField} />
                  ) : (
                    <span className="text-xs text-rose-600 font-mono">{m.targetField}</span>
                  )}
                </div>
                {/* Transform */}
                <select
                  value={m.transform}
                  onChange={(e) => updateTransform(idx, e.target.value as MappingTransform)}
                  className="text-xs border border-slate-200 rounded px-1.5 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-sky-400 text-slate-700"
                >
                  {TRANSFORMS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                {/* Remove */}
                <button
                  type="button"
                  onClick={() => removeMapping(idx)}
                  className="p-1 rounded hover:bg-rose-50 text-slate-400 hover:text-rose-500 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Add new mapping row */}
      <div className="flex items-center gap-2">
        <FieldSelect
          fields={sourceFields}
          value={newSrc}
          onChange={setNewSrc}
          placeholder={`${sourceLabel} field…`}
        />
        <ArrowRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
        <FieldSelect
          fields={targetFields}
          value={newTgt}
          onChange={setNewTgt}
          placeholder={`${targetLabel} field…`}
        />
        <select
          value={newTransform}
          onChange={(e) => setNewTransform(e.target.value as MappingTransform)}
          className="px-2 py-1.5 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-400 text-slate-700"
        >
          {TRANSFORMS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <button
          type="button"
          disabled={!canAdd}
          onClick={addMapping}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-sky-600 transition-colors flex-shrink-0"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
      </div>

      {/* Empty state hint */}
      {mappings.length === 0 && (
        <p className="text-xs text-slate-400 text-center py-2">
          No mappings yet. Pick a source field and target field above, or click Auto-suggest.
        </p>
      )}
    </div>
  );
}
