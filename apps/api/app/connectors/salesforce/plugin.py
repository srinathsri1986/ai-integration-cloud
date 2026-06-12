"""Salesforce CRM connector plugin — mock + live OAuth2 mode.

In mock mode (no OAuth token): returns structured fake responses.
In live mode (token stored via /connectors/salesforce/oauth/callback):
    uses simple-salesforce to make real Salesforce REST API calls.

Security: tokens are encrypted at rest via ConnectorCredentialService.
All data operations go through the approved tool list — no arbitrary SOQL.
"""
from __future__ import annotations

import logging

from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject

logger = logging.getLogger(__name__)

_TOOLS = [
    ConnectorTool(
        "create_opportunity",
        "Create Opportunity",
        "Create a new sales opportunity record.",
        "salesforce",
        [
            ConnectorToolParam("name", "string", True, "Opportunity name"),
            ConnectorToolParam("account_id", "string", False, "Parent account ID"),
            ConnectorToolParam("amount", "number", False, "Expected revenue amount"),
            ConnectorToolParam("close_date", "string", False, "Expected close date (YYYY-MM-DD)"),
        ],
    ),
    ConnectorTool(
        "update_contact",
        "Update Contact",
        "Update fields on an existing contact.",
        "salesforce",
        [
            ConnectorToolParam("contact_id", "string", True, "Salesforce contact ID"),
            ConnectorToolParam("email", "string", False, "New email address"),
            ConnectorToolParam("title", "string", False, "Job title"),
        ],
    ),
    ConnectorTool(
        "get_account",
        "Get Account",
        "Retrieve account details by ID.",
        "salesforce",
        [ConnectorToolParam("account_id", "string", True, "Salesforce account ID")],
    ),
    ConnectorTool(
        "list_opportunities",
        "List Opportunities",
        "List open opportunities, optionally filtered by stage.",
        "salesforce",
        [
            ConnectorToolParam("stage", "string", False, "Pipeline stage filter"),
            ConnectorToolParam("limit", "number", False, "Max records to return (default 20)"),
        ],
    ),
    ConnectorTool(
        "create_case",
        "Create Case",
        "Open a support case linked to an account.",
        "salesforce",
        [
            ConnectorToolParam("account_id", "string", True, "Account ID"),
            ConnectorToolParam("subject", "string", True, "Case subject"),
            ConnectorToolParam("priority", "string", False, "High | Medium | Low"),
        ],
    ),
    ConnectorTool(
        "create_account",
        "Create / Upsert Account",
        "Create a new Account or upsert by SAP_Vendor_ID__c external ID to prevent duplicates on repeated syncs. Falls back to upsert-by-Name if external ID is not provided.",
        "salesforce",
        [
            ConnectorToolParam("name", "string", True, "Account name"),
            ConnectorToolParam("SAP_Vendor_ID__c", "string", False, "SAP Vendor external ID — used as the upsert key to prevent duplicates"),
            ConnectorToolParam("industry", "string", False, "Industry picklist value, e.g. 'Technology'"),
            ConnectorToolParam("annual_revenue", "number", False, "Annual revenue"),
            ConnectorToolParam("phone", "string", False, "Main phone number"),
            ConnectorToolParam("billing_city", "string", False, "Billing city"),
        ],
    ),
    ConnectorTool(
        "create_project",
        "Create Project (custom object)",
        "Create a Project_c__c record — populates the custom object with standard project field values.",
        "salesforce",
        [
            ConnectorToolParam("name", "string", True, "Project name (Project_c__c.Name)"),
            ConnectorToolParam("status", "string", False, "Status picklist value (Project_c__c.Status__c), e.g. 'In Progress'"),
            ConnectorToolParam("budget", "number", False, "Approved budget (Project_c__c.Budget__c)"),
            ConnectorToolParam("start_date", "string", False, "Start/due date YYYY-MM-DD (Project_c__c.Start_Date__c)"),
            ConnectorToolParam("is_active", "boolean", False, "Whether the project is active (Project_c__c.Is_Active__c)"),
            ConnectorToolParam("owner_id", "string", False, "Salesforce User record ID for the project owner lookup (Project_c__c.Project_Owner__c)"),
        ],
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK_DATA = {
    "create_opportunity": {"id": "OPP-0042", "status": "created", "name": "Mock Opportunity"},
    "update_contact": {"id": "CON-0099", "status": "updated"},
    "get_account": {
        "id": "ACC-0001",
        "name": "Acme Corp",
        "industry": "Technology",
        "annualRevenue": 5_000_000,
    },
    "list_opportunities": {
        "items": [
            {"id": "OPP-0040", "name": "Q4 Renewal", "stage": "Negotiation", "amount": 120_000}
        ],
        "total": 1,
    },
    "create_case": {"id": "CASE-0011", "status": "open", "subject": "Mock Case"},
    "create_project": {"id": "a0B0x000004MockPr", "status": "created", "name": "Mock Project"},
    "create_account": {"id": "ACC-mock-0001", "status": "created", "name": "Mock Account"},
}


def _get_live_creds(tenant_id: int | None = None) -> dict | None:
    """Return decrypted Salesforce OAuth token dict, or None if not configured."""
    try:
        from app.services.credential_service import credential_service
        return credential_service.get_oauth_token("salesforce", tenant_id)
    except Exception as exc:
        logger.debug("Could not load Salesforce credentials: %s", exc)
    return None


# ── Automatic refresh-token handling ─────────────────────────────────────────
#
# Salesforce access tokens (session IDs) expire — often within ~2 hours for
# Developer Edition orgs — and every live call up to now failed hard with
# "Session expired or invalid / INVALID_SESSION_ID" once that happened, even
# though we already store a refresh_token from the original OAuth grant.
#
# This wraps every live call: on a session-expiry error, exchange the stored
# refresh_token for a fresh access_token (re-persisting it), then retry once.

def _is_session_expired(exc: Exception) -> bool:
    msg = str(exc)
    return (
        "INVALID_SESSION_ID" in msg
        or "Session expired" in msg
        or "invalid_grant" in msg
    )


def _refresh_access_token(creds: dict, tenant_id: int | None = None) -> dict | None:
    """Exchange the stored refresh_token for a new access_token.

    Returns the updated, already-persisted credential dict on success, or
    None if refresh isn't possible (no refresh_token, missing Connected App
    creds, or the refresh request itself failed).
    """
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        logger.warning("Salesforce session expired and no refresh_token is stored — re-authorisation required.")
        return None

    try:
        import httpx
        from app.services.credential_service import credential_service

        app_creds = credential_service.get_credentials("oauth_app:salesforce", tenant_id)
        client_id = (app_creds or {}).get("client_id")
        client_secret = (app_creds or {}).get("client_secret")
        if not client_id or not client_secret:
            logger.warning("Cannot refresh Salesforce token — Connected App client_id/secret not stored.")
            return None

        # The instance_url also accepts /services/oauth2/token for refresh grants.
        token_host = creds.get("instance_url") or "https://login.salesforce.com"
        resp = httpx.post(
            f"{token_host}/services/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        token_data = resp.json()
        if "access_token" not in token_data:
            logger.warning(
                "Salesforce token refresh failed: %s",
                token_data.get("error_description", token_data),
            )
            return None

        # The refresh response usually omits refresh_token (it's long-lived and
        # stable) — preserve the original alongside any other stored fields.
        updated = {**creds, **token_data}
        updated.setdefault("refresh_token", refresh_token)
        credential_service.store_oauth_token("salesforce", updated, tenant_id=tenant_id)
        logger.info("Refreshed Salesforce access token for tenant=%s", tenant_id)
        return updated
    except Exception as exc:
        logger.warning("Salesforce token refresh failed: %s", exc)
        return None


def _with_session_refresh(creds: dict, tenant_id: int | None, call):
    """Invoke call(creds); on session-expiry, refresh once and retry.

    `call` is a single-argument callable taking the credential dict and
    returning whatever the live operation returns. Re-raises the original
    exception if refresh isn't possible or the retry also fails.
    """
    try:
        return call(creds)
    except Exception as exc:
        if not _is_session_expired(exc):
            raise
        refreshed = _refresh_access_token(creds, tenant_id)
        if not refreshed:
            raise
        return call(refreshed)


def _execute_live(tool_id: str, params: dict, creds: dict) -> dict:
    """Dispatch a tool call to the real Salesforce REST API via simple-salesforce."""
    try:
        from simple_salesforce import Salesforce, SalesforceError  # type: ignore[import]
    except ImportError:
        raise RuntimeError(
            "simple-salesforce is not installed. Add it to requirements to use live Salesforce mode."
        )

    access_token = creds.get("access_token")
    instance_url = creds.get("instance_url", "")

    if not access_token or not instance_url:
        raise RuntimeError("Salesforce credentials missing access_token or instance_url.")

    # Strip protocol prefix for simple-salesforce
    instance = instance_url.replace("https://", "").replace("http://", "").rstrip("/")

    try:
        sf = Salesforce(instance=instance, session_id=access_token)

        if tool_id == "create_opportunity":
            name = params.get("name", "New Opportunity")
            close_date = params.get("close_date", "2026-12-31")
            data: dict = {"Name": name, "StageName": "Prospecting", "CloseDate": close_date}
            if params.get("account_id"):
                data["AccountId"] = params["account_id"]
            if params.get("amount"):
                data["Amount"] = float(params["amount"])
            result = sf.Opportunity.create(data)
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {"id": result["id"], "success": result["success"]},
            }

        elif tool_id == "update_contact":
            contact_id = params["contact_id"]
            updates: dict = {}
            if params.get("email"):
                updates["Email"] = params["email"]
            if params.get("title"):
                updates["Title"] = params["title"]
            sf.Contact.update(contact_id, updates)
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {"id": contact_id, "status": "updated"},
            }

        elif tool_id == "get_account":
            account_id = params["account_id"]
            acct = sf.Account.get(account_id)
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {
                    "id": acct.get("Id"),
                    "name": acct.get("Name"),
                    "industry": acct.get("Industry"),
                    "annualRevenue": acct.get("AnnualRevenue"),
                },
            }

        elif tool_id == "list_opportunities":
            stage = params.get("stage", "")
            limit = int(params.get("limit", 20))
            # Approved SOQL — stage and limit are parameterised, no raw input
            where = f"WHERE StageName = '{stage}'" if stage else ""
            query = f"SELECT Id, Name, StageName, Amount, CloseDate FROM Opportunity {where} ORDER BY CreatedDate DESC LIMIT {limit}"  # noqa: S608
            rows = sf.query(query)
            items = [
                {
                    "id": r["Id"],
                    "name": r["Name"],
                    "stage": r["StageName"],
                    "amount": r.get("Amount"),
                    "closeDate": r.get("CloseDate"),
                }
                for r in rows.get("records", [])
            ]
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {"items": items, "total": rows.get("totalSize", len(items))},
            }

        elif tool_id == "create_project":
            # Project_c__c is the custom object discovered via live schema fetch
            # (15 fields, incl. Name, Status__c, Budget__c, Start_Date__c,
            # Is_Active__c, Project_Owner__c — see mapping_catalog "salesforce-project-c").
            # Populate it with standard/sample values supplied by the caller.
            data = {"Name": params.get("name", "New Project")}
            if params.get("status") is not None:
                data["Status__c"] = params["status"]
            if params.get("budget") is not None:
                data["Budget__c"] = float(params["budget"])
            if params.get("start_date"):
                data["Start_Date__c"] = params["start_date"]
            if params.get("is_active") is not None:
                data["Is_Active__c"] = bool(params["is_active"])
            if params.get("owner_id"):
                data["Project_Owner__c"] = params["owner_id"]
            result = sf.Project_c__c.create(data)
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {"id": result["id"], "success": result["success"], "fields": data},
            }

        elif tool_id == "create_account":
            # Accept both camelCase tool-param style ("name") and Salesforce field-name
            # style ("Name") so that both direct tool calls and mapped payloads work.
            name = params.get("name") or params.get("Name") or "Unnamed Account"
            acct_data: dict = {"Name": name}

            # Populate optional fields — accept both API field names and param aliases
            sap_vendor_id = params.get("SAP_Vendor_ID__c") or params.get("sap_vendor_id")
            if sap_vendor_id:
                acct_data["SAP_Vendor_ID__c"] = str(sap_vendor_id)
            if params.get("industry") or params.get("Industry"):
                acct_data["Industry"] = params.get("industry") or params.get("Industry")
            ann_rev = params.get("annual_revenue") or params.get("AnnualRevenue")
            if ann_rev is not None:
                acct_data["AnnualRevenue"] = float(ann_rev)
            if params.get("phone") or params.get("Phone"):
                acct_data["Phone"] = params.get("phone") or params.get("Phone")
            if params.get("billing_city") or params.get("BillingCity"):
                acct_data["BillingCity"] = params.get("billing_city") or params.get("BillingCity")

            if sap_vendor_id:
                # Preferred: upsert on SAP_Vendor_ID__c — prevents duplicate Accounts
                # on repeated syncs. Uses PATCH sobjects/Account/SAP_Vendor_ID__c/{id}
                # IMPORTANT: Salesforce requires the upsert key field to be EXCLUDED
                # from the request body — only include it in the URL path.
                upsert_body = {k: v for k, v in acct_data.items() if k != "SAP_Vendor_ID__c"}
                upsert_result = sf.Account.upsert(f"SAP_Vendor_ID__c/{sap_vendor_id}", upsert_body)
                return {
                    "connector": "salesforce",
                    "tool": tool_id,
                    "mode": "live",
                    "result": {
                        "upserted": True,
                        "upsert_key": f"SAP_Vendor_ID__c={sap_vendor_id}",
                        "http_status": upsert_result,
                        "name": name,
                        "fields": upsert_body,
                    },
                }
            else:
                # Fallback: plain create when no external ID is available
                result = sf.Account.create(acct_data)
                return {
                    "connector": "salesforce",
                    "tool": tool_id,
                    "mode": "live",
                    "result": {"id": result["id"], "success": result["success"], "fields": acct_data},
                }

        elif tool_id == "create_case":
            case_data: dict = {
                "AccountId": params["account_id"],
                "Subject": params["subject"],
                "Priority": params.get("priority", "Medium"),
                "Status": "New",
            }
            result = sf.Case.create(case_data)
            return {
                "connector": "salesforce",
                "tool": tool_id,
                "mode": "live",
                "result": {"id": result["id"], "success": result["success"]},
            }

        raise KeyError(f"Unknown Salesforce tool: {tool_id!r}")

    except SalesforceError as exc:  # type: ignore[possibly-undefined]
        raise RuntimeError(f"Salesforce API error: {exc}") from exc


