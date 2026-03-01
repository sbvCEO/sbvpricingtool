from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.rbac import require_permission
from app.schemas import AuthContext

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

plugins_registry: dict[str, list[dict]] = {}


class PluginCreateRequest(BaseModel):
    name: str
    plugin_type: str
    entrypoint: str


@router.post("/register")
def register_plugin(
    payload: PluginCreateRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    plugin = {
        "id": str(uuid4()),
        "tenant_id": str(ctx.tenant_id),
        **payload.model_dump(),
        "status": "REGISTERED",
        "sandbox_mode": "RESTRICTED",
    }
    plugins_registry.setdefault(str(ctx.tenant_id), []).append(plugin)
    return plugin


@router.get("")
def list_plugins(
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return plugins_registry.get(str(ctx.tenant_id), [])
