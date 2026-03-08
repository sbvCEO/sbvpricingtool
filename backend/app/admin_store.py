from typing import Any
from uuid import UUID, uuid4

from app.admin_repo import admin_repo

LEAD_LIFECYCLE = ["NEW", "QUALIFICATION", "NURTURE", "CONVERTED", "DISQUALIFIED"]
OPPORTUNITY_LIFECYCLE = [
    "NEW",
    "PROSPECTING",
    "QUALIFICATION",
    "SCOPING",
    "SOLUTION_FIT",
    "PROPOSAL",
    "NEGOTIATION",
    "CLOSED_WON",
    "CLOSED_LOST",
]

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
        "contacts": [],
        "opportunities": [],
    }


def _ensure_guided_state(state: dict[str, Any]) -> None:
    state.setdefault("customers", [])
    state.setdefault("contacts", [])
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


def get_customer(tenant_id: UUID, customer_id: str) -> dict[str, Any]:
    state = _ensure(tenant_id)
    customer = next((item for item in state["customers"] if item.get("id") == customer_id), None)
    if not customer:
        raise KeyError("Customer not found")
    return customer


def create_customer(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Customer name is required")
    external_id = str(payload.get("external_id") or f"CUST-{uuid4().hex[:8].upper()}").strip()
    for existing in state["customers"]:
        if str(existing.get("external_id", "")).strip().lower() == external_id.lower():
            raise ValueError("Customer external_id already exists")
    customer = {
        "id": str(uuid4()),
        "name": name,
        "external_id": external_id,
        "segment": payload.get("segment", "UNSPECIFIED"),
        "industry": payload.get("industry", "UNSPECIFIED"),
        "website": payload.get("website", ""),
        "owner": payload.get("owner", ""),
        "notes": payload.get("notes", ""),
        "active": True,
    }
    state["customers"].append(customer)
    _persist(tenant_id, state)
    return customer


def update_customer(tenant_id: UUID, customer_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    customer = next((item for item in state["customers"] if item.get("id") == customer_id), None)
    if not customer:
        raise KeyError("Customer not found")

    if "external_id" in patch and patch["external_id"]:
        candidate = str(patch["external_id"]).strip()
        for existing in state["customers"]:
            if existing.get("id") != customer_id and str(existing.get("external_id", "")).strip().lower() == candidate.lower():
                raise ValueError("Customer external_id already exists")

    allowed = {"name", "external_id", "segment", "industry", "website", "owner", "notes", "active"}
    for key, value in patch.items():
        if key in allowed and value is not None:
            customer[key] = value
    _persist(tenant_id, state)
    return customer


def delete_customer(tenant_id: UUID, customer_id: str) -> None:
    state = _ensure(tenant_id)
    before = len(state["customers"])
    state["customers"] = [item for item in state["customers"] if item.get("id") != customer_id]
    if len(state["customers"]) == before:
        raise KeyError("Customer not found")
    state["contacts"] = [item for item in state["contacts"] if item.get("customer_id") != customer_id]
    state["opportunities"] = [item for item in state["opportunities"] if item.get("customer_id") != customer_id]
    _persist(tenant_id, state)


def list_contacts(tenant_id: UUID, customer_id: str | None = None, search: str = "") -> list[dict[str, Any]]:
    state = _ensure(tenant_id)
    contacts = state["contacts"]
    if customer_id:
        contacts = [contact for contact in contacts if contact.get("customer_id") == customer_id]
    q = search.strip().lower()
    if not q:
        return contacts
    return [
        contact
        for contact in contacts
        if q in str(contact.get("name", "")).lower()
        or q in str(contact.get("email", "")).lower()
        or q in str(contact.get("title", "")).lower()
    ]


def get_contact(tenant_id: UUID, contact_id: str) -> dict[str, Any]:
    state = _ensure(tenant_id)
    contact = next((item for item in state["contacts"] if item.get("id") == contact_id), None)
    if not contact:
        raise KeyError("Contact not found")
    return contact


def create_contact(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    customer_id = str(payload.get("customer_id", "")).strip()
    if not customer_id:
        raise ValueError("customer_id is required")
    if not next((item for item in state["customers"] if item.get("id") == customer_id), None):
        raise KeyError("Customer not found")
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise ValueError("Contact email is required")
    for existing in state["contacts"]:
        if existing.get("customer_id") == customer_id and str(existing.get("email", "")).strip().lower() == email:
            raise ValueError("Contact email already exists for this customer")
    contact = {
        "id": str(uuid4()),
        "customer_id": customer_id,
        "name": str(payload.get("name", "")).strip() or email,
        "email": email,
        "phone": str(payload.get("phone", "")).strip(),
        "title": str(payload.get("title", "")).strip(),
        "role": str(payload.get("role", "STAKEHOLDER")).strip().upper(),
        "status": str(payload.get("status", "ACTIVE")).strip().upper(),
        "is_primary": bool(payload.get("is_primary", False)),
    }
    if contact["is_primary"]:
        for existing in state["contacts"]:
            if existing.get("customer_id") == customer_id:
                existing["is_primary"] = False
    state["contacts"].append(contact)
    _persist(tenant_id, state)
    return contact


def update_contact(tenant_id: UUID, contact_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    contact = next((item for item in state["contacts"] if item.get("id") == contact_id), None)
    if not contact:
        raise KeyError("Contact not found")

    if "customer_id" in patch and patch["customer_id"]:
        customer_id = str(patch["customer_id"]).strip()
        if not next((item for item in state["customers"] if item.get("id") == customer_id), None):
            raise KeyError("Customer not found")
        contact["customer_id"] = customer_id

    if "email" in patch and patch["email"]:
        email = str(patch["email"]).strip().lower()
        for existing in state["contacts"]:
            if existing.get("id") != contact_id and existing.get("customer_id") == contact.get("customer_id") and str(existing.get("email", "")).strip().lower() == email:
                raise ValueError("Contact email already exists for this customer")
        contact["email"] = email

    allowed = {"name", "phone", "title", "role", "status", "is_primary"}
    for key, value in patch.items():
        if key in allowed and value is not None:
            contact[key] = value

    if bool(contact.get("is_primary")):
        for existing in state["contacts"]:
            if existing.get("id") != contact_id and existing.get("customer_id") == contact.get("customer_id"):
                existing["is_primary"] = False

    _persist(tenant_id, state)
    return contact


def delete_contact(tenant_id: UUID, contact_id: str) -> None:
    state = _ensure(tenant_id)
    before = len(state["contacts"])
    state["contacts"] = [item for item in state["contacts"] if item.get("id") != contact_id]
    if len(state["contacts"]) == before:
        raise KeyError("Contact not found")
    _persist(tenant_id, state)


def list_opportunities(
    tenant_id: UUID,
    customer_id: str | None = None,
    search: str = "",
    record_type: str | None = None,
) -> list[dict[str, Any]]:
    state = _ensure(tenant_id)
    opportunities = state["opportunities"]
    if customer_id:
        opportunities = [opp for opp in opportunities if opp.get("customer_id") == customer_id]
    if record_type:
        opportunities = [opp for opp in opportunities if str(opp.get("record_type", "OPPORTUNITY")).upper() == record_type.upper()]
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
    customer_id = str(payload.get("customer_id", "")).strip()
    if not customer_id:
        raise ValueError("customer_id is required")
    if not next((item for item in state["customers"] if item.get("id") == customer_id), None):
        raise KeyError("Customer not found")
    record_type = str(payload.get("record_type", "OPPORTUNITY")).strip().upper()
    lifecycle = LEAD_LIFECYCLE if record_type == "LEAD" else OPPORTUNITY_LIFECYCLE
    stage = str(payload.get("stage", "NEW")).strip().upper()
    if stage not in lifecycle:
        stage = "NEW"
    opportunity = {
        "id": str(uuid4()),
        "customer_id": customer_id,
        "record_type": record_type,
        "name": payload["name"],
        "stage": stage,
        "amount": float(payload.get("amount", 0.0)),
        "close_date": payload.get("close_date"),
        "probability_pct": float(payload.get("probability_pct", 20.0)),
        "owner": payload.get("owner", ""),
        "source": payload.get("source", "MANUAL"),
        "status": payload.get("status", "OPEN"),
        "notes": payload.get("notes", ""),
    }
    state["opportunities"].append(opportunity)
    _persist(tenant_id, state)
    return opportunity


def get_opportunity(tenant_id: UUID, opportunity_id: str) -> dict[str, Any]:
    state = _ensure(tenant_id)
    opportunity = next((item for item in state["opportunities"] if item.get("id") == opportunity_id), None)
    if not opportunity:
        raise KeyError("Opportunity not found")
    return opportunity


def update_opportunity(tenant_id: UUID, opportunity_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    state = _ensure(tenant_id)
    opportunity = next((item for item in state["opportunities"] if item.get("id") == opportunity_id), None)
    if not opportunity:
        raise KeyError("Opportunity not found")

    if "customer_id" in patch and patch["customer_id"]:
        customer_id = str(patch["customer_id"]).strip()
        if not next((item for item in state["customers"] if item.get("id") == customer_id), None):
            raise KeyError("Customer not found")
        opportunity["customer_id"] = customer_id

    if "record_type" in patch and patch["record_type"]:
        opportunity["record_type"] = str(patch["record_type"]).strip().upper()

    lifecycle = LEAD_LIFECYCLE if str(opportunity.get("record_type", "OPPORTUNITY")).upper() == "LEAD" else OPPORTUNITY_LIFECYCLE
    if "stage" in patch and patch["stage"]:
        stage = str(patch["stage"]).strip().upper()
        if stage not in lifecycle:
            raise ValueError(f"Invalid lifecycle stage. Allowed: {', '.join(lifecycle)}")
        opportunity["stage"] = stage

    allowed = {"name", "amount", "close_date", "probability_pct", "owner", "source", "status", "notes"}
    for key, value in patch.items():
        if key in allowed and value is not None:
            opportunity[key] = value

    _persist(tenant_id, state)
    return opportunity


def delete_opportunity(tenant_id: UUID, opportunity_id: str) -> None:
    state = _ensure(tenant_id)
    before = len(state["opportunities"])
    state["opportunities"] = [item for item in state["opportunities"] if item.get("id") != opportunity_id]
    if len(state["opportunities"]) == before:
        raise KeyError("Opportunity not found")
    _persist(tenant_id, state)


def get_lifecycle_config() -> dict[str, list[str]]:
    return {
        "lead": LEAD_LIFECYCLE,
        "opportunity": OPPORTUNITY_LIFECYCLE,
    }


def get_pipeline_summary(tenant_id: UUID) -> dict[str, Any]:
    state = _ensure(tenant_id)
    opportunities = state["opportunities"]
    customers = {item["id"]: item for item in state["customers"]}

    by_stage: dict[str, int] = {}
    by_record_type: dict[str, int] = {}
    total_amount = 0.0
    weighted_amount = 0.0

    for opp in opportunities:
        stage = str(opp.get("stage", "NEW")).upper()
        by_stage[stage] = by_stage.get(stage, 0) + 1
        kind = str(opp.get("record_type", "OPPORTUNITY")).upper()
        by_record_type[kind] = by_record_type.get(kind, 0) + 1

        amount = float(opp.get("amount", 0.0))
        total_amount += amount
        probability_pct = float(opp.get("probability_pct", 0.0))
        weighted_amount += amount * (probability_pct / 100.0)

    account_totals: dict[str, float] = {}
    for opp in opportunities:
        customer_id = str(opp.get("customer_id", ""))
        account = customers.get(customer_id)
        if not account:
            continue
        account_name = str(account.get("name", "Unknown Account"))
        account_totals[account_name] = account_totals.get(account_name, 0.0) + float(opp.get("amount", 0.0))

    top_accounts = [
        {"account_name": name, "amount": round(amount, 2)}
        for name, amount in sorted(account_totals.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    closed_won = by_stage.get("CLOSED_WON", 0)
    closed_lost = by_stage.get("CLOSED_LOST", 0)
    closed_total = closed_won + closed_lost
    conversion_rate = round((closed_won / closed_total) * 100, 2) if closed_total > 0 else 0.0

    return {
        "accounts_total": len(state["customers"]),
        "contacts_total": len(state["contacts"]),
        "deals_total": len(opportunities),
        "open_deals": len([opp for opp in opportunities if str(opp.get("status", "OPEN")).upper() == "OPEN"]),
        "by_stage": by_stage,
        "by_record_type": by_record_type,
        "total_pipeline_amount": round(total_amount, 2),
        "weighted_pipeline_amount": round(weighted_amount, 2),
        "win_rate_pct": conversion_rate,
        "top_accounts": top_accounts,
    }


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
