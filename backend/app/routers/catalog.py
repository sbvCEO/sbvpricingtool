from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.rbac import require_permission
from app.schemas import (
    AuthContext,
    BundleItemLinkCreate,
    BundleItemLinkRead,
    CommercialItemCreate,
    CommercialItemRead,
)
from app.store import catalog_store

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.post(
    "/items",
    response_model=CommercialItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    payload: CommercialItemCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("catalog:write"))],
):
    try:
        item = catalog_store.create_item(ctx.tenant_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CommercialItemRead(**item)


@router.get("/items", response_model=list[CommercialItemRead])
def list_items(
    ctx: Annotated[AuthContext, Depends(require_permission("catalog:read"))],
):
    items = catalog_store.list_items(ctx.tenant_id)
    return [CommercialItemRead(**item) for item in items]


@router.get("/items/{item_id}", response_model=CommercialItemRead)
def get_item(
    item_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("catalog:read"))],
):
    item = catalog_store.get_item(ctx.tenant_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Commercial item not found")
    return CommercialItemRead(**item)


@router.post(
    "/bundles/{bundle_item_id}/items",
    response_model=BundleItemLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def link_bundle_item(
    bundle_item_id: UUID,
    payload: BundleItemLinkCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("catalog:write"))],
):
    try:
        link = catalog_store.link_bundle_item(
            ctx.tenant_id,
            bundle_item_id,
            payload.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BundleItemLinkRead(**link)
