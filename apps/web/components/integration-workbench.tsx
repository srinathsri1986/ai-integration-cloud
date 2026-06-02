"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowRight,
  CheckCircle2,
  MousePointer2,
  Network,
  PanelRightOpen,
  ShieldCheck,
  Sparkles,
  WandSparkles
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { integrationStages, integrationSystems } from "@/lib/integration-catalog";

export function IntegrationWorkbench() {
  const [sourceId, setSourceId] = useState("netsuite");
  const [targetId, setTargetId] = useState("salesforce");
  const source = useMemo(
    () => integrationSystems.find((system) => system.id === sourceId) ?? integrationSystems[0],
    [sourceId]
  );
  const target = useMemo(
    () => integrationSystems.find((system) => system.id === targetId) ?? integrationSystems[1],
    [targetId]
  );

  return (
    <section className="space-y-6 px-6 pb-8">
      <Card className="overflow-hidden border-white/80 bg-slate-950 p-0 text-white shadow-xl shadow-slate-300/40">
        <div className="grid gap-6 p-6 lg:grid-cols-[1fr_360px] lg:p-8">
          <div>
            <Badge className="border-white/15 bg-white/10 text-white">
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              SaaS-ready integration workspace
            </Badge>
            <h2 className="mt-5 max-w-4xl text-3xl font-semibold leading-tight tracking-normal">
              Connect any approved system with a guided, visual, AI-assisted path.
            </h2>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
              Choose systems, pick data, match fields, add governed AI help, review controls,
              and publish only after approval. NetSuite CFO is now one solution template inside
              a broader Integration Cloud.
            </p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/10 p-4">
            <p className="text-sm font-semibold">Workspace posture</p>
            <div className="mt-4 grid gap-3">
              <PostureRow label="Tenant" value="Local demo tenant" />
              <PostureRow label="Environment" value="Local / Sandbox-ready" />
              <PostureRow label="Edition" value="Founder MVP" />
              <PostureRow label="Governance" value="Human approval required" />
            </div>
          </div>
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Card className="bg-white/90">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Guided integration path</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">
                Build in plain business steps
              </h2>
            </div>
            <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">
              No raw system access
            </Badge>
          </div>

          <div className="mt-6 grid gap-3 lg:grid-cols-7">
            {integrationStages.map((stage, index) => (
              <div
                className="relative rounded-md border border-slate-200 bg-slate-50 p-3"
                key={stage.label}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-950 text-sm font-semibold text-white">
                  {index + 1}
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-950">{stage.label}</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{stage.description}</p>
                {index < integrationStages.length - 1 ? (
                  <ArrowRight className="absolute -right-3 top-5 hidden h-5 w-5 text-slate-400 lg:block" />
                ) : null}
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50 to-white p-4">
            <div className="grid items-center gap-4 lg:grid-cols-[1fr_auto_1fr]">
              <SystemPreview system={source} title="Source" />
              <div className="flex items-center justify-center">
                <div className="rounded-full border border-slate-200 bg-white p-4 shadow-sm">
                  <Network className="h-6 w-6 text-primary" />
                </div>
              </div>
              <SystemPreview system={target} title="Target" />
            </div>
          </div>
        </Card>

        <Card className="bg-white/90">
          <div className="flex items-center gap-2">
            <PanelRightOpen className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">No-code builder guide</p>
          </div>
          <div className="mt-5 space-y-4">
            <GuideStep
              icon={<MousePointer2 className="h-4 w-4" />}
              label="Choose a system"
              text="Start from visual cards instead of technical endpoints."
            />
            <GuideStep
              icon={<WandSparkles className="h-4 w-4" />}
              label="Ask AI for a draft"
              text="AI suggests from approved systems, objects, and actions only."
            />
            <GuideStep
              icon={<ShieldCheck className="h-4 w-4" />}
              label="Review and publish"
              text="Human approval is required before anything becomes runnable."
            />
          </div>
          <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
            Data Mapping Studio is the next workbench: source fields, target fields, drag/drop
            mapping, validation, and AI suggestions with human approval.
          </div>
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">System catalog</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">
              Connectors as reusable SaaS assets
            </h2>
          </div>
          <Badge className="border-sky-200 bg-sky-50 text-sky-900">Marketplace foundation</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {integrationSystems.map((system) => {
            const Icon = system.icon;
            const isSource = system.id === sourceId;
            const isTarget = system.id === targetId;

            return (
              <button
                className={`rounded-lg border bg-white p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
                  isSource || isTarget ? "border-slate-950 ring-2 ring-slate-950/10" : "border-border"
                }`}
                key={system.id}
                onClick={() => {
                  if (sourceId === system.id) {
                    setTargetId(system.id);
                  } else {
                    setSourceId(system.id);
                  }
                }}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className={`flex h-11 w-11 items-center justify-center rounded-md border ${system.color}`}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <Badge>{system.readiness}</Badge>
                </div>
                <p className="mt-4 text-base font-semibold text-slate-950">{system.name}</p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">{system.category}</p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{system.description}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {system.objects.slice(0, 3).map((object) => (
                    <Badge className="bg-slate-50" key={object}>
                      {object}
                    </Badge>
                  ))}
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                  {system.auth}
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </section>
  );
}

function PostureRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-slate-300">{label}</span>
      <span className="font-medium text-white">{value}</span>
    </div>
  );
}

function SystemPreview({
  system,
  title
}: {
  system: (typeof integrationSystems)[number];
  title: string;
}) {
  const Icon = system.icon;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{title}</p>
      <div className="mt-3 flex items-start gap-3">
        <span className={`flex h-10 w-10 items-center justify-center rounded-md border ${system.color}`}>
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <p className="font-semibold text-slate-950">{system.name}</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{system.objects.join(", ")}</p>
        </div>
      </div>
    </div>
  );
}

function GuideStep({
  icon,
  label,
  text
}: {
  icon: ReactNode;
  label: string;
  text: string;
}) {
  return (
    <div className="flex gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-primary">
        {icon}
      </span>
      <div>
        <p className="text-sm font-semibold text-slate-950">{label}</p>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p>
      </div>
    </div>
  );
}
