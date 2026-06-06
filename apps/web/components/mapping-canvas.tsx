"use client";

/**
 * MappingCanvas — Release 14.0
 *
 * Two-panel drag-and-drop field mapping canvas with live SVG bezier connector lines.
 *
 * Left panel:  source connector + object → draggable field rows
 * Right panel: target connector + object → droppable field rows
 * SVG overlay: absolutely-positioned bezier curves between mapped pairs
 *
 * Uses live schema from GET /connectors/{id}/schema (R13).
 * All interaction is HTML5 native drag-and-drop; no external DnD library.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowRight,
  GripVertical,
  Link2,
  Loader2,
  Unlink,
  X,
} from "lucide-react";
import type { ConnectorDefinition } from "@ai-integration-cloud/shared";
import type { ConnectorSchema, ConnectorSchemaField } from "@/lib/api";
import { getConnectors, getConnectorSchema } from "@/lib/api";
import { mappingTransforms } from "@/lib/mapping-catalog";
import type { MappingTransform } from "@/lib/mapping-catalog";

// ---------------------------------------------------------------------------
// Exported types
// ---------------------------------------------------------------------------

export type CanvasMappingRow = {
  id: string;
  sourceField: string;
  targetField: string;
  transform: MappingTransform;
};

export interface MappingCanvasProps {
  /** Pre-seed mappings (e.g. when opening a saved definition). */
  initialMappings?: CanvasMappingRow[];
  /**
   * Called whenever the canvas mapping state changes.
   * @param allRequiredMapped - true when every required target field has ≥1 mapping
   */
  onMappingsChange?: (
    mappings: CanvasMappingRow[],
    sourceConnectorId: string,
    sourceObjectId: string,
    targetConnectorId: string,
    targetObjectId: string,
    allRequiredMapped: boolean,
  ) => void;
}

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

