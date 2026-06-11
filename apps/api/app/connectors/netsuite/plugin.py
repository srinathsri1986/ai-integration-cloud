"""NetSuite connector plugin — wraps mock implementation; live connector activated when credentials present."""
from __future__ import annotations

import logging

from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject
from .mock_connector import MockNetSuiteConnector
from .mock_data import (
    MOCK_CUSTOMERS,
    MOCK_CONTACTS,
    MOCK_OPPORTUNITIES,
    MOCK_SALES_ORDERS,
    MOCK_INVOICES_EXTENDED,
    MOCK_VENDOR_BILLS,
    MOCK_PURCHASE_ORDERS,
    MOCK_JOURNAL_ENTRIES,
    MOCK_EMPLOYEES,
    MOCK_ITEMS,
)

logger = logging.getLogger(__name__)

_mock = MockNetSuiteConnector()


# ── Live connector wiring (OAuth 1.0a token-based auth) ──────────────────────
#
# Mirrors the Salesforce plugin's _get_live_creds / _execute_live pattern:
# credentials are resolved from the encrypted vault, and a real
# NetSuiteLiveConnector (HMAC-SHA256 TBA signing — see live_connector.py) is
# used whenever they're present. Any failure falls back to mock data so the
# UI never breaks — but is logged so a "live" connector never silently behaves
# like mock without a trace (the simple-salesforce lesson).

_LIVE_RECORD_TOOL_MAP: dict[str, tuple[str, str]] = {
    # tool_id -> (NetSuite REST record type, mock-data key for filtering shape)
    "crm.list_customers": ("customer", "entity_id"),
    "crm.list_opportunities": ("opportunity", "entity_id"),
    "o2c.list_sales_orders": ("salesOrder", "entity_id"),
    "o2c.list_invoices": ("invoice", "entity_id"),
    "p2p.list_vendor_bills": ("vendorBill", "entity_id"),
    "p2p.list_purchase_orders": ("purchaseOrder", "entity_id"),
}


def _get_live_creds(tenant_id: int | None = None) -> dict | None:
    """Return decrypted NetSuite token-based-auth credential dict, or None if not configured."""
    try:
        from app.services.credential_service import credential_service
        return credential_service.get_credentials("netsuite", tenant_id)
    except Exception as exc:
        logger.debug("Could not load NetSuite credentials: %s", exc)
    return None


def _build_live_connector(creds: dict):
    """Construct a NetSuiteLiveConnector from a decrypted credential dict."""
    from .live_connector import NetSuiteLiveConfig, NetSuiteLiveConnector

    config = NetSuiteLiveConfig(
        account_id=creds.get("account_id", ""),
        consumer_key=creds.get("consumer_key", ""),
        consumer_secret=creds.get("consumer_secret", ""),
        token_id=creds.get("token_id", ""),
        token_secret=creds.get("token_secret", ""),
    )
    return NetSuiteLiveConnector(config)


def _execute_live(tool_id: str, params: dict, creds: dict) -> dict:
    """Dispatch a list-style tool call to the real NetSuite REST Record API."""
    mapping = _LIVE_RECORD_TOOL_MAP.get(tool_id)
    if mapping is None:
        raise RuntimeError(f"NetSuite tool '{tool_id}' has no live implementation yet.")

    record_type, _filter_key = mapping
    connector = _build_live_connector(creds)
    limit = int(params.get("limit", 50))
    records = connector.list_record(record_type, limit=limit)
    return {
        "connector": "netsuite",
        "tool": tool_id,
        "mode": "live",
        "source": "live",
        "records": records,
        "count": len(records),
    }

