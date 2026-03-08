from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.admin_store import (
    create_contact,
    create_customer,
    create_opportunity,
    delete_contact,
    delete_customer,
    delete_opportunity,
    get_contact,
    get_customer,
    get_lifecycle_config,
    get_opportunity,
    get_pipeline_summary,
    list_contacts,
    list_customers,
    list_opportunities,
    update_contact,
    update_customer,
    update_opportunity,
)
from app.pricing import price_quote
from app.quote_generation_engine import QuoteComputationEngine, QuoteGeneralInput, QuoteLineInput, StorePriceBookResolver
from app.rbac import require_permission
from app.schemas import AuthContext, QuoteRead
from app.store import quote_store

router = APIRouter(prefix="/api/guided-quotes", tags=["guided-quotes"])


class CustomerCreatePayload(BaseModel):
    name: str
    external_id: str | None = None
    segment: str = "UNSPECIFIED"
    industry: str = "UNSPECIFIED"
    website: str = ""
    owner: str = ""
    notes: str = ""


class CustomerUpdatePayload(BaseModel):
    name: str | None = None
    external_id: str | None = None
    segment: str | None = None
    industry: str | None = None
    website: str | None = None
    owner: str | None = None
    notes: str | None = None
    active: bool | None = None


class ContactCreatePayload(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str = ""
    title: str = ""
    role: str = "STAKEHOLDER"
    status: str = "ACTIVE"
    is_primary: bool = False


class ContactUpdatePayload(BaseModel):
    customer_id: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    role: str | None = None
    status: str | None = None
    is_primary: bool | None = None


class OpportunityCreatePayload(BaseModel):
    customer_id: str
    name: str
    record_type: str = "OPPORTUNITY"
    stage: str = "NEW"
    amount: float = 0.0
    close_date: str | None = None
    probability_pct: float = 20.0
    owner: str = ""
    source: str = "MANUAL"
    status: str = "OPEN"
    notes: str = ""


class OpportunityUpdatePayload(BaseModel):
    customer_id: str | None = None
    record_type: str | None = None
    name: str | None = None
    stage: str | None = None
    amount: float | None = None
    close_date: str | None = None
    probability_pct: float | None = None
    owner: str | None = None
    source: str | None = None
    status: str | None = None
    notes: str | None = None


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


@router.get("/lifecycle")
def get_lifecycle(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return get_lifecycle_config()


@router.get("/pipeline/summary")
def get_pipeline(
    ctx: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    return get_pipeline_summary(ctx.tenant_id)


@router.get("/customers")
def get_customers(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
    search: Annotated[str, Query()] = "",
):
    return list_customers(ctx.tenant_id, search)


@router.get("/customers/{customer_id}")
def get_customer_by_id(
    customer_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    try:
        return get_customer(ctx.tenant_id, customer_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/customers", status_code=status.HTTP_201_CREATED)
def post_customer(
    payload: CustomerCreatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return create_customer(ctx.tenant_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/customers/{customer_id}")
def patch_customer(
    customer_id: str,
    payload: CustomerUpdatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return update_customer(ctx.tenant_id, customer_id, payload.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_customer(
    customer_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        delete_customer(ctx.tenant_id, customer_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/contacts")
def get_contacts(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
    customer_id: Annotated[str | None, Query()] = None,
    search: Annotated[str, Query()] = "",
):
    return list_contacts(ctx.tenant_id, customer_id=customer_id, search=search)


@router.get("/contacts/{contact_id}")
def get_contact_by_id(
    contact_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    try:
        return get_contact(ctx.tenant_id, contact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
def post_contact(
    payload: ContactCreatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return create_contact(ctx.tenant_id, payload.model_dump())
    except (KeyError, ValueError) as exc:
        status_code = 404 if isinstance(exc, KeyError) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/contacts/{contact_id}")
def patch_contact(
    contact_id: str,
    payload: ContactUpdatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return update_contact(ctx.tenant_id, contact_id, payload.model_dump(exclude_unset=True))
    except (KeyError, ValueError) as exc:
        status_code = 404 if isinstance(exc, KeyError) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_contact(
    contact_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        delete_contact(ctx.tenant_id, contact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities")
def get_opportunities(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
    customer_id: Annotated[str | None, Query()] = None,
    search: Annotated[str, Query()] = "",
    record_type: Annotated[str | None, Query()] = None,
):
    return list_opportunities(ctx.tenant_id, customer_id=customer_id, search=search, record_type=record_type)


@router.get("/opportunities/{opportunity_id}")
def get_opportunity_by_id(
    opportunity_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    try:
        return get_opportunity(ctx.tenant_id, opportunity_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
def post_opportunity(
    payload: OpportunityCreatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return create_opportunity(ctx.tenant_id, payload.model_dump())
    except (KeyError, ValueError) as exc:
        status_code = 404 if isinstance(exc, KeyError) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/opportunities/{opportunity_id}")
def patch_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdatePayload,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        return update_opportunity(ctx.tenant_id, opportunity_id, payload.model_dump(exclude_unset=True))
    except (KeyError, ValueError) as exc:
        status_code = 404 if isinstance(exc, KeyError) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete("/opportunities/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_opportunity(
    opportunity_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    try:
        delete_opportunity(ctx.tenant_id, opportunity_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/quotes", response_model=list[QuoteRead])
def get_quotes_for_customer(
    customer_id: str,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quotes = [
        quote
        for quote in quote_store.list_quotes(ctx.tenant_id)
        if str(quote.get("customer_external_id") or quote.get("customer_account_id") or "") == customer_id
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
            "customer_account_id": payload.customer_id,
            "opportunity_id": payload.opportunity_id,
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
