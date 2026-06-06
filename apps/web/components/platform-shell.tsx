"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, LogOut, ShieldCheck, Sparkles } from "lucide-react";
import type { UserRole } from "@ai-integration-cloud/shared";

import { Button } from "@/components/ui/button";
import { EnvironmentSelector } from "@/components/environment-selector";
import {
  getCurrentTenant,
  LOCAL_AUTH_EMAIL_KEY,
  LOCAL_AUTH_ROLE_KEY,
  LOCAL_AUTH_TOKEN_KEY,
  logoutUser,
  type TenantInfo,
} from "@/lib/api";
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
  title,
}: PlatformShellProps) {
  const pathname = usePathname();
  const [role, setRole] = useState<UserRole>("Integration Admin");
  const [email, setEmail] = useState("local-dev@example.com");
  const [tenant, setTenant] = useState<TenantInfo | null>(null);

  useEffect(() => {
    const storedRole = window.localStorage.getItem(LOCAL_AUTH_ROLE_KEY) as UserRole | null;
    const storedEmail = window.localStorage.getItem(LOCAL_AUTH_EMAIL_KEY);
    if (storedRole) setRole(storedRole);
    if (storedEmail) setEmail(storedEmail);

    const token = window.localStorage.getItem(LOCAL_AUTH_TOKEN_KEY);
    const isRealJwt = token ? token.split(".").length === 3 : false;
    if (isRealJwt) {
      getCurrentTenant().then((result) => {
        if (result.ok) setTenant(result.data);
      });
    }
  }, []);

  const routes = routesForRole(role);
  const tenantName = tenant?.name ?? "Local Workspace";
  const plan = tenant?.plan
    ? tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1)
    : "MVP";
  const initials = email.slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen bg-background">
      {/* ── Dark sidebar ───────────────────────────────────────── */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col bg-slate-900 xl:flex">
        {/* Teal top accent bar */}
        <div className="h-0.5 w-full bg-gradient-to-r from-teal-400 via-teal-500 to-cyan-400" />

        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500 shadow-lg shadow-teal-900/40">
            <BrainCircuit className="h-5 w-5 text-white" />
          </span>
          <div>
            <p className="text-sm font-semibold leading-5 text-white">AI Integration Cloud</p>
            <p className="text-[11px] font-medium text-slate-400">Governed iPaaS</p>
          </div>
        </div>

        {/* Divider */}
        <div className="mx-5 h-px bg-slate-800" />

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
          {routes.map((route) => {
            const Icon = route.icon;
            const isActive = active === route.href || pathname === route.href;

            return (
              <Link
                key={route.href}
                href={route.href}
                className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                  isActive
                    ? "bg-teal-600 text-white shadow-sm shadow-teal-900/30"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 ${
                    isActive ? "text-teal-100" : "text-slate-500 group-hover:text-slate-300"
                  }`}
                />
                <span>
                  <span className="block font-medium leading-5">{route.label}</span>
                  <span
                    className={`block text-[11px] leading-4 ${
                      isActive ? "text-teal-200" : "text-slate-500 group-hover:text-slate-400"
                    }`}
                  >
                    {route.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom panel */}
        <div className="mx-3 mb-4 space-y-2">
          {/* Workspace */}
          <div className="rounded-lg bg-slate-800 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-teal-600/20 text-teal-400">
                <Sparkles className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-white">{tenantName}</p>
                <p className="text-[11px] text-slate-400">{plan} plan</p>
              </div>
            </div>
          </div>

          {/* User */}
          <div className="rounded-lg bg-slate-800 px-3 py-2.5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-600 text-[11px] font-bold text-white">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-white">{role}</p>
                <p className="truncate text-[11px] text-slate-400">{email}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                await logoutUser();
                window.location.href = "/login";
              }}
              className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-600 hover:text-white"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────── */}
      <div className="xl:pl-64">
        {/* Sticky page header */}
        <header className="sticky top-0 z-10 border-b border-border bg-white/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-8">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-primary">
                {eyebrow}
              </p>
              <h1 className="mt-0.5 text-xl font-bold tracking-tight text-slate-900">{title}</h1>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{subtitle}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <EnvironmentSelector />
              <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                {tenantName}
              </span>
              <span className="inline-flex items-center rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700">
                {plan} plan
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                <ShieldCheck className="h-3 w-3 text-slate-400" />
                {role}
              </span>
            </div>
          </div>

          {/* Mobile nav */}
          <nav className="flex gap-1.5 overflow-x-auto px-5 pb-3 xl:hidden">
            {routes.map((route) => {
              const Icon = route.icon;
              const isActive = active === route.href || pathname === route.href;

              return (
                <Link
                  key={route.href}
                  href={route.href}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                    isActive
                      ? "border-teal-600 bg-teal-600 text-white"
                      : "border-border bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
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
