from datetime import UTC, datetime


MOCK_CFO_SUMMARY = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "mock",
    "cash_position": {"amount": 4_250_000, "currency": "USD"},
    "open_receivables": {"amount": 1_175_000, "currency": "USD"},
    "monthly_revenue": {"amount": 2_980_000, "currency": "USD"},
    "kpis": [
        {
            "label": "Cash runway",
            "value": "14.2 months",
            "trend": "up",
            "narrative": "Mock operating cash trend improved against the prior period.",
        },
        {
            "label": "DSO",
            "value": 42,
            "trend": "down",
            "narrative": "Mock receivables collection velocity improved by 3 days.",
        },
        {
            "label": "Gross margin",
            "value": "61.4%",
            "trend": "flat",
            "narrative": "Mock margin stayed within the expected operating band.",
        },
    ],
}

MOCK_TEMPLATE_ROWS: dict[str, list[dict[str, str | float]]] = {
    "cash_position_summary": [
        {"account": "Operating Cash", "balance": 2_850_000, "currency": "USD"},
        {"account": "Money Market", "balance": 1_400_000, "currency": "USD"},
    ],
    "ar_aging_summary": [
        {"bucket": "Current", "amount": 720_000, "currency": "USD"},
        {"bucket": "1-30", "amount": 310_000, "currency": "USD"},
        {"bucket": "31-60", "amount": 110_000, "currency": "USD"},
        {"bucket": "60+", "amount": 35_000, "currency": "USD"},
    ],
    "monthly_revenue_trend": [
        {"period": "2026-01", "revenue": 2_620_000, "currency": "USD"},
        {"period": "2026-02", "revenue": 2_740_000, "currency": "USD"},
        {"period": "2026-03", "revenue": 2_910_000, "currency": "USD"},
        {"period": "2026-04", "revenue": 2_980_000, "currency": "USD"},
    ],
    "pl_vs_budget": [
        {
            "period": "2026-Q1",
            "subsidiary_id": "NA",
            "line": "Revenue",
            "actual": 8_270_000,
            "budget": 7_950_000,
            "variance": 320_000,
            "variance_pct": 4.03,
            "currency": "USD",
        },
        {
            "period": "2026-Q1",
            "subsidiary_id": "NA",
            "line": "Cost of revenue",
            "actual": 3_180_000,
            "budget": 3_250_000,
            "variance": 70_000,
            "variance_pct": 2.15,
            "currency": "USD",
        },
        {
            "period": "2026-Q1",
            "subsidiary_id": "EMEA",
            "line": "Revenue",
            "actual": 4_430_000,
            "budget": 4_500_000,
            "variance": -70_000,
            "variance_pct": -1.56,
            "currency": "USD",
        },
    ],
    "yoy_comparison": [
        {
            "current_year": 2026,
            "prior_year": 2025,
            "subsidiary_id": "NA",
            "metric": "Revenue",
            "current_value": 8_270_000,
            "prior_value": 7_610_000,
            "change": 660_000,
            "change_pct": 8.67,
            "currency": "USD",
        },
        {
            "current_year": 2026,
            "prior_year": 2025,
            "subsidiary_id": "NA",
            "metric": "Gross margin",
            "current_value": 5_090_000,
            "prior_value": 4_630_000,
            "change": 460_000,
            "change_pct": 9.94,
            "currency": "USD",
        },
        {
            "current_year": 2026,
            "prior_year": 2025,
            "subsidiary_id": "EMEA",
            "metric": "Revenue",
            "current_value": 4_430_000,
            "prior_value": 4_210_000,
            "change": 220_000,
            "change_pct": 5.23,
            "currency": "USD",
        },
    ],
    "subsidiary_drilldown": [
        {
            "period": "2026-Q1",
            "subsidiary_id": "NA",
            "subsidiary_name": "North America",
            "department": "Enterprise Services",
            "revenue": 4_950_000,
            "expenses": 2_020_000,
            "operating_income": 2_930_000,
            "currency": "USD",
        },
        {
            "period": "2026-Q1",
            "subsidiary_id": "NA",
            "subsidiary_name": "North America",
            "department": "Customer Success",
            "revenue": 3_320_000,
            "expenses": 1_160_000,
            "operating_income": 2_160_000,
            "currency": "USD",
        },
        {
            "period": "2026-Q1",
            "subsidiary_id": "EMEA",
            "subsidiary_name": "EMEA",
            "department": "Enterprise Services",
            "revenue": 4_430_000,
            "expenses": 1_820_000,
            "operating_income": 2_610_000,
            "currency": "USD",
        },
    ],
    "running_projects": [
        {
            "project_id": "PRJ-1001",
            "project_name": "Revenue Automation Rollout",
            "customer": "Aster Manufacturing",
            "account_manager": "Maya Rao",
            "subsidiary_id": "NA",
            "status": "on_track",
            "budget": 420_000,
            "actual_cost": 231_000,
            "forecast_cost": 398_000,
            "currency": "USD",
        },
        {
            "project_id": "PRJ-1002",
            "project_name": "Multi-Book Close Optimization",
            "customer": "Northstar Retail",
            "account_manager": "Ethan Chen",
            "subsidiary_id": "NA",
            "status": "at_risk",
            "budget": 360_000,
            "actual_cost": 292_000,
            "forecast_cost": 388_000,
            "currency": "USD",
        },
        {
            "project_id": "PRJ-2001",
            "project_name": "EMEA RevRec Controls",
            "customer": "Helio Foods",
            "account_manager": "Maya Rao",
            "subsidiary_id": "EMEA",
            "status": "on_track",
            "budget": 280_000,
            "actual_cost": 141_000,
            "forecast_cost": 265_000,
            "currency": "USD",
        },
    ],
    "overdue_projects_by_account_manager": [
        {
            "account_manager": "Maya Rao",
            "overdue_project_count": 2,
            "total_overdue_amount": 145_000,
            "max_days_overdue": 31,
            "currency": "USD",
        },
        {
            "account_manager": "Ethan Chen",
            "overdue_project_count": 1,
            "total_overdue_amount": 82_000,
            "max_days_overdue": 18,
            "currency": "USD",
        },
    ],
}

