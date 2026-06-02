import type { UserRole } from "@netsuite-cfo/shared";
import {
  BarChart3,
  Bot,
  Cable,
  ClipboardCheck,
  Gauge,
  GitBranch,
  Settings
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type PlatformRoute = {
  description: string;
  href: string;
  icon: LucideIcon;
  label: string;
  roles: UserRole[];
};

export const platformRoutes: PlatformRoute[] = [
  {
    description: "Executive finance cockpit",
    href: "/cfo",
    icon: BarChart3,
    label: "CFO Dashboard",
    roles: ["CFO", "Finance Controller", "Integration Admin", "Viewer"]
  },
  {
    description: "Ask governed CFO questions",
    href: "/orchestrator",
    icon: Bot,
    label: "Orchestrator",
    roles: ["CFO", "Finance Controller", "Integration Admin", "Developer"]
  },
  {
    description: "Guided no-code integration builder",
    href: "/flows",
    icon: GitBranch,
    label: "Integration Studio",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "Systems, APIs, and connector health",
    href: "/connectors",
    icon: Cable,
    label: "Systems",
    roles: ["Integration Admin", "Developer"]
  },
  {
    description: "Review tool and model activity",
    href: "/audit",
    icon: ClipboardCheck,
    label: "Governance",
    roles: ["Integration Admin", "Developer", "Viewer"]
  },
  {
    description: "Local role and runtime controls",
    href: "/admin",
    icon: Settings,
    label: "Admin",
    roles: ["Integration Admin", "Developer"]
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
    description: "Executive dashboard, narrative insight, variance, and project risk.",
    label: "CFO",
    signal: "Board-ready finance view"
  },
  {
    defaultPath: "/cfo",
    description: "Variance review, drilldowns, CFO queries, and operating follow-up.",
    label: "Finance Controller",
    signal: "Close and review workspace"
  },
  {
    defaultPath: "/flows",
    description: "Connector setup, flow design, governance, and platform operations.",
    label: "Integration Admin",
    signal: "Integration command center"
  },
  {
    defaultPath: "/orchestrator",
    description: "Tool contracts, orchestration behavior, MCP readiness, and APIs.",
    label: "Developer",
    signal: "Builder and API workspace"
  },
  {
    defaultPath: "/cfo",
    description: "Read-only CFO visibility and limited governance review.",
    label: "Viewer",
    signal: "Controlled visibility"
  }
];

export function defaultPathForRole(role: UserRole) {
  return personas.find((persona) => persona.label === role)?.defaultPath ?? "/cfo";
}

export function routesForRole(role: UserRole) {
  return platformRoutes.filter((route) => route.roles.includes(role));
}

export const defaultPlatformIcon = Gauge;
