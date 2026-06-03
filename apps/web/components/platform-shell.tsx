"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, LogOut, ShieldCheck } from "lucide-react";
import type { UserRole } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LOCAL_AUTH_EMAIL_KEY, LOCAL_AUTH_ROLE_KEY, logoutUser } from "@/lib/api";
import { routesForRole } from "@/lib/navigation";

type PlatformShellProps = {
  active: string;
  children: React.ReactNode;
  eyebrow?: string;
  subtitle: string;
  title: string;
};

export function PlatformShell({
  active,
  children,
  eyebrow = "AI Integration Cloud",
  subtitle,
  title
}: PlatformShellProps) {
  const pathname = usePathname();
  const [role, setRole] = useState<UserRole>("Integration Admin");
  const [email, setEmail] = useState("local-dev@example.com");

  useEffect(() => {
    const storedRole = window.localStorage.getItem(LOCAL_AUTH_ROLE_KEY) as UserRole | null;
    const storedEmail = window.localStorage.getItem(LOCAL_AUTH_EMAIL_KEY);

    if (storedRole) {
      setRole(storedRole);
    }

    if (storedEmail) {
      setEmail(storedEmail);
    }
  }, []);

  const routes = routesForRole(role);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.10),transparent_34rem),linear-gradient(180deg,#f8fafc_0%,#eef2f6_100%)]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/70 bg-white/85 px-4 py-5 shadow-xl shadow-slate-200/60 backdrop-blur xl:block">
        <Link className="flex items-center gap-3 rounded-md px-2 py-2" href="/cfo">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold leading-5">AI Integration Cloud</span>
            <span className="block text-xs text-muted-foreground">Governed iPaaS MVP</span>
          </span>
        </Link>

        <div className="mt-7 space-y-1">
          {routes.map((route) => {
            const Icon = route.icon;
            const isActive = active === route.href || pathname === route.href;

            return (
              <Link
                className={`flex items-center gap-3 rounded-md px-3 py-3 text-sm transition-colors ${
                  isActive
                    ? "bg-slate-950 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
                href={route.href}
                key={route.href}
              >
                <Icon className="h-4 w-4" />
                <span>
                  <span className="block font-medium">{route.label}</span>
                  <span className={isActive ? "text-xs text-slate-300" : "text-xs text-muted-foreground"}>
                    {route.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </div>

        <div className="absolute bottom-5 left-4 right-4 rounded-md border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-4 w-4 text-primary" />
            <div>
              <p className="text-sm font-semibold">{role}</p>
              <p className="mt-1 break-all text-xs leading-5 text-muted-foreground">{email}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge className="bg-white">Tenant: local</Badge>
                <Badge className="bg-white">Plan: MVP</Badge>
              </div>
            </div>
          </div>
          <Button
            className="mt-3 w-full"
            onClick={async () => { await logoutUser(); window.location.href = "/login"; }}
            type="button"
            variant="secondary"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="xl:pl-72">
        <header className="sticky top-0 z-10 border-b border-white/70 bg-white/80 backdrop-blur">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between lg:px-8">
            <div>
              <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal text-slate-950">{title}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{subtitle}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">Local MVP</Badge>
              <Badge className="border-sky-200 bg-sky-50 text-sky-900">Ollama ready</Badge>
              <Badge className="border-violet-200 bg-violet-50 text-violet-900">Tenant workspace</Badge>
              <Badge className="border-slate-200 bg-white text-slate-700">{role}</Badge>
            </div>
          </div>

          <nav className="flex gap-2 overflow-x-auto px-5 pb-4 xl:hidden">
            {routes.map((route) => {
              const Icon = route.icon;
              const isActive = active === route.href || pathname === route.href;

              return (
                <Link
                  className={`inline-flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                    isActive
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-border bg-white text-slate-700"
                  }`}
                  href={route.href}
                  key={route.href}
                >
                  <Icon className="h-4 w-4" />
                  {route.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <main className="mx-auto max-w-7xl px-5 py-8 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