# ── CRM ───────────────────────────────────────────────────────────────────────

MOCK_CUSTOMERS: list[dict] = [
    {
        "id": "42", "entity_id": "CUST-0042", "company_name": "Acme Manufacturing",
        "email": "billing@acme.com", "phone": "+1 415 555 0100", "currency": "USD",
        "subsidiary_id": "1", "sales_rep": "Maya Rao", "status": "CUSTOMER",
        "credit_limit": 100_000, "balance": 12_850, "date_created": "2024-01-15",
    },
    {
        "id": "43", "entity_id": "CUST-0043", "company_name": "Zenith Logistics",
        "email": "ap@zenith.io", "phone": "+44 20 7946 0101", "currency": "GBP",
        "subsidiary_id": "2", "sales_rep": "Ethan Chen", "status": "CUSTOMER",
        "credit_limit": 75_000, "balance": 4_320, "date_created": "2024-03-10",
    },
    {
        "id": "44", "entity_id": "CUST-0044", "company_name": "Orbit Tech GmbH",
        "email": "finance@orbit.de", "phone": "+49 30 555 0200", "currency": "EUR",
        "subsidiary_id": "3", "sales_rep": "Aiko Tanaka", "status": "CUSTOMER",
        "credit_limit": 200_000, "balance": 31_200, "date_created": "2023-11-22",
    },
    {
        "id": "55", "entity_id": "LEAD-0055", "company_name": "PineFront Capital",
        "email": "info@pinefront.com", "phone": "+1 212 555 0300", "currency": "USD",
        "subsidiary_id": "1", "sales_rep": "Maya Rao", "status": "PROSPECT",
        "credit_limit": 0, "balance": 0, "date_created": "2026-04-01",
    },
]

