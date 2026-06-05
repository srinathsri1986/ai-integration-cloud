"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, Building2, LogOut, ShieldCheck } from "lucide-react";
import type { UserRole } from "@netsuite-cfo/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EnvironmentSelector } from "@/components/environment-selector";
import { getCurrentTenant, LOCAL_AUTH_EMAIL_KEY, LOCAL_AUTH_ROLE_KEY, LOCAL_AUTH_TOKEN_KEY, logoutUser, type TenantInfo } from "@/lib/api";
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
  const [tenant, setTenant] = useState<TenantInfo | null>(null);

  useEffect(() => {
    const storedRole = window.localStorage.getItem(LOCAL_AUTH_ROLE_KEY) as UserRole | null;
    const storedEmail = window.localStorage.getItem(LOCAL_AUTH_EMAIL_KEY);
    if (storedRole) setRole(storedRole);
    if (storedEmail) setEmail(storedEmail);

    // Only call the tenant endpoint when a real JWT exists.
    // The placeholder dev token has no tenant_id and always returns 403.
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
  const plan = tenant?.plan ? tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1) : "MVP";

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.10),transparent_34rem),linear-gradient(180deg,#f8fafc_0%,#eef2f6_100%)]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/70 bg-white/85 px-4 py-5 shadow-xl shadow-slate-200/60 backdrop-blur xl:block">
        <Link className="flex items-center gap-3 rounded-md px-2 py-2" href="/cfo">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BrainCircuit className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold leading-5">AI Integration Cloud</span>
            <span className="block text-xs text-muted-foreground">Governed iPaaS</span>
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

        <div className="absolute bottom-5 left-4 right-4 space-y-2">
          {/* Workspace card */}
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 shrink-0 text-slate-500" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">{tenantName}</p>
                <p className="text-xs text-muted-foreground">{plan} plan</p>
              </div>
            </div>
          </div>

          {/* User card */}
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 text-primary" />
              <div className="min-w-0">
                <p className="text-sm font-semibold">{role}</p>
                <p className="mt-0.5 truncate text-xs leading-5 text-muted-foreground">{email}</p>
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
            <div className="flex flex-wrap items-center gap-2">
              <EnvironmentSelector />
              <Badge className="border-emerald-200 bg-emerald-50 text-emerald-900">{tenantName}</Badge>
              <Badge className="border-sky-200 bg-sky-50 text-sky-900">{plan} plan</Badge>
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
