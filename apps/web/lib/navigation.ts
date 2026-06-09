import type { UserRole } from "@ai-integration-cloud/shared";
import {
  BarChart3,
  Bot,
  Cable,
  ClipboardCheck,
  Gauge,
  GitBranch,
  LayoutDashboard,
  Map,
  Settings,
  Wand2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type PlatformRoute = {
  description: string;
  href: string;
  icon: LucideIcon;
  label: string;
  roles: UserRole[];
};

/**
 * Core iPaaS platform routes.
 *
 * Route order = sidebar order.
 * Core platform features come first; the Finance Analytics demo sits at the
 * bottom so it's clearly a sample use-case showcase rather than a product pillar.
 */
export const platformRoutes: PlatformRoute[] = [
  // ── Core platform ──────────────────────────────────────────────────────────
  {
    description: "Integration estate overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    label: "Dashboard",
    roles: ["Integration Admin", "Developer", "CFO", "Finance Controller", "Viewer"]
  },
  {
    description: "Build and manage integration flows",
    href: "/flows",
    icon: GitBranch,
    label: "Integration Studio",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "NL → canvas → governed publish",
    href: "/flows/builder",
    icon: Wand2,
    label: "AI Builder",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "Map fields between connected systems",
    href: "/mapping",
    icon: Map,
    label: "Data Mapping",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "Connected systems, APIs, and health",
    href: "/connectors",
    icon: Cable,
    label: "Connectors",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "AI integration design and troubleshooting",
    href: "/orchestrator",
    icon: Bot,
    label: "AI Assistant",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "Audit trail, compliance, and governance",
    href: "/audit",
    icon: ClipboardCheck,
    label: "Governance",
    roles: ["Integration Admin", "Developer", "Viewer"]
  },
  {
    description: "Role and runtime platform controls",
    href: "/admin",
    icon: Settings,
    label: "Admin",
    roles: ["Integration Admin", "Developer"]
  },
  // ── Sample use-case demo ───────────────────────────────────────────────────
  // Demonstrates a live NetSuite + Salesforce integration built on this platform.
  // Shown to finance personas so they can see platform output without needing
  // to configure integrations themselves.
  {
    description: "Live demo: NetSuite finance analytics",
    href: "/cfo",
    icon: BarChart3,
    label: "Finance Analytics",
    roles: ["CFO", "Finance Controller", "Integration Admin", "Viewer"]
  }
];

export const personas: Array<{
  defaultPath: string;
  description: string;
  label: UserRole;
  signal: string;
}> = [
  {
    defaultPath: "/cfo",
    description: "Live finance analytics powered by NetSuite integration — variance, projects, subsidiaries.",
    label: "CFO",
    signal: "Finance integration demo"
  },
  {
    defaultPath: "/cfo",
    description: "Integration-driven variance review, project risk, and operating follow-up.",
    label: "Finance Controller",
    signal: "Finance integration demo"
  },
  {
    defaultPath: "/flows",
    description: "Connector setup, integration flow design, governance, and platform operations.",
    label: "Integration Admin",
    signal: "Integration command center"
  },
  {
    defaultPath: "/flows",
    description: "Flow builder, data mapping, connector APIs, and AI integration assistant.",
    label: "Developer",
    signal: "Builder workspace"
  },
  {
    defaultPath: "/dashboard",
    description: "Read-only integration estate and governance visibility.",
    label: "Viewer",
    signal: "Controlled visibility"
  }
];

export function defaultPathForRole(role: UserRole) {
  return personas.find((persona) => persona.label === role)?.defaultPath ?? "/dashboard";
}

export function routesForRole(role: UserRole) {
  return platformRoutes.filter((route) => route.roles.includes(role));
}

export const defaultPlatformIcon = Gauge;
