from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.config import settings
from app.store import catalog_store, price_book_store, quote_store
from main import app

client = TestClient(app)


def _token(tenant_id: str, roles: list[str] | None = None, scopes: list[str] | None = None) -> str:
    payload = {
        "sub": "extended-user",
        "tenant_id": tenant_id,
        "roles": roles or ["ADMIN"],
        "scopes": scopes or [],
        "aud": settings.jwt_audience,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _headers(tenant_id: str, token: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "Authorization": f"Bearer {token}",
        "X-User-Sub": "extended-user",
    }


def setup_function() -> None:
    catalog_store.clear()
    price_book_store.clear()
    quote_store.clear()


def test_rules_ai_integrations_and_observability() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, roles=["ADMIN"])
    headers = _headers(tenant_id, token)

    # Rule create/validate/simulate
    rule_payload = {
        "name": "High Value Approval",
        "rule_type": "APPROVAL_TRIGGER",
        "priority": 10,
        "dsl_json": {"when": {"region": "US"}, "then": {"approval_levels": 2}},
    }
    create_rule = client.post("/api/rules", headers=headers, json=rule_payload)
    assert create_rule.status_code == 200
    rule_id = create_rule.json()["id"]

    validate_rule = client.post("/api/rules/validate", headers=headers, json=rule_payload)
    assert validate_rule.status_code == 200
    assert validate_rule.json()["valid"] is True

    publish_rule = client.post(f"/api/rules/{rule_id}/publish", headers=headers)
    assert publish_rule.status_code == 200

    simulate = client.post(
        "/api/rules/simulate",
        headers=headers,
        json={"rule": rule_payload, "context": {"region": "US"}},
    )
    assert simulate.status_code == 200
    assert simulate.json()["matched"] is True

    # Create minimal priced quote for AI endpoints
    item = client.post(
        "/api/catalog/items",
        headers=headers,
        json={"item_code": "AI-1", "name": "AI Item", "item_type": "SERVICE", "versionable": False},
    )
    assert item.status_code == 201
    item_id = item.json()["id"]

    pb = client.post("/api/price-books", headers=headers, json={"name": "ADV", "currency": "USD"})
    assert pb.status_code == 201
    pb_id = pb.json()["id"]
    client.post(f"/api/price-books/{pb_id}/publish", headers=headers)

    entry = client.post(
        "/api/price-books/entries",
        headers=headers,
        json={
            "price_book_id": pb_id,
            "commercial_item_id": item_id,
            "pricing_model": "FIXED_PRICE",
            "base_price": 1200,
            "max_discount_pct": 30,
            "currency": "USD",
            "region": "US",
        },
    )
    assert entry.status_code == 201

    quote = client.post(
        "/api/quotes",
        headers=headers,
        json={"currency": "USD", "region": "US", "price_book_id": pb_id},
    )
    assert quote.status_code == 201
    quote_id = quote.json()["id"]

    line = client.post(
        f"/api/quotes/{quote_id}/line-items",
        headers=headers,
        json={"commercial_item_id": item_id, "quantity": 2, "discount_pct": 5},
    )
    assert line.status_code == 201

    preview = client.post(f"/api/quotes/{quote_id}/price-preview", headers=headers)
    assert preview.status_code == 200

    ai_suggest = client.post(f"/api/ai/pricing-suggestions/{quote_id}", headers=headers)
    assert ai_suggest.status_code == 200

    ai_risk = client.post(f"/api/ai/quote-risk/{quote_id}", headers=headers)
    assert ai_risk.status_code == 200

    optimize = client.post(
        "/api/ai/discount-optimization",
        headers=headers,
        json={"quote_id": quote_id, "target_margin_pct": 22},
    )
    assert optimize.status_code == 200

    # Integration queue
    endpoint = client.post(
        "/api/integrations/endpoints",
        headers=headers,
        json={"provider": "Salesforce", "endpoint_url": "https://example.test/sf", "auth_mode": "OAUTH2"},
    )
    assert endpoint.status_code == 200

    sync = client.post(f"/api/integrations/sync/quotes/{quote_id}", headers=headers)
    assert sync.status_code == 200
    assert sync.json()["status"] in {"QUEUED", "EXECUTED_LOCAL"}

    # Audit and observability
    audit = client.get("/api/audit/events", headers=headers)
    assert audit.status_code == 200
    assert len(audit.json()) > 0

    metrics = client.get("/api/observability/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["request_count"] > 0