MOCK_CONTACTS: list[dict] = [
    {
        "id": "88", "first_name": "Maya", "last_name": "Rao",
        "email": "maya.rao@acme.com", "phone": "+1 415 555 0101", "title": "CFO",
        "company_id": "42", "company_name": "Acme Manufacturing", "subsidiary": "NA",
    },
    {
        "id": "89", "first_name": "James", "last_name": "Wu",
        "email": "james.wu@acme.com", "phone": "+1 415 555 0102", "title": "Controller",
        "company_id": "42", "company_name": "Acme Manufacturing", "subsidiary": "NA",
    },
    {
        "id": "90", "first_name": "Sophie", "last_name": "Laurent",
        "email": "s.laurent@zenith.io", "phone": "+44 20 7946 0102", "title": "Finance Director",
        "company_id": "43", "company_name": "Zenith Logistics", "subsidiary": "EMEA",
    },
    {
        "id": "91", "first_name": "Klaus", "last_name": "Brandt",
        "email": "k.brandt@orbit.de", "phone": "+49 30 555 0201", "title": "CEO",
        "company_id": "44", "company_name": "Orbit Tech GmbH", "subsidiary": "DACH",
    },
]

MOCK_OPPORTUNITIES: list[dict] = [
    {
        "id": "201", "title": "Acme Q4 ERP Expansion", "entity_id": "42",
        "entity_name": "Acme Manufacturing", "amount": 250_000, "probability": 65,
        "expected_close": "2026-12-31", "stage": "Proposal/Price Quote",
        "sales_rep": "Maya Rao", "subsidiary_id": "1", "currency": "USD", "source": "Web",
    },
    {
        "id": "202", "title": "Zenith Logistics Module Rollout", "entity_id": "43",
        "entity_name": "Zenith Logistics", "amount": 95_000, "probability": 40,
        "expected_close": "2026-09-30", "stage": "Needs Analysis",
        "sales_rep": "Ethan Chen", "subsidiary_id": "2", "currency": "GBP", "source": "Referral",
    },
    {
        "id": "203", "title": "Orbit Tech GmbH — HCM Integration", "entity_id": "44",
        "entity_name": "Orbit Tech GmbH", "amount": 180_000, "probability": 80,
        "expected_close": "2026-07-31", "stage": "Negotiation/Review",
        "sales_rep": "Aiko Tanaka", "subsidiary_id": "3", "currency": "EUR", "source": "Partner",
    },
]

# ── Order-to-Cash ──────────────────────────────────────────────────────────────

MOCK_SALES_ORDERS: list[dict] = [
    {
        "id": "SO-1001", "tran_id": "SO1001", "entity_id": "42",
        "entity_name": "Acme Manufacturing", "amount": 48_500,
        "tran_date": "2026-06-01", "ship_date": "2026-06-15",
        "status": "Pending Fulfillment", "currency": "USD",
        "subsidiary_id": "1", "memo": "Priority order — Q4 close", "po_number": "PO-ACM-9988",
    },
    {
        "id": "SO-1002", "tran_id": "SO1002", "entity_id": "43",
        "entity_name": "Zenith Logistics", "amount": 22_000,
        "tran_date": "2026-05-15", "ship_date": "2026-05-28",
        "status": "Billed", "currency": "GBP",
        "subsidiary_id": "2", "memo": "Spring shipment", "po_number": "ZEN-2026-001",
    },
    {
        "id": "SO-1003", "tran_id": "SO1003", "entity_id": "44",
        "entity_name": "Orbit Tech GmbH", "amount": 61_200,
        "tran_date": "2026-06-03", "ship_date": "2026-06-20",
        "status": "Pending Approval", "currency": "EUR",
        "subsidiary_id": "3", "memo": "Annual software licenses", "po_number": "ORB-2026-008",
    },
]

