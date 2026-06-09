"""Tests for the Salesforce create_account tool — SAP_Vendor_ID__c upsert path.

Guards three post-R20 behaviours:
1. When SAP_Vendor_ID__c is supplied, Salesforce.Account.upsert() is called
   (not .create()) and the external ID is excluded from the request body.
2. No body duplication — the external-ID field appears only in the URL path,
   not duplicated inside the PATCH body.
3. Both "name" (tool-param style) and "Name" (Salesforce field-name style)
   are accepted for the account name.

We test _execute_live directly with a mocked Salesforce session so no real
OAuth token or network call is needed.
"""

from __future__ import annotations

import sys
import types
import unittest.mock as mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_CREDS = {"access_token": "tok-test", "instance_url": "https://test.salesforce.com"}


def _make_sf_module(upsert_return=204, create_return=None):
    """Return (module, sf_instance) where module fakes simple_salesforce."""
    sf_instance = mock.MagicMock()
    sf_instance.Account.upsert.return_value = upsert_return
    sf_instance.Account.create.return_value = create_return or {"id": "ACC-001", "success": True}

    mod = types.ModuleType("simple_salesforce")
    mod.Salesforce = mock.MagicMock(return_value=sf_instance)
    mod.SalesforceError = Exception
    return mod, sf_instance


def _call_execute_live(params: dict, *, upsert_return=204, create_return=None):
    """Run _execute_live("create_account", params, creds) against a fake SF session."""
    sf_mod, sf_instance = _make_sf_module(upsert_return=upsert_return, create_return=create_return)
    orig = sys.modules.get("simple_salesforce")
    sys.modules["simple_salesforce"] = sf_mod
    try:
        from app.connectors.salesforce.plugin import _execute_live
        result = _execute_live("create_account", params, _FAKE_CREDS)
    finally:
        if orig is None:
            sys.modules.pop("simple_salesforce", None)
        else:
            sys.modules["simple_salesforce"] = orig
    return result, sf_instance


# ---------------------------------------------------------------------------
# Upsert path
# ---------------------------------------------------------------------------

def test_upsert_called_when_sap_vendor_id_supplied() -> None:
    result, sf = _call_execute_live({"name": "ACME", "SAP_Vendor_ID__c": "V-001"})

    sf.Account.upsert.assert_called_once()
    sf.Account.create.assert_not_called()
    assert result["result"]["upserted"] is True


def test_upsert_key_contains_vendor_id() -> None:
    _, sf = _call_execute_live({"name": "ACME", "SAP_Vendor_ID__c": "V-042"})

    upsert_path, _ = sf.Account.upsert.call_args[0]
    assert upsert_path == "SAP_Vendor_ID__c/V-042"


def test_upsert_body_excludes_external_id_field() -> None:
    """Salesforce PATCH body must NOT contain the external-ID field — it's URL-only."""
    _, sf = _call_execute_live({"name": "ACME", "SAP_Vendor_ID__c": "V-001"})

    _, body = sf.Account.upsert.call_args[0]
    assert "SAP_Vendor_ID__c" not in body, (
        "External-ID field must be excluded from the body — Salesforce rejects duplicates"
    )


def test_upsert_body_contains_name() -> None:
    _, sf = _call_execute_live({"name": "ACME Corp", "SAP_Vendor_ID__c": "V-001"})

    _, body = sf.Account.upsert.call_args[0]
    assert body["Name"] == "ACME Corp"


def test_upsert_http_status_returned_in_result() -> None:
    result, _ = _call_execute_live({"name": "ACME", "SAP_Vendor_ID__c": "V-001"}, upsert_return=204)

    assert result["result"]["http_status"] == 204


# ---------------------------------------------------------------------------
# Both "name" and "Name" accepted
# ---------------------------------------------------------------------------

def test_lowercase_name_param_is_accepted() -> None:
    result, sf = _call_execute_live({"name": "From Param", "SAP_Vendor_ID__c": "V-001"})

    _, body = sf.Account.upsert.call_args[0]
    assert body["Name"] == "From Param"
    assert result["result"]["name"] == "From Param"


def test_uppercase_name_param_is_accepted() -> None:
    result, sf = _call_execute_live({"Name": "From Field", "SAP_Vendor_ID__c": "V-001"})

    _, body = sf.Account.upsert.call_args[0]
    assert body["Name"] == "From Field"
    assert result["result"]["name"] == "From Field"


# ---------------------------------------------------------------------------
# Fallback: no external ID → plain create
# ---------------------------------------------------------------------------

def test_create_called_when_no_vendor_id() -> None:
    result, sf = _call_execute_live({"name": "Plain Create"}, create_return={"id": "ACC-001", "success": True})

    sf.Account.create.assert_called_once()
    sf.Account.upsert.assert_not_called()
    assert result["result"]["id"] == "ACC-001"


def test_missing_name_falls_back_to_unnamed() -> None:
    _, sf = _call_execute_live({}, create_return={"id": "ACC-002", "success": True})

    call_args = sf.Account.create.call_args[0][0]
    assert call_args["Name"] == "Unnamed Account"
