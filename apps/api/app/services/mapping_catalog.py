from app.models.mapping import MappingObject


MAPPING_OBJECTS: list[MappingObject] = [
    MappingObject(
        id="netsuite-project",
        displayName="NetSuite Project",
        systemId="netsuite",
        fields=[
            {
                "name": "project_id",
                "description": "Internal project identifier.",
                "type": "string",
                "required": True,
                "sample": "PRJ-1042",
            },
            {
                "name": "customer_name",
                "description": "Customer account name.",
                "type": "string",
                "required": True,
                "sample": "Acme Manufacturing",
            },
            {
                "name": "account_manager",
                "description": "Finance owner responsible for the project.",
                "type": "string",
                "sample": "Maya Rao",
            },
            {
                "name": "budget_amount",
                "description": "Approved project budget.",
                "type": "number",
                "sample": 420000,
            },
            {
                "name": "due_date",
                "description": "Project due date.",
                "type": "date",
                "sample": "2026-03-31",
            },
        ],
    ),
    MappingObject(
        id="salesforce-opportunity",
        displayName="Salesforce Opportunity",
        systemId="salesforce",
        fields=[
            {
                "name": "Name",
                "description": "Salesforce opportunity name.",
                "type": "string",
                "required": True,
                "sample": "Acme CFO Renewal",
            },
            {
                "name": "AccountName",
                "description": "Linked customer account.",
                "type": "string",
                "required": True,
                "sample": "Acme Manufacturing",
            },
            {
                "name": "Amount",
                "description": "Forecast amount.",
                "type": "number",
                "required": True,
                "sample": 420000,
            },
            {
                "name": "CloseDate",
                "description": "Opportunity close date.",
                "type": "date",
                "required": True,
                "sample": "2026-03-31",
            },
            {
                "name": "OwnerName",
                "description": "Opportunity owner.",
                "type": "string",
                "sample": "Maya Rao",
            },
        ],
    ),
    MappingObject(
        id="oracle-legal-entity",
        displayName="Oracle Fusion Legal Entity",
        systemId="oracle-fusion",
        fields=[
            {
                "name": "legal_entity_code",
                "description": "Legal entity identifier.",
                "type": "string",
                "required": True,
                "sample": "US01",
            },
            {
                "name": "legal_entity_name",
                "description": "Legal entity display name.",
                "type": "string",
                "required": True,
                "sample": "Acme US Operations",
            },
            {
                "name": "currency_code",
                "description": "Reporting currency.",
                "type": "string",
                "sample": "USD",
            },
        ],
    ),
    MappingObject(
        id="rest-customer",
        displayName="REST Customer Payload",
        systemId="rest-api",
        fields=[
            {
                "name": "externalId",
                "description": "External customer identifier.",
                "type": "string",
                "required": True,
                "sample": "CUST-982",
            },
            {
                "name": "displayName",
                "description": "Customer name.",
                "type": "string",
                "required": True,
                "sample": "Acme Manufacturing",
            },
            {
                "name": "isActive",
                "description": "Customer active flag.",
                "type": "boolean",
                "sample": True,
            },
        ],
    ),
    MappingObject(
        id="csv-invoice",
        displayName="CSV Invoice Row",
        systemId="sftp-csv",
        fields=[
            {
                "name": "invoice_number",
                "description": "Invoice number from CSV file.",
                "type": "string",
                "required": True,
                "sample": "INV-2026-0042",
            },
            {
                "name": "customer",
                "description": "Customer name from CSV file.",
                "type": "string",
                "required": True,
                "sample": "Acme Manufacturing",
            },
            {
                "name": "amount",
                "description": "Invoice amount.",
                "type": "number",
                "required": True,
                "sample": 12850,
            },
            {
                "name": "invoice_date",
                "description": "Invoice date.",
                "type": "date",
                "required": True,
                "sample": "2026-02-15",
            },
        ],
    ),
]

APPROVED_MAPPING_TRANSFORMS = [
    "direct",
    "rename",
    "format_date",
    "lookup_placeholder",
    "constant_placeholder",
]


def get_mapping_object(object_id: str) -> MappingObject:
    for mapping_object in MAPPING_OBJECTS:
        if mapping_object.id == object_id:
            return mapping_object

    raise KeyError(object_id)
