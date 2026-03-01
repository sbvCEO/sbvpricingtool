from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.config import settings
from app.store import catalog_store, price_book_store, quote_store
from main import app

client = TestClient(app)


def _token(tenant_id: str, roles: list[str] | None = None, scopes: list[str] | None = None) -> str:
    payload = {
        "sub": "workflow-user",
        "tenant_id": tenant_id,
        "roles": roles or ["FUNCTION_ADMIN"],
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


def test_price_book_quote_pricing_and_approval_flow() -> None:
    tenant_id = str(uuid4())
    admin_token = _token(tenant_id, roles=["ADMIN"])
    headers = _headers(tenant_id, admin_token)

    item_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={
            "item_code": "SKU-SEC-1",
            "name": "Security Module",
            "item_type": "LICENSED_SOFTWARE",
            "versionable": True,
        },
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    pb_resp = client.post(
        "/api/price-books",
        headers=headers,
        json={"name": "FY26", "currency": "USD"},
    )
    assert pb_resp.status_code == 201
    pb_id = pb_resp.json()["id"]

    entry_resp = client.post(
        "/api/price-books/entries",
        headers=headers,
        json={
            "price_book_id": pb_id,
            "commercial_item_id": item_id,
            "pricing_model": "PER_USER",
            "base_price": 100,
            "min_price": 70,
            "max_discount_pct": 20,
        },
    )
    assert entry_resp.status_code == 201

    quote_resp = client.post(
        "/api/quotes",
        headers=headers,
        json={"currency": "USD", "price_book_id": pb_id},
    )
    assert quote_resp.status_code == 201
    quote_id = quote_resp.json()["id"]

    line_resp = client.post(
        f"/api/quotes/{quote_id}/line-items",
        headers=headers,
        json={
            "commercial_item_id": item_id,
            "quantity": 10,
            "discount_pct": 25,
        },
    )
    assert line_resp.status_code == 201

    preview_resp = client.post(f"/api/quotes/{quote_id}/price-preview", headers=headers)
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["grand_total"] == 800.0  # discount capped at 20%
    assert len(preview["pricing_explanations"]) == 1
    assert "engine_metadata" in preview

    trace_resp = client.get(f"/api/quotes/{quote_id}/traces", headers=headers)
    assert trace_resp.status_code == 200
    assert len(trace_resp.json()) == 1

    rev_resp = client.post(
        f"/api/quotes/{quote_id}/revisions",
        headers=headers,
        json={"change_reason": "Applied customer update"},
    )
    assert rev_resp.status_code == 201

    submit_resp = client.post(f"/api/quotes/{quote_id}/submit", headers=headers)
    assert submit_resp.status_code == 200
    approval_id = submit_resp.json()["id"]

    approve_resp = client.post(
        f"/api/approvals/{approval_id}/actions",
        headers=headers,
        json={"action": "APPROVE", "comments": "Approved"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    state_resp = client.get(f"/api/quotes/{quote_id}/state", headers=headers)
    assert state_resp.status_code == 200
    assert state_resp.json()["status"] == "FINALIZED"

    metrics_resp = client.get("/api/analytics/dashboard", headers=headers)
    assert metrics_resp.status_code == 200
    assert metrics_resp.json()["finalized_quotes"] == 1

    outbox_resp = client.get("/api/outbox/events", headers=headers)
    assert outbox_resp.status_code == 200
    assert len(outbox_resp.json()) >= 3


def test_request_changes_updates_quote_and_timeline() -> None:
    tenant_id = str(uuid4())
    admin_token = _token(tenant_id, roles=["ADMIN"])
    headers = _headers(tenant_id, admin_token)

    item_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={
            "item_code": "SKU-SVC-2",
            "name": "Advisory Service",
            "item_type": "SERVICE",
            "versionable": True,
        },
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    pb_resp = client.post("/api/price-books", headers=headers, json={"name": "FY26-US", "currency": "USD"})
    assert pb_resp.status_code == 201
    pb_id = pb_resp.json()["id"]

    entry_resp = client.post(
        "/api/price-books/entries",
        headers=headers,
        json={
            "price_book_id": pb_id,
            "commercial_item_id": item_id,
            "pricing_model": "FIXED_PRICE",
            "base_price": 5000,
            "min_price": 4000,
            "max_discount_pct": 15,
        },
    )
    assert entry_resp.status_code == 201

    quote_resp = client.post("/api/quotes", headers=headers, json={"currency": "USD", "price_book_id": pb_id})
    assert quote_resp.status_code == 201
    quote_id = quote_resp.json()["id"]

    line_resp = client.post(
        f"/api/quotes/{quote_id}/line-items",
        headers=headers,
        json={"commercial_item_id": item_id, "quantity": 5, "discount_pct": 10},
    )
    assert line_resp.status_code == 201

    submit_resp = client.post(f"/api/quotes/{quote_id}/submit", headers=headers)
    assert submit_resp.status_code == 200
    approval_id = submit_resp.json()["id"]

    action_resp = client.post(
        f"/api/approvals/{approval_id}/actions",
        headers=headers,
        json={"action": "REQUEST_CHANGES", "comments": "Discount rationale required"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "CHANGES_REQUESTED"

    state_resp = client.get(f"/api/quotes/{quote_id}/state", headers=headers)
    assert state_resp.status_code == 200
    assert state_resp.json()["status"] == "REJECTED"

    timeline_resp = client.get(f"/api/approvals/{approval_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()["timeline"]
    assert len(timeline) >= 1
    assert timeline[0]["status"] == "CHANGES_REQUESTED"
    assert timeline[0]["comments"] == "Discount rationale required"


def test_reject_requires_reason() -> None:
    tenant_id = str(uuid4())
    admin_token = _token(tenant_id, roles=["ADMIN"])
    headers = _headers(tenant_id, admin_token)

    item_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={"item_code": "SKU-RJ-1", "name": "Reject Test Item", "item_type": "SERVICE", "versionable": True},
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    pb_resp = client.post("/api/price-books", headers=headers, json={"name": "RJ-PB", "currency": "USD"})
    assert pb_resp.status_code == 201
    pb_id = pb_resp.json()["id"]

    entry_resp = client.post(
        "/api/price-books/entries",
        headers=headers,
        json={
            "price_book_id": pb_id,
            "commercial_item_id": item_id,
            "pricing_model": "FIXED_PRICE",
            "base_price": 1000,
            "max_discount_pct": 20,
        },
    )
    assert entry_resp.status_code == 201

    quote_resp = client.post("/api/quotes", headers=headers, json={"currency": "USD", "price_book_id": pb_id})
    assert quote_resp.status_code == 201
    quote_id = quote_resp.json()["id"]

    line_resp = client.post(
        f"/api/quotes/{quote_id}/line-items",
        headers=headers,
        json={"commercial_item_id": item_id, "quantity": 1, "discount_pct": 10},
    )
    assert line_resp.status_code == 201

    submit_resp = client.post(f"/api/quotes/{quote_id}/submit", headers=headers)
    assert submit_resp.status_code == 200
    approval_id = submit_resp.json()["id"]

    reject_resp = client.post(
        f"/api/approvals/{approval_id}/actions",
        headers=headers,
        json={"action": "REJECT", "comments": ""},
    )
    assert reject_resp.status_code == 400
    assert "required" in reject_resp.json()["detail"].lower()