MOCK_INVOICES_EXTENDED: list[dict] = [
    {
        "id": "101", "tran_id": "INV-2026-0042", "entity_id": "42",
        "entity_name": "Acme Manufacturing", "amount": 12_850, "amount_remaining": 12_850,
        "tran_date": "2026-06-01", "due_date": "2026-07-01",
        "currency": "USD", "status": "Open", "subsidiary_id": "1",
        "memo": "Q2 professional services",
    },
    {
        "id": "102", "tran_id": "INV-2026-0043", "entity_id": "43",
        "entity_name": "Zenith Logistics", "amount": 8_400, "amount_remaining": 0,
        "tran_date": "2026-05-01", "due_date": "2026-06-01",
        "currency": "GBP", "status": "Paid", "subsidiary_id": "2",
        "memo": "Consulting — April",
    },
    {
        "id": "103", "tran_id": "INV-2026-0044", "entity_id": "44",
        "entity_name": "Orbit Tech GmbH", "amount": 31_200, "amount_remaining": 31_200,
        "tran_date": "2026-04-15", "due_date": "2026-05-15",
        "currency": "EUR", "status": "Overdue", "subsidiary_id": "3",
        "memo": "License renewal Q2",
    },
]

# ── Procure-to-Pay ────────────────────────────────────────────────────────────

MOCK_VENDOR_BILLS: list[dict] = [
    {
        "id": "201", "tran_id": "BILL-2026-0088", "entity_id": "V-001",
        "entity_name": "Tech Supplies Ltd", "amount": 7_200,
        "tran_date": "2026-06-01", "due_date": "2026-07-01",
        "currency": "USD", "status": "Open", "ap_account": "2000",
        "subsidiary_id": "1", "memo": "SaaS licenses Q2",
    },
    {
        "id": "202", "tran_id": "BILL-2026-0089", "entity_id": "V-002",
        "entity_name": "CloudInfra AG", "amount": 15_400,
        "tran_date": "2026-05-15", "due_date": "2026-06-15",
        "currency": "EUR", "status": "Overdue", "ap_account": "2000",
        "subsidiary_id": "3", "memo": "AWS reserved capacity Q2",
    },
    {
        "id": "203", "tran_id": "BILL-2026-0090", "entity_id": "V-003",
        "entity_name": "Office Interiors Co.", "amount": 3_800,
        "tran_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "USD", "status": "Open", "ap_account": "2100",
        "subsidiary_id": "1", "memo": "Office refit — meeting rooms",
    },
]

MOCK_PURCHASE_ORDERS: list[dict] = [
    {
        "id": "301", "tran_id": "PO-2026-0301", "entity_id": "V-001",
        "entity_name": "Tech Supplies Ltd", "amount": 15_000,
        "tran_date": "2026-06-01", "expected_receipt_date": "2026-06-20",
        "status": "Pending Receipt", "currency": "USD",
        "subsidiary_id": "1", "memo": "Hardware refresh batch 2", "ship_to": "HQ — San Francisco",
    },
    {
        "id": "302", "tran_id": "PO-2026-0302", "entity_id": "V-002",
        "entity_name": "CloudInfra AG", "amount": 48_000,
        "tran_date": "2026-05-01", "expected_receipt_date": "2026-05-10",
        "status": "Fully Received", "currency": "EUR",
        "subsidiary_id": "3", "memo": "Annual cloud capacity prepay", "ship_to": "Berlin Office",
    },
    {
        "id": "303", "tran_id": "PO-2026-0303", "entity_id": "V-004",
        "entity_name": "Stationery Direct", "amount": 850,
        "tran_date": "2026-06-06", "expected_receipt_date": "2026-06-10",
        "status": "Pending Approval", "currency": "USD",
        "subsidiary_id": "1", "memo": "Office supplies June", "ship_to": "HQ — San Francisco",
    },
]

# ── GL ────────────────────────────────────────────────────────────────────────