type SvgLine = {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

// ---------------------------------------------------------------------------
// Connector-color map (re-use the same palette as connector-catalog.tsx)
// ---------------------------------------------------------------------------

const COLORS: Record<string, { dot: string; light: string; border: string; text: string }> = {
  netsuite:   { dot: "bg-cyan-500",    light: "bg-cyan-50",    border: "border-cyan-200",   text: "text-cyan-700"   },
  salesforce: { dot: "bg-blue-500",    light: "bg-blue-50",    border: "border-blue-200",   text: "text-blue-700"   },
  sap:        { dot: "bg-violet-500",  light: "bg-violet-50",  border: "border-violet-200", text: "text-violet-700" },
  oracle:     { dot: "bg-orange-500",  light: "bg-orange-50",  border: "border-orange-200", text: "text-orange-700" },
  hcm:        { dot: "bg-green-500",   light: "bg-green-50",   border: "border-green-200",  text: "text-green-700"  },
  postgres:   { dot: "bg-indigo-500",  light: "bg-indigo-50",  border: "border-indigo-200", text: "text-indigo-700" },
  "rest-api": { dot: "bg-amber-500",   light: "bg-amber-50",   border: "border-amber-200",  text: "text-amber-700"  },
  slack:      { dot: "bg-rose-500",    light: "bg-rose-50",    border: "border-rose-200",   text: "text-rose-700"   },
};
const DEFAULT_COLOR = { dot: "bg-slate-400", light: "bg-slate-50", border: "border-slate-200", text: "text-slate-600" };

function getColor(cid: string) {
  return COLORS[cid] ?? DEFAULT_COLOR;
}

function typeColor(t: string) {
  if (t === "string")  return "bg-sky-100 text-sky-700";
  if (t === "number")  return "bg-amber-100 text-amber-700";
  if (t === "boolean") return "bg-violet-100 text-violet-700";
  if (t === "date" || t === "datetime") return "bg-teal-100 text-teal-700";
  if (t === "id")      return "bg-rose-100 text-rose-700";
  return "bg-slate-100 text-slate-500";
}

// ---------------------------------------------------------------------------
// Helper: flatten schema objects into a selector-friendly list
// ---------------------------------------------------------------------------

function schemaToObjects(schema: ConnectorSchema | null) {
  if (!schema) return [];
  return schema.objects.map((o) => ({ id: o.objectId, label: o.label }));
}

function schemaFields(schema: ConnectorSchema | null, objectId: string): ConnectorSchemaField[] {
  if (!schema) return [];
  return schema.objects.find((o) => o.objectId === objectId)?.fields ?? [];
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function MappingCanvas({ initialMappings = [], onMappingsChange }: MappingCanvasProps) {
  // Stable ref for the callback — prevents it from being a useEffect dependency
  // and causing an infinite re-render loop when the parent re-creates the function.
  const onMappingsChangeRef = useRef(onMappingsChange);
  useEffect(() => { onMappingsChangeRef.current = onMappingsChange; });

  // --- Connector / object selection ---
  const [connectors, setConnectors] = useState<ConnectorDefinition[]>([]);

  const [srcConnId, setSrcConnId]   = useState("salesforce");
  const [srcObjId,  setSrcObjId]    = useState("");
  const [srcSchema, setSrcSchema]   = useState<ConnectorSchema | null>(null);
  const [srcLoading, setSrcLoading] = useState(false);

  const [tgtConnId, setTgtConnId]   = useState("netsuite");
  const [tgtObjId,  setTgtObjId]    = useState("");
  const [tgtSchema, setTgtSchema]   = useState<ConnectorSchema | null>(null);
  const [tgtLoading, setTgtLoading] = useState(false);

  // --- Mapping state ---
  const [mappings, setMappings] = useState<CanvasMappingRow[]>(initialMappings);

  // --- DnD state ---
  const [dragging, setDragging]           = useState<string | null>(null);
  const [hoveredTarget, setHoveredTarget] = useState<string | null>(null);
  // Ref stores the field being dragged — more reliable than dataTransfer.getData()
  // which React can clear before the drop handler fires.
  const dragSourceRef = useRef<string | null>(null);

  // --- SVG lines ---
  const [svgLines, setSvgLines]   = useState<SvgLine[]>([]);
  const [scrollTick, setScrollTick] = useState(0);        // incremented on scroll to trigger re-measure

  // --- Refs for position measurement ---
  const containerRef   = useRef<HTMLDivElement>(null);
  const srcPanelRef    = useRef<HTMLDivElement>(null);
  const tgtPanelRef    = useRef<HTMLDivElement>(null);
  const srcRowRefs     = useRef<Map<string, HTMLDivElement>>(new Map());
  const tgtRowRefs     = useRef<Map<string, HTMLDivElement>>(new Map());

  // -------------------------------------------------------------------------
  // Bootstrap connector list
  // -------------------------------------------------------------------------

  useEffect(() => {
    getConnectors().then((r) => setConnectors(r.data));
  }, []);

  // -------------------------------------------------------------------------
  // Schema fetch helpers
  // -------------------------------------------------------------------------

  async function fetchSrcSchema(connId: string) {
    setSrcLoading(true);
    setSrcSchema(null);
    srcRowRefs.current.clear();
    const r = await getConnectorSchema(connId);
    setSrcSchema(r.data);
    const first = r.data.objects[0];
    setSrcObjId(first?.objectId ?? "");
    setSrcLoading(false);
  }

  async function fetchTgtSchema(connId: string) {
    setTgtLoading(true);
    setTgtSchema(null);
    tgtRowRefs.current.clear();
    const r = await getConnectorSchema(connId);
    setTgtSchema(r.data);
    const first = r.data.objects[0];
    setTgtObjId(first?.objectId ?? "");
    setTgtLoading(false);
  }

  useEffect(() => { void fetchSrcSchema(srcConnId); }, [srcConnId]);
  useEffect(() => { void fetchTgtSchema(tgtConnId); }, [tgtConnId]);

  // Clear mappings when objects change (stale field names)
  useEffect(() => { setMappings([]); }, [srcObjId, tgtObjId]);

  // -------------------------------------------------------------------------
  // Notify parent when mappings change
  // -------------------------------------------------------------------------

  useEffect(() => {
    // Use ref so this never re-triggers because the parent re-created the callback.
    // allRequiredMapped: every required target field has at least one mapping pointing to it.
    const mappedTgt = new Set(mappings.map((m) => m.targetField));
    const requiredTgt = tgtFields.filter((f) => f.required);
    const allRequiredMapped = mappings.length > 0 && requiredTgt.every((f) => mappedTgt.has(f.name));
    onMappingsChangeRef.current?.(mappings, srcConnId, srcObjId, tgtConnId, tgtObjId, allRequiredMapped);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mappings, srcConnId, srcObjId, tgtConnId, tgtObjId]);

  // -------------------------------------------------------------------------
  // SVG line computation
  // -------------------------------------------------------------------------

  const computeLines = useCallback(() => {
    if (!containerRef.current) return;
    const cr = containerRef.current.getBoundingClientRect();
    const lines: SvgLine[] = [];
    for (const m of mappings) {
      const srcEl = srcRowRefs.current.get(m.sourceField);
      const tgtEl = tgtRowRefs.current.get(m.targetField);
      if (!srcEl || !tgtEl) continue;
      const sr = srcEl.getBoundingClientRect();
      const tr = tgtEl.getBoundingClientRect();
      lines.push({
        id: m.id,
        x1: sr.right - cr.left,
        y1: (sr.top + sr.bottom) / 2 - cr.top,
        x2: tr.left - cr.left,
        y2: (tr.top + tr.bottom) / 2 - cr.top,
      });
    }
    setSvgLines(lines);
  }, [mappings]);

  // Re-compute after render & on scroll
  useLayoutEffect(() => { computeLines(); }, [computeLines, scrollTick]);

  function onPanelScroll() { setScrollTick((t) => t + 1); }

  // -------------------------------------------------------------------------
  // Drag-and-drop handlers
  // -------------------------------------------------------------------------

  function handleDragStart(e: React.DragEvent<HTMLDivElement>, fieldName: string) {
    // Store in ref — this is the reliable path.
    // dataTransfer.getData() can return "" in the drop handler because React's
    // synthetic event system clears the event object before the handler fires.
    dragSourceRef.current = fieldName;
    e.dataTransfer.setData("text/plain", fieldName); // fallback for native DnD
    e.dataTransfer.effectAllowed = "copy";
    setDragging(fieldName);
  }

  function handleDragEnd() {
    dragSourceRef.current = null;
    setDragging(null);
    setHoveredTarget(null);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>, fieldName: string) {
    // Must preventDefault to allow drop
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    if (hoveredTarget !== fieldName) setHoveredTarget(fieldName);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    // Only clear hover when truly leaving the drop zone (not just moving to a child).
    // relatedTarget is where the cursor is going; if it's inside the current target, ignore.
    const related = e.relatedTarget as Node | null;
    if (related && (e.currentTarget as HTMLElement).contains(related)) return;
    setHoveredTarget(null);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>, targetFieldName: string) {
    e.preventDefault();
    e.stopPropagation();
    // Read from ref first (React-safe), fall back to dataTransfer
    const sourceFieldName = dragSourceRef.current ?? e.dataTransfer.getData("text/plain");
    dragSourceRef.current = null;
    setDragging(null);
    setHoveredTarget(null);
    if (!sourceFieldName || sourceFieldName === targetFieldName) return;

    // Determine sensible default transform
    const srcFields  = schemaFields(srcSchema, srcObjId);
    const tgtFields  = schemaFields(tgtSchema, tgtObjId);
    const srcF = srcFields.find((f) => f.name === sourceFieldName);
    const tgtF = tgtFields.find((f) => f.name === targetFieldName);
    const transform: MappingTransform =
      tgtF?.type === "date" || tgtF?.type === "datetime" ? "format_date" : "direct";

    void srcF; // used for future inference in R18

    setMappings((prev) => {
      // Skip exact duplicate (same source → same target already mapped)
      if (prev.some((m) => m.sourceField === sourceFieldName && m.targetField === targetFieldName)) {
        return prev;
      }
      // Allow many-to-many: one source → many targets, many sources → one target
      return [
        ...prev,
        {
          id: `${sourceFieldName}--${targetFieldName}`,
          sourceField: sourceFieldName,
          targetField: targetFieldName,
          transform,
        },
      ];
    });
  }

  function removeMapping(id: string) {
    setMappings((prev) => prev.filter((m) => m.id !== id));
  }

  function updateTransform(id: string, transform: MappingTransform) {
    setMappings((prev) =>
      prev.map((m) => (m.id === id ? { ...m, transform } : m)),
    );
  }

  // -------------------------------------------------------------------------
  // Derived state
  // -------------------------------------------------------------------------

  const srcFields  = schemaFields(srcSchema, srcObjId);
  const tgtFields  = schemaFields(tgtSchema, tgtObjId);
  const srcObjects = schemaToObjects(srcSchema);
  const tgtObjects = schemaToObjects(tgtSchema);

  const mappedSrcFields = new Set(mappings.map((m) => m.sourceField));
  const mappedTgtFields = new Set(mappings.map((m) => m.targetField));

  // Cardinality: count how many times each src/tgt field appears in mappings
  const srcMappingCount = mappings.reduce<Record<string, number>>((acc, m) => {
    acc[m.sourceField] = (acc[m.sourceField] ?? 0) + 1;
    return acc;
  }, {});
  const tgtMappingCount = mappings.reduce<Record<string, number>>((acc, m) => {
    acc[m.targetField] = (acc[m.targetField] ?? 0) + 1;
    return acc;
  }, {});
  const hasOneTgtMultiSrc = Object.values(tgtMappingCount).some((c) => c > 1); // many → 1
  const hasOneSrcMultiTgt = Object.values(srcMappingCount).some((c) => c > 1); // 1 → many
  const cardinality =
    hasOneTgtMultiSrc && hasOneSrcMultiTgt
      ? "many:many"
      : hasOneTgtMultiSrc
      ? "many:1"
      : hasOneSrcMultiTgt
      ? "1:many"
      : "1:1";

  const srcColor = getColor(srcConnId);
  const tgtColor = getColor(tgtConnId);

  const requiredUnmapped = tgtFields.filter(
    (f) => f.required && !mappedTgtFields.has(f.name),
  );

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* ------------------------------------------------------------------ */}
      {/* Connector + object selectors                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 gap-4">
        {/* Source selectors */}
        <div className="flex items-center gap-2">
          <div className={`h-2.5 w-2.5 rounded-full ${srcColor.dot} shrink-0`} />
          <select
            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={srcConnId}
            onChange={(e) => {
              setSrcConnId(e.target.value);
              setMappings([]);
            }}
          >
            {connectors.map((c) => (
              <option key={c.connectorId} value={c.connectorId}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={srcObjId}
            onChange={(e) => setSrcObjId(e.target.value)}
            disabled={srcObjects.length === 0}
          >
            {srcObjects.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Target selectors */}
        <div className="flex items-center gap-2">
          <div className={`h-2.5 w-2.5 rounded-full ${tgtColor.dot} shrink-0`} />
          <select
            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={tgtConnId}
            onChange={(e) => {
              setTgtConnId(e.target.value);
              setMappings([]);
            }}
          >
            {connectors.map((c) => (
              <option key={c.connectorId} value={c.connectorId}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={tgtObjId}
            onChange={(e) => setTgtObjId(e.target.value)}
            disabled={tgtObjects.length === 0}
          >
            {tgtObjects.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Canvas — two panels + SVG overlay                                   */}
      {/* ------------------------------------------------------------------ */}
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-50"
        style={{ minHeight: "480px" }}
      >
        {/* SVG overlay — sits on top of both panels, pointer-events-none */}
        <svg
          className="pointer-events-none absolute inset-0 z-20"
          style={{ width: "100%", height: "100%" }}
          aria-hidden="true"
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L0,6 L6,3 z" fill="#0d9488" opacity="0.7" />
            </marker>
          </defs>

          {svgLines.map((line) => {
            const cx1 = line.x1 + (line.x2 - line.x1) * 0.45;
            const cx2 = line.x2 - (line.x2 - line.x1) * 0.45;
            return (
              <path
                key={line.id}
                d={`M ${line.x1} ${line.y1} C ${cx1} ${line.y1}, ${cx2} ${line.y2}, ${line.x2} ${line.y2}`}
                fill="none"
                stroke="#0d9488"
                strokeWidth="1.75"
                strokeOpacity="0.75"
                markerEnd="url(#arrowhead)"
              />
            );
          })}
        </svg>

        {/* Two-panel layout */}
        <div className="grid h-full" style={{ gridTemplateColumns: "1fr 120px 1fr" }}>
          {/* --- Source panel -------------------------------------------- */}
          <div
            ref={srcPanelRef}
            onScroll={onPanelScroll}
            className="overflow-y-auto border-r border-slate-200 bg-white"
            style={{ maxHeight: "520px" }}
          >
            <div className={`sticky top-0 z-10 border-b ${srcColor.border} ${srcColor.light} px-4 py-2.5`}>
              <p className={`text-xs font-bold uppercase tracking-wider ${srcColor.text}`}>
                Source — {srcObjId || "…"}
              </p>
              <p className="mt-0.5 text-[10px] text-slate-400">Drag a field to the right panel</p>
            </div>

            {srcLoading ? (
              <div className="flex items-center justify-center py-16 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : srcFields.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No fields — select a connector and object above.
              </div>
            ) : (
              <ul className="p-3 space-y-1">
                {srcFields.map((field) => {
                  const isMapped = mappedSrcFields.has(field.name);
                  const isDragging = dragging === field.name;
                  return (
                    <li key={field.name}>
                      <div
                        ref={(el) => {
                          if (el) srcRowRefs.current.set(field.name, el);
                          else srcRowRefs.current.delete(field.name);
                        }}
                        draggable
                        onDragStart={(e) => handleDragStart(e, field.name)}
                        onDragEnd={handleDragEnd}
                        className={`flex cursor-grab items-center gap-2 rounded-lg border px-3 py-2 transition-all select-none ${
                          isDragging
                            ? "border-teal-300 bg-teal-50 opacity-60 ring-2 ring-teal-200"
                            : isMapped
                            ? `${srcColor.border} ${srcColor.light}`
                            : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                        }`}
                      >
                        <GripVertical className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate font-mono text-[11px] font-semibold text-slate-800">
                              {field.name}
                            </span>
                            {field.required && (
                              <span className="rounded bg-rose-50 px-0.5 text-[8px] font-bold text-rose-500">
                                req
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 truncate text-[10px] text-slate-400">{field.label}</p>
                        </div>
                        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium ${typeColor(field.type)}`}>
                          {field.type}
                        </span>
                        {isMapped && (
                          <ArrowRight className={`h-3 w-3 shrink-0 ${srcColor.text}`} />
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* --- Center zone (lines pass through here) ------------------- */}
          <div className="flex flex-col items-center justify-center gap-2 bg-slate-50 px-2">
            <div className="text-center">
              <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                {mappings.length}
              </p>
              <p className="text-[9px] text-slate-400">mapped</p>
            </div>
            {requiredUnmapped.length > 0 && (
              <div className="rounded-full bg-amber-100 px-1.5 py-0.5 text-center">
                <p className="text-[9px] font-bold text-amber-700">
                  {requiredUnmapped.length} req.
                </p>
                <p className="text-[9px] text-amber-600">missing</p>
              </div>
            )}
          </div>

          {/* --- Target panel -------------------------------------------- */}
          <div
            ref={tgtPanelRef}
            onScroll={onPanelScroll}
            className="overflow-y-auto border-l border-slate-200 bg-white"
            style={{ maxHeight: "520px" }}
          >
            <div className={`sticky top-0 z-10 border-b ${tgtColor.border} ${tgtColor.light} px-4 py-2.5`}>
              <p className={`text-xs font-bold uppercase tracking-wider ${tgtColor.text}`}>
                Target — {tgtObjId || "…"}
              </p>
              <p className="mt-0.5 text-[10px] text-slate-400">Drop source fields here</p>
            </div>

            {tgtLoading ? (
              <div className="flex items-center justify-center py-16 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : tgtFields.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No fields — select a connector and object above.
              </div>
            ) : (
              <ul className="p-3 space-y-1">
                {tgtFields.map((field) => {
                  const isMapped  = mappedTgtFields.has(field.name);
                  const isHovered = hoveredTarget === field.name;
                  return (
                    <li key={field.name}>
                      <div
                        ref={(el) => {
                          if (el) tgtRowRefs.current.set(field.name, el);
                          else tgtRowRefs.current.delete(field.name);
                        }}
                        onDragOver={(e) => handleDragOver(e, field.name)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, field.name)}
                        className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-all select-none ${
                          isHovered
                            ? "border-teal-400 bg-teal-50 ring-2 ring-teal-200 ring-offset-0"
                            : isMapped
                            ? `${tgtColor.border} ${tgtColor.light}`
                            : "border-slate-200 bg-white border-dashed hover:border-slate-300"
                        }`}
                      >
                        {/* pointer-events-none on ALL children prevents dragLeave
                            firing falsely when cursor moves onto a child element */}
                        <div className="pointer-events-none min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate font-mono text-[11px] font-semibold text-slate-800">
                              {field.name}
                            </span>
                            {field.required && (
                              <span className={`rounded px-0.5 text-[8px] font-bold ${
                                isMapped ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-500"
                              }`}>
                                req
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 truncate text-[10px] text-slate-400">{field.label}</p>
                        </div>
                        <span className={`pointer-events-none shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium ${typeColor(field.type)}`}>
                          {field.type}
                        </span>
                        {isMapped && (
                          <Link2 className={`pointer-events-none h-3 w-3 shrink-0 ${tgtColor.text}`} />
                        )}
                        {isHovered && !isMapped && (
                          <span className="pointer-events-none shrink-0 rounded bg-teal-100 px-1 text-[9px] font-bold text-teal-700">
                            Drop
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Mapping summary table                                               */}
      {/* ------------------------------------------------------------------ */}
      {mappings.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <Link2 className="h-4 w-4 text-teal-600" />
              <span className="text-sm font-semibold text-slate-900">
                {mappings.length} field {mappings.length === 1 ? "mapping" : "mappings"}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ring-1 ring-inset ${
                cardinality === "1:1"
                  ? "bg-teal-50 text-teal-700 ring-teal-200"
                  : cardinality === "1:many"
                  ? "bg-indigo-50 text-indigo-700 ring-indigo-200"
                  : cardinality === "many:1"
                  ? "bg-violet-50 text-violet-700 ring-violet-200"
                  : "bg-rose-50 text-rose-700 ring-rose-200"
              }`}>
                {cardinality}
              </span>
            </div>
            {requiredUnmapped.length === 0 ? (
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                All required fields mapped ✓
              </span>
            ) : (
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">
                {requiredUnmapped.length} required field{requiredUnmapped.length > 1 ? "s" : ""} unmapped
              </span>
            )}
          </div>

          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-2 pl-4 pr-2">Source field</th>
                <th className="px-2 py-2" />
                <th className="px-2 py-2">Target field</th>
                <th className="px-2 py-2">Transform</th>
                <th className="py-2 pl-2 pr-4" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {mappings.map((m) => (
                <tr key={m.id} className="group">
                  <td className="py-2 pl-4 pr-2">
                    <span className={`rounded-md px-2 py-1 font-mono text-[11px] font-semibold ${srcColor.light} ${srcColor.text}`}>
                      {m.sourceField}
                    </span>
                  </td>
                  <td className="px-2 py-2 text-slate-300">
                    <ArrowRight className="h-3.5 w-3.5" />
                  </td>
                  <td className="px-2 py-2">
                    <span className={`rounded-md px-2 py-1 font-mono text-[11px] font-semibold ${tgtColor.light} ${tgtColor.text}`}>
                      {m.targetField}
                    </span>
                  </td>
                  <td className="px-2 py-2">
                    <select
                      value={m.transform}
                      onChange={(e) => updateTransform(m.id, e.target.value as MappingTransform)}
                      className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 focus:border-teal-400 focus:outline-none"
                    >
                      {mappingTransforms.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 pl-2 pr-4">
                    <button
                      type="button"
                      onClick={() => removeMapping(m.id)}
                      className="rounded p-1 text-slate-300 opacity-0 transition-opacity hover:bg-rose-50 hover:text-rose-500 group-hover:opacity-100"
                      title="Remove mapping"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state hint */}
      {mappings.length === 0 && !srcLoading && !tgtLoading && srcFields.length > 0 && tgtFields.length > 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 py-8 text-center">
          <Unlink className="mx-auto h-6 w-6 text-slate-300" />
          <p className="mt-3 text-sm font-medium text-slate-600">No fields mapped yet.</p>
          <p className="mt-1 text-xs text-slate-400">
            Drag a source field (left panel) and drop it onto a target field (right panel).
          </p>
        </div>
      )}
    </div>
  );
}
