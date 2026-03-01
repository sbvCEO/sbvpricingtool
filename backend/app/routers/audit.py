from typing import Annotated

from fastapi import APIRouter, Depends

from app.audit import list_audit_events
from app.rbac import require_permission
from app.schemas import AuthContext

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/events")
def get_audit_events(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return list_audit_events(ctx.tenant_id)
