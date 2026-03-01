from typing import Any
from uuid import UUID, uuid4

from app.admin_repo import admin_repo


def _default_state() -> dict[str, Any]:
    return {
        "org_settings": {
            "name": "Default Organization",
            "region": "US",
            "timezone": "UTC",
            "default_currency": "USD",
            "fiscal_year_start": "2026-01-01",
            "tax_behavior": "CALCULATED",
            "primary_color": "#0f8f7a",
            "logo_url": "",
        },
        "users": [
            {"id": str(uuid4()), "email": "admin@tenant.com", "role": "ADMIN", "active": True},
        ],
        "role_matrix": {
            "ADMIN": {
                "quotes:view": True,
                "quotes:edit": True,
                "pricebooks:edit": True,
                "analytics:view": True,
                "margin:view": True,
                "discount:view": True,
                "export:quote": True,
            },
            "FUNCTION_ADMIN": {
                "quotes:view": True,
                "quotes:edit": True,
                "pricebooks:edit": True,
                "analytics:view": True,
                "margin:view": True,
                "discount:view": True,
                "export:quote": True,
            },
            "END_USER": {
                "quotes:view": True,
                "quotes:edit": True,
                "pricebooks:edit": False,
                "analytics:view": True,
                "margin:view": False,
                "discount:view": False,
                "export:quote": True,
            },
        },
        "feature_flags": {
            "pricing_simulator_v2": True,
            "approval_risk_panel": True,
            "advanced_anomalies": True,
        },
        "rate_cards": [
            {"id": str(uuid4()), "role": "Architect", "delivery": "ONSITE", "rate": 250.0, "region": "US", "effective": "2026-01-01"},
            {"id": str(uuid4()), "role": "Analyst", "delivery": "OFFSHORE", "rate": 90.0, "region": "IN", "effective": "2026-01-01"},
        ],
    }


def _ensure(tenant_id: UUID) -> dict[str, Any]:
    state = admin_repo.get_state(tenant_id)
    if state is None:
        state = _default_state()
        admin_repo.save_state(tenant_id, state)
    return state


def _persist(tenant_id: UUID, state: dict[str, Any]) -> dict[str, Any]:
    return admin_repo.save_state(tenant_id, state)


def get_org_settings(tenant_id: UUID) -> dict[str, Any]:
    return _ensure(tenant_id)["org_settings"]


def save_org_settings(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    state["org_settings"] = payload
    _persist(tenant_id, state)
    return payload


def list_users(tenant_id: UUID) -> list[dict[str, Any]]:
    return _ensure(tenant_id)["users"]


def invite_user(tenant_id: UUID, email: str, role: str) -> dict[str, Any]:
    state = _ensure(tenant_id)
    user = {"id": str(uuid4()), "email": email, "role": role, "active": True}
    state["users"].append(user)
    _persist(tenant_id, state)
    return user


def toggle_user(tenant_id: UUID, user_id: str) -> dict[str, Any]:
    state = _ensure(tenant_id)
    for user in state["users"]:
        if user["id"] == user_id:
            user["active"] = not user["active"]
            _persist(tenant_id, state)
            return user
    raise KeyError("User not found")


def get_role_matrix(tenant_id: UUID) -> dict[str, Any]:
    return _ensure(tenant_id)["role_matrix"]


def save_role_matrix(tenant_id: UUID, matrix: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    state["role_matrix"] = matrix
    _persist(tenant_id, state)
    return matrix


def get_feature_flags(tenant_id: UUID) -> dict[str, bool]:
    return _ensure(tenant_id)["feature_flags"]


def save_feature_flags(tenant_id: UUID, flags: dict[str, bool]) -> dict[str, bool]:
    state = _ensure(tenant_id)
    state["feature_flags"] = flags
    _persist(tenant_id, state)
    return flags


def list_rate_cards(tenant_id: UUID) -> list[dict[str, Any]]:
    return _ensure(tenant_id)["rate_cards"]


def create_rate_card_row(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    row = {"id": str(uuid4()), **payload}
    state["rate_cards"].append(row)
    _persist(tenant_id, state)
    return row


def bulk_update_rate_cards(tenant_id: UUID, pct: float) -> list[dict[str, Any]]:
    state = _ensure(tenant_id)
    rows = state["rate_cards"]
    factor = 1 + (pct / 100.0)
    for row in rows:
        row["rate"] = round(float(row["rate"]) * factor, 2)
    _persist(tenant_id, state)
    return rows