class SalesforcePlugin:
    connector_id = "salesforce"
    name = "Salesforce CRM"
    logo_slug = "salesforce"
    auth_scheme = "oauth2"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict, tenant_id: int | None = None) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown Salesforce tool: {tool_id!r}")

        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                return _with_session_refresh(creds, tenant_id, lambda c: _execute_live(tool_id, params, c))
            except Exception as exc:
                logger.warning(
                    "Salesforce live execution failed for tool=%s, falling back to mock: %s",
                    tool_id,
                    exc,
                )

        return {
            "connector": "salesforce",
            "tool": tool_id,
            "mode": "mock",
            "result": _MOCK_DATA.get(tool_id, {}),
        }

    def test_connection(self, tenant_id: int | None = None) -> dict:
        creds = _get_live_creds(tenant_id)
        if creds:
            def _ping(c: dict) -> dict:
                from simple_salesforce import Salesforce  # type: ignore[import]

                instance = (
                    c.get("instance_url", "")
                    .replace("https://", "")
                    .replace("http://", "")
                    .rstrip("/")
                )
                sf = Salesforce(instance=instance, session_id=c.get("access_token", ""))
                identity = sf.restful("chatter/users/me")
                display = identity.get("displayName", identity.get("name", "user"))
                return {
                    "ok": True,
                    "mode": "live",
                    "message": f"Connected to Salesforce as {display} ({instance}).",
                }

            try:
                return _with_session_refresh(creds, tenant_id, _ping)
            except Exception as exc:
                return {"ok": False, "mode": "live", "message": f"Salesforce connection test failed: {exc}"}

        return {
            "ok": True,
            "mode": "mock",
            "message": "Salesforce connector ready in mock mode. Click Connect to link a Salesforce org.",
        }

    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                return _with_session_refresh(creds, tenant_id, _fetch_live_schema)
            except Exception as exc:
                logger.warning("Salesforce live schema fetch failed, using mock: %s", exc)
        return _MOCK_SCHEMA


