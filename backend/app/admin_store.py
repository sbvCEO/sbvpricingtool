from typing import Any
from uuid import UUID, uuid4

from app.admin_repo import admin_repo

DEFAULT_LOGIN_USERS = [
    {"email": "admin@spt.com", "role": "ADMIN", "password": "r@ndom11", "active": True},
    {"email": "user@spt.com", "role": "SALES", "password": "r@ndom11", "active": True},
]


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
            {"id": str(uuid4()), "email": user["email"], "role": user["role"], "active": user["active"]}
            for user in DEFAULT_LOGIN_USERS
        ],
        "auth_directory": [
            {"email": user["email"], "password": user["password"], "role": user["role"], "active": user["active"]}
            for user in DEFAULT_LOGIN_USERS
        ],
        "role_matrix": {
            "ADMIN": {
                "admin:manage": True,
                "admin:org:read": True,
                "admin:org:write": True,
                "admin:user:read": True,
                "admin:user:write": True,
                "admin:rbac:read": True,
                "admin:rbac:write": True,
                "admin:governance:read": True,
                "admin:governance:write": True,
                "catalog:read": True,
                "catalog:write": True,
                "pricebook:read": True,
                "pricebook:write": True,
                "quote:read": True,
                "quote:write": True,
                "approval:act": True,
                "dashboard:read": True,
                "async:run": True,
            },
            "SALES": {
                "catalog:read": True,
                "pricebook:read": True,
                "quote:read": True,
                "quote:write": True,
                "approval:act": True,
                "dashboard:read": True,
            },
            "OPERATIONS": {
                "catalog:read": True,
                "pricebook:read": True,
                "pricebook:write": True,
                "quote:read": True,
                "quote:write": True,
                "dashboard:read": True,
            },
            "FINANCE": {
                "catalog:read": True,
                "pricebook:read": True,
                "quote:read": True,
                "approval:act": True,
                "dashboard:read": True,
            },
            "DELIVERY": {
                "catalog:read": True,
                "pricebook:read": True,
                "quote:read": True,
                "quote:write": True,
                "dashboard:read": True,
            },
            "LEADERSHIP": {
                "catalog:read": True,
                "pricebook:read": True,
                "quote:read": True,
                "approval:act": True,
                "dashboard:read": True,
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
        "customers": [
            {"id": str(uuid4()), "name": "Acme Healthcare", "external_id": "CUST-ACME", "segment": "ENTERPRISE", "active": True},
            {"id": str(uuid4()), "name": "Globex Manufacturing", "external_id": "CUST-GLOBEX", "segment": "MID_MARKET", "active": True},
        ],
        "opportunities": [],
    }


def _ensure_guided_state(state: dict[str, Any]) -> None:
    state.setdefault("customers", [])
    state.setdefault("opportunities", [])


def _ensure_auth_directory(state: dict[str, Any]) -> None:
    auth_directory = state.setdefault("auth_directory", [])
    by_email = {
        str(entry.get("email", "")).strip().lower(): entry
        for entry in auth_directory
        if entry.get("email")
    }
    users = state.setdefault("users", [])
    user_by_email = {str(user.get("email", "")).strip().lower(): user for user in users if user.get("email")}

    for seed in DEFAULT_LOGIN_USERS:
        email = seed["email"].strip().lower()

        user_entry = user_by_email.get(email)
        if user_entry is None:
            users.append({"id": str(uuid4()), "email": seed["email"], "role": seed["role"], "active": seed["active"]})
        else:
            user_entry["role"] = seed["role"]
            user_entry["active"] = seed["active"]

        auth_entry = by_email.get(email)
        if auth_entry is None:
            auth_directory.append(
                {"email": seed["email"], "password": seed["password"], "role": seed["role"], "active": seed["active"]}
            )
        else:
            auth_entry["role"] = seed["role"]
            auth_entry["password"] = seed["password"]
            auth_entry["active"] = seed["active"]


def _ensure(tenant_id: UUID) -> dict[str, Any]:
    state = admin_repo.get_state(tenant_id)
    if state is None:
        state = _default_state()
        admin_repo.save_state(tenant_id, state)
    _ensure_guided_state(state)
    _ensure_auth_directory(state)
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


def resolve_user_role(tenant_id: UUID, email: str, password: str | None = None) -> str | None:
    state = _ensure(tenant_id)
    normalized = email.strip().lower()
    for auth_user in state.get("auth_directory", []):
        if str(auth_user.get("email", "")).strip().lower() != normalized:
            continue
        if not bool(auth_user.get("active", True)):
            return None
        if password is not None and str(auth_user.get("password", "")) != password:
            return None
        return str(auth_user.get("role", "")).upper() or None

    for user in list_users(tenant_id):
        if str(user.get("email", "")).strip().lower() == normalized and bool(user.get("active", True)):
            if password is not None:
                return None
            return str(user.get("role", "")).upper() or None
    return None


def list_customers(tenant_id: UUID, search: str = "") -> list[dict[str, Any]]:
    state = _ensure(tenant_id)
    customers = state["customers"]
    q = search.strip().lower()
    if not q:
        return customers
    return [
        customer
        for customer in customers
        if q in str(customer.get("name", "")).lower() or q in str(customer.get("external_id", "")).lower()
    ]


def create_customer(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    customer = {
        "id": str(uuid4()),
        "name": payload["name"],
        "external_id": payload.get("external_id") or f"CUST-{uuid4().hex[:8].upper()}",
        "segment": payload.get("segment", "UNSPECIFIED"),
        "active": True,
    }
    state["customers"].append(customer)
    _persist(tenant_id, state)
    return customer


def list_opportunities(tenant_id: UUID, customer_id: str | None = None, search: str = "") -> list[dict[str, Any]]:
    state = _ensure(tenant_id)
    opportunities = state["opportunities"]
    if customer_id:
        opportunities = [opp for opp in opportunities if opp.get("customer_id") == customer_id]
    q = search.strip().lower()
    if not q:
        return opportunities
    return [
        opp
        for opp in opportunities
        if q in str(opp.get("name", "")).lower() or q in str(opp.get("stage", "")).lower()
    ]


def create_opportunity(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    opportunity = {
        "id": str(uuid4()),
        "customer_id": payload["customer_id"],
        "name": payload["name"],
        "stage": payload.get("stage", "QUALIFICATION"),
        "amount": float(payload.get("amount", 0.0)),
        "close_date": payload.get("close_date"),
    }
    state["opportunities"].append(opportunity)
    _persist(tenant_id, state)
    return opportunity


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