_TOOLS: list[ConnectorTool] = [
    # ── CFO / Finance reporting ────────────────────────────────────────────────
    ConnectorTool(
        tool_id="cfo.dashboard_summary",
        label="CFO Dashboard Summary",
        description="Summarised cash, AR and revenue KPIs for the CFO dashboard.",
        connector_id="netsuite",
    ),
    ConnectorTool(
        tool_id="cfo.pl_vs_budget",
        label="P/L vs Budget",
        description="Profit and loss actuals compared with approved budget.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("period", "string", False, "Reporting period e.g. 2026-Q1"),
            ConnectorToolParam("subsidiary_id", "string", False, "Subsidiary identifier"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.yoy_comparison",
        label="Year-over-Year Comparison",
        description="YoY revenue and cost comparison for CFO reporting.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("current_year", "number", False, "Current year"),
            ConnectorToolParam("prior_year", "number", False, "Prior year"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.subsidiary_drilldown",
        label="Subsidiary Drilldown",
        description="P/L breakdown by approved subsidiary.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("subsidiary_id", "string", True, "Subsidiary identifier"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.running_projects",
        label="Running Projects",
        description="List of active projects with budget and timeline status.",
        connector_id="netsuite",
    ),
    ConnectorTool(
        tool_id="cfo.overdue_projects_by_account_manager",
        label="Overdue Projects by Account Manager",
        description="Projects overdue grouped by account manager.",
        connector_id="netsuite",
    ),
    # ── CRM ───────────────────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="crm.list_customers",
        label="List Customers",
        description="Retrieve active customers with balance and subsidiary details.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("subsidiary_id", "string", False, "Filter by subsidiary ID"),
            ConnectorToolParam("limit", "number", False, "Maximum records to return (default 50)"),
        ],
    ),
    ConnectorTool(
        tool_id="crm.list_contacts",
        label="List Contacts",
        description="Retrieve contacts linked to a customer account.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("company_id", "string", False, "Filter by parent customer ID"),
        ],
    ),
    ConnectorTool(
        tool_id="crm.list_opportunities",
        label="List Opportunities",
        description="Retrieve open CRM opportunities with stage and probability.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("sales_rep", "string", False, "Filter by sales rep name"),
            ConnectorToolParam("min_probability", "number", False, "Minimum win probability (0–100)"),
        ],
    ),
    # ── Order-to-Cash ─────────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="o2c.list_sales_orders",
        label="List Sales Orders",
        description="Retrieve sales orders with status and fulfilment details.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("status", "string", False, "Filter by order status"),
            ConnectorToolParam("entity_id", "string", False, "Filter by customer ID"),
        ],
    ),
    ConnectorTool(
        tool_id="o2c.list_invoices",
        label="List Invoices",
        description="Retrieve AR invoices with outstanding balance and due date.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("status", "string", False, "Open | Paid | Overdue"),
            ConnectorToolParam("entity_id", "string", False, "Filter by customer ID"),
        ],
    ),
    # ── Procure-to-Pay ────────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="p2p.list_vendor_bills",
        label="List Vendor Bills",
        description="Retrieve AP vendor bills with approval status and due dates.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("status", "string", False, "Open | Paid | Overdue"),
            ConnectorToolParam("entity_id", "string", False, "Filter by vendor ID"),
        ],
    ),
    ConnectorTool(
        tool_id="p2p.list_purchase_orders",
        label="List Purchase Orders",
        description="Retrieve purchase orders with receipt status.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("status", "string", False, "Filter by PO status"),
            ConnectorToolParam("entity_id", "string", False, "Filter by vendor ID"),
        ],
    ),
    # ── GL / Accounting ───────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="gl.list_journal_entries",
        label="List Journal Entries",
        description="Retrieve approved GL journal entries for a period.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("period", "string", False, "Accounting period e.g. JUN-26"),
            ConnectorToolParam("account", "string", False, "Filter by GL account number"),
        ],
    ),
    # ── HR ────────────────────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="hr.list_employees",
        label="List Employees",
        description="Retrieve active employees with department and subsidiary.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("department", "string", False, "Filter by department name"),
            ConnectorToolParam("subsidiary_id", "string", False, "Filter by subsidiary ID"),
        ],
    ),
    # ── Inventory ─────────────────────────────────────────────────────────────
    ConnectorTool(
        tool_id="inv.list_items",
        label="List Inventory Items",
        description="Retrieve inventory and service items with pricing.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("type", "string", False, "Item type filter e.g. Inventory, Service"),
            ConnectorToolParam("is_inactive", "boolean", False, "Include inactive items"),
        ],
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}


