from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.config import settings
from app.store import catalog_store, price_book_store, quote_store
from main import app

client = TestClient(app)


def _token(tenant_id: str, roles: list[str] | None = None, scopes: list[str] | None = None) -> str:
    payload = {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "roles": roles or [],
        "scopes": scopes or [],
        "aud": settings.jwt_audience,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _headers(tenant_id: str, token: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "Authorization": f"Bearer {token}",
    }


def setup_function() -> None:
    catalog_store.clear()
    price_book_store.clear()
    quote_store.clear()


def test_public_health_no_tenant() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200


def test_protected_requires_tenant_header() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 400


def test_auth_me_with_valid_token() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, roles=["ADMIN"])
    response = client.get("/api/auth/me", headers=_headers(tenant_id, token))
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id


def test_auth_tenant_mismatch_forbidden() -> None:
    token_tenant = str(uuid4())
    header_tenant = str(uuid4())
    token = _token(token_tenant, roles=["ADMIN"])
    response = client.get("/api/auth/me", headers=_headers(header_tenant, token))
    assert response.status_code == 403


def test_catalog_crud_and_bundle_link() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, roles=["ADMIN"])
    headers = _headers(tenant_id, token)

    bundle_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={
            "item_code": "BNDL-1",
            "name": "Bundle 1",
            "item_type": "BUNDLE",
            "versionable": False,
        },
    )
    assert bundle_resp.status_code == 201
    bundle_id = bundle_resp.json()["id"]

    child_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={
            "item_code": "SKU-1",
            "name": "Core Module",
            "item_type": "LICENSED_SOFTWARE",
            "versionable": True,
        },
    )
    assert child_resp.status_code == 201
    child_id = child_resp.json()["id"]

    link_resp = client.post(
        f"/api/catalog/bundles/{bundle_id}/items",
        headers=headers,
        json={
            "child_item_id": child_id,
            "inclusion_type": "REQUIRED",
            "qty_rule_json": {"fixed_qty": 1},
            "override_price_allowed": False,
            "sort_order": 1,
        },
    )
    assert link_resp.status_code == 201

    list_resp = client.get("/api/catalog/items", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


def test_catalog_write_permission_enforced() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, roles=["SALES"], scopes=["catalog:read"])
    headers = _headers(tenant_id, token)

    response = client.post(
        "/api/catalog/items",
        headers=headers,
        json={
            "item_code": "SKU-READONLY",
            "name": "Should Fail",
            "item_type": "SERVICE",
        },
    )
    assert response.status_code == 403
