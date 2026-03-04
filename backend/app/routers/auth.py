from typing import Annotated
from uuid import UUID

import jwt
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException, status

from app.admin_store import resolve_user_role
from app.config import settings
from app.rbac import require_permission, resolved_permissions
from app.schemas import AuthContext
from app.security import get_current_auth_context

router = APIRouter(prefix="/api/auth", tags=["auth"])


class DevTokenRequest(BaseModel):
    tenant_id: UUID
    email: EmailStr
    password: str
    scopes: list[str] = []


@router.get("/me")
def me(ctx: Annotated[AuthContext, Depends(get_current_auth_context)]):
    return {
        "sub": ctx.sub,
        "tenant_id": str(ctx.tenant_id),
        "roles": ctx.roles,
        "scopes": ctx.scopes,
        "permissions": sorted(resolved_permissions(ctx)),
    }


@router.get("/permissions-check")
def permissions_check(
    _: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    return {"ok": True, "permission": "dashboard:read"}


@router.post("/dev-token")
def dev_token(payload: DevTokenRequest):
    role = resolve_user_role(payload.tenant_id, payload.email, payload.password)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not provisioned for this tenant or is inactive",
        )

    token = jwt.encode(
        {
            "sub": str(payload.email).lower(),
            "tenant_id": str(payload.tenant_id),
            "roles": [role],
            "scopes": payload.scopes,
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"access_token": token}