MOCK_JOURNAL_ENTRIES: list[dict] = [
    {
        "id": "JE-401", "tran_id": "JE2026001", "tran_date": "2026-06-01", "period": "JUN-26",
        "account": "4000", "debit": 12_500, "credit": 0,
        "memo": "Revenue recognition Q2", "currency": "USD", "subsidiary_id": "1", "approved": True,
    },
    {
        "id": "JE-402", "tran_id": "JE2026001", "tran_date": "2026-06-01", "period": "JUN-26",
        "account": "1200", "debit": 0, "credit": 12_500,
        "memo": "Revenue recognition Q2 — offset", "currency": "USD", "subsidiary_id": "1", "approved": True,
    },
    {
        "id": "JE-403", "tran_id": "JE2026002", "tran_date": "2026-06-03", "period": "JUN-26",
        "account": "6100", "debit": 3_200, "credit": 0,
        "memo": "Accrued payroll June W1", "currency": "USD", "subsidiary_id": "1", "approved": True,
    },
    {
        "id": "JE-404", "tran_id": "JE2026002", "tran_date": "2026-06-03", "period": "JUN-26",
        "account": "2300", "debit": 0, "credit": 3_200,
        "memo": "Accrued payroll June W1 — offset", "currency": "USD", "subsidiary_id": "1", "approved": True,
    },
    {
        "id": "JE-405", "tran_id": "JE2026003", "tran_date": "2026-06-05", "period": "JUN-26",
        "account": "5000", "debit": 2_100, "credit": 0,
        "memo": "COGS — June licence batch", "currency": "USD", "subsidiary_id": "1", "approved": False,
    },
]

# ── HR ────────────────────────────────────────────────────────────────────────

MOCK_EMPLOYEES: list[dict] = [
    {
        "id": "EMP-001", "entity_id": "E-001", "first_name": "Maya", "last_name": "Rao",
        "email": "maya.rao@company.com", "title": "CFO", "department": "Finance",
        "subsidiary_id": "1", "hire_date": "2023-03-15",
        "employment_type": "Full-time", "is_active": True, "pay_frequency": "Semi-monthly",
    },
    {
        "id": "EMP-002", "entity_id": "E-002", "first_name": "Ethan", "last_name": "Chen",
        "email": "ethan.chen@company.com", "title": "VP Sales", "department": "Sales",
        "subsidiary_id": "1", "hire_date": "2022-07-01",
        "employment_type": "Full-time", "is_active": True, "pay_frequency": "Semi-monthly",
    },
    {
        "id": "EMP-003", "entity_id": "E-003", "first_name": "Aiko", "last_name": "Tanaka",
        "email": "aiko.tanaka@company.com", "title": "Sales Manager APAC", "department": "Sales",
        "subsidiary_id": "4", "hire_date": "2024-01-10",
        "employment_type": "Full-time", "is_active": True, "pay_frequency": "Monthly",
    },
    {
        "id": "EMP-004", "entity_id": "E-004", "first_name": "Sophie", "last_name": "Laurent",
        "email": "sophie.laurent@company.com", "title": "Finance Director EMEA", "department": "Finance",
        "subsidiary_id": "2", "hire_date": "2021-09-01",
        "employment_type": "Full-time", "is_active": True, "pay_frequency": "Monthly",
    },
    {
        "id": "EMP-005", "entity_id": "E-005", "first_name": "James", "last_name": "Wu",
        "email": "james.wu@company.com", "title": "Controller", "department": "Finance",
        "subsidiary_id": "1", "hire_date": "2023-11-15",
        "employment_type": "Full-time", "is_active": True, "pay_frequency": "Semi-monthly",
    },
]

# ── Inventory ─────────────────────────────────────────────────────────────────

