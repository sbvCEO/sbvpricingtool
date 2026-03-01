from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.rbac import require_permission
from app.schemas import AuthContext

router = APIRouter(prefix="/api/security", tags=["security"])


class StepUpRequest(BaseModel):
    quote_id: UUID
    reason: str


@router.post("/step-up")
def step_up_auth(
    payload: StepUpRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    return {
        "tenant_id": str(ctx.tenant_id),
        "quote_id": str(payload.quote_id),
        "required": True,
        "factor": "TOTP_OR_WEBAUTHN",
        "reason": payload.reason,
    }


@router.get("/key-rotation-status")
def key_rotation_status(
    _: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    return {
        "last_rotation": "2026-02-01T00:00:00Z",
        "next_rotation_due": "2026-05-01T00:00:00Z",
        "status": "ON_TRACK",
    }
