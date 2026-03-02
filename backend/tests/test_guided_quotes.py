from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.admin_repo import admin_repo
from app.config import settings
from app.store import catalog_store, price_book_store, quote_store
from main import app

client = TestClient(app)


def _token(tenant_id: str) -> str:
    payload = {
        "sub": "guided-user",
        "tenant_id": tenant_id,
        "roles": ["ADMIN"],
        "scopes": [],
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
    admin_repo.clear()


def test_guided_quote_generation_flow() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id)
    headers = _headers(tenant_id, token)

    item_resp = client.post(
        "/api/catalog/items",
        headers=headers,
        json={"item_code": "SKU-GD-1", "name": "Guided Product", "item_type": "SERVICE", "versionable": False},
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    pb_resp = client.post("/api/price-books", headers=headers, json={"name": "GUIDED-PB", "currency": "USD"})
    assert pb_resp.status_code == 201
    pb_id = pb_resp.json()["id"]

    entry_resp = client.post(
        "/api/price-books/entries",
        headers=headers,
        json={
            "price_book_id": pb_id,
            "commercial_item_id": item_id,
            "pricing_model": "FIXED_PRICE",
            "base_price": 100,
            "max_discount_pct": 20,
            "currency": "USD",
            "region": "US",
        },
    )
    assert entry_resp.status_code == 201

    customers = client.get("/api/guided-quotes/customers", headers=headers)
    assert customers.status_code == 200
    assert len(customers.json()) >= 1

    new_customer = client.post(
        "/api/guided-quotes/customers",
        headers=headers,
        json={"name": "Northwind Labs", "external_id": "CUST-NW"},
    )
    assert new_customer.status_code == 201
    customer_id = new_customer.json()["id"]

    new_opp = client.post(
        "/api/guided-quotes/opportunities",
        headers=headers,
        json={"customer_id": customer_id, "name": "Northwind Renewal", "stage": "PROPOSAL", "amount": 15000},
    )
    assert new_opp.status_code == 201
    opp_id = new_opp.json()["id"]

    generated = client.post(
        "/api/guided-quotes/generate",
        headers=headers,
        json={
            "customer_id": customer_id,
            "opportunity_id": opp_id,
            "general": {
                "duration_type": "MONTHS",
                "duration_value": 3,
                "valid_until": "2026-12-31",
                "price_book_id": pb_id,
                "currency": "USD",
                "region": "US",
                "overall_discount_pct": 5,
            },
            "line_items": [
                {
                    "commercial_item_id": item_id,
                    "line_discount_pct": 10,
                    "quantity_schedule": {"1": 2, "2": 3, "3": 1},
                }
            ],
        },
    )
    assert generated.status_code == 200
    payload = generated.json()
    assert payload["quote"]["customer_external_id"] == customer_id
    assert payload["preview"]["grand_total"] > 0
    assert payload["computation"]["grand_total"] > 0

    customer_quotes = client.get(f"/api/guided-quotes/customers/{customer_id}/quotes", headers=headers)
    assert customer_quotes.status_code == 200
    assert len(customer_quotes.json()) >= 1
