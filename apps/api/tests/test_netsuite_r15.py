"""R15 — NetSuite connector expansion tests.

Covers:
- All 13 record types present in fetch_schema()
- All 17 tools registered and callable via execute_tool()
- New mock data collections (customers, contacts, opportunities, etc.)
- Tool filtering / param logic
- Live connector OAuth header structure (no real network calls)
- Mapping catalog has all new netsuite-* objects
"""
import pytest

from app.connectors.netsuite.plugin import NetSuitePlugin
from app.connectors.netsuite.mock_data import (
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
    MOCK_EXPENSE_REPORTS,
    MOCK_SUBSIDIARIES,
)
from app.services.mapping_catalog import list_mapping_objects


@pytest.fixture()
def plugin() -> NetSuitePlugin:
    return NetSuitePlugin()


# ── Schema coverage ────────────────────────────────────────────────────────────

class TestFetchSchema:
    EXPECTED_OBJECTS = {
        "customer", "contact", "opportunity", "salesorder", "invoice",
        "vendorbill", "purchaseorder", "journalentry", "employee",
        "inventoryitem", "expensereport", "subsidiary", "project",
    }

    def test_returns_all_13_record_types(self, plugin: NetSuitePlugin) -> None:
        schema = plugin.fetch_schema()
        ids = {obj.object_id for obj in schema}
        assert ids == self.EXPECTED_OBJECTS

    def test_all_objects_have_fields(self, plugin: NetSuitePlugin) -> None:
        for obj in plugin.fetch_schema():
            assert len(obj.fields) >= 4, f"{obj.object_id} has too few fields"

    def test_required_fields_marked(self, plugin: NetSuitePlugin) -> None:
        schema_map = {obj.object_id: obj for obj in plugin.fetch_schema()}
        # Customer must require id, entity_id, company_name
        customer_required = {f.name for f in schema_map["customer"].fields if f.required}
        assert {"id", "entity_id", "company_name"}.issubset(customer_required)

    def test_invoice_has_amount_remaining(self, plugin: NetSuitePlugin) -> None:
        schema_map = {obj.object_id: obj for obj in plugin.fetch_schema()}
        field_names = {f.name for f in schema_map["invoice"].fields}
        assert "amount_remaining" in field_names

    def test_employee_has_hire_date_and_type(self, plugin: NetSuitePlugin) -> None:
        schema_map = {obj.object_id: obj for obj in plugin.fetch_schema()}
        field_names = {f.name for f in schema_map["employee"].fields}
        assert {"hire_date", "employment_type", "is_active"}.issubset(field_names)

    def test_item_has_pricing_and_inventory_fields(self, plugin: NetSuitePlugin) -> None:
        schema_map = {obj.object_id: obj for obj in plugin.fetch_schema()}
        field_names = {f.name for f in schema_map["inventoryitem"].fields}
        assert {"sales_price", "purchase_price", "quantity_on_hand"}.issubset(field_names)


# ── Tool registry ──────────────────────────────────────────────────────────────

class TestToolRegistry:
    EXPECTED_TOOL_IDS = {
        "cfo.dashboard_summary", "cfo.pl_vs_budget", "cfo.yoy_comparison",
        "cfo.subsidiary_drilldown", "cfo.running_projects",
        "cfo.overdue_projects_by_account_manager",
        "crm.list_customers", "crm.list_contacts", "crm.list_opportunities",
        "o2c.list_sales_orders", "o2c.list_invoices",
        "p2p.list_vendor_bills", "p2p.list_purchase_orders",
        "gl.list_journal_entries",
        "hr.list_employees",
        "inv.list_items",
    }

    def test_all_17_tools_registered(self, plugin: NetSuitePlugin) -> None:
        ids = {t.tool_id for t in plugin.list_tools()}
        assert ids == self.EXPECTED_TOOL_IDS

    def test_unknown_tool_raises_key_error(self, plugin: NetSuitePlugin) -> None:
        with pytest.raises(KeyError, match="Unknown NetSuite tool"):
            plugin.execute_tool("no.such.tool", {})


# ── CRM tool execution ─────────────────────────────────────────────────────────

