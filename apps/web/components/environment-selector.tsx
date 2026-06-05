"use client";

import { useEffect, useState } from "react";
import { Server } from "lucide-react";

type Env = "dev" | "staging" | "production";

const ENVS: Env[] = ["dev", "staging", "production"];

const ENV_CONFIG: Record<Env, { label: string; dot: string; text: string; bg: string }> = {
  dev: {
    label: "Dev",
    dot: "bg-sky-400",
    text: "text-sky-700",
    bg: "bg-sky-50 border-sky-200 hover:bg-sky-100"
  },
  staging: {
    label: "Staging",
    dot: "bg-amber-400",
    text: "text-amber-700",
    bg: "bg-amber-50 border-amber-200 hover:bg-amber-100"
  },
  production: {
    label: "Production",
    dot: "bg-emerald-400",
    text: "text-emerald-700",
    bg: "bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
  }
};

const STORAGE_KEY = "env-context";

export function EnvironmentSelector() {
  const [env, setEnv] = useState<Env>("dev");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Env | null;
    if (saved && ENVS.includes(saved)) setEnv(saved);
    setMounted(true);
  }, []);

  function cycle() {
    const next = ENVS[(ENVS.indexOf(env) + 1) % ENVS.length];
    setEnv(next);
    localStorage.setItem(STORAGE_KEY, next);
  }

  if (!mounted) return null;

  const cfg = ENV_CONFIG[env];

  return (
    <button
      onClick={cycle}
      title={`Environment: ${env} (click to switch)`}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${cfg.bg} ${cfg.text}`}
    >
      <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
      <Server className="h-3 w-3 opacity-60" />
      {cfg.label}
    </button>
  );
}
