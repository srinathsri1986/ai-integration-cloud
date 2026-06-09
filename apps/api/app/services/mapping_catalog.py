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
    # ── NetSuite record objects ───────────────────────────────────────────────
    MappingObject(
        id="netsuite-customer",
        displayName="NetSuite Customer",
        systemId="netsuite",
        fields=[
            {"name": "id",               "description": "NetSuite internal customer ID.",          "type": "string", "required": True,  "sample": "42"},
            {"name": "entity_id",        "description": "Customer entity ID / number.",            "type": "string", "required": True,  "sample": "CUST-0042"},
            {"name": "company_name",     "description": "Company or individual name.",             "type": "string", "required": True,  "sample": "Acme Manufacturing"},
            {"name": "email",            "description": "Primary email address.",                  "type": "string",                    "sample": "billing@acme.com"},
            {"name": "phone",            "description": "Primary phone number.",                   "type": "string",                    "sample": "+1 415 555 0100"},
            {"name": "currency",         "description": "Customer billing currency code.",         "type": "string",                    "sample": "USD"},
            {"name": "subsidiary_id",    "description": "Owning subsidiary ID.",                   "type": "string",                    "sample": "1"},
            {"name": "sales_rep",        "description": "Assigned sales representative.",          "type": "string",                    "sample": "Maya Rao"},
            {"name": "status",           "description": "Customer status (CUSTOMER, PROSPECT).",   "type": "string",                    "sample": "CUSTOMER"},
            {"name": "credit_limit",     "description": "Approved credit limit.",                  "type": "number",                    "sample": 100000},
            {"name": "balance",          "description": "Current outstanding AR balance.",         "type": "number",                    "sample": 12850},
            {"name": "date_created",     "description": "Record creation date.",                   "type": "date",                      "sample": "2024-01-15"},
        ],
    ),
    MappingObject(
        id="netsuite-contact",
        displayName="NetSuite Contact",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "NetSuite internal contact ID.",    "type": "string", "required": True,  "sample": "88"},
            {"name": "first_name",   "description": "Contact first name.",              "type": "string", "required": True,  "sample": "Maya"},
            {"name": "last_name",    "description": "Contact last name.",               "type": "string", "required": True,  "sample": "Rao"},
            {"name": "email",        "description": "Contact email address.",           "type": "string",                    "sample": "maya.rao@acme.com"},
            {"name": "phone",        "description": "Contact phone number.",            "type": "string",                    "sample": "+1 415 555 0101"},
            {"name": "title",        "description": "Job title.",                       "type": "string",                    "sample": "CFO"},
            {"name": "company_id",   "description": "Parent customer/company ID.",      "type": "string",                    "sample": "42"},
            {"name": "company_name", "description": "Parent company name.",             "type": "string",                    "sample": "Acme Manufacturing"},
            {"name": "subsidiary",   "description": "Owning subsidiary.",               "type": "string",                    "sample": "EMEA"},
        ],
    ),
    MappingObject(
        id="netsuite-opportunity",
        displayName="NetSuite Opportunity",
        systemId="netsuite",
        fields=[
            {"name": "id",             "description": "NetSuite opportunity ID.",               "type": "string", "required": True,  "sample": "55"},
            {"name": "title",          "description": "Opportunity title / name.",              "type": "string", "required": True,  "sample": "Acme Q4 ERP Expansion"},
            {"name": "entity_id",      "description": "Customer entity ID.",                    "type": "string", "required": True,  "sample": "42"},
            {"name": "entity_name",    "description": "Customer company name.",                 "type": "string",                    "sample": "Acme Manufacturing"},
            {"name": "amount",         "description": "Estimated opportunity value.",           "type": "number",                    "sample": 250000},
            {"name": "probability",    "description": "Win probability percentage (0–100).",    "type": "number",                    "sample": 65},
            {"name": "expected_close", "description": "Expected close date.",                   "type": "date",                      "sample": "2026-12-31"},
            {"name": "stage",          "description": "Sales stage.",                           "type": "string",                    "sample": "Proposal/Price Quote"},
            {"name": "sales_rep",      "description": "Assigned sales rep.",                    "type": "string",                    "sample": "Maya Rao"},
            {"name": "subsidiary_id",  "description": "Owning subsidiary ID.",                  "type": "string",                    "sample": "1"},
            {"name": "currency",       "description": "Currency code.",                         "type": "string",                    "sample": "USD"},
            {"name": "source",         "description": "Lead source.",                           "type": "string",                    "sample": "Web"},
        ],
    ),
    MappingObject(
        id="netsuite-sales-order",
        displayName="NetSuite Sales Order",
        systemId="netsuite",
        fields=[
            {"name": "id",              "description": "NetSuite sales order ID.",       "type": "string", "required": True,  "sample": "SO-1001"},
            {"name": "tran_id",         "description": "Transaction number.",            "type": "string", "required": True,  "sample": "SO1001"},
            {"name": "entity_id",       "description": "Customer entity ID.",            "type": "string", "required": True,  "sample": "42"},
            {"name": "entity_name",     "description": "Customer company name.",         "type": "string",                    "sample": "Acme Manufacturing"},
            {"name": "amount",          "description": "Order total amount.",            "type": "number", "required": True,  "sample": 48500},
            {"name": "tran_date",       "description": "Transaction date.",              "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "ship_date",       "description": "Expected ship date.",            "type": "date",                      "sample": "2026-06-15"},
            {"name": "status",          "description": "Order status.",                  "type": "string",                    "sample": "Pending Fulfillment"},
            {"name": "currency",        "description": "Currency code.",                 "type": "string",                    "sample": "USD"},
            {"name": "subsidiary_id",   "description": "Owning subsidiary ID.",          "type": "string",                    "sample": "1"},
            {"name": "memo",            "description": "Internal memo / notes.",         "type": "string",                    "sample": "Priority order — Q4 close"},
            {"name": "po_number",       "description": "Customer purchase order ref.",   "type": "string",                    "sample": "PO-ACM-9988"},
        ],
    ),
    MappingObject(
        id="netsuite-invoice",
        displayName="NetSuite Invoice",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "NetSuite internal invoice ID.",   "type": "string", "required": True,  "sample": "101"},
            {"name": "tran_id",      "description": "Invoice transaction number.",     "type": "string", "required": True,  "sample": "INV-2026-0042"},
            {"name": "entity_id",    "description": "Customer entity ID.",             "type": "string", "required": True,  "sample": "42"},
            {"name": "entity_name",  "description": "Customer company name.",          "type": "string",                    "sample": "Acme Manufacturing"},
            {"name": "amount",       "description": "Invoice total amount.",           "type": "number", "required": True,  "sample": 12850},
            {"name": "amount_remaining", "description": "Outstanding balance.",        "type": "number",                    "sample": 12850},
            {"name": "tran_date",    "description": "Invoice date.",                   "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "due_date",     "description": "Payment due date.",               "type": "date",   "required": True,  "sample": "2026-07-01"},
            {"name": "currency",     "description": "Currency code.",                  "type": "string",                    "sample": "USD"},
            {"name": "status",       "description": "Invoice status.",                 "type": "string",                    "sample": "Open"},
            {"name": "subsidiary_id","description": "Owning subsidiary ID.",           "type": "string",                    "sample": "1"},
            {"name": "memo",         "description": "Internal memo.",                  "type": "string",                    "sample": "Q2 professional services"},
        ],
    ),
    MappingObject(
        id="netsuite-vendor-bill",
        displayName="NetSuite Vendor Bill",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "NetSuite vendor bill ID.",        "type": "string", "required": True,  "sample": "201"},
            {"name": "tran_id",      "description": "Bill transaction number.",        "type": "string", "required": True,  "sample": "BILL-2026-0088"},
            {"name": "entity_id",    "description": "Vendor entity ID.",               "type": "string", "required": True,  "sample": "V-001"},
            {"name": "entity_name",  "description": "Vendor name.",                   "type": "string",                    "sample": "Tech Supplies Ltd"},
            {"name": "amount",       "description": "Bill total amount.",              "type": "number", "required": True,  "sample": 7200},
            {"name": "tran_date",    "description": "Bill date.",                     "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "due_date",     "description": "Payment due date.",              "type": "date",   "required": True,  "sample": "2026-07-01"},
            {"name": "currency",     "description": "Currency code.",                 "type": "string",                    "sample": "USD"},
            {"name": "status",       "description": "Bill status.",                   "type": "string",                    "sample": "Open"},
            {"name": "ap_account",   "description": "AP account number.",             "type": "string",                    "sample": "2000"},
            {"name": "subsidiary_id","description": "Owning subsidiary ID.",          "type": "string",                    "sample": "1"},
            {"name": "memo",         "description": "Internal memo.",                 "type": "string",                    "sample": "SaaS licenses Q2"},
        ],
    ),
    MappingObject(
        id="netsuite-purchase-order",
        displayName="NetSuite Purchase Order",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "NetSuite PO ID.",                "type": "string", "required": True,  "sample": "301"},
            {"name": "tran_id",      "description": "PO transaction number.",         "type": "string", "required": True,  "sample": "PO-2026-0301"},
            {"name": "entity_id",    "description": "Vendor entity ID.",              "type": "string", "required": True,  "sample": "V-001"},
            {"name": "entity_name",  "description": "Vendor name.",                  "type": "string",                    "sample": "Tech Supplies Ltd"},
            {"name": "amount",       "description": "PO total amount.",              "type": "number", "required": True,  "sample": 15000},
            {"name": "tran_date",    "description": "PO creation date.",             "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "expected_receipt_date", "description": "Expected delivery date.", "type": "date",                   "sample": "2026-06-20"},
            {"name": "status",       "description": "PO status.",                    "type": "string",                    "sample": "Pending Receipt"},
            {"name": "currency",     "description": "Currency code.",                "type": "string",                    "sample": "USD"},
            {"name": "subsidiary_id","description": "Owning subsidiary ID.",         "type": "string",                    "sample": "1"},
            {"name": "memo",         "description": "Internal memo.",                "type": "string",                    "sample": "Hardware refresh batch 2"},
            {"name": "ship_to",      "description": "Delivery address label.",       "type": "string",                    "sample": "HQ — San Francisco"},
        ],
    ),
    MappingObject(
        id="netsuite-journal-entry",
        displayName="NetSuite Journal Entry",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "NetSuite journal entry ID.",     "type": "string", "required": True,  "sample": "JE-401"},
            {"name": "tran_id",      "description": "Journal entry number.",          "type": "string", "required": True,  "sample": "JE2026001"},
            {"name": "tran_date",    "description": "Posting date.",                  "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "account",      "description": "GL account number.",             "type": "string", "required": True,  "sample": "4000"},
            {"name": "debit",        "description": "Debit amount.",                  "type": "number",                    "sample": 12500},
            {"name": "credit",       "description": "Credit amount.",                 "type": "number",                    "sample": 0},
            {"name": "memo",         "description": "Line memo / description.",       "type": "string",                    "sample": "Revenue recognition Q2"},
            {"name": "currency",     "description": "Currency code.",                 "type": "string",                    "sample": "USD"},
            {"name": "subsidiary_id","description": "Owning subsidiary ID.",          "type": "string",                    "sample": "1"},
            {"name": "approved",     "description": "Whether the entry is approved.", "type": "boolean",                   "sample": True},
        ],
    ),
    MappingObject(
        id="netsuite-employee",
        displayName="NetSuite Employee",
        systemId="netsuite",
        fields=[
            {"name": "id",              "description": "NetSuite employee ID.",             "type": "string", "required": True,  "sample": "EMP-001"},
            {"name": "entity_id",       "description": "Employee entity number.",           "type": "string", "required": True,  "sample": "E-001"},
            {"name": "first_name",      "description": "First name.",                       "type": "string", "required": True,  "sample": "Maya"},
            {"name": "last_name",       "description": "Last name.",                        "type": "string", "required": True,  "sample": "Rao"},
            {"name": "email",           "description": "Work email address.",               "type": "string",                    "sample": "maya.rao@company.com"},
            {"name": "title",           "description": "Job title.",                        "type": "string",                    "sample": "CFO"},
            {"name": "department",      "description": "Department name.",                  "type": "string",                    "sample": "Finance"},
            {"name": "subsidiary_id",   "description": "Owning subsidiary ID.",             "type": "string",                    "sample": "1"},
            {"name": "hire_date",       "description": "Employment start date.",            "type": "date",                      "sample": "2023-03-15"},
            {"name": "employment_type", "description": "Full-time, Part-time, Contractor.", "type": "string",                    "sample": "Full-time"},
            {"name": "is_active",       "description": "Whether employee is active.",       "type": "boolean",                   "sample": True},
            {"name": "pay_frequency",   "description": "Payroll frequency.",                "type": "string",                    "sample": "Semi-monthly"},
        ],
    ),
    MappingObject(
        id="netsuite-item",
        displayName="NetSuite Inventory Item",
        systemId="netsuite",
        fields=[
            {"name": "id",               "description": "NetSuite item ID.",                "type": "string", "required": True,  "sample": "ITEM-001"},
            {"name": "item_id",          "description": "Item name / SKU.",                 "type": "string", "required": True,  "sample": "ENT-LIC-2026"},
            {"name": "display_name",     "description": "Display name.",                    "type": "string", "required": True,  "sample": "Enterprise License 2026"},
            {"name": "type",             "description": "Item type (Inventory, Service…).", "type": "string",                    "sample": "Service"},
            {"name": "sales_price",      "description": "Standard sales price.",            "type": "number",                    "sample": 4999},
            {"name": "purchase_price",   "description": "Standard purchase cost.",          "type": "number",                    "sample": 1200},
            {"name": "quantity_on_hand", "description": "Current inventory quantity.",      "type": "number",                    "sample": 150},
            {"name": "unit_of_measure",  "description": "Unit of measure.",                 "type": "string",                    "sample": "Each"},
            {"name": "income_account",   "description": "GL income account.",               "type": "string",                    "sample": "4000"},
            {"name": "cogs_account",     "description": "COGS GL account.",                 "type": "string",                    "sample": "5000"},
            {"name": "is_inactive",      "description": "Whether item is inactive.",        "type": "boolean",                   "sample": False},
        ],
    ),
    MappingObject(
        id="netsuite-expense-report",
        displayName="NetSuite Expense Report",
        systemId="netsuite",
        fields=[
            {"name": "id",           "description": "Expense report ID.",             "type": "string", "required": True,  "sample": "EXP-2026-0055"},
            {"name": "tran_id",      "description": "Transaction number.",            "type": "string", "required": True,  "sample": "ER2026055"},
            {"name": "employee_id",  "description": "Submitting employee ID.",        "type": "string", "required": True,  "sample": "EMP-001"},
            {"name": "employee_name","description": "Submitting employee name.",      "type": "string",                    "sample": "Maya Rao"},
            {"name": "total",        "description": "Total expense amount.",          "type": "number", "required": True,  "sample": 2340},
            {"name": "tran_date",    "description": "Report submission date.",        "type": "date",   "required": True,  "sample": "2026-06-01"},
            {"name": "status",       "description": "Approval status.",               "type": "string",                    "sample": "Pending Approval"},
            {"name": "currency",     "description": "Currency code.",                 "type": "string",                    "sample": "USD"},
            {"name": "department",   "description": "Submitter department.",          "type": "string",                    "sample": "Finance"},
            {"name": "memo",         "description": "Description / purpose.",         "type": "string",                    "sample": "Customer onsite visit — Acme Q2"},
        ],
    ),
    MappingObject(
        id="netsuite-subsidiary",
        displayName="NetSuite Subsidiary",
        systemId="netsuite",
        fields=[
            {"name": "id",            "description": "NetSuite subsidiary ID.",       "type": "string", "required": True,  "sample": "1"},
            {"name": "subsidiary_id", "description": "Subsidiary code.",              "type": "string", "required": True,  "sample": "EMEA"},
            {"name": "name",          "description": "Subsidiary display name.",      "type": "string", "required": True,  "sample": "Acme EMEA Ltd"},
            {"name": "currency",      "description": "Reporting currency.",           "type": "string",                    "sample": "EUR"},
            {"name": "country",       "description": "Country of registration.",      "type": "string",                    "sample": "GB"},
            {"name": "is_elimination","description": "Elimination subsidiary flag.",  "type": "boolean",                   "sample": False},
        ],
    ),
    # ── Salesforce (extra objects from live schema) ───────────────────────────
    MappingObject(
        id="salesforce-account",
        displayName="Salesforce Account",
        systemId="salesforce",
        fields=[
            {"name": "Id",                "description": "Account Salesforce ID (system-assigned, read-only — do not map as a target).", "type": "string", "sample": "0010x000002XyZa"},
            {"name": "Name",              "description": "Account name.",                                       "type": "string", "required": True, "sample": "Acme Manufacturing"},
            {"name": "SAP_Vendor_ID__c",  "description": "External ID — SAP Vendor master ID. Used as upsert key to prevent duplicate Account creation on repeated syncs.", "type": "string", "sample": "V-001"},
            {"name": "Industry",          "description": "Industry vertical.",        "type": "string",                    "sample": "Technology"},
            {"name": "AnnualRevenue",     "description": "Annual revenue.",           "type": "number",                    "sample": 5000000},
            {"name": "BillingCity",       "description": "Billing city.",             "type": "string",                    "sample": "San Francisco"},
            {"name": "Phone",             "description": "Account phone number.",     "type": "string",                    "sample": "+1 415 555 0100"},
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
    MappingObject(
        id="salesforce-project-c",
        displayName="Salesforce Project__c (custom object)",
        systemId="salesforce",
        fields=[
            {"name": "Id",               "description": "Project__c Salesforce record ID (system-assigned; do not map as target).", "type": "string", "sample": "a0B0x000004AbCd"},
            {"name": "Name",             "description": "Project__c display name.",                 "type": "string",                    "sample": "PRJ-1042"},
            {"name": "Status__c",        "description": "Project status picklist.",                 "type": "string", "required": True,  "sample": "In Progress"},
            {"name": "Budget__c",        "description": "Approved project budget.",                 "type": "number",                    "sample": 420000},
            {"name": "Start_Date__c",    "description": "Project start/due date.",                  "type": "date",                      "sample": "2026-03-31"},
            {"name": "Is_Active__c",     "description": "Whether the project is currently active.", "type": "boolean",                   "sample": True},
            {"name": "Project_Owner__c", "description": "Reference to the owning user/contact record.", "type": "string",                "sample": "Maya Rao"},
            {"name": "OwnerId",          "description": "Salesforce record owner ID (system; use lookup_placeholder).", "type": "string", "sample": "0050x000003WxYz"},
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
            {"name": "id",             "description": "Vendor master ID (API field name returned by list_vendors).",  "type": "string", "required": True,  "sample": "V-001"},
            {"name": "vendor_id",      "description": "Vendor master ID (alias — same value as id).",                 "type": "string",                    "sample": "V-001"},
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
