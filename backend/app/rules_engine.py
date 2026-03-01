from typing import Any
from uuid import UUID, uuid4

rules_store: dict[UUID, list[dict[str, Any]]] = {}


def create_rule(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    rule = {
        "id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "status": "DRAFT",
        **payload,
    }
    rules_store.setdefault(tenant_id, []).append(rule)
    return rule


def list_rules(tenant_id: UUID) -> list[dict[str, Any]]:
    return list(rules_store.get(tenant_id, []))


def validate_rule(payload: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    dsl = payload.get("dsl_json", {})
    if "when" not in dsl:
        issues.append("dsl_json.when missing")
    if "then" not in dsl:
        issues.append("dsl_json.then missing")
    return {"valid": len(issues) == 0, "issues": issues}


def publish_rule(tenant_id: UUID, rule_id: str) -> dict[str, Any]:
    for rule in rules_store.get(tenant_id, []):
        if rule["id"] == rule_id:
            rule["status"] = "PUBLISHED"
            return rule
    raise KeyError("Rule not found")


def simulate_rule(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    dsl = payload.get("dsl_json", {})
    when = dsl.get("when", {})
    then = dsl.get("then", {})

    for key, expected in when.items():
        if context.get(key) != expected:
            return {"matched": False, "action": None}

    return {"matched": True, "action": then}
