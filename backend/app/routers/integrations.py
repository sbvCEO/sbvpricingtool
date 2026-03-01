from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.async_dispatch import dispatch_task
from app.rbac import require_permission
from app.schemas import AuthContext
from app.tasks import crm_sync_quote, publish_outbox_events

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

integration_registry: dict[str, list[dict]] = {}


class IntegrationEndpointCreate(BaseModel):
    provider: str
    endpoint_url: str
    auth_mode: str = "API_KEY"


@router.post("/endpoints")
def register_endpoint(
    payload: IntegrationEndpointCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    rec = {
        "id": str(uuid4()),
        "tenant_id": str(ctx.tenant_id),
        **payload.model_dump(),
        "status": "ACTIVE",
    }
    integration_registry.setdefault(str(ctx.tenant_id), []).append(rec)
    return rec


@router.get("/endpoints")
def list_endpoints(
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return integration_registry.get(str(ctx.tenant_id), [])


@router.post("/sync")
def trigger_sync(
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return dispatch_task(publish_outbox_events, str(ctx.tenant_id))


@router.post("/sync/quotes/{quote_id}")
def trigger_quote_sync(
    quote_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return dispatch_task(crm_sync_quote, str(ctx.tenant_id), quote_id)
