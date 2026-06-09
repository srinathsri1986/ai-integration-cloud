"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BrainCircuit,
  Loader2,
  Map,
  Sparkles,
  TriangleAlert,
  Workflow,
  X,
} from "lucide-react";
import type { AskAIResponse } from "@ai-integration-cloud/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { askAI } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface AskAIPanelProps {
  onClose: () => void;
  initialQuestion?: string;
}

// ── Intent badge ─────────────────────────────────────────────────────────────

function IntentBadge({ intent }: { intent: string }) {
  const map: Record<string, { label: string; className: string }> = {
    CREATE_FLOW:      { label: "Flow",    className: "border-teal-200   bg-teal-50   text-teal-700"   },
    SUGGEST_MAPPING:  { label: "Mapping", className: "border-sky-200    bg-sky-50    text-sky-700"    },
    EXPLAIN_ERROR:    { label: "Debug",   className: "border-rose-200   bg-rose-50   text-rose-700"   },
    GENERAL:          { label: "Info",    className: "border-slate-200  bg-slate-50  text-slate-600"  },
  };
  const cfg = map[intent] ?? map.GENERAL;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${cfg.className}`}
    >
      {cfg.label}
    </span>
  );
}

// ── Action icon ───────────────────────────────────────────────────────────────

function ActionIcon({ type }: { type: string }) {
  if (type === "SUGGEST_FLOW")          return <Workflow        className="h-4 w-4 shrink-0" />;
  if (type === "OPEN_MAPPING")          return <Map             className="h-4 w-4 shrink-0" />;
  if (type === "OPEN_ERROR_DEBUGGER")   return <TriangleAlert   className="h-4 w-4 shrink-0" />;
  return <Sparkles className="h-4 w-4 shrink-0" />;
}

function actionLabel(type: string) {
  if (type === "SUGGEST_FLOW")        return "Open in AI Builder";
  if (type === "OPEN_MAPPING")        return "Open Mapping Studio";
  if (type === "OPEN_ERROR_DEBUGGER") return "Open Error Debugger";
  return null;
}

// ── Provider badge ────────────────────────────────────────────────────────────

function ProviderBadge({ provider, model }: { provider: string; model: string | null }) {
  if (provider === "template") return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-teal-200 bg-teal-50 px-2.5 py-0.5 text-[11px] font-medium text-teal-700">
      <BrainCircuit className="h-3 w-3" />
      {model ?? provider}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function AskAIPanel({ onClose, initialQuestion = "" }: AskAIPanelProps) {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [question, setQuestion] = useState(initialQuestion);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskAIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    const q = question.trim();
    if (!q || q.length < 5) return;

    setLoading(true);
    setResult(null);
    setError(null);

    const res = await askAI({ question: q });

    setLoading(false);

    if (res.ok) {
      setResult(res.data);
    } else {
      setError(res.error ?? "The AI assistant returned an unexpected response.");
    }
  }

  function handleAction(res: AskAIResponse) {
    const nav = res.action?.navigateTo;
    if (!nav) return;

    if (res.action?.type === "SUGGEST_FLOW" && res.action.payload) {
      // Store the suggested flow so the AI Builder page can pre-populate it
      sessionStorage.setItem("askAI_suggestedFlow", JSON.stringify(res.action.payload));
    }

    if (res.action?.type === "OPEN_MAPPING" && res.action.payload) {
      // Store source/target pre-fill context so the mapping studio auto-selects the right objects
      sessionStorage.setItem("askAI_mappingSuggestion", JSON.stringify(res.action.payload));
    }

    onClose();
    router.push(nav);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleAsk();
    }
  }

  const ctaLabel = result?.action ? actionLabel(result.action.type) : null;

  return (
    // ── Backdrop ──────────────────────────────────────────────────────────
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Ask AI assistant"
    >
      {/* Translucent overlay */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* ── Panel ─────────────────────────────────────────────────────── */}
      <div className="relative w-full max-w-2xl">
        <Card className="overflow-hidden rounded-2xl border border-white/70 bg-white/95 p-0 shadow-2xl shadow-slate-900/20 backdrop-blur">

          {/* Header */}
          <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500 shadow-sm shadow-teal-900/20">
              <BrainCircuit className="h-4 w-4 text-white" />
            </span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900">Ask AI</p>
              <p className="text-[11px] text-slate-400">
                Describe an integration, map fields, or diagnose an error
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close Ask AI panel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Input area */}
          <div className="px-5 pt-4 pb-3">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder='Try: "Create a flow to sync SAP vendors to Salesforce every hour" or "Why did RUN-10491 fail?"'
              rows={3}
              autoFocus
              className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 transition-colors focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-400/20"
            />
            <div className="mt-2 flex items-center justify-between">
              <p className="text-[11px] text-slate-400">
                Press <kbd className="rounded border border-slate-200 bg-slate-100 px-1 py-0.5 text-[10px] font-mono">⌘ Enter</kbd> to ask
              </p>
              <Button
                onClick={handleAsk}
                disabled={loading || question.trim().length < 5}
                className="h-9 gap-2 rounded-lg px-4 text-sm"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                {loading ? "Thinking…" : "Ask"}
              </Button>
            </div>
          </div>

          {/* ── Result area ─────────────────────────────────────────────── */}
          {(result || error) && (
            <div className="border-t border-slate-100 px-5 pb-5 pt-4">
              {error && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
                  <p className="text-sm text-rose-700">{error}</p>
                </div>
              )}

              {result && (
                <div className="space-y-3">
                  {/* Intent + provider row */}
                  <div className="flex flex-wrap items-center gap-2">
                    <IntentBadge intent={result.intent} />
                    <ProviderBadge provider={result.provider} model={result.model} />
                  </div>

                  {/* Answer */}
                  <p className="text-sm leading-relaxed text-slate-700">{result.answer}</p>

                  {/* CTA — navigate to the relevant screen */}
                  {ctaLabel && result.action?.navigateTo && (
                    <button
                      type="button"
                      onClick={() => handleAction(result)}
                      className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90"
                    >
                      <ActionIcon type={result.action.type} />
                      {ctaLabel}
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Quick-start suggestions (shown before first query) */}
          {!result && !loading && !error && (
            <div className="border-t border-slate-100 px-5 pb-4 pt-3">
              <p className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Quick starts
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  "Sync NetSuite customers to Salesforce every 15 min",
                  "Map SAP vendor fields to Salesforce Account",
                  "Why did my last flow run fail?",
                  "What connectors are available?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setQuestion(suggestion)}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
