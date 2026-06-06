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