_STANDARD_OBJECTS = ("Opportunity", "Account", "Contact", "Lead", "Case")

# Safety cap on total objects described per discovery run — keeps the UI
# manageable and avoids excessive describe-call volume against the org.
_MAX_CUSTOM_OBJECTS = 25


def _fetch_live_schema(creds: dict) -> list[SchemaObject]:
    """Describe Salesforce objects via simple-salesforce.

    Always includes the curated standard objects (Opportunity, Account,
    Contact, Lead, Case) and additionally auto-discovers any *custom*
    objects (API names ending in "__c") defined in the connected org —
    so user-created objects show up in schema discovery / field mapping
    without any code changes on our side.
    """
    from simple_salesforce import Salesforce  # type: ignore[import]

    instance = (
        creds.get("instance_url", "")
        .replace("https://", "").replace("http://", "").rstrip("/")
    )
    sf = Salesforce(instance=instance, session_id=creds.get("access_token", ""))

    _SF_TYPE_MAP = {
        "string": "string", "textarea": "string", "email": "string",
        "phone": "string", "url": "string", "picklist": "string",
        "multipicklist": "string", "combobox": "string", "id": "id",
        "reference": "reference", "double": "number", "currency": "number",
        "percent": "number", "int": "number", "boolean": "boolean",
        "date": "date", "datetime": "date",
    }

    # ── Discover custom objects (API names ending in "__c") ──────────────────
    custom_object_names: list[str] = []
    try:
        global_desc = sf.describe()
        custom_object_names = sorted(
            sobj["name"]
            for sobj in global_desc.get("sobjects", [])
            if sobj.get("name", "").endswith("__c")
            and sobj.get("queryable", True)
            and not sobj.get("deprecatedAndHidden", False)
        )[:_MAX_CUSTOM_OBJECTS]
    except Exception as exc:
        logger.warning("Could not list Salesforce custom objects: %s", exc)

    object_names = list(_STANDARD_OBJECTS) + custom_object_names

    objects: list[SchemaObject] = []
    session_expired_seen = False
    for obj_name in object_names:
        try:
            desc = sf.restful(f"sobjects/{obj_name}/describe")
            fields: list[SchemaField] = []
            for f in desc.get("fields", []):
                sf_type = f.get("type", "string")
                mapped = _SF_TYPE_MAP.get(sf_type, "string")
                if sf_type in ("address", "location", "anyType", "base64", "encryptedstring"):
                    continue
                fields.append(SchemaField(
                    name=f["name"],
                    label=f.get("label", f["name"]),
                    type=mapped,
                    required=not f.get("nillable", True) and not f.get("defaultedOnCreate", False),
                    updateable=f.get("updateable", True),
                    sample=None,
                ))
            label = desc.get("label", obj_name)
            # Custom fields first so they're never truncated by the 40-field cap
            custom = [f for f in fields if f.name.endswith("__c")]
            standard = [f for f in fields if not f.name.endswith("__c")]
            objects.append(SchemaObject(object_id=obj_name, label=label, fields=(custom + standard)[:40]))
        except Exception as exc:
            if _is_session_expired(exc):
                session_expired_seen = True
            logger.warning("Could not describe Salesforce object %s: %s", obj_name, exc)

    # IMPORTANT: per-object describe() failures are caught and logged above so a
    # handful of missing/renamed objects don't blank out the whole schema. But if
    # the session expired, EVERY describe call fails the same way and this loop
    # would silently return an empty object list — `_with_session_refresh()` (the
    # caller) only retries on a *raised* exception, so a "successful" empty return
    # would never trigger a refresh. Detect the all-failed-due-to-expiry case and
    # raise so the wrapper can refresh the token and retry the whole fetch.
    if not objects and session_expired_seen:
        raise RuntimeError(
            "Expired session while describing Salesforce schema objects "
            "(INVALID_SESSION_ID) — every object describe call failed."
        )
    return objects


