"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";
import type { UserRole } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { loginWithRole } from "@/lib/api";
import { defaultPathForRole, personas } from "@/lib/navigation";

export function PersonaLogin() {
  const router = useRouter();
  const [role, setRole] = useState<UserRole>("CFO");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const selected = personas.find((persona) => persona.label === role) ?? personas[0];

  async function continueAsPersona() {
    setIsLoading(true);
    setError(undefined);
    const response = await loginWithRole(role);

    if (!response.ok) {
      setError("API login is unavailable, so a local persona session will be used.");
    }

    router.push(defaultPathForRole(role));
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_15%,hsl(var(--primary)/0.16),transparent_30rem),radial-gradient(circle_at_85%_20%,hsl(var(--accent)/0.15),transparent_26rem),linear-gradient(135deg,#f8fafc_0%,#eef2f6_52%,#f6f7fb_100%)] px-5 py-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <section>
          <Badge className="border-slate-200 bg-white/80 text-slate-700">
            <Sparkles className="mr-1 h-3.5 w-3.5" />
            AI-native Integration Cloud
          </Badge>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-tight tracking-normal text-slate-950 md:text-5xl">
            NetSuite CFO Intelligence Orchestrator
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Enter through the persona that matches your work. Finance leaders see executive
            insight first, while integration teams land directly in governed orchestration tools.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {["Governed AI", "Approved tools", "Full audit trail"].map((item) => (
              <div className="rounded-md border border-white/80 bg-white/75 p-4 shadow-sm" key={item}>
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <p className="mt-3 text-sm font-medium text-slate-800">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/80 bg-white/90 p-5 shadow-2xl shadow-slate-300/40 backdrop-blur">
          <div className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Local secure entry</p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-950">Choose your workspace</h2>
            </div>
            <Badge className="border-sky-200 bg-sky-50 text-sky-900">
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
              Placeholder JWT
            </Badge>
          </div>

          <div className="mt-5 grid gap-3">
            {personas.map((persona) => {
              const isSelected = persona.label === role;

              return (
                <button
                  className={`rounded-md border p-4 text-left transition-all ${
                    isSelected
                      ? "border-slate-950 bg-slate-950 text-white shadow-lg shadow-slate-300"
                      : "border-slate-200 bg-white text-slate-800 hover:border-slate-400"
                  }`}
                  key={persona.label}
                  onClick={() => setRole(persona.label)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold">{persona.label}</p>
                      <p className={isSelected ? "mt-1 text-sm text-slate-300" : "mt-1 text-sm text-muted-foreground"}>
                        {persona.description}
                      </p>
                    </div>
                    <Badge className={isSelected ? "border-white/20 bg-white/10 text-white" : "bg-slate-50"}>
                      {persona.signal}
                    </Badge>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-semibold">Landing page</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {selected.label} opens <span className="font-medium text-slate-900">{selected.defaultPath}</span>.
            </p>
          </div>

          {error ? (
            <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              {error}
            </p>
          ) : null}

          <Button className="mt-5 w-full" disabled={isLoading} onClick={continueAsPersona} type="button">
            {isLoading ? "Starting session" : `Continue as ${role}`}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </section>
      </div>
    </main>
  );
}
