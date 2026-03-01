from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.admin_repo import admin_repo
from app.config import settings
from main import app

client = TestClient(app)


def _token(tenant_id: str, role: str) -> str:
    payload = {
        "sub": "admin-user",
        "tenant_id": tenant_id,
        "roles": [role],
        "scopes": [],
        "aud": settings.jwt_audience,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _headers(tenant_id: str, token: str):
    return {
        "X-Tenant-Id": tenant_id,
        "Authorization": f"Bearer {token}",
    }


def setup_function() -> None:
    admin_repo.clear()


def test_admin_org_users_and_flags_flow() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, "ADMIN")
    headers = _headers(tenant_id, token)

    org = client.get('/api/admin/org-settings', headers=headers)
    assert org.status_code == 200

    update_org = client.put(
        '/api/admin/org-settings',
        headers=headers,
        json={
            "name": "Acme",
            "region": "US",
            "timezone": "America/New_York",
            "default_currency": "USD",
            "fiscal_year_start": "2026-01-01",
            "tax_behavior": "CALCULATED",
            "primary_color": "#0f8f7a",
            "logo_url": "https://cdn/logo.png",
        },
    )
    assert update_org.status_code == 200

    invite = client.post('/api/admin/users', headers=headers, json={"email": "new@tenant.com", "role": "END_USER"})
    assert invite.status_code == 200
    uid = invite.json()['id']

    toggle = client.patch(f'/api/admin/users/{uid}/toggle', headers=headers)
    assert toggle.status_code == 200
    assert toggle.json()['active'] is False

    matrix = client.get('/api/admin/role-matrix', headers=headers)
    assert matrix.status_code == 200

    put_matrix = client.put('/api/admin/role-matrix', headers=headers, json={"matrix": matrix.json()})
    assert put_matrix.status_code == 200

    flags = client.get('/api/admin/feature-flags', headers=headers)
    assert flags.status_code == 200

    put_flags = client.put('/api/admin/feature-flags', headers=headers, json={"flags": {"pricing_simulator_v2": False}})
    assert put_flags.status_code == 200


def test_rate_card_flow_for_function_admin() -> None:
    tenant_id = str(uuid4())
    token = _token(tenant_id, "FUNCTION_ADMIN")
    headers = _headers(tenant_id, token)

    list_resp = client.get('/api/admin/rate-cards', headers=headers)
    assert list_resp.status_code == 200

    create_resp = client.post(
        '/api/admin/rate-cards',
        headers=headers,
        json={"role": "SME", "delivery": "REMOTE", "rate": 180, "region": "US", "effective": "2026-01-01"},
    )
    assert create_resp.status_code == 200

    bulk = client.post('/api/admin/rate-cards/bulk-update', headers=headers, json={"pct": 5})
    assert bulk.status_code == 200
    assert len(bulk.json()) >= 1