_MOCK_SCHEMA: list[SchemaObject] = [
    SchemaObject("Opportunity", "Opportunity", [
        SchemaField("Id", "Opportunity ID", "id", required=True, updateable=False, sample="0060x000001AbCd"),
        SchemaField("Name", "Opportunity Name", "string", required=True, sample="Acme Q4 Renewal"),
        SchemaField("AccountId", "Account ID", "reference", sample="0010x000002XyZa"),
        SchemaField("Amount", "Amount", "number", sample="420000"),
        SchemaField("CloseDate", "Close Date", "date", required=True, sample="2026-12-31"),
        SchemaField("StageName", "Stage", "string", required=True, sample="Prospecting"),
        SchemaField("Probability", "Probability (%)", "number", sample="30"),
        SchemaField("OwnerId", "Owner ID", "reference", sample="0050x000003WxYz"),
    ]),
    SchemaObject("Account", "Account", [
        SchemaField("Id", "Account ID", "id", required=True, updateable=False, sample="0010x000002XyZa"),
        SchemaField("Name", "Account Name", "string", required=True, sample="Acme Manufacturing"),
        SchemaField("Industry", "Industry", "string", sample="Technology"),
        SchemaField("AnnualRevenue", "Annual Revenue", "number", sample="5000000"),
        SchemaField("BillingCity", "Billing City", "string", sample="San Francisco"),
        SchemaField("Phone", "Phone", "string", sample="+1 415 555 0100"),
        SchemaField("SAP_Vendor_ID__c", "SAP Vendor ID (External)", "string", sample="V-001"),
    ]),
    SchemaObject("Contact", "Contact", [
        SchemaField("Id", "Contact ID", "id", required=True, updateable=False, sample="0030x000004AbCd"),
        SchemaField("FirstName", "First Name", "string", sample="Maya"),
        SchemaField("LastName", "Last Name", "string", required=True, sample="Rao"),
        SchemaField("Email", "Email", "string", sample="maya.rao@acme.com"),
        SchemaField("Title", "Title", "string", sample="CFO"),
        SchemaField("AccountId", "Account ID", "reference", sample="0010x000002XyZa"),
    ]),
]