MOCK_ITEMS: list[dict] = [
    {
        "id": "ITEM-001", "item_id": "ENT-LIC-2026", "display_name": "Enterprise License 2026",
        "type": "Service", "sales_price": 4_999, "purchase_price": 0,
        "quantity_on_hand": 0, "unit_of_measure": "Each",
        "income_account": "4000", "cogs_account": "5000", "is_inactive": False,
    },
    {
        "id": "ITEM-002", "item_id": "PRO-SVCS-HR", "display_name": "Professional Services — Hourly",
        "type": "Service", "sales_price": 225, "purchase_price": 0,
        "quantity_on_hand": 0, "unit_of_measure": "Hour",
        "income_account": "4100", "cogs_account": "5100", "is_inactive": False,
    },
    {
        "id": "ITEM-003", "item_id": "HW-LAPTOP-16", "display_name": "Laptop 16-inch (M-series)",
        "type": "Inventory", "sales_price": 2_499, "purchase_price": 1_450,
        "quantity_on_hand": 28, "unit_of_measure": "Each",
        "income_account": "4200", "cogs_account": "5200", "is_inactive": False,
    },
    {
        "id": "ITEM-004", "item_id": "HW-MONITOR-4K", "display_name": "4K Monitor 27-inch",
        "type": "Inventory", "sales_price": 699, "purchase_price": 340,
        "quantity_on_hand": 42, "unit_of_measure": "Each",
        "income_account": "4200", "cogs_account": "5200", "is_inactive": False,
    },
    {
        "id": "ITEM-005", "item_id": "SUPT-ANNUAL", "display_name": "Annual Support Contract",
        "type": "Service", "sales_price": 1_200, "purchase_price": 0,
        "quantity_on_hand": 0, "unit_of_measure": "Each",
        "income_account": "4300", "cogs_account": "5000", "is_inactive": False,
    },
    {
        "id": "ITEM-006", "item_id": "LEGACY-PKG-V1", "display_name": "Legacy Package v1 (discontinued)",
        "type": "Service", "sales_price": 799, "purchase_price": 0,
        "quantity_on_hand": 0, "unit_of_measure": "Each",
        "income_account": "4000", "cogs_account": "5000", "is_inactive": True,
    },
]

# ── Expense Reports ───────────────────────────────────────────────────────────

MOCK_EXPENSE_REPORTS: list[dict] = [
    {
        "id": "EXP-2026-0055", "tran_id": "ER2026055", "employee_id": "EMP-001",
        "employee_name": "Maya Rao", "total": 2_340,
        "tran_date": "2026-06-01", "status": "Pending Approval",
        "currency": "USD", "department": "Finance",
        "memo": "Customer onsite visit — Acme Q2",
    },
    {
        "id": "EXP-2026-0056", "tran_id": "ER2026056", "employee_id": "EMP-002",
        "employee_name": "Ethan Chen", "total": 4_820,
        "tran_date": "2026-05-28", "status": "Approved",
        "currency": "USD", "department": "Sales",
        "memo": "Sales conference — Chicago",
    },
    {
        "id": "EXP-2026-0057", "tran_id": "ER2026057", "employee_id": "EMP-004",
        "employee_name": "Sophie Laurent", "total": 1_150,
        "tran_date": "2026-06-04", "status": "Pending Approval",
        "currency": "GBP", "department": "Finance",
        "memo": "EMEA finance offsite — London",
    },
]

# ── Subsidiaries ─────────────────────────────────────────────────────────────

MOCK_SUBSIDIARIES: list[dict] = [
    {"id": "1", "subsidiary_id": "NA", "name": "Acme Group — North America", "currency": "USD", "country": "US", "is_elimination": False},
    {"id": "2", "subsidiary_id": "EMEA", "name": "Acme EMEA Ltd", "currency": "EUR", "country": "GB", "is_elimination": False},
    {"id": "3", "subsidiary_id": "DACH", "name": "Acme GmbH", "currency": "EUR", "country": "DE", "is_elimination": False},
    {"id": "4", "subsidiary_id": "APAC", "name": "Acme Asia Pacific Pte Ltd", "currency": "SGD", "country": "SG", "is_elimination": False},
    {"id": "99", "subsidiary_id": "ELIM", "name": "Elimination", "currency": "USD", "country": "US", "is_elimination": True},
]
