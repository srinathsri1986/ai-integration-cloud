export type MappingField = {
  description: string;
  name: string;
  required?: boolean;
  sample: string | number | boolean | null;
  type: "string" | "number" | "date" | "boolean";
};

export type MappingObject = {
  displayName: string;
  fields: MappingField[];
  id: string;
  systemId: string;
};

export type MappingTransform =
  | "direct"
  | "rename"
  | "format_date"
  | "lookup_placeholder"
  | "constant_placeholder";

export const mappingTransforms: Array<{
  description: string;
  label: string;
  value: MappingTransform;
}> = [
  {
    description: "Copy the source value directly into the target field.",
    label: "Direct",
    value: "direct"
  },
  {
    description: "Rename or normalize the field label while preserving the value.",
    label: "Rename",
    value: "rename"
  },
  {
    description: "Format dates into the target system date shape.",
    label: "Format date",
    value: "format_date"
  },
  {
    description: "Use an approved lookup table placeholder.",
    label: "Lookup placeholder",
    value: "lookup_placeholder"
  },
  {
    description: "Set a reviewed constant value placeholder.",
    label: "Constant placeholder",
    value: "constant_placeholder"
  }
];

export const mappingObjects: MappingObject[] = [
  {
    displayName: "NetSuite Project",
    id: "netsuite-project",
    systemId: "netsuite",
    fields: [
      {
        description: "Internal project identifier.",
        name: "project_id",
        required: true,
        sample: "PRJ-1042",
        type: "string"
      },
      {
        description: "Customer account name.",
        name: "customer_name",
        required: true,
        sample: "Acme Manufacturing",
        type: "string"
      },
      {
        description: "Finance owner responsible for the project.",
        name: "account_manager",
        sample: "Maya Rao",
        type: "string"
      },
      {
        description: "Approved project budget.",
        name: "budget_amount",
        sample: 420000,
        type: "number"
      },
      {
        description: "Project due date.",
        name: "due_date",
        sample: "2026-03-31",
        type: "date"
      }
    ]
  },
  {
    displayName: "Salesforce Opportunity",
    id: "salesforce-opportunity",
    systemId: "salesforce",
    fields: [
      {
        description: "Salesforce opportunity name.",
        name: "Name",
        required: true,
        sample: "Acme CFO Renewal",
        type: "string"
      },
      {
        description: "Linked customer account.",
        name: "AccountName",
        required: true,
        sample: "Acme Manufacturing",
        type: "string"
      },
      {
        description: "Forecast amount.",
        name: "Amount",
        required: true,
        sample: 420000,
        type: "number"
      },
      {
        description: "Opportunity close date.",
        name: "CloseDate",
        required: true,
        sample: "2026-03-31",
        type: "date"
      },
      {
        description: "Opportunity owner.",
        name: "OwnerName",
        sample: "Maya Rao",
        type: "string"
      }
    ]
  },
  {
    displayName: "Oracle Fusion Legal Entity",
    id: "oracle-legal-entity",
    systemId: "oracle-fusion",
    fields: [
      {
        description: "Legal entity identifier.",
        name: "legal_entity_code",
        required: true,
        sample: "US01",
        type: "string"
      },
      {
        description: "Legal entity display name.",
        name: "legal_entity_name",
        required: true,
        sample: "Acme US Operations",
        type: "string"
      },
      {
        description: "Reporting currency.",
        name: "currency_code",
        sample: "USD",
        type: "string"
      }
    ]
  },
  {
    displayName: "REST Customer Payload",
    id: "rest-customer",
    systemId: "rest-api",
    fields: [
      {
        description: "External customer identifier.",
        name: "externalId",
        required: true,
        sample: "CUST-982",
        type: "string"
      },
      {
        description: "Customer name.",
        name: "displayName",
        required: true,
        sample: "Acme Manufacturing",
        type: "string"
      },
      {
        description: "Customer active flag.",
        name: "isActive",
        sample: true,
        type: "boolean"
      }
    ]
  },
  {
    displayName: "CSV Invoice Row",
    id: "csv-invoice",
    systemId: "sftp-csv",
    fields: [
      {
        description: "Invoice number from CSV file.",
        name: "invoice_number",
        required: true,
        sample: "INV-2026-0042",
        type: "string"
      },
      {
        description: "Customer name from CSV file.",
        name: "customer",
        required: true,
        sample: "Acme Manufacturing",
        type: "string"
      },
      {
        description: "Invoice amount.",
        name: "amount",
        required: true,
        sample: 12850,
        type: "number"
      },
      {
        description: "Invoice date.",
        name: "invoice_date",
        required: true,
        sample: "2026-02-15",
        type: "date"
      }
    ]
  },
  // ── SAP ──────────────────────────────────────────────────────────────────
  {
    displayName: "SAP Cost Center Entry",
    id: "sap-cost-center",
    systemId: "sap",
    fields: [
      {
        description: "SAP cost center identifier.",
        name: "cost_center_id",
        required: true,
        sample: "CC-1200",
        type: "string"
      },
      {
        description: "Cost center display name.",
        name: "description",
        required: true,
        sample: "Finance Operations",
        type: "string"
      },
      {
        description: "Controlling area code.",
        name: "controlling_area",
        required: true,
        sample: "0001",
        type: "string"
      },
      {
        description: "Validity start date.",
        name: "valid_from",
        sample: "2026-01-01",
        type: "date"
      },
      {
        description: "Approved budget for the cost center.",
        name: "budget_amount",
        sample: 850000,
        type: "number"
      }
    ]
  },
  {
    displayName: "SAP Journal Entry Line",
    id: "sap-journal-line",
    systemId: "sap",
    fields: [
      {
        description: "SAP company code.",
        name: "company_code",
        required: true,
        sample: "1000",
        type: "string"
      },
      {
        description: "GL account number.",
        name: "gl_account",
        required: true,
        sample: "400000",
        type: "string"
      },
      {
        description: "Transaction amount.",
        name: "amount",
        required: true,
        sample: 12500,
        type: "number"
      },
      {
        description: "Journal posting date.",
        name: "posting_date",
        required: true,
        sample: "2026-06-01",
        type: "date"
      },
      {
        description: "External document reference.",
        name: "reference",
        sample: "INV-2026-0042",
        type: "string"
      }
    ]
  },
  // ── Oracle ────────────────────────────────────────────────────────────────
  {
    displayName: "Oracle GL Balance",
    id: "oracle-gl-balance",
    systemId: "oracle-fusion",
    fields: [
      {
        description: "Oracle ledger identifier.",
        name: "ledger_id",
        required: true,
        sample: "1",
        type: "string"
      },
      {
        description: "Chart of accounts segment.",
        name: "account_segment",
        required: true,
        sample: "01-000-1110-0000-000",
        type: "string"
      },
      {
        description: "Accounting period.",
        name: "period_name",
        required: true,
        sample: "JUN-26",
        type: "string"
      },
      {
        description: "Entered debit amount.",
        name: "entered_dr",
        sample: 45000,
        type: "number"
      },
      {
        description: "Entered credit amount.",
        name: "entered_cr",
        sample: 0,
        type: "number"
      }
    ]
  },
  // ── HCM ──────────────────────────────────────────────────────────────────
  {
    displayName: "HCM Employee Record",
    id: "hcm-employee",
    systemId: "hcm",
    fields: [
      {
        description: "HCM system employee identifier.",
        name: "employee_id",
        required: true,
        sample: "EMP-4421",
        type: "string"
      },
      {
        description: "Employee full name.",
        name: "full_name",
        required: true,
        sample: "Maya Rao",
        type: "string"
      },
      {
        description: "Assigned department.",
        name: "department",
        required: true,
        sample: "Finance",
        type: "string"
      },
      {
        description: "Employment start date.",
        name: "start_date",
        sample: "2023-03-15",
        type: "date"
      },
      {
        description: "Annual salary (base).",
        name: "salary",
        sample: 110000,
        type: "number"
      },
      {
        description: "Direct manager employee ID.",
        name: "manager_id",
        sample: "EMP-1001",
        type: "string"
      }
    ]
  },
  // ── PostgreSQL ────────────────────────────────────────────────────────────
  {
    displayName: "PostgreSQL Analytics Row",
    id: "postgres-analytics-row",
    systemId: "postgresql",
    fields: [
      {
        description: "Unique row identifier.",
        name: "row_id",
        required: true,
        sample: "row-8821",
        type: "string"
      },
      {
        description: "Name of the analytics metric.",
        name: "metric_name",
        required: true,
        sample: "monthly_revenue",
        type: "string"
      },
      {
        description: "Numeric metric value.",
        name: "metric_value",
        required: true,
        sample: 245000.5,
        type: "number"
      },
      {
        description: "Metric dimension or segment.",
        name: "dimension",
        sample: "APAC",
        type: "string"
      },
      {
        description: "Timestamp the metric was recorded.",
        name: "recorded_at",
        sample: "2026-06-01",
        type: "date"
      }
    ]
  },
  // ── Slack ─────────────────────────────────────────────────────────────────
  {
    displayName: "Slack Channel Message",
    id: "slack-channel-message",
    systemId: "slack",
    fields: [
      {
        description: "Target Slack channel name or ID.",
        name: "channel",
        required: true,
        sample: "#finance-alerts",
        type: "string"
      },
      {
        description: "Plain-text message body.",
        name: "text",
        required: true,
        sample: "Budget variance alert: Acme Manufacturing is 12% over budget.",
        type: "string"
      },
      {
        description: "Display name for the message author.",
        name: "username",
        sample: "AI Integration Cloud",
        type: "string"
      }
    ]
  }
];

export function objectsForSystem(systemId: string) {
  return mappingObjects.filter((object) => object.systemId === systemId);
}

export function samplePayload(fields: MappingField[]) {
  return fields.reduce<Record<string, string | number | boolean | null>>((payload, field) => {
    payload[field.name] = field.sample;
    return payload;
  }, {});
}
