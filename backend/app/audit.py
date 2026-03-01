from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


audit_events: dict[UUID, list[dict[str, Any]]] = {}


def record_audit_event(
    tenant_id: UUID,
    entity_type: str,
    action: str,
    actor_sub: str | None,
    path: str,
    method: str,
    status_code: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "entity_type": entity_type,
        "action": action,
        "actor_sub": actor_sub,
        "path": path,
        "method": method,
        "status_code": status_code,
        "metadata": metadata or {},
        "created_at": datetime.now(UTC).isoformat(),
    }
    audit_events.setdefault(tenant_id, []).append(event)
    return event


def list_audit_events(tenant_id: UUID) -> list[dict[str, Any]]:
    return list(audit_events.get(tenant_id, []))
