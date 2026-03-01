from typing import Annotated
from uuid import UUID

import jwt
from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.config import settings
from app.rbac import require_permission
from app.schemas import AuthContext
from app.security import get_current_auth_context

router = APIRouter(prefix="/api/auth", tags=["auth"])


class DevTokenRequest(BaseModel):
    tenant_id: UUID
    roles: list[str] = ["ADMIN"]
    scopes: list[str] = []


@router.get("/me")
def me(ctx: Annotated[AuthContext, Depends(get_current_auth_context)]):
    return {
        "sub": ctx.sub,
        "tenant_id": str(ctx.tenant_id),
        "roles": ctx.roles,
        "scopes": ctx.scopes,
    }


@router.get("/permissions-check")
def permissions_check(
    _: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    return {"ok": True, "permission": "dashboard:read"}


@router.post("/dev-token")
def dev_token(payload: DevTokenRequest):
    token = jwt.encode(
        {
            "sub": "dev-user",
            "tenant_id": str(payload.tenant_id),
            "roles": payload.roles,
            "scopes": payload.scopes,
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"access_token": token}
