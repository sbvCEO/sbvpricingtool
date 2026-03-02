from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.admin_store import (
    create_customer,
    create_opportunity,
    list_customers,
    list_opportunities,
)
from app.pricing import price_quote
from app.quote_generation_engine import (
    QuoteComputationEngine,
    QuoteGeneralInput,
    QuoteLineInput,
    StorePriceBookResolver,
)
from app.rbac import require_permission
from app.schemas import AuthContext, QuoteRead
from app.store import quote_store

router = APIRouter(prefix="/api/guided-quotes", tags=["guided-quotes"])


class CustomerCreatePayload(BaseModel):
    name: str
    external_id: str | None = None
    segment: str = "UNSPECIFIED"


class OpportunityCreatePayload(BaseModel):
    customer_id: str
    name: str
    stage: str = "QUALIFICATION"
    amount: float = 0.0
    close_date: str | None = None


class GuidedGeneralPayload(BaseModel):
    duration_type: Literal["ONETIME", "YEARS", "MONTHS"]
    duration_value: int = Field(ge=1, le=120)
    valid_until: str | None = None
    price_book_id: UUID
    currency: str = "USD"
    region: str = "US"
    overall_discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class GuidedLinePayload(BaseModel):
    commercial_item_id: UUID
    line_discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    quantity_schedule: dict[int, float] = Field(default_factory=dict)


class GuidedQuoteGeneratePayload(BaseModel):
    customer_id: str
    opportunity_id: str | None = None
    clone_quote_id: UUID | None = None
    general: GuidedGeneralPayload
    line_items: list[GuidedLinePayload] = Field(default_factory=list)


@router.get("/customers")
def get_customers(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
    search: Annotated[str, Query()] = "",
):
    return list_customers(ctx.tenant_id, search)


@router.post("/customers", status_code=status.HTTP_201_CREATED)
def post_customer(
    payload: CustomerCreatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    return create_customer(ctx.tenant_id, payload.model_dump())


@router.get("/opportunities")
def get_opportunities(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
    customer_id: Annotated[str | None, Query()] = None,
    search: Annotated[str, Query()] = "",
):
    return list_opportunities(ctx.tenant_id, customer_id=customer_id, search=search)


@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
def post_opportunity(
    payload: OpportunityCreatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    return create_opportunity(ctx.tenant_id, payload.model_dump())


@router.get("/customers/{customer_id}/quotes", response_model=list[QuoteRead])
def get_quotes_for_customer(
    customer_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quotes = [
        quote
        for quote in quote_store.list_quotes(ctx.tenant_id)
        if str(quote.get("customer_external_id") or "") == customer_id
    ]
    return [QuoteRead(**quote) for quote in quotes]


@router.post("/generate")
def generate_guided_quote(
    payload: GuidedQuoteGeneratePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    line_inputs: list[QuoteLineInput] = []

    if payload.clone_quote_id:
        source_quote = quote_store.get_quote(ctx.tenant_id, payload.clone_quote_id)
        if not source_quote:
            raise HTTPException(status_code=404, detail="Clone quote not found")
        source_lines = quote_store.list_lines(ctx.tenant_id, payload.clone_quote_id)
        for source in source_lines:
            line_inputs.append(
                QuoteLineInput(
                    commercial_item_id=source["commercial_item_id"],
                    line_discount_pct=float(source.get("discount_pct", 0.0)),
                    quantity_schedule={1: float(source.get("quantity", 0.0))},
                )
            )

    for line in payload.line_items:
        line_inputs.append(
            QuoteLineInput(
                commercial_item_id=line.commercial_item_id,
                line_discount_pct=line.line_discount_pct,
                quantity_schedule=line.quantity_schedule,
            )
        )

    if not line_inputs:
        raise HTTPException(status_code=400, detail="At least one line item is required")

    general = QuoteGeneralInput(
        duration_type=payload.general.duration_type,
        duration_value=payload.general.duration_value,
        overall_discount_pct=payload.general.overall_discount_pct,
    )
    resolver = StorePriceBookResolver(
        tenant_id=ctx.tenant_id,
        price_book_id=payload.general.price_book_id,
        region=payload.general.region,
        currency=payload.general.currency,
    )
    engine = QuoteComputationEngine(resolver)
    try:
        computation = engine.compute(general, line_inputs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    quote = quote_store.create_quote(
        ctx.tenant_id,
        {
            "customer_external_id": payload.customer_id,
            "currency": payload.general.currency,
            "region": payload.general.region,
            "price_book_id": payload.general.price_book_id,
            "valid_until": payload.general.valid_until,
        },
    )

    for line in computation.lines:
        quote_store.add_line(
            ctx.tenant_id,
            quote["id"],
            {
                "commercial_item_id": line.commercial_item_id,
                "quantity": line.quantity_total,
                "discount_pct": line.line_discount_pct,
                "config_json": {
                    "quantity_schedule": line.quantity_schedule,
                    "duration_type": payload.general.duration_type,
                    "duration_value": payload.general.duration_value,
                    "opportunity_id": payload.opportunity_id,
                    "overall_discount_pct": payload.general.overall_discount_pct,
                },
            },
        )

    preview = price_quote(ctx.tenant_id, quote["id"])
    return {
        "quote": QuoteRead(**quote),
        "computation": computation.to_dict(),
        "preview": preview,
    }
