from threading import Lock

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
            {
                "name": "status",
                "description": "Project status.",
                "type": "string",
                "sample": "In Progress",
            },
            {
                "name": "subsidiary_id",
                "description": "Owning NetSuite subsidiary.",
                "type": "string",
                "sample": "EMEA",
            },
        ],
    ),
    MappingObject(
        id="salesforce-opportunity",
        displayName="Salesforce Opportunity",
        systemId="salesforce",
        fields=[
            {"name": "Id",          "description": "Salesforce opportunity ID (system-assigned; do not map as target).", "type": "string", "sample": "0060x000001AbCd"},
            {"name": "Name",        "description": "Opportunity name.",                             "type": "string", "required": True,  "sample": "Acme Q4 Renewal"},
            {"name": "AccountId",   "description": "Parent account Salesforce ID.",                "type": "string",                    "sample": "0010x000002XyZa"},
            {"name": "AccountName", "description": "Linked customer account name.",                "type": "string",                    "sample": "Acme Manufacturing"},
            {"name": "Amount",      "description": "Forecast amount.",                             "type": "number", "required": True,  "sample": 420000},
            {"name": "CloseDate",   "description": "Opportunity close date.",                      "type": "date",   "required": True,  "sample": "2026-12-31"},
            {"name": "StageName",   "description": "Pipeline stage (use constant_placeholder if no source field).", "type": "string", "sample": "Prospecting"},
            {"name": "Probability", "description": "Win probability percentage.",                  "type": "number",                    "sample": 30},
            {"name": "OwnerId",     "description": "Opportunity owner Salesforce ID.",             "type": "string",                    "sample": "0050x000003WxYz"},
            {"name": "OwnerName",   "description": "Opportunity owner display name.",              "type": "string",                    "sample": "Maya Rao"},
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
    # ── SAP ──────────────────────────────────────────────────────────────────
    MappingObject(
        id="sap-cost-center",
        displayName="SAP Cost Center Entry",
        systemId="sap",
        fields=[
            {
                "name": "cost_center_id",
                "description": "SAP cost center identifier.",
                "type": "string",
                "required": True,
                "sample": "CC-1200",
            },
            {
                "name": "description",
                "description": "Cost center display name.",
                "type": "string",
                "required": True,
                "sample": "Finance Operations",
            },
            {
                "name": "controlling_area",
                "description": "Controlling area code.",
                "type": "string",
                "required": True,
                "sample": "0001",
            },
            {
                "name": "valid_from",
                "description": "Validity start date.",
                "type": "date",
                "sample": "2026-01-01",
            },
            {
                "name": "budget_amount",
                "description": "Approved budget for the cost center.",
                "type": "number",
                "sample": 850000,
            },
        ],
    ),
    MappingObject(
        id="sap-journal-line",
        displayName="SAP Journal Entry Line",
        systemId="sap",
        fields=[
            {
                "name": "company_code",
                "description": "SAP company code.",
                "type": "string",
                "required": True,
                "sample": "1000",
            },
            {
                "name": "gl_account",
                "description": "GL account number.",
                "type": "string",
                "required": True,
                "sample": "400000",
            },
            {
                "name": "amount",
                "description": "Transaction amount.",
                "type": "number",
                "required": True,
                "sample": 12500.00,
            },
            {
                "name": "posting_date",
                "description": "Journal posting date.",
                "type": "date",
                "required": True,
                "sample": "2026-06-01",
            },
            {
                "name": "reference",
                "description": "External document reference.",
                "type": "string",
                "sample": "INV-2026-0042",
            },
        ],
    ),
    # ── Oracle ────────────────────────────────────────────────────────────────
    MappingObject(
        id="oracle-gl-balance",
        displayName="Oracle GL Balance",
        systemId="oracle-fusion",
        fields=[
            {
                "name": "ledger_id",
                "description": "Oracle ledger identifier.",
                "type": "string",
                "required": True,
                "sample": "1",
            },
            {
                "name": "account_segment",
                "description": "Chart of accounts segment.",
                "type": "string",
                "required": True,
                "sample": "01-000-1110-0000-000",
            },
            {
                "name": "period_name",
                "description": "Accounting period.",
                "type": "string",
                "required": True,
                "sample": "JUN-26",
            },
            {
                "name": "entered_dr",
                "description": "Entered debit amount.",
                "type": "number",
                "sample": 45000.00,
            },
            {
                "name": "entered_cr",
                "description": "Entered credit amount.",
                "type": "number",
                "sample": 0.00,
            },
        ],
    ),
    # ── HCM (Workday / SuccessFactors) ────────────────────────────────────────
    MappingObject(
        id="hcm-employee",
        displayName="HCM Employee Record",
        systemId="hcm",
        fields=[
            {
                "name": "employee_id",
                "description": "HCM system employee identifier.",
                "type": "string",
                "required": True,
                "sample": "EMP-4421",
            },
            {
                "name": "full_name",
                "description": "Employee full name.",
                "type": "string",
                "required": True,
                "sample": "Maya Rao",
            },
            {
                "name": "department",
                "description": "Assigned department.",
                "type": "string",
                "required": True,
                "sample": "Finance",
            },
            {
                "name": "start_date",
                "description": "Employment start date.",
                "type": "date",
                "sample": "2023-03-15",
            },
            {
                "name": "salary",
                "description": "Annual salary (base).",
                "type": "number",
                "sample": 110000,
            },
            {
                "name": "manager_id",
                "description": "Direct manager employee ID.",
                "type": "string",
                "sample": "EMP-1001",
            },
        ],
    ),
    # ── PostgreSQL ────────────────────────────────────────────────────────────
    MappingObject(
        id="postgres-analytics-row",
        displayName="PostgreSQL Analytics Row",
        systemId="postgresql",
        fields=[
            {
                "name": "row_id",
                "description": "Unique row identifier.",
                "type": "string",
                "required": True,
                "sample": "row-8821",
            },
            {
                "name": "metric_name",
                "description": "Name of the analytics metric.",
                "type": "string",
                "required": True,
                "sample": "monthly_revenue",
            },
            {
                "name": "metric_value",
                "description": "Numeric metric value.",
                "type": "number",
                "required": True,
                "sample": 245000.50,
            },
            {
                "name": "dimension",
                "description": "Metric dimension or segment.",
                "type": "string",
                "sample": "APAC",
            },
            {
                "name": "recorded_at",
                "description": "Timestamp the metric was recorded.",
                "type": "date",
                "sample": "2026-06-01",
            },
        ],
    ),
    # ── NetSuite (extra objects from live schema) ─────────────────────────────
    MappingObject(
        id="netsuite-invoice",
        displayName="NetSuite Invoice",
        systemId="netsuite",
        fields=[
            {"name": "invoice_id",   "description": "Invoice identifier.",         "type": "string", "required": True,  "sample": "INV-2026-0042"},
            {"name": "customer_id",  "description": "Customer record ID.",          "type": "string", "required": True,  "sample": "CUST-001"},
            {"name": "amount",       "description": "Invoice total amount.",        "type": "number", "required": True,  "sample": 12850},
            {"name": "due_date",     "description": "Payment due date.",            "type": "date",   "required": True,  "sample": "2026-07-01"},
            {"name": "currency",     "description": "Currency code.",               "type": "string",                    "sample": "USD"},
            {"name": "status",       "description": "Invoice status.",              "type": "string",                    "sample": "Open"},
        ],
    ),
    MappingObject(
        id="netsuite-subsidiary",
        displayName="NetSuite Subsidiary",
        systemId="netsuite",
        fields=[
            {"name": "subsidiary_id", "description": "Subsidiary identifier.",    "type": "string", "required": True,  "sample": "EMEA"},
            {"name": "name",          "description": "Subsidiary display name.",  "type": "string", "required": True,  "sample": "Acme EMEA Ltd"},
            {"name": "currency",      "description": "Reporting currency.",        "type": "string",                    "sample": "EUR"},
            {"name": "country",       "description": "Country of registration.",   "type": "string",                    "sample": "GB"},
        ],
    ),
    # ── Salesforce (extra objects from live schema) ───────────────────────────
    MappingObject(
        id="salesforce-account",
        displayName="Salesforce Account",
        systemId="salesforce",
        fields=[
            {"name": "Id",             "description": "Account Salesforce ID.",   "type": "string",     "required": True,  "sample": "0010x000002XyZa"},
            {"name": "Name",           "description": "Account name.",            "type": "string", "required": True,  "sample": "Acme Manufacturing"},
            {"name": "Industry",       "description": "Industry vertical.",        "type": "string",                    "sample": "Technology"},
            {"name": "AnnualRevenue",  "description": "Annual revenue.",           "type": "number",                    "sample": 5000000},
            {"name": "BillingCity",    "description": "Billing city.",             "type": "string",                    "sample": "San Francisco"},
            {"name": "Phone",          "description": "Account phone number.",     "type": "string",                    "sample": "+1 415 555 0100"},
        ],
    ),
    MappingObject(
        id="salesforce-contact",
        displayName="Salesforce Contact",
        systemId="salesforce",
        fields=[
            {"name": "Id",        "description": "Contact Salesforce ID.",   "type": "string",     "required": True,  "sample": "0030x000004AbCd"},
            {"name": "FirstName", "description": "First name.",               "type": "string",                    "sample": "Maya"},
            {"name": "LastName",  "description": "Last name.",                "type": "string", "required": True,  "sample": "Rao"},
            {"name": "Email",     "description": "Email address.",            "type": "string",                    "sample": "maya.rao@acme.com"},
            {"name": "Title",     "description": "Job title.",                "type": "string",                    "sample": "CFO"},
            {"name": "AccountId", "description": "Parent account ID.",        "type": "string",                    "sample": "0010x000002XyZa"},
        ],
    ),
    # ── SAP (extra objects from live schema) ──────────────────────────────────
    MappingObject(
        id="sap-journal-entry",
        displayName="SAP Journal Entry",
        systemId="sap",
        fields=[
            {"name": "company_code",  "description": "SAP company code.",         "type": "string", "required": True,  "sample": "1000"},
            {"name": "gl_account",    "description": "G/L account number.",        "type": "string", "required": True,  "sample": "400000"},
            {"name": "amount",        "description": "Transaction amount.",        "type": "number", "required": True,  "sample": 12500.00},
            {"name": "posting_date",  "description": "Journal posting date.",      "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "reference",     "description": "External document ref.",     "type": "string",                    "sample": "INV-2026-0042"},
            {"name": "currency",      "description": "Transaction currency.",      "type": "string",                    "sample": "USD"},
        ],
    ),
    MappingObject(
        id="sap-vendor",
        displayName="SAP Vendor",
        systemId="sap",
        fields=[
            {"name": "vendor_id",      "description": "Vendor master ID.",         "type": "string", "required": True,  "sample": "V-001"},
            {"name": "name",           "description": "Vendor name.",              "type": "string", "required": True,  "sample": "Tech Supplies Ltd"},
            {"name": "payment_terms",  "description": "Standard payment terms.",   "type": "string",                    "sample": "Net 30"},
        ],
    ),
    # ── HCM (extra objects from live schema) ──────────────────────────────────
    MappingObject(
        id="hcm-open-role",
        displayName="HCM Open Requisition",
        systemId="hcm",
        fields=[
            {"name": "requisition_id",  "description": "Open role requisition ID.",     "type": "string", "required": True,  "sample": "REQ-0088"},
            {"name": "title",           "description": "Job title.",                     "type": "string", "required": True,  "sample": "Senior SWE"},
            {"name": "department_id",   "description": "Owning department code.",        "type": "string", "required": True,  "sample": "ENG-001"},
            {"name": "target_date",     "description": "Target start date.",             "type": "date",                      "sample": "2026-06-01"},
            {"name": "hiring_manager",  "description": "Hiring manager name.",           "type": "string",                    "sample": "Ada Lovelace"},
        ],
    ),
    # ── PostgreSQL (objects from live schema mock tables) ─────────────────────
    MappingObject(
        id="postgres-orders",
        displayName="PostgreSQL Orders",
        systemId="postgres",
        fields=[
            {"name": "id",          "description": "Order primary key.",   "type": "number", "required": True,  "sample": 1042},
            {"name": "customer_id", "description": "Customer FK.",         "type": "number", "required": True,  "sample": 201},
            {"name": "amount",      "description": "Order total amount.",  "type": "number", "required": True,  "sample": 12850.00},
            {"name": "created_at",  "description": "Order creation date.", "type": "date",                      "sample": "2026-06-01"},
            {"name": "status",      "description": "Order status.",        "type": "string",                    "sample": "completed"},
        ],
    ),
    MappingObject(
        id="postgres-customers",
        displayName="PostgreSQL Customers",
        systemId="postgres",
        fields=[
            {"name": "id",            "description": "Customer primary key.",   "type": "number", "required": True,  "sample": 201},
            {"name": "name",          "description": "Customer name.",          "type": "string", "required": True,  "sample": "Acme Manufacturing"},
            {"name": "email",         "description": "Billing email.",          "type": "string",                    "sample": "billing@acme.com"},
            {"name": "last_order_at", "description": "Date of last order.",     "type": "date",                      "sample": "2026-05-20"},
        ],
    ),
    MappingObject(
        id="postgres-products",
        displayName="PostgreSQL Products",
        systemId="postgres",
        fields=[
            {"name": "id",    "description": "Product primary key.", "type": "number", "required": True, "sample": 5},
            {"name": "name",  "description": "Product name.",        "type": "string", "required": True, "sample": "Enterprise License"},
            {"name": "sku",   "description": "Stock keeping unit.",  "type": "string", "required": True, "sample": "ENT-LIC-001"},
            {"name": "price", "description": "Unit price.",          "type": "number",                   "sample": 4999.00},
        ],
    ),
    # ── Slack ─────────────────────────────────────────────────────────────────
    MappingObject(
        id="slack-channel-message",
        displayName="Slack Channel Message",
        systemId="slack",
        fields=[
            {
                "name": "channel",
                "description": "Target Slack channel name or ID.",
                "type": "string",
                "required": True,
                "sample": "#finance-alerts",
            },
            {
                "name": "text",
                "description": "Plain-text message body.",
                "type": "string",
                "required": True,
                "sample": "Budget variance alert: Acme Manufacturing is 12% over budget.",
            },
            {
                "name": "username",
                "description": "Display name for the message author.",
                "type": "string",
                "sample": "AI Integration Cloud",
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

_promoted_mapping_objects: dict[str, MappingObject] = {}
_promoted_mapping_objects_lock = Lock()


def list_mapping_objects() -> list[MappingObject]:
    with _promoted_mapping_objects_lock:
        return [*MAPPING_OBJECTS, *_promoted_mapping_objects.values()]


def promote_mapping_object(mapping_object: MappingObject) -> MappingObject:
    with _promoted_mapping_objects_lock:
        _promoted_mapping_objects[mapping_object.id] = mapping_object
        return mapping_object.model_copy()


def clear_promoted_mapping_objects_for_tests() -> None:
    with _promoted_mapping_objects_lock:
        _promoted_mapping_objects.clear()


def get_mapping_object(object_id: str) -> MappingObject:
    for mapping_object in list_mapping_objects():
        if mapping_object.id == object_id:
            return mapping_object

    raise KeyError(object_id)


def sample_payload_for_object(object_id: str) -> dict[str, str | int | float | bool | None]:
    mapping_object = get_mapping_object(object_id)
    return {field.name: field.sample for field in mapping_object.fields}
