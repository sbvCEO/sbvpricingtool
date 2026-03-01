from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.rbac import require_permission
from app.schemas import AuthContext, PriceBookCreate, PriceBookEntryCreate, PriceBookEntryRead, PriceBookRead
from app.store import price_book_store

router = APIRouter(prefix="/api/price-books", tags=["price-books"])


class PriceBookUpdate(BaseModel):
    name: str | None = None
    currency: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str | None = None
    metadata_json: dict | None = None


@router.post("", response_model=PriceBookRead, status_code=status.HTTP_201_CREATED)
def create_price_book(
    payload: PriceBookCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    book = price_book_store.create_book(ctx.tenant_id, payload.model_dump())
    return PriceBookRead(**book)


@router.get("", response_model=list[PriceBookRead])
def list_price_books(
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:read"))],
):
    return [PriceBookRead(**book) for book in price_book_store.list_books(ctx.tenant_id)]


@router.post("/{price_book_id}/publish", response_model=PriceBookRead)
def publish_price_book(
    price_book_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    try:
        book = price_book_store.publish_book(ctx.tenant_id, price_book_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PriceBookRead(**book)


@router.patch("/{price_book_id}", response_model=PriceBookRead)
def update_price_book(
    price_book_id: UUID,
    payload: PriceBookUpdate,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    try:
        book = price_book_store.update_book(
            ctx.tenant_id,
            price_book_id,
            payload.model_dump(exclude_unset=True),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PriceBookRead(**book)


@router.delete("/{price_book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_book(
    price_book_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    try:
        price_book_store.delete_book(ctx.tenant_id, price_book_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"Cannot delete price book: {exc}") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/entries", response_model=PriceBookEntryRead, status_code=status.HTTP_201_CREATED)
def create_price_book_entry(
    payload: PriceBookEntryCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:write"))],
):
    if not price_book_store.get_book(ctx.tenant_id, payload.price_book_id):
        raise HTTPException(status_code=404, detail="Price book not found")

    entry = price_book_store.create_entry(ctx.tenant_id, payload.model_dump())
    return PriceBookEntryRead(**entry)


@router.get("/{price_book_id}/entries", response_model=list[PriceBookEntryRead])
def list_price_book_entries(
    price_book_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("pricebook:read"))],
):
    entries = price_book_store.list_entries(ctx.tenant_id, price_book_id)
    return [PriceBookEntryRead(**entry) for entry in entries]
