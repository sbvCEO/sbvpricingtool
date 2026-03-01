from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.admin_store import (
    bulk_update_rate_cards,
    create_rate_card_row,
    get_feature_flags,
    get_org_settings,
    get_role_matrix,
    invite_user,
    list_rate_cards,
    list_users,
    save_feature_flags,
    save_org_settings,
    save_role_matrix,
    toggle_user,
)
from app.rbac import require_any_role, require_role
from app.schemas import AuthContext

router = APIRouter(prefix="/api/admin", tags=["admin"])


class OrgSettingsPayload(BaseModel):
    name: str
    region: str
    timezone: str
    default_currency: str
    fiscal_year_start: str
    tax_behavior: str
    primary_color: str
    logo_url: str


class InviteUserPayload(BaseModel):
    email: str
    role: str


class RoleMatrixPayload(BaseModel):
    matrix: dict[str, dict[str, bool]]


class FeatureFlagsPayload(BaseModel):
    flags: dict[str, bool]


class RateCardRowPayload(BaseModel):
    role: str
    delivery: str
    rate: float
    region: str
    effective: str


class BulkRatePayload(BaseModel):
    pct: float


@router.get("/org-settings")
def get_org(
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return get_org_settings(ctx.tenant_id)


@router.put("/org-settings")
def put_org(
    payload: OrgSettingsPayload,
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return save_org_settings(ctx.tenant_id, payload.model_dump())


@router.get("/users")
def get_users(
    ctx: Annotated[AuthContext, Depends(require_any_role("ADMIN", "FUNCTION_ADMIN"))],
):
    return list_users(ctx.tenant_id)


@router.post("/users")
def post_user(
    payload: InviteUserPayload,
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return invite_user(ctx.tenant_id, payload.email, payload.role)


@router.patch("/users/{user_id}/toggle")
def patch_user_toggle(
    user_id: str,
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    try:
        return toggle_user(ctx.tenant_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/role-matrix")
def get_matrix(
    ctx: Annotated[AuthContext, Depends(require_any_role("ADMIN", "FUNCTION_ADMIN"))],
):
    return get_role_matrix(ctx.tenant_id)


@router.put("/role-matrix")
def put_matrix(
    payload: RoleMatrixPayload,
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return save_role_matrix(ctx.tenant_id, payload.matrix)


@router.get("/feature-flags")
def get_flags(
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return get_feature_flags(ctx.tenant_id)


@router.put("/feature-flags")
def put_flags(
    payload: FeatureFlagsPayload,
    ctx: Annotated[AuthContext, Depends(require_role("ADMIN"))],
):
    return save_feature_flags(ctx.tenant_id, payload.flags)


@router.get("/rate-cards")
def get_rate_cards(
    ctx: Annotated[AuthContext, Depends(require_role("FUNCTION_ADMIN"))],
):
    return list_rate_cards(ctx.tenant_id)


@router.post("/rate-cards")
def post_rate_card(
    payload: RateCardRowPayload,
    ctx: Annotated[AuthContext, Depends(require_role("FUNCTION_ADMIN"))],
):
    return create_rate_card_row(ctx.tenant_id, payload.model_dump())


@router.post("/rate-cards/bulk-update")
def post_rate_bulk(
    payload: BulkRatePayload,
    ctx: Annotated[AuthContext, Depends(require_role("FUNCTION_ADMIN"))],
):
    return bulk_update_rate_cards(ctx.tenant_id, payload.pct)
