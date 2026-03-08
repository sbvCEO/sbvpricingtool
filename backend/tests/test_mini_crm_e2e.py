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
        "sub": "mini-crm-e2e",
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


def test_mini_crm_to_quote_e2e() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id)
    headers = _headers(tenant_id, token)

    # 1) Create customer
    customer_resp = client.post(
        "/api/guided-quotes/customers",
        headers=headers,
        json={
            "name": "E2E Customer",
            "external_id": "CUST-E2E-001",
            "segment": "ENTERPRISE",
            "industry": "TECHNOLOGY",
            "owner": "E2E Owner",
        },
    )
    assert customer_resp.status_code == 201
    customer_id = customer_resp.json()["id"]

    # 2) Create contact and assign to customer
    contact_resp = client.post(
        "/api/guided-quotes/contacts",
        headers=headers,
        json={
            "customer_id": customer_id,
            "name": "E2E Contact",
            "email": "e2e.contact@example.com",
            "phone": "+1-555-0100",
            "title": "Procurement Manager",
            "role": "DECISION_MAKER",
        },
    )
    assert contact_resp.status_code == 201
    assert contact_resp.json()["customer_id"] == customer_id

    # 3) Create opportunity and assign to customer
    opp_resp = client.post(
        "/api/guided-quotes/opportunities",
        headers=headers,
        json={
            "customer_id": customer_id,
            "record_type": "OPPORTUNITY",
            "name": "E2E Renewal Opportunity",
            "stage": "PROSPECTING",
            "amount": 125000,
            "probability_pct": 40,
            "owner": "E2E Owner",
        },
    )
    assert opp_resp.status_code == 201
    opportunity_id = opp_resp.json()["id"]
    assert opp_resp.json()["customer_id"] == customer_id

    # 4) If no pricebook exists, create one for tenant
    pb_list_resp = client.get("/api/price-books", headers=headers)
    assert pb_list_resp.status_code == 200
    existing_books = pb_list_resp.json()
    if existing_books:
        price_book_id = existing_books[0]["id"]
    else:
        pb_create_resp = client.post(
            "/api/price-books",
            headers=headers,
            json={"name": "E2E-TENANT-PB", "currency": "USD"},
        )
        assert pb_create_resp.status_code == 201
        price_book_id = pb_create_resp.json()["id"]

    # 5) Create quote on opportunity using selected pricebook
    quote_resp = client.post(
        "/api/quotes",
        headers=headers,
        json={
            "customer_external_id": customer_id,
            "customer_account_id": customer_id,
            "opportunity_id": opportunity_id,
            "currency": "USD",
            "region": "US",
            "price_book_id": price_book_id,
        },
    )
    assert quote_resp.status_code == 201
    quote = quote_resp.json()
    assert quote["customer_external_id"] == customer_id
    assert quote["customer_account_id"] == customer_id
    assert quote["opportunity_id"] == opportunity_id
    assert quote["price_book_id"] == price_book_id
