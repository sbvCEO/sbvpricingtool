from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.cache import clear_cache
from app.pricing import price_quote
from app.rbac import require_permission
from app.schemas import (
    AuthContext,
    PricePreviewResult,
    QuoteCreate,
    QuoteLineCreate,
    QuoteLineRead,
    QuoteLineUpdate,
    QuoteRead,
    RevisionRead,
)
from app.store import quote_store

router = APIRouter(prefix="/api/quotes", tags=["quotes"])

ALLOWED_TRANSITIONS = {
    "DRAFT": {"REVIEW", "ARCHIVED", "APPROVAL_PENDING"},
    "REVIEW": {"DRAFT", "APPROVAL_PENDING", "ARCHIVED"},
    "APPROVAL_PENDING": {"FINALIZED", "REJECTED"},
    "FINALIZED": {"ARCHIVED"},
    "REJECTED": {"DRAFT", "ARCHIVED"},
    "ARCHIVED": set(),
}


class RevisionRequest(BaseModel):
    change_reason: str


class StatusTransitionRequest(BaseModel):
    target_status: str


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    quote = quote_store.create_quote(ctx.tenant_id, payload.model_dump())
    return QuoteRead(**quote)


@router.get("", response_model=list[QuoteRead])
def list_quotes(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return [QuoteRead(**quote) for quote in quote_store.list_quotes(ctx.tenant_id)]


@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteRead(**quote)


@router.post("/{quote_id}/line-items", response_model=QuoteLineRead, status_code=status.HTTP_201_CREATED)
def add_line_item(
    quote_id: UUID,
    payload: QuoteLineCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        line = quote_store.add_line(ctx.tenant_id, quote_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clear_cache(prefix=f"price-preview:{ctx.tenant_id}:{quote_id}")
    return QuoteLineRead(**line)


@router.get("/{quote_id}/line-items", response_model=list[QuoteLineRead])
def list_line_items(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return [QuoteLineRead(**line) for line in quote_store.list_lines(ctx.tenant_id, quote_id)]


@router.patch("/{quote_id}/line-items/{line_id}", response_model=QuoteLineRead)
def update_line_item(
    quote_id: UUID,
    line_id: UUID,
    payload: QuoteLineUpdate,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        line = quote_store.update_line(ctx.tenant_id, quote_id, line_id, payload.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clear_cache(prefix=f"price-preview:{ctx.tenant_id}:{quote_id}")
    return QuoteLineRead(**line)


@router.delete("/{quote_id}/line-items/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line_item(
    quote_id: UUID,
    line_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        quote_store.delete_line(ctx.tenant_id, quote_id, line_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clear_cache(prefix=f"price-preview:{ctx.tenant_id}:{quote_id}")


@router.post("/{quote_id}/price-preview", response_model=PricePreviewResult)
def quote_price_preview(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        result = price_quote(ctx.tenant_id, quote_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PricePreviewResult(**result)


@router.post("/{quote_id}/revisions", response_model=RevisionRead, status_code=status.HTTP_201_CREATED)
def create_revision(
    quote_id: UUID,
    payload: RevisionRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        rev = quote_store.create_revision(ctx.tenant_id, quote_id, payload.change_reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clear_cache(prefix=f"price-preview:{ctx.tenant_id}:{quote_id}")
    return RevisionRead(**rev)


@router.get("/{quote_id}/revisions", response_model=list[RevisionRead])
def list_revisions(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    revisions = quote_store.list_revisions(ctx.tenant_id, quote_id)
    return [RevisionRead(**rev) for rev in revisions]


@router.get("/{quote_id}/traces")
def list_traces(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    traces = quote_store.list_traces(ctx.tenant_id, quote_id)
    return traces


@router.post("/{quote_id}/status", response_model=QuoteRead)
def transition_status(
    quote_id: UUID,
    payload: StatusTransitionRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    current = quote["status"]
    target = payload.target_status
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: {current} -> {target}",
        )

    updated = quote_store.set_status(ctx.tenant_id, quote_id, target)
    return QuoteRead(**updated)