class TestCrmTools:
    def test_list_customers_returns_all(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_customers", {})
        assert result["source"] == "mock"
        assert result["count"] == len(MOCK_CUSTOMERS)
        assert result["count"] >= 4

    def test_list_customers_filters_by_subsidiary(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_customers", {"subsidiary_id": "1"})
        assert all(r["subsidiary_id"] == "1" for r in result["records"])

    def test_list_customers_respects_limit(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_customers", {"limit": 2})
        assert result["count"] <= 2

    def test_list_contacts_no_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_contacts", {})
        assert result["count"] == len(MOCK_CONTACTS)

    def test_list_contacts_filters_by_company(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_contacts", {"company_id": "42"})
        assert all(r["company_id"] == "42" for r in result["records"])
        assert result["count"] >= 2

    def test_list_opportunities_no_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_opportunities", {})
        assert result["count"] == len(MOCK_OPPORTUNITIES)

    def test_list_opportunities_min_probability_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_opportunities", {"min_probability": 70})
        assert all(r["probability"] >= 70 for r in result["records"])

    def test_list_opportunities_sales_rep_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("crm.list_opportunities", {"sales_rep": "Maya Rao"})
        assert all(r["sales_rep"] == "Maya Rao" for r in result["records"])


# ── Order-to-Cash tool execution ───────────────────────────────────────────────

class TestO2CTools:
    def test_list_sales_orders(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("o2c.list_sales_orders", {})
        assert result["count"] == len(MOCK_SALES_ORDERS)

    def test_list_sales_orders_status_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("o2c.list_sales_orders", {"status": "Billed"})
        assert all(r["status"] == "Billed" for r in result["records"])

    def test_list_invoices_all(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("o2c.list_invoices", {})
        assert result["count"] == len(MOCK_INVOICES_EXTENDED)

    def test_list_invoices_overdue_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("o2c.list_invoices", {"status": "Overdue"})
        assert result["count"] >= 1
        assert all(r["status"] == "Overdue" for r in result["records"])


# ── Procure-to-Pay tool execution ──────────────────────────────────────────────

class TestP2PTools:
    def test_list_vendor_bills(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("p2p.list_vendor_bills", {})
        assert result["count"] == len(MOCK_VENDOR_BILLS)

    def test_list_vendor_bills_vendor_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("p2p.list_vendor_bills", {"entity_id": "V-001"})
        assert all(r["entity_id"] == "V-001" for r in result["records"])

    def test_list_purchase_orders(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("p2p.list_purchase_orders", {})
        assert result["count"] == len(MOCK_PURCHASE_ORDERS)

    def test_list_purchase_orders_status_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("p2p.list_purchase_orders", {"status": "Fully Received"})
        assert all(r["status"] == "Fully Received" for r in result["records"])


# ── GL tool execution ──────────────────────────────────────────────────────────

class TestGLTools:
    def test_list_journal_entries_all(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("gl.list_journal_entries", {})
        assert result["count"] == len(MOCK_JOURNAL_ENTRIES)

    def test_list_journal_entries_period_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("gl.list_journal_entries", {"period": "JUN-26"})
        assert result["count"] == len(MOCK_JOURNAL_ENTRIES)  # all are JUN-26

    def test_list_journal_entries_account_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("gl.list_journal_entries", {"account": "4000"})
        assert all(r["account"] == "4000" for r in result["records"])
        assert result["count"] >= 1


# ── HR tool execution ──────────────────────────────────────────────────────────

class TestHRTools:
    def test_list_employees_all(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("hr.list_employees", {})
        assert result["count"] == len(MOCK_EMPLOYEES)

    def test_list_employees_department_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("hr.list_employees", {"department": "Finance"})
        assert all(r["department"] == "Finance" for r in result["records"])
        assert result["count"] >= 3

    def test_list_employees_subsidiary_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("hr.list_employees", {"subsidiary_id": "2"})
        assert all(r["subsidiary_id"] == "2" for r in result["records"])


# ── Inventory tool execution ───────────────────────────────────────────────────

class TestInventoryTools:
    def test_list_items_excludes_inactive_by_default(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("inv.list_items", {})
        assert all(not r.get("is_inactive", False) for r in result["records"])

    def test_list_items_include_inactive(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("inv.list_items", {"is_inactive": True})
        assert result["count"] == len(MOCK_ITEMS)

    def test_list_items_type_filter(self, plugin: NetSuitePlugin) -> None:
        result = plugin.execute_tool("inv.list_items", {"type": "Inventory"})
        assert all(r["type"] == "Inventory" for r in result["records"])
        assert result["count"] >= 2


# ── Mapping catalog coverage ───────────────────────────────────────────────────

class TestMappingCatalog:
    EXPECTED_NETSUITE_IDS = {
        "netsuite-project", "netsuite-customer", "netsuite-contact",
        "netsuite-opportunity", "netsuite-sales-order", "netsuite-invoice",
        "netsuite-vendor-bill", "netsuite-purchase-order", "netsuite-journal-entry",
        "netsuite-employee", "netsuite-item", "netsuite-expense-report",
        "netsuite-subsidiary",
    }

    def test_all_13_netsuite_objects_in_catalog(self) -> None:
        all_ids = {obj.id for obj in list_mapping_objects()}
        missing = self.EXPECTED_NETSUITE_IDS - all_ids
        assert not missing, f"Missing catalog objects: {missing}"

    def test_netsuite_customer_has_required_fields(self) -> None:
        obj = next(o for o in list_mapping_objects() if o.id == "netsuite-customer")
        required = {f.name for f in obj.fields if f.required}
        assert {"id", "entity_id", "company_name"}.issubset(required)

    def test_netsuite_journal_entry_has_debit_credit(self) -> None:
        obj = next(o for o in list_mapping_objects() if o.id == "netsuite-journal-entry")
        field_names = {f.name for f in obj.fields}
        assert {"debit", "credit", "account", "tran_date"}.issubset(field_names)

    def test_netsuite_employee_catalog_fields(self) -> None:
        obj = next(o for o in list_mapping_objects() if o.id == "netsuite-employee")
        field_names = {f.name for f in obj.fields}
        assert {"hire_date", "department", "employment_type"}.issubset(field_names)


# ── Live connector — unit tests (no network) ───────────────────────────────────

class TestLiveConnectorOAuth:
    def _make_config(self):
        from app.connectors.netsuite.live_connector import NetSuiteLiveConfig
        return NetSuiteLiveConfig(
            account_id="TSTDRV1234567",
            consumer_key="test_consumer_key",
            consumer_secret="test_consumer_secret",
            token_id="test_token_id",
            token_secret="test_token_secret",
        )

    def test_base_url_format(self) -> None:
        config = self._make_config()
        assert "tstdrv1234567" in config.base_url
        assert config.base_url.startswith("https://")

    def test_record_url_and_query_url(self) -> None:
        config = self._make_config()
        assert "/record/v1" in config.record_url
        assert "/suiteql" in config.query_url

    def test_auth_header_contains_required_oauth_params(self) -> None:
        from app.connectors.netsuite.live_connector import NetSuiteLiveConnector
        connector = NetSuiteLiveConnector(self._make_config())
        header = connector._auth_header("GET", "https://example.suitetalk.api.netsuite.com/services/rest/record/v1/customer")
        assert "OAuth" in header
        assert "oauth_consumer_key" in header
        assert "oauth_token" in header
        assert "oauth_signature_method" in header
        assert "oauth_signature" in header
        assert "HMAC-SHA256" in header
        assert "oauth_nonce" in header
        assert "oauth_timestamp" in header
        # Credentials must not appear in plaintext
        assert "test_consumer_secret" not in header
        assert "test_token_secret" not in header

    def test_auth_header_realm_is_account_id(self) -> None:
        from app.connectors.netsuite.live_connector import NetSuiteLiveConnector
        connector = NetSuiteLiveConnector(self._make_config())
        header = connector._auth_header("GET", "https://example.com/api")
        assert "TSTDRV1234567" in header

    def test_different_nonces_each_call(self) -> None:
        from app.connectors.netsuite.live_connector import NetSuiteLiveConnector
        connector = NetSuiteLiveConnector(self._make_config())
        url = "https://example.com/api"
        h1 = connector._auth_header("GET", url)
        h2 = connector._auth_header("GET", url)
        # Extract nonce values — they must differ
        assert h1 != h2  # nonce + timestamp differ between calls

    def test_error_on_network_failure(self) -> None:
        from app.connectors.netsuite.live_connector import NetSuiteLiveConnector, NetSuiteLiveConnectorError
        connector = NetSuiteLiveConnector(self._make_config())
        result = connector.test_connection()  # no network → returns ok=False
        assert result["mode"] == "live"
        assert not result["ok"]
        assert isinstance(result["message"], str)
        # Message must not contain raw credential values
        assert "test_consumer_secret" not in result["message"]
        assert "test_token_secret" not in result["message"]
