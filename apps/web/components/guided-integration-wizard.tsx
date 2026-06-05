"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  DatabaseZap,
  FilePenLine,
  Link2,
  Save,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import type {
  ApprovedFlowTool,
  FlowDefinitionUpsertRequest,
  MappingDefinition
} from "@ai-integration-cloud/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  type ApiResult,
  saveFlowDefinition,
  suggestFlowDefinition
} from "@/lib/api";

const steps = ["Describe", "Systems", "Mapping", "Action", "Review"];

const targetModules = [
  { id: "salesforce_opportunity", label: "Salesforce Opportunity" },
  { id: "cfo_dashboard", label: "CFO Dashboard" },
  { id: "rest_customer_event", label: "REST Customer Event" },
  { id: "project_risk", label: "Project Risk" }
];

const approvedTools: Array<{ label: string; tool: ApprovedFlowTool }> = [
  { label: "Governed orchestration", tool: "orchestrator.query" },
  { label: "CFO dashboard summary", tool: "cfo.dashboard_summary" },
  { label: "P/L vs budget", tool: "cfo.pl_vs_budget" },
  { label: "Overdue project risk", tool: "cfo.overdue_projects_by_account_manager" }
];

function defaultDraft(): FlowDefinitionUpsertRequest {
  return {
    description: "Governed integration draft created through the guided wizard.",
    flowId: "guided-customer-event-integration",
    mappingDefinitionId: null,
    name: "Guided Customer Event Integration",
    sourceConnector: "netsuite",
    status: "draft",
    steps: [
      {
        approvedTool: "orchestrator.query",
        description: "Route an approved business request through governed orchestration.",
        id: "governed-orchestration",
        name: "Governed orchestration"
      }
    ],
    targetModule: "salesforce_opportunity",
    triggerType: "manual"
  };
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export function GuidedIntegrationWizard({
  initialMappings
}: {
  initialMappings: ApiResult<MappingDefinition[]>;
}) {
  const router = useRouter();
  const [activeStep, setActiveStep] = useState(0);
  const [goal, setGoal] = useState(
    "Create an integration that maps a customer event into a Salesforce opportunity and keeps an audit trail."
  );
  const [draft, setDraft] = useState<FlowDefinitionUpsertRequest>(defaultDraft());
  const [message, setMessage] = useState<string | undefined>(
    initialMappings.isFallback ? initialMappings.error : undefined
  );
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const publishedMappings = useMemo(
    () => initialMappings.data.filter((mapping) => mapping.status === "published"),
    [initialMappings.data]
  );
  const selectedMapping = publishedMappings.find(
    (mapping) => mapping.mappingId === draft.mappingDefinitionId
  );

  function goNext() {
    setActiveStep((current) => Math.min(current + 1, steps.length - 1));
  }

  function goBack() {
    setActiveStep((current) => Math.max(current - 1, 0));
  }

  async function generateWithLiveAi() {
    setIsSuggesting(true);
    setMessage("Asking the configured live AI provider for a governed draft.");
    const response = await suggestFlowDefinition({
      prompt: goal,
      requireLiveAi: true
    });

    if (response.ok && !response.data.suggestionFallbackUsed) {
      setDraft(response.data.suggestedFlow);
      setMessage(
        `${response.data.suggestionProvider} / ${
          response.data.suggestionModel ?? "live model"
        } created a governed draft.`
      );
      setActiveStep(1);
    } else {
      setMessage(response.error ?? "Live AI did not return a valid governed draft.");
    }
    setIsSuggesting(false);
  }

  async function saveDraft() {
    setIsSaving(true);
    setMessage(undefined);
    const response = await saveFlowDefinition(draft);
    if (response.ok) {
      setMessage(`${response.data.name} saved as a draft integration.`);
      router.push("/flows");
      router.refresh();
    } else {
      setMessage(response.error ?? "Unable to save integration draft.");
    }
    setIsSaving(false);
  }

  return (
    <section className="space-y-6 px-6 pb-12">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              Guided builder
            </Badge>
            <h2 className="mt-4 max-w-3xl text-3xl font-semibold tracking-normal text-slate-950">
              Create one governed integration without seeing every control at once.
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              The wizard uses live AI only when available, validates every draft, and saves nothing
              until you review and confirm.
            </p>
          </div>
          <Button onClick={() => router.push("/flows")} type="button" variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Back to integrations
          </Button>
        </div>
      </div>

      {message ? (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
          {message}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Card className="h-fit bg-white">
          <p className="text-sm font-semibold text-slate-950">Progress</p>
          <div className="mt-4 space-y-2">
            {steps.map((step, index) => (
              <button
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-3 text-left text-sm transition ${
                  activeStep === index
                    ? "border-slate-950 bg-slate-950 text-white"
                    : index < activeStep
                      ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                      : "border-slate-200 bg-slate-50 text-slate-700"
                }`}
                key={step}
                onClick={() => setActiveStep(index)}
                type="button"
              >
                {index < activeStep ? <CheckCircle2 className="h-4 w-4" /> : <span>{index + 1}</span>}
                {step}
              </button>
            ))}
          </div>
        </Card>

        <Card className="min-h-[520px] bg-white">
          {activeStep === 0 ? (
            <div>
              <StepHeader icon={<Bot className="h-5 w-5" />} title="Describe the integration" />
              <textarea
                className="mt-5 min-h-40 w-full rounded-xl border border-border bg-white px-4 py-3 text-sm leading-6 outline-none focus:border-primary"
                onChange={(event) => {
                  const value = event.target.value;
                  setGoal(value);
                  setDraft((current) => ({
                    ...current,
                    flowId: slugify(value) || current.flowId,
                    name: value.length > 10 ? value.slice(0, 90) : current.name
                  }));
                }}
                value={goal}
              />
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Button disabled={isSuggesting || goal.length < 10} onClick={generateWithLiveAi} type="button">
                  <Sparkles className="h-4 w-4" />
                  {isSuggesting ? "Asking live AI" : "Generate with live AI"}
                </Button>
                <Button onClick={goNext} type="button" variant="secondary">
                  Continue manually
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : null}

          {activeStep === 1 ? (
            <div>
              <StepHeader icon={<DatabaseZap className="h-5 w-5" />} title="Choose systems" />
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <ChoiceCard
                  label="Source"
                  title="NetSuite"
                  text="Approved template-backed source for this MVP."
                />
                <label className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-950">
                  Target
                  <select
                    className="mt-3 h-11 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, targetModule: event.target.value }))
                    }
                    value={draft.targetModule}
                  >
                    {targetModules.map((target) => (
                      <option key={target.id} value={target.id}>
                        {target.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <WizardControls onBack={goBack} onNext={goNext} />
            </div>
          ) : null}

          {activeStep === 2 ? (
            <div>
              <StepHeader icon={<Link2 className="h-5 w-5" />} title="Attach mapping" />
              <label className="mt-5 block text-sm font-medium text-slate-950">
                Published mapping
                <select
                  className="mt-3 h-11 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
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
              {selectedMapping ? (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                  {selectedMapping.mappings.length} approved field matches are ready for runtime preview.
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                  You can save a draft without a mapping, but runtime preview will require a published mapping.
                </div>
              )}
              <WizardControls onBack={goBack} onNext={goNext} />
            </div>
          ) : null}

          {activeStep === 3 ? (
            <div>
              <StepHeader icon={<ShieldCheck className="h-5 w-5" />} title="Choose approved action" />
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {approvedTools.map((item) => (
                  <button
                    className={`rounded-xl border p-4 text-left transition ${
                      draft.steps[0]?.approvedTool === item.tool
                        ? "border-slate-950 bg-slate-950 text-white"
                        : "border-slate-200 bg-slate-50 hover:border-primary"
                    }`}
                    key={item.tool}
                    onClick={() =>
                      setDraft((current) => ({
                        ...current,
                        steps: [
                          {
                            approvedTool: item.tool,
                            description: `Run approved action ${item.tool}.`,
                            id: item.tool.replaceAll(".", "-"),
                            name: item.label
                          }
                        ]
                      }))
                    }
                    type="button"
                  >
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="mt-2 text-xs opacity-80">{item.tool}</p>
                  </button>
                ))}
              </div>
              <WizardControls onBack={goBack} onNext={goNext} />
            </div>
          ) : null}

          {activeStep === 4 ? (
            <div>
              <StepHeader icon={<FilePenLine className="h-5 w-5" />} title="Review and save" />
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <TextInput
                  label="Integration ID"
                  onChange={(value) => setDraft((current) => ({ ...current, flowId: slugify(value) }))}
                  value={draft.flowId}
                />
                <TextInput
                  label="Integration name"
                  onChange={(value) => setDraft((current) => ({ ...current, name: value }))}
                  value={draft.name}
                />
                <label className="text-sm font-medium text-slate-950 md:col-span-2">
                  Description
                  <textarea
                    className="mt-2 min-h-24 w-full rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-primary"
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, description: event.target.value }))
                    }
                    value={draft.description}
                  />
                </label>
              </div>
              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge>Draft only</Badge>
                  <Badge>{draft.sourceConnector}</Badge>
                  <Badge>{draft.targetModule}</Badge>
                  <Badge>{draft.steps[0]?.approvedTool}</Badge>
                  {draft.mappingDefinitionId ? <Badge>{draft.mappingDefinitionId}</Badge> : null}
                </div>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <Button onClick={goBack} type="button" variant="secondary">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button disabled={isSaving} onClick={saveDraft} type="button">
                  <Save className="h-4 w-4" />
                  {isSaving ? "Saving" : "Save draft integration"}
                </Button>
              </div>
            </div>
          ) : null}
        </Card>
      </div>
    </section>
  );
}

function StepHeader({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white">
        {icon}
      </span>
      <div>
        <p className="text-sm font-medium text-muted-foreground">Current step</p>
        <h3 className="text-2xl font-semibold tracking-normal text-slate-950">{title}</h3>
      </div>
    </div>
  );
}

function WizardControls({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  return (
    <div className="mt-6 grid gap-3 sm:grid-cols-2">
      <Button onClick={onBack} type="button" variant="secondary">
        <ArrowLeft className="h-4 w-4" />
        Back
      </Button>
      <Button onClick={onNext} type="button">
        Continue
        <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

function ChoiceCard({ label, text, title }: { label: string; text: string; title: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
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
    <label className="text-sm font-medium text-slate-950">
      {label}
      <input
        className="mt-2 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-primary"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}
