import {
  Building2,
  CloudCog,
  Database,
  FileSpreadsheet,
  Globe2,
  Layers3,
  ServerCog,
  ShieldCheck
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type IntegrationSystem = {
  auth: string;
  category: string;
  color: string;
  description: string;
  icon: LucideIcon;
  id: string;
  name: string;
  objects: string[];
  readiness: "Ready" | "Template" | "Planned";
};

export const integrationSystems: IntegrationSystem[] = [
  {
    auth: "Token placeholder",
    category: "ERP",
    color: "border-cyan-200 bg-cyan-50 text-cyan-950",
    description: "Finance, projects, subsidiaries, revenue, and CFO reporting objects.",
    icon: Building2,
    id: "netsuite",
    name: "NetSuite",
    objects: ["Projects", "Invoices", "Subsidiaries", "P/L lines"],
    readiness: "Ready"
  },
  {
    auth: "OAuth placeholder",
    category: "CRM",
    color: "border-blue-200 bg-blue-50 text-blue-950",
    description: "Accounts, opportunities, pipeline, and customer handoff events.",
    icon: CloudCog,
    id: "salesforce",
    name: "Salesforce",
    objects: ["Accounts", "Opportunities", "Contacts", "Forecasts"],
    readiness: "Template"
  },
  {
    auth: "OAuth placeholder",
    category: "ERP",
    color: "border-violet-200 bg-violet-50 text-violet-950",
    description: "Payables, receivables, legal entities, and procurement signals.",
    icon: Layers3,
    id: "oracle-fusion",
    name: "Oracle Fusion",
    objects: ["Suppliers", "Invoices", "Legal entities", "AP aging"],
    readiness: "Template"
  },
  {
    auth: "OAuth placeholder",
    category: "ITSM",
    color: "border-emerald-200 bg-emerald-50 text-emerald-950",
    description: "Incidents, change requests, service tickets, and risk events.",
    icon: ShieldCheck,
    id: "servicenow",
    name: "ServiceNow",
    objects: ["Incidents", "Changes", "Tasks", "Approvals"],
    readiness: "Template"
  },
  {
    auth: "Connection string placeholder",
    category: "Database",
    color: "border-slate-200 bg-slate-50 text-slate-950",
    description: "Approved relational datasets with governed query templates only.",
    icon: Database,
    id: "postgresql",
    name: "PostgreSQL",
    objects: ["Tables", "Views", "Approved reports", "Lookups"],
    readiness: "Planned"
  },
  {
    auth: "API key placeholder",
    category: "API",
    color: "border-amber-200 bg-amber-50 text-amber-950",
    description: "Generic REST resources from OpenAPI or sample JSON payloads.",
    icon: Globe2,
    id: "rest-api",
    name: "REST API",
    objects: ["Resources", "Endpoints", "JSON payloads", "Webhooks"],
    readiness: "Template"
  },
  {
    auth: "Key placeholder",
    category: "File",
    color: "border-rose-200 bg-rose-50 text-rose-950",
    description: "Flat files, CSV extracts, and secure file arrival triggers.",
    icon: FileSpreadsheet,
    id: "sftp-csv",
    name: "SFTP / CSV",
    objects: ["CSV files", "Folders", "Batches", "Imports"],
    readiness: "Planned"
  },
  {
    auth: "Managed runtime",
    category: "Platform",
    color: "border-indigo-200 bg-indigo-50 text-indigo-950",
    description: "Approved APIs, audit events, AI steps, and human approvals.",
    icon: ServerCog,
    id: "integration-cloud",
    name: "AI Integration Cloud",
    objects: ["Approvals", "Audit events", "AI actions", "Mappings"],
    readiness: "Ready"
  }
];

export const integrationStages = [
  {
    description: "Schedule, webhook, file arrival, or manual start.",
    label: "Start",
    shortLabel: "Trigger"
  },
  {
    description: "Pick a source system and approved business object.",
    label: "Choose System",
    shortLabel: "Source"
  },
  {
    description: "Select an approved object action, not raw system access.",
    label: "Pick Data",
    shortLabel: "Object"
  },
  {
    description: "Match source fields to target fields with validation.",
    label: "Match Fields",
    shortLabel: "Map"
  },
  {
    description: "Apply governed transforms and optional AI suggestions.",
    label: "Transform",
    shortLabel: "Rules"
  },
  {
    description: "Route through human approval before publishing.",
    label: "Review",
    shortLabel: "Approval"
  },
  {
    description: "Run published integrations with complete audit trace.",
    label: "Publish",
    shortLabel: "Run"
  }
];
