"""SAP ERP connector plugin — wraps mock implementation; live connector activated when credentials present."""
from __future__ import annotations

import logging

from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject

logger = logging.getLogger(__name__)

_TOOLS = [
    ConnectorTool("post_journal_entry", "Post Journal Entry", "Post a double-entry journal to the general ledger.", "sap",
                  [ConnectorToolParam("debit_account", "string", True, "GL debit account code"),
                   ConnectorToolParam("credit_account", "string", True, "GL credit account code"),
                   ConnectorToolParam("amount", "number", True, "Transaction amount"),
                   ConnectorToolParam("currency", "string", False, "ISO currency code"),
                   ConnectorToolParam("posting_date", "string", False, "Posting date YYYY-MM-DD")]),
    ConnectorTool("get_cost_center", "Get Cost Center", "Retrieve cost center details and YTD spend.", "sap",
                  [ConnectorToolParam("cost_center_id", "string", True, "SAP cost center ID")]),
    ConnectorTool("get_gl_balance", "Get G/L Balance", "Current balance for a G/L account.", "sap",
                  [ConnectorToolParam("account_code", "string", True, "G/L account code"),
                   ConnectorToolParam("fiscal_period", "string", False, "Fiscal period e.g. 2026-03")]),
    ConnectorTool("list_vendors", "List Vendors", "Paginated list of approved vendors.", "sap",
                  [ConnectorToolParam("limit", "number", False, "Max records")]),
    ConnectorTool("create_purchase_order", "Create Purchase Order", "Raise a purchase order for approval.", "sap",
                  [ConnectorToolParam("vendor_id", "string", True, "Vendor ID"),
                   ConnectorToolParam("line_items", "string", True, "JSON array of line items"),
                   ConnectorToolParam("currency", "string", False, "ISO currency code")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK = {
    "post_journal_entry": {"documentNumber": "JE-20260315-001", "status": "posted"},
    "get_cost_center": {"id": "CC-1100", "name": "Engineering", "ytdSpend": 412000, "budget": 600000},
    "get_gl_balance": {"accountCode": "1000", "balance": 2450000, "currency": "USD"},
    "list_vendors": {"items": [{"id": "V-001", "name": "Tech Supplies Ltd"}, {"id": "V-002", "name": "Cloud Services Inc"}], "total": 2},
    "create_purchase_order": {"poNumber": "PO-2026-0099", "status": "pending_approval"},
}

_STATIC_SCHEMA = [
    SchemaObject("cost_center", "Cost Center", [
        SchemaField("cost_center_id", "Cost Center ID", "string", required=True, sample="CC-1200"),
        SchemaField("description", "Description", "string", required=True, sample="Finance Operations"),
        SchemaField("controlling_area", "Controlling Area", "string", required=True, sample="0001"),
        SchemaField("valid_from", "Valid From", "date", sample="2026-01-01"),
        SchemaField("budget_amount", "Budget Amount", "number", sample="850000"),
    ]),
    SchemaObject("journal_entry", "Journal Entry", [
        SchemaField("company_code", "Company Code", "string", required=True, sample="1000"),
        SchemaField("gl_account", "G/L Account", "string", required=True, sample="400000"),
        SchemaField("amount", "Amount", "number", required=True, sample="12500"),
        SchemaField("posting_date", "Posting Date", "date", required=True, sample="2026-06-01"),
        SchemaField("reference", "Reference", "string", sample="INV-2026-0042"),
        SchemaField("currency", "Currency", "string", sample="USD"),
    ]),
    SchemaObject("vendor", "Vendor", [
        SchemaField("vendor_id", "Vendor ID", "string", required=True, sample="V-001"),
        SchemaField("name", "Name", "string", required=True, sample="Tech Supplies Ltd"),
        SchemaField("payment_terms", "Payment Terms", "string", sample="Net 30"),
    ]),
]


# ── Live connector wiring (OData v2/v4 — Basic Auth + CSRF handshake) ────────
#
# Mirrors the NetSuite/Salesforce plugins' _get_live_creds / _execute_live
# pattern: credentials are resolved from the encrypted vault, and a real
# SAPLiveConnector (HTTPS + the two-step OData CSRF write handshake — see
# live_connector.py) is used whenever they're present. Any failure falls back
# to mock data so the UI never breaks — but is logged so a "live" connector
# never silently behaves like mock without a trace.
#
# Tool → (OData service path, entity set, kind) map. Service paths reference
# the SAP Business Accelerator Hub sandbox API namespaces — the same services
# a real S/4HANA Cloud Public Edition tenant exposes, so this connector talks
# the identical protocol whether pointed at the sandbox or a production system.
_LIVE_TOOL_MAP: dict[str, tuple[str, str, str]] = {
    # tool_id -> (service_path, entity_set, "read" | "write")
    # service_path is the OData service root (registered with SAP API Hub).
    # entity_set is the collection name appended by list_entities / create_entity.
    # Do NOT include the entity_set name in the service_path — it would be doubled.
    "list_vendors": ("API_BUSINESS_PARTNER", "A_BusinessPartner", "read"),
    "get_cost_center": ("API_COSTCENTER_SRV", "A_CostCenter", "read"),
    "get_gl_balance": ("API_GLACCOUNTLINEITEM_SRV", "A_GLAccountLineItem", "read"),
    "create_purchase_order": ("API_PURCHASEORDER_PROCESS_SRV", "A_PurchaseOrder", "write"),
    # NOTE: post_journal_entry is intentionally NOT live-wired.
    #
    # The original mapping pointed at "API_OPLACCTGDOCITEMCRUDQP_SRV" — a
    # service ID that does not exist (confirmed against the live sandbox,
    # which returned HTTP 400 "Invalid system query options value" — Apigee's
    # generic error for an unroutable service path). The *real* service for
    # operational accounting document items is API_OPLACCTGDOCITEMCUBE_SRV
    # ("Accounting Document - Read") — but, critically, it is READ-ONLY: an
    # analytical reporting cube, not a transactional posting endpoint. SAP's
    # actual journal-entry posting APIs (JOURNALENTRYCREATEREQUESTCONFI —
    # "Journal Entry - Post (Synchronous)", and JOURNALENTRYBULKLEDGERCREATION
    # — "Journal Entry by Ledger - Post (Asynchronous)") are message-based
    # inbound integration services with a JournalEntryCreateRequest envelope —
    # a fundamentally different integration pattern than the OData entity-set
    # CSRF create_entity() flow this connector implements. Wiring this up
    # properly (a dedicated message-based posting client) is a follow-up
    # release, not a one-line service-path fix — so post_journal_entry stays
    # mock-only until then; the plugin's mock fallback handles it cleanly.
}


def _get_live_creds(tenant_id: int | None = None) -> dict | None:
    """Return decrypted SAP basic-auth credential dict, or None if not configured."""
    try:
        from app.services.credential_service import credential_service
        return credential_service.get_credentials("sap", tenant_id)
    except Exception as exc:
        logger.debug("Could not load SAP credentials: %s", exc)
    return None


def _build_live_connector(creds: dict):
    """Construct a SAPLiveConnector from a decrypted credential dict."""
    from .live_connector import SAPLiveConfig, SAPLiveConnector

    config = SAPLiveConfig(
        host=creds.get("host", ""),
        client=creds.get("client", "100"),
        username=creds.get("username", ""),
        password=creds.get("password", ""),
        system_number=creds.get("system_number", "00"),
        # Sandbox-mode fields (see SAPLiveConfig docstring) — populated only
        # when the tenant connected via "SAP Business Accelerator Hub Sandbox"
        # in the credential UI rather than a production Basic-Auth system.
        api_key=creds.get("api_key", ""),
        api_base_path=creds.get("api_base_path", ""),
    )
    return SAPLiveConnector(config)


def _execute_live(tool_id: str, params: dict, creds: dict) -> dict:
    """Dispatch a tool call to the real SAP OData Gateway via the two-step handshake."""
    mapping = _LIVE_TOOL_MAP.get(tool_id)
    if mapping is None:
        raise RuntimeError(f"SAP tool '{tool_id}' has no live implementation yet.")

    service_path, entity_set, kind = mapping
    connector = _build_live_connector(creds)

    if kind == "read":
        limit = int(params.get("limit", 50))
        records = connector.list_entities(service_path, entity_set, top=limit)
        # Normalise field names so downstream mapping rules stay stable
        # regardless of which SAP OData service is called.
        if tool_id == "list_vendors":
            records = [
                {
                    "id":   r.get("BusinessPartner") or r.get("id", ""),
                    "name": r.get("BusinessPartnerFullName") or r.get("OrganizationBPName1") or r.get("name", ""),
                    "type": r.get("BusinessPartnerType", ""),
                    "search_term": r.get("SearchTerm1", ""),
                }
                for r in records
            ]
        return {
            "connector": "sap",
            "tool": tool_id,
            "mode": "live",
            "result": {"items": records, "total": len(records)},
        }

    # write — build a minimal payload from the supplied params; the OData
    # service validates field names server-side, so we pass through whatever
    # the caller supplied rather than guessing at SAP's exact entity shape.
    payload = {k: v for k, v in params.items() if k not in ("tenant_id",)}
    created = connector.create_entity(service_path, entity_set, payload)
    return {
        "connector": "sap",
        "tool": tool_id,
        "mode": "live",
        "result": created,
    }


class SAPPlugin:
    connector_id = "sap"
    name = "SAP ERP"
    logo_slug = "sap"
    auth_scheme = "basic"

    def list_tools(self):
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict, tenant_id: int | None = None) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown SAP tool: {tool_id!r}")

        if tool_id in _LIVE_TOOL_MAP:
            creds = _get_live_creds(tenant_id)
            if creds:
                try:
                    return _execute_live(tool_id, params, creds)
                except Exception as exc:
                    logger.warning(
                        "SAP live execution failed for tool=%s, falling back to mock: %s",
                        tool_id,
                        exc,
                    )

        return {"connector": "sap", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self, tenant_id: int | None = None) -> dict:
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                connector = _build_live_connector(creds)
                return connector.test_connection()
            except Exception as exc:
                logger.warning("SAP live connection test failed: %s", exc)
                return {"ok": False, "mode": "live", "message": f"SAP connection test failed: {exc}"}

        return {"ok": True, "mode": "mock", "message": "SAP mock connector is ready (mock mode). Click Connect to link an SAP system."}

    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:
        """Return SAP entity types with field definitions.

        When live credentials are present, parse the real API_BUSINESS_PARTNER
        $metadata document and return the actual entity sets (A_BusinessPartner,
        A_AddressEmailAddress, A_BusinessPartnerContact, etc.) so the mapping
        UI shows the connector's true schema — not a static mock catalog.

        Falls back to the curated _STATIC_SCHEMA only when no credentials are
        stored (mock mode), or when the $metadata endpoint cannot be reached.
        """
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                connector = _build_live_connector(creds)
                # Pass only the service path — NOT an entity set; $metadata is a
                # service-root document (see live_connector.py test_connection for
                # the exact reason appending an entity set here causes HTTP 400).
                live_objects = connector.fetch_schema_objects("API_BUSINESS_PARTNER")
                if live_objects:
                    logger.info(
                        "SAP live schema: %d entity sets returned from API_BUSINESS_PARTNER $metadata.",
                        len(live_objects),
                    )
                    return live_objects
                # $metadata fetch succeeded but returned nothing (shouldn't happen
                # with a real SAP system; treat as a connectivity issue and fall back)
                logger.warning("SAP live $metadata returned no entity sets — using static catalog.")
            except Exception as exc:
                logger.warning("Could not reach SAP live $metadata catalog: %s", exc)

        return list(_STATIC_SCHEMA)