class NetSuitePlugin:
    connector_id = "netsuite"
    name = "Oracle NetSuite"
    logo_slug = "netsuite"
    auth_scheme = "token_based"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict, tenant_id: int | None = None) -> dict:  # noqa: C901
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown NetSuite tool: {tool_id!r}")

        # ── Live mode — try the real NetSuite REST API for list-style tools ───
        if tool_id in _LIVE_RECORD_TOOL_MAP:
            creds = _get_live_creds(tenant_id)
            if creds:
                try:
                    return _execute_live(tool_id, params, creds)
                except Exception as exc:
                    logger.warning(
                        "NetSuite live execution failed for tool=%s, falling back to mock: %s",
                        tool_id,
                        exc,
                    )

        # ── CFO tools — delegate to CfoService (existing mock) ────────────────
        if tool_id == "cfo.dashboard_summary":
            from app.services.cfo_service import CfoService
            return CfoService().dashboard_summary().model_dump(by_alias=True)

        if tool_id == "cfo.pl_vs_budget":
            from app.services.cfo_service import CfoService
            return CfoService().pl_vs_budget(
                period=params.get("period", "2026-Q1"),
                subsidiary_id=params.get("subsidiary_id", "NA"),
            ).model_dump(by_alias=True)

        if tool_id == "cfo.yoy_comparison":
            from app.services.cfo_service import CfoService
            return CfoService().yoy_comparison(
                current_year=int(params.get("current_year", 2026)),
                prior_year=int(params.get("prior_year", 2025)),
                subsidiary_id=params.get("subsidiary_id", "NA"),
            ).model_dump(by_alias=True)

        if tool_id == "cfo.subsidiary_drilldown":
            from app.services.cfo_service import CfoService
            return CfoService().subsidiary_drilldown(
                period=params.get("period", "2026-Q1"),
                subsidiary_id=params.get("subsidiary_id", "EMEA"),
            ).model_dump(by_alias=True)

        if tool_id == "cfo.running_projects":
            from app.services.cfo_service import CfoService
            return CfoService().running_projects().model_dump(by_alias=True)

        if tool_id == "cfo.overdue_projects_by_account_manager":
            from app.services.cfo_service import CfoService
            return CfoService().overdue_projects_by_account_manager().model_dump(by_alias=True)

        # ── CRM tools ─────────────────────────────────────────────────────────
        if tool_id == "crm.list_customers":
            sub = params.get("subsidiary_id")
            limit = int(params.get("limit", 50))
            rows = [r for r in MOCK_CUSTOMERS if not sub or r["subsidiary_id"] == sub]
            return {"source": "mock", "records": rows[:limit], "count": len(rows[:limit])}

        if tool_id == "crm.list_contacts":
            company_id = params.get("company_id")
            rows = [r for r in MOCK_CONTACTS if not company_id or r["company_id"] == company_id]
            return {"source": "mock", "records": rows, "count": len(rows)}

        if tool_id == "crm.list_opportunities":
            sales_rep = params.get("sales_rep")
            min_prob = float(params.get("min_probability", 0))
            rows = [
                r for r in MOCK_OPPORTUNITIES
                if (not sales_rep or r["sales_rep"] == sales_rep)
                and r["probability"] >= min_prob
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        # ── Order-to-Cash ─────────────────────────────────────────────────────
        if tool_id == "o2c.list_sales_orders":
            status = params.get("status")
            entity_id = params.get("entity_id")
            rows = [
                r for r in MOCK_SALES_ORDERS
                if (not status or r["status"] == status)
                and (not entity_id or r["entity_id"] == entity_id)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        if tool_id == "o2c.list_invoices":
            status = params.get("status")
            entity_id = params.get("entity_id")
            rows = [
                r for r in MOCK_INVOICES_EXTENDED
                if (not status or r["status"] == status)
                and (not entity_id or r["entity_id"] == entity_id)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        # ── Procure-to-Pay ────────────────────────────────────────────────────
        if tool_id == "p2p.list_vendor_bills":
            status = params.get("status")
            entity_id = params.get("entity_id")
            rows = [
                r for r in MOCK_VENDOR_BILLS
                if (not status or r["status"] == status)
                and (not entity_id or r["entity_id"] == entity_id)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        if tool_id == "p2p.list_purchase_orders":
            status = params.get("status")
            entity_id = params.get("entity_id")
            rows = [
                r for r in MOCK_PURCHASE_ORDERS
                if (not status or r["status"] == status)
                and (not entity_id or r["entity_id"] == entity_id)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        # ── GL ────────────────────────────────────────────────────────────────
        if tool_id == "gl.list_journal_entries":
            period = params.get("period")
            account = params.get("account")
            rows = [
                r for r in MOCK_JOURNAL_ENTRIES
                if (not period or r.get("period") == period)
                and (not account or r["account"] == account)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        # ── HR ────────────────────────────────────────────────────────────────
        if tool_id == "hr.list_employees":
            dept = params.get("department")
            sub = params.get("subsidiary_id")
            rows = [
                r for r in MOCK_EMPLOYEES
                if (not dept or r["department"] == dept)
                and (not sub or r["subsidiary_id"] == sub)
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        # ── Inventory ─────────────────────────────────────────────────────────
        if tool_id == "inv.list_items":
            item_type = params.get("type")
            include_inactive = params.get("is_inactive", False)
            rows = [
                r for r in MOCK_ITEMS
                if (not item_type or r["type"] == item_type)
                and (include_inactive or not r.get("is_inactive", False))
            ]
            return {"source": "mock", "records": rows, "count": len(rows)}

        raise KeyError(f"Unhandled NetSuite tool: {tool_id!r}")

    def test_connection(self) -> dict:
        creds = _get_live_creds()
        if creds:
            try:
                connector = _build_live_connector(creds)
                result = connector.test_connection()
                if result.get("ok"):
                    return result
                # Live config present but the API call failed — surface the
                # real reason rather than pretending we're in mock mode.
                return result
            except Exception as exc:
                logger.warning("NetSuite live connection test failed: %s", exc)
                return {"ok": False, "mode": "live", "message": f"NetSuite connection test failed: {exc}"}

        return {"ok": True, "mode": "mock", "message": "NetSuite mock connector is ready (mock mode). Click Connect to link a NetSuite account."}

    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:  # noqa: PLR0915
        """Return NetSuite record types with full field definitions.

        The curated catalog below is always used for *field-level* metadata —
        NetSuite's REST metadata-catalog only exposes record-type names, not
        field definitions, so faithfully discovering field schemas live would
        require parsing per-record OpenAPI documents (a larger follow-up).
        When live credentials are present we additionally ping the metadata
        catalog purely to confirm connectivity / log which record types exist
        in the connected account — but the curated, richly-typed catalog is
        what powers the mapping UI.
        """
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                connector = _build_live_connector(creds)
                live_record_types = connector.fetch_schema_objects()
                if live_record_types:
                    logger.info(
                        "NetSuite live account exposes %d record types (using curated field catalog for mapping).",
                        len(live_record_types),
                    )
            except Exception as exc:
                logger.warning("Could not reach NetSuite live metadata catalog: %s", exc)

        return [
            SchemaObject("customer", "Customer", [
                SchemaField("id", "Internal ID", "string", required=True, sample="42"),
                SchemaField("entity_id", "Entity ID", "string", required=True, sample="CUST-0042"),
                SchemaField("company_name", "Company Name", "string", required=True, sample="Acme Manufacturing"),
                SchemaField("email", "Email", "string", sample="billing@acme.com"),
                SchemaField("phone", "Phone", "string", sample="+1 415 555 0100"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("sales_rep", "Sales Rep", "string", sample="Maya Rao"),
                SchemaField("status", "Status", "string", sample="CUSTOMER"),
                SchemaField("credit_limit", "Credit Limit", "number", sample="100000"),
                SchemaField("balance", "Balance", "number", sample="12850"),
                SchemaField("date_created", "Date Created", "date", sample="2024-01-15"),
            ]),
            SchemaObject("contact", "Contact", [
                SchemaField("id", "Internal ID", "string", required=True, sample="88"),
                SchemaField("first_name", "First Name", "string", required=True, sample="Maya"),
                SchemaField("last_name", "Last Name", "string", required=True, sample="Rao"),
                SchemaField("email", "Email", "string", sample="maya.rao@acme.com"),
                SchemaField("phone", "Phone", "string", sample="+1 415 555 0101"),
                SchemaField("title", "Title", "string", sample="CFO"),
                SchemaField("company_id", "Company ID", "string", sample="42"),
                SchemaField("company_name", "Company Name", "string", sample="Acme Manufacturing"),
                SchemaField("subsidiary", "Subsidiary", "string", sample="EMEA"),
            ]),
            SchemaObject("opportunity", "Opportunity", [
                SchemaField("id", "Internal ID", "string", required=True, sample="55"),
                SchemaField("title", "Title", "string", required=True, sample="Acme Q4 ERP Expansion"),
                SchemaField("entity_id", "Customer ID", "string", required=True, sample="42"),
                SchemaField("entity_name", "Customer Name", "string", sample="Acme Manufacturing"),
                SchemaField("amount", "Amount", "number", sample="250000"),
                SchemaField("probability", "Probability %", "number", sample="65"),
                SchemaField("expected_close", "Expected Close", "date", sample="2026-12-31"),
                SchemaField("stage", "Stage", "string", sample="Proposal/Price Quote"),
                SchemaField("sales_rep", "Sales Rep", "string", sample="Maya Rao"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("source", "Lead Source", "string", sample="Web"),
            ]),
            SchemaObject("salesorder", "Sales Order", [
                SchemaField("id", "Internal ID", "string", required=True, sample="SO-1001"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="SO1001"),
                SchemaField("entity_id", "Customer ID", "string", required=True, sample="42"),
                SchemaField("entity_name", "Customer Name", "string", sample="Acme Manufacturing"),
                SchemaField("amount", "Amount", "number", required=True, sample="48500"),
                SchemaField("tran_date", "Transaction Date", "date", required=True, sample="2026-06-01"),
                SchemaField("ship_date", "Ship Date", "date", sample="2026-06-15"),
                SchemaField("status", "Status", "string", sample="Pending Fulfillment"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("memo", "Memo", "string", sample="Priority order — Q4 close"),
                SchemaField("po_number", "Customer PO #", "string", sample="PO-ACM-9988"),
            ]),
            SchemaObject("invoice", "Invoice", [
                SchemaField("id", "Internal ID", "string", required=True, sample="101"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="INV-2026-0042"),
                SchemaField("entity_id", "Customer ID", "string", required=True, sample="42"),
                SchemaField("entity_name", "Customer Name", "string", sample="Acme Manufacturing"),
                SchemaField("amount", "Amount", "number", required=True, sample="12850"),
                SchemaField("amount_remaining", "Amount Remaining", "number", sample="12850"),
                SchemaField("tran_date", "Invoice Date", "date", required=True, sample="2026-06-01"),
                SchemaField("due_date", "Due Date", "date", required=True, sample="2026-07-01"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("status", "Status", "string", sample="Open"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("memo", "Memo", "string", sample="Q2 professional services"),
            ]),
            SchemaObject("vendorbill", "Vendor Bill", [
                SchemaField("id", "Internal ID", "string", required=True, sample="201"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="BILL-2026-0088"),
                SchemaField("entity_id", "Vendor ID", "string", required=True, sample="V-001"),
                SchemaField("entity_name", "Vendor Name", "string", sample="Tech Supplies Ltd"),
                SchemaField("amount", "Amount", "number", required=True, sample="7200"),
                SchemaField("tran_date", "Bill Date", "date", required=True, sample="2026-06-01"),
                SchemaField("due_date", "Due Date", "date", required=True, sample="2026-07-01"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("status", "Status", "string", sample="Open"),
                SchemaField("ap_account", "AP Account", "string", sample="2000"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("memo", "Memo", "string", sample="SaaS licenses Q2"),
            ]),
            SchemaObject("purchaseorder", "Purchase Order", [
                SchemaField("id", "Internal ID", "string", required=True, sample="301"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="PO-2026-0301"),
                SchemaField("entity_id", "Vendor ID", "string", required=True, sample="V-001"),
                SchemaField("entity_name", "Vendor Name", "string", sample="Tech Supplies Ltd"),
                SchemaField("amount", "Amount", "number", required=True, sample="15000"),
                SchemaField("tran_date", "PO Date", "date", required=True, sample="2026-06-01"),
                SchemaField("expected_receipt_date", "Expected Receipt", "date", sample="2026-06-20"),
                SchemaField("status", "Status", "string", sample="Pending Receipt"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("memo", "Memo", "string", sample="Hardware refresh batch 2"),
                SchemaField("ship_to", "Ship To", "string", sample="HQ — San Francisco"),
            ]),
            SchemaObject("journalentry", "Journal Entry", [
                SchemaField("id", "Internal ID", "string", required=True, sample="JE-401"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="JE2026001"),
                SchemaField("tran_date", "Posting Date", "date", required=True, sample="2026-06-01"),
                SchemaField("account", "GL Account", "string", required=True, sample="4000"),
                SchemaField("debit", "Debit", "number", sample="12500"),
                SchemaField("credit", "Credit", "number", sample="0"),
                SchemaField("memo", "Memo", "string", sample="Revenue recognition Q2"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("approved", "Approved", "boolean", sample="true"),
            ]),
            SchemaObject("employee", "Employee", [
                SchemaField("id", "Internal ID", "string", required=True, sample="EMP-001"),
                SchemaField("entity_id", "Entity No.", "string", required=True, sample="E-001"),
                SchemaField("first_name", "First Name", "string", required=True, sample="Maya"),
                SchemaField("last_name", "Last Name", "string", required=True, sample="Rao"),
                SchemaField("email", "Work Email", "string", sample="maya.rao@company.com"),
                SchemaField("title", "Job Title", "string", sample="CFO"),
                SchemaField("department", "Department", "string", sample="Finance"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="1"),
                SchemaField("hire_date", "Hire Date", "date", sample="2023-03-15"),
                SchemaField("employment_type", "Employment Type", "string", sample="Full-time"),
                SchemaField("is_active", "Is Active", "boolean", sample="true"),
                SchemaField("pay_frequency", "Pay Frequency", "string", sample="Semi-monthly"),
            ]),
            SchemaObject("inventoryitem", "Inventory Item", [
                SchemaField("id", "Internal ID", "string", required=True, sample="ITEM-001"),
                SchemaField("item_id", "Item Name / SKU", "string", required=True, sample="ENT-LIC-2026"),
                SchemaField("display_name", "Display Name", "string", required=True, sample="Enterprise License 2026"),
                SchemaField("type", "Item Type", "string", sample="Service"),
                SchemaField("sales_price", "Sales Price", "number", sample="4999"),
                SchemaField("purchase_price", "Purchase Price", "number", sample="1200"),
                SchemaField("quantity_on_hand", "Qty on Hand", "number", sample="150"),
                SchemaField("unit_of_measure", "Unit of Measure", "string", sample="Each"),
                SchemaField("income_account", "Income Account", "string", sample="4000"),
                SchemaField("cogs_account", "COGS Account", "string", sample="5000"),
                SchemaField("is_inactive", "Is Inactive", "boolean", sample="false"),
            ]),
            SchemaObject("expensereport", "Expense Report", [
                SchemaField("id", "Internal ID", "string", required=True, sample="EXP-2026-0055"),
                SchemaField("tran_id", "Transaction No.", "string", required=True, sample="ER2026055"),
                SchemaField("employee_id", "Employee ID", "string", required=True, sample="EMP-001"),
                SchemaField("employee_name", "Employee Name", "string", sample="Maya Rao"),
                SchemaField("total", "Total Amount", "number", required=True, sample="2340"),
                SchemaField("tran_date", "Submission Date", "date", required=True, sample="2026-06-01"),
                SchemaField("status", "Status", "string", sample="Pending Approval"),
                SchemaField("currency", "Currency", "string", sample="USD"),
                SchemaField("department", "Department", "string", sample="Finance"),
                SchemaField("memo", "Purpose", "string", sample="Customer onsite visit — Acme Q2"),
            ]),
            SchemaObject("subsidiary", "Subsidiary", [
                SchemaField("id", "Internal ID", "string", required=True, sample="1"),
                SchemaField("subsidiary_id", "Subsidiary Code", "string", required=True, sample="EMEA"),
                SchemaField("name", "Name", "string", required=True, sample="Acme EMEA Ltd"),
                SchemaField("currency", "Currency", "string", sample="EUR"),
                SchemaField("country", "Country", "string", sample="GB"),
                SchemaField("is_elimination", "Is Elimination", "boolean", sample="false"),
            ]),
            SchemaObject("project", "Project", [
                SchemaField("project_id", "Project ID", "string", required=True, sample="PRJ-1042"),
                SchemaField("customer_name", "Customer Name", "string", required=True, sample="Acme Manufacturing"),
                SchemaField("account_manager", "Account Manager", "string", sample="Maya Rao"),
                SchemaField("budget_amount", "Budget Amount", "number", sample="420000"),
                SchemaField("due_date", "Due Date", "date", sample="2026-03-31"),
                SchemaField("status", "Status", "string", sample="In Progress"),
                SchemaField("subsidiary_id", "Subsidiary ID", "string", sample="EMEA"),
            ]),
        ]
