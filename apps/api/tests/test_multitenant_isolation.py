"""Multi-tenant isolation tests.

Covers:
- Repository _scope: tenant_id=None only sees unscoped records; tenant sees own + unscoped.
- _assert_visible: cross-tenant access on a specific resource returns 403, not 404.
- require_tenant dependency: missing tenant in non-local env → 403 on write endpoints.
- Dev fallback: no auth token in non-local env → 401.
- Two-tenant data isolation: each tenant's list endpoint only returns their own records.
"""

from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.core.auth import create_placeholder_token
from app.main import app
from app.models.auth import AuthUser
from app.services.flow_service import flow_service
from app.services.audit_service import audit_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token(tenant_id: int | None, role: str = "Integration Admin") -> str:
    """Mint a signed placeholder token for the given tenant."""
    user = AuthUser(
        userId=f"test-user-tenant-{tenant_id}",
        email=f"user-t{tenant_id}@example.com",
        role=role,
        tenantId=tenant_id,
    )
    return create_placeholder_token(user)


def _headers(tenant_id: int | None, role: str = "Integration Admin") -> dict:
    return {"Authorization": f"Bearer {_token(tenant_id, role)}"}


def _flow_payload(flow_id: str) -> dict:
    return {
        "flowId": flow_id,
        "name": f"Test Flow {flow_id}",
        "description": "Multi-tenant isolation test flow.",
        "sourceConnector": "netsuite",
        "targetModule": "finance",
        "status": "draft",
        "triggerType": "manual",
        "steps": [
            {
                "id": "step-1",
                "name": "Load data",
                "description": "Load approved data.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }


def _mapping_payload(mapping_id: str) -> dict:
    """Full mapping payload covering all required salesforce-opportunity target fields."""
    return {
        "mappingId": mapping_id,
        "name": f"Test Mapping {mapping_id}",
        "description": "Multi-tenant isolation test mapping.",
        "sourceObjectId": "netsuite-project",
        "targetObjectId": "salesforce-opportunity",
        "status": "draft",
        "mappings": [
            {"id": "m1", "sourceField": "project_id", "targetField": "Name", "transform": "rename"},
            {"id": "m2", "sourceField": "customer_name", "targetField": "AccountName", "transform": "direct"},
            {"id": "m3", "sourceField": "budget_amount", "targetField": "Amount", "transform": "direct"},
            {"id": "m4", "sourceField": "due_date", "targetField": "CloseDate", "transform": "format_date"},
        ],
    }


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


# ---------------------------------------------------------------------------
# 1. Two-tenant list isolation
# ---------------------------------------------------------------------------

def test_tenant_flow_lists_are_isolated() -> None:
    """Tenant 1 and tenant 2 create separate flows; each only sees their own in the list."""
    # Tenant 1 creates a flow
    r1 = client.post(
        "/api/v1/flows/definitions",
        json=_flow_payload("mt-flow-tenant-1"),
        headers=_headers(1),
    )
    assert r1.status_code == 200, r1.text

    # Tenant 2 creates a flow
    r2 = client.post(
        "/api/v1/flows/definitions",
        json=_flow_payload("mt-flow-tenant-2"),
        headers=_headers(2),
    )
    assert r2.status_code == 200, r2.text

    # Tenant 1's list should include their flow and seed (global) flows, not tenant 2's
    list1 = client.get("/api/v1/flows", headers=_headers(1)).json()
    list2 = client.get("/api/v1/flows", headers=_headers(2)).json()

    ids1 = {f["flowId"] for f in list1["items"]}
    ids2 = {f["flowId"] for f in list2["items"]}

    assert "mt-flow-tenant-1" in ids1
    assert "mt-flow-tenant-1" not in ids2

    assert "mt-flow-tenant-2" in ids2
    assert "mt-flow-tenant-2" not in ids1


# ---------------------------------------------------------------------------
# 2. Cross-tenant specific-resource access returns 403
# ---------------------------------------------------------------------------

def test_cross_tenant_flow_get_returns_403() -> None:
    """Tenant 2 cannot GET a specific flow owned by tenant 1 — must get 403, not 200 or 404."""
    # Create the flow as tenant 1
    r = client.post(
        "/api/v1/flows/definitions",
        json=_flow_payload("mt-cross-tenant-flow"),
        headers=_headers(1),
    )
    assert r.status_code == 200, r.text

    # Tenant 2 attempts to read it directly
    response = client.get("/api/v1/flows/mt-cross-tenant-flow", headers=_headers(2))
    assert response.status_code == 403, (
        f"Expected 403 for cross-tenant access, got {response.status_code}: {response.text}"
    )


def test_cross_tenant_mapping_get_returns_403() -> None:
    """Tenant 2 cannot GET a specific mapping definition owned by tenant 1."""
    r = client.post(
        "/api/v1/mappings/definitions",
        json=_mapping_payload("mt-cross-tenant-mapping"),
        headers=_headers(1),
    )
    assert r.status_code == 200, r.text

    response = client.get("/api/v1/mappings/definitions/mt-cross-tenant-mapping", headers=_headers(2))
    assert response.status_code == 403, (
        f"Expected 403 for cross-tenant access, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# 3. require_tenant blocks writes without tenant_id in non-local environments
# ---------------------------------------------------------------------------

def _prod_settings():
    """Return a mock Settings object with environment='production'.

    Wraps the real settings so JWT/placeholder-token fields remain valid —
    only `environment` is overridden to simulate a non-local deployment.
    """
    from app.core.config import get_settings as _real_get_settings
    real = _real_get_settings()
    mock_settings = MagicMock(wraps=real)
    mock_settings.environment = "production"
    return mock_settings


def _staging_settings():
    """Same as production mock but with environment='staging'."""
    from app.core.config import get_settings as _real_get_settings
    real = _real_get_settings()
    mock_settings = MagicMock(wraps=real)
    mock_settings.environment = "staging"
    return mock_settings


def test_write_without_tenant_in_production_returns_403() -> None:
    """A token with no tenant_id must be rejected with 403 on write endpoints in production."""
    # Create a token with tenant_id=None (valid auth, but no tenant context)
    no_tenant_user = AuthUser(
        userId="notenant-user",
        email="notenant@example.com",
        role="Integration Admin",
        tenantId=None,
    )
    no_tenant_token = create_placeholder_token(no_tenant_user)
    headers = {"Authorization": f"Bearer {no_tenant_token}"}

    with patch("app.core.auth.get_settings", return_value=_prod_settings()):
        response = client.post(
            "/api/v1/flows/definitions",
            json=_flow_payload("mt-no-tenant-write"),
            headers=headers,
        )

    assert response.status_code == 403, (
        f"Expected 403 when tenant_id=None in production, got {response.status_code}: {response.text}"
    )
    assert "tenant" in response.json()["detail"].lower()


def test_write_without_tenant_in_staging_returns_403() -> None:
    """Staging (any non-local/test env) must also reject writes without a tenant."""
    no_tenant_user = AuthUser(
        userId="notenant-user",
        email="notenant@example.com",
        role="Integration Admin",
        tenantId=None,
    )
    # Create token BEFORE entering the patch so _sign uses the real settings
    no_tenant_headers = {"Authorization": f"Bearer {create_placeholder_token(no_tenant_user)}"}

    with patch("app.core.auth.get_settings", return_value=_staging_settings()):
        response = client.post(
            "/api/v1/mappings/definitions",
            json=_mapping_payload("mt-staging-no-tenant"),
            headers=no_tenant_headers,
        )

    assert response.status_code == 403, (
        f"Expected 403 in staging without tenant, got {response.status_code}: {response.text}"
    )


def test_write_with_tenant_in_production_is_allowed() -> None:
    """A properly tenanted token must succeed on write endpoints even in 'production' mode."""
    # Create token BEFORE entering the patch so _sign uses the real settings
    tenant_headers = _headers(42)

    with patch("app.core.auth.get_settings", return_value=_prod_settings()):
        response = client.post(
            "/api/v1/flows/definitions",
            json=_flow_payload("mt-prod-tenant-write"),
            headers=tenant_headers,
        )

    # 200 = created/upserted; some implementations return 200 for upsert
    assert response.status_code in (200, 201), (
        f"Expected 200/201 for tenanted write in production, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# 4. Unauthenticated requests in non-local environments return 401
# ---------------------------------------------------------------------------

def test_unauthenticated_request_in_production_returns_401() -> None:
    """No Authorization header → 401 when environment is not local/test."""
    with patch("app.core.auth.get_settings", return_value=_prod_settings()):
        response = client.get("/api/v1/flows")

    assert response.status_code == 401, (
        f"Expected 401 without auth in production, got {response.status_code}: {response.text}"
    )
    assert response.headers.get("www-authenticate", "").lower().startswith("bearer")


def test_unauthenticated_write_in_production_returns_401() -> None:
    """POST without auth → 401, not 403 (auth check runs before tenant check)."""
    with patch("app.core.auth.get_settings", return_value=_prod_settings()):
        response = client.post(
            "/api/v1/flows/definitions",
            json=_flow_payload("mt-no-auth-write"),
        )

    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated write in production, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# 5. Dev fallback (local env) with no tenant only sees unscoped records
# ---------------------------------------------------------------------------

def test_dev_fallback_only_sees_unscoped_flows() -> None:
    """Unauthenticated dev requests (tenant_id=None) must not see tenant-owned flows."""
    # Tenant 99 creates a private flow
    r = client.post(
        "/api/v1/flows/definitions",
        json=_flow_payload("mt-private-tenant-99-flow"),
        headers=_headers(99),
    )
    assert r.status_code == 200, r.text

    # Unauthenticated dev request (no token → dev fallback with tenant_id=None)
    dev_list = client.get("/api/v1/flows").json()
    dev_ids = {f["flowId"] for f in dev_list["items"]}

    assert "mt-private-tenant-99-flow" not in dev_ids, (
        "Dev fallback (tenant_id=None) must not expose tenant 99's private flow."
    )


def test_dev_fallback_only_sees_unscoped_mappings() -> None:
    """Unauthenticated dev requests must not expose tenant-owned mapping definitions."""
    r = client.post(
        "/api/v1/mappings/definitions",
        json=_mapping_payload("mt-private-tenant-77-mapping"),
        headers=_headers(77),
    )
    assert r.status_code == 200, r.text

    dev_list = client.get("/api/v1/mappings/definitions").json()
    dev_ids = {m["mappingId"] for m in dev_list}

    assert "mt-private-tenant-77-mapping" not in dev_ids, (
        "Dev fallback (tenant_id=None) must not expose tenant 77's private mapping."
    )


# ---------------------------------------------------------------------------
# 6. Tenant cannot delete another tenant's resource
# ---------------------------------------------------------------------------

def test_cross_tenant_delete_returns_403_or_404() -> None:
    """Tenant 2 attempting to delete tenant 1's flow must not succeed."""
    # Tenant 1 creates a flow
    r = client.post(
        "/api/v1/flows/definitions",
        json=_flow_payload("mt-delete-target"),
        headers=_headers(1),
    )
    assert r.status_code == 200, r.text

    # Tenant 2 tries to delete it
    response = client.delete("/api/v1/flows/mt-delete-target", headers=_headers(2))
    # Either 403 (visible but denied) or 404 (not visible = not found in their scope).
    # Both outcomes prevent unauthorised deletion.
    assert response.status_code in (403, 404), (
        f"Expected 403 or 404 when tenant 2 deletes tenant 1's flow, got {response.status_code}"
    )

    # Confirm the flow still exists for tenant 1
    verify = client.get("/api/v1/flows/mt-delete-target", headers=_headers(1))
    assert verify.status_code == 200, "Tenant 1's flow must still exist after cross-tenant delete attempt."
