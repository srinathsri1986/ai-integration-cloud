"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Calendar,
  Check,
  Hand,
  Loader2,
  Webhook
} from "lucide-react";
import type { FlowDefinitionUpsertRequest, FlowTriggerType } from "@netsuite-cfo/shared";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CronPreview } from "@/components/cron-preview";
import { saveFlowDefinition } from "@/lib/api";

// --- Trigger type cards ---

interface TriggerCardProps {
  selected: boolean;
  onSelect: () => void;
  icon: React.ReactNode;
  label: string;
  description: string;
}

function TriggerCard({ selected, onSelect, icon, label, description }: TriggerCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`
        relative flex flex-col gap-3 p-5 rounded-xl border-2 text-left transition-all
        hover:border-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-400
        ${selected
          ? "border-sky-500 bg-sky-50 ring-2 ring-sky-400"
          : "border-slate-200 bg-white hover:bg-sky-50/40"
        }
      `}
    >
      {selected && (
        <div className="absolute top-3 right-3">
          <Check className="h-4 w-4 text-sky-600" />
        </div>
      )}
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${selected ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600"}`}>
        {icon}
      </div>
      <div>
        <p className={`text-sm font-semibold ${selected ? "text-sky-700" : "text-slate-800"}`}>{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </div>
    </button>
  );
}

// --- Step progress bar ---

function StepBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`
            h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors
            ${i + 1 < current ? "bg-emerald-500 text-white" : i + 1 === current ? "bg-sky-500 text-white" : "bg-slate-200 text-slate-400"}
          `}>
            {i + 1 < current ? <Check className="h-3.5 w-3.5" /> : i + 1}
          </div>
          {i < total - 1 && (
            <div className={`h-0.5 flex-1 w-16 ${i + 1 < current ? "bg-emerald-400" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// --- Main wizard ---

export function FlowCreationWizard() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<FlowTriggerType>("manual");
  const [cronExpression, setCronExpression] = useState("0 9 * * 1-5");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [targetModule, setTargetModule] = useState("cfo_dashboard");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canProceedStep1 = name.trim().length >= 3 && (
    triggerType !== "schedule" || cronExpression.trim().split(/\s+/).length === 5
  );

  async function handleSubmit() {
    if (!canProceedStep1) return;
    setSubmitting(true);
    setError(null);

    // Derive a slug-style flowId from the name
    const flowId = name.trim().toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 96);

    const descriptionValue = description.trim().length >= 10
      ? description.trim()
      : `${name.trim()} — integration draft created via wizard.`;

    const payload: FlowDefinitionUpsertRequest = {
      flowId,
      name: name.trim(),
      description: descriptionValue,
      sourceConnector: "netsuite",
      targetModule,
      status: "draft",
      triggerType,
      steps: [
        {
          id: "step-1",
          name: "Default step",
          description: "Initial step — configure in Integration Studio.",
          approvedTool: "orchestrator.query"
        }
      ],
      ...(triggerType === "schedule" ? { triggerCron: cronExpression.trim() } : {})
    };
    const result = await saveFlowDefinition(payload);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error ?? "Failed to create integration.");
      return;
    }
    router.push(`/flows/${result.data.flowId}`);
  }

  return (
    <div className="px-5 lg:px-8 py-6 max-w-2xl mx-auto">
      <StepBar current={step} total={3} />

      {/* Step 1 — Trigger & Name */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Integration name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. NetSuite CFO dashboard refresh"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What does this integration do?"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Trigger type <span className="text-rose-500">*</span>
            </label>
            <div className="grid grid-cols-3 gap-3">
              <TriggerCard
                selected={triggerType === "manual"}
                onSelect={() => setTriggerType("manual")}
                icon={<Hand className="h-5 w-5" />}
                label="Manual"
                description="Run on demand from the dashboard."
              />
              <TriggerCard
                selected={triggerType === "schedule"}
                onSelect={() => setTriggerType("schedule")}
                icon={<Calendar className="h-5 w-5" />}
                label="Schedule"
                description="Run automatically on a cron schedule."
              />
              <TriggerCard
                selected={triggerType === "webhook"}
                onSelect={() => setTriggerType("webhook")}
                icon={<Webhook className="h-5 w-5" />}
                label="Webhook"
                description="Run when an HTTP event arrives."
              />
            </div>
          </div>

          {triggerType === "schedule" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Cron expression{" "}
                <span className="text-xs text-slate-400 font-normal ml-1">(minute hour dom month dow)</span>
              </label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                placeholder="0 9 * * 1-5"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
              />
              <CronPreview expression={cronExpression} count={3} />
            </div>
          )}

          {triggerType === "webhook" && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Webhook HMAC secret{" "}
                <span className="text-xs text-slate-400 font-normal ml-1">(optional — used to sign incoming requests)</span>
              </label>
              <input
                type="password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                placeholder="Leave blank to auto-generate"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
              />
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              disabled={!canProceedStep1}
              onClick={() => setStep(2)}
              className="gap-2"
            >
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2 — Connector Config */}
      {step === 2 && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Source connector</label>
            <div className="px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm font-mono text-slate-700">
              netsuite
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Additional connectors will be available in Release 6.0.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Target module</label>
            <input
              type="text"
              value={targetModule}
              onChange={(e) => setTargetModule(e.target.value)}
              placeholder="e.g. cfo_dashboard"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-400 bg-white"
            />
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(1)} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button onClick={() => setStep(3)} className="gap-2">
              Next <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3 — Review & Submit */}
      {step === 3 && (
        <div className="space-y-6">
          <Card className="bg-slate-50 border border-slate-200 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Review your integration</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium text-slate-800">{name}</dd>

              {description && (
                <>
                  <dt className="text-slate-500">Description</dt>
                  <dd className="text-slate-700">{description}</dd>
                </>
              )}

              <dt className="text-slate-500">Trigger</dt>
              <dd>
                <span className="inline-flex items-center rounded-md border border-slate-200 bg-muted px-2 py-1 text-xs font-medium capitalize">
                  {triggerType}
                </span>
              </dd>

              {triggerType === "schedule" && (
                <>
                  <dt className="text-slate-500">Schedule</dt>
                  <dd className="font-mono text-xs text-slate-700">{cronExpression}</dd>
                </>
              )}

              <dt className="text-slate-500">Source</dt>
              <dd className="font-mono text-xs text-slate-700">netsuite</dd>

              <dt className="text-slate-500">Target</dt>
              <dd className="font-mono text-xs text-slate-700">{targetModule}</dd>
            </dl>
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mt-2">
              This integration will be created as a <strong>draft</strong>. Submit it for approval before it can run.
            </p>
          </Card>

          {error && (
            <div className="flex items-start gap-2 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(2)} disabled={submitting} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button onClick={handleSubmit} disabled={submitting} className="gap-2">
              {submitting ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Creating…</>
              ) : (
                <><Check className="h-4 w-4" /> Create Integration</>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
