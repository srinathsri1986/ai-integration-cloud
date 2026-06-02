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
