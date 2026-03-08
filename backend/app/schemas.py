from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuthContext(BaseModel):
    sub: str
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)


class CommercialItemCreate(BaseModel):
    item_code: str
    name: str
    description: str | None = None
    item_type: str
    is_active: bool = True
    versionable: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CommercialItemRead(CommercialItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID


class BundleItemLinkCreate(BaseModel):
    child_item_id: UUID
    inclusion_type: str = "OPTIONAL"
    qty_rule_json: dict[str, Any] = Field(default_factory=dict)
    override_price_allowed: bool = False
    sort_order: int = 0


class BundleItemLinkRead(BundleItemLinkCreate):
    id: UUID = Field(default_factory=uuid4)
    bundle_item_id: UUID
    tenant_id: UUID


class PriceBookCreate(BaseModel):
    name: str
    currency: str
    valid_from: date | None = None
    valid_to: date | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PriceBookRead(PriceBookCreate):
    id: UUID
    tenant_id: UUID
    status: str


class PriceBookEntryCreate(BaseModel):
    price_book_id: UUID
    commercial_item_id: UUID
    pricing_model: str
    region: str | None = None
    currency: str | None = None
    base_price: float | None = None
    min_qty: float | None = None
    max_qty: float | None = None
    min_price: float | None = None
    max_discount_pct: float | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PriceBookEntryRead(PriceBookEntryCreate):
    id: UUID
    tenant_id: UUID


class QuoteCreate(BaseModel):
    customer_external_id: str | None = None
    customer_account_id: UUID | None = None
    opportunity_id: UUID | None = None
    currency: str
    region: str | None = None
    price_book_id: UUID
    valid_until: date | None = None


class QuoteRead(BaseModel):
    id: UUID
    tenant_id: UUID
    quote_no: str
    customer_external_id: str | None = None
    customer_account_id: UUID | None = None
    opportunity_id: UUID | None = None
    status: str
    currency: str
    region: str | None = None
    price_book_id: UUID
    subtotal: float
    discount_total: float
    surcharge_total: float
    tax_total: float
    grand_total: float
    margin_pct: float
    revision_no: int
    valid_until: date | None = None


class QuoteLineCreate(BaseModel):
    commercial_item_id: UUID
    quantity: float = 1
    discount_pct: float = 0
    term_months: int | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)


class QuoteLineRead(QuoteLineCreate):
    id: UUID
    tenant_id: UUID
    quote_id: UUID
    line_no: int
    unit_price: float | None = None
    list_price: float | None = None
    net_price: float | None = None
    pricing_snapshot_json: dict[str, Any] = Field(default_factory=dict)


class QuoteLineUpdate(BaseModel):
    quantity: float | None = None
    discount_pct: float | None = None
    term_months: int | None = None
    config_json: dict[str, Any] | None = None


class RevisionRead(BaseModel):
    id: UUID
    tenant_id: UUID
    quote_id: UUID
    revision_no: int
    change_reason: str
    snapshot_json: dict[str, Any]


class PricePreviewResult(BaseModel):
    quote_id: UUID
    subtotal: float
    discount_total: float
    grand_total: float
    margin_pct: float
    line_breakdown: list[dict[str, Any]]
    pricing_explanations: list[dict[str, Any]] = Field(default_factory=list)
    approval_signals: list[dict[str, Any]] = Field(default_factory=list)
    rule_impact_heatmap: list[dict[str, Any]] = Field(default_factory=list)
    engine_metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: UUID


class ApprovalInstanceRead(BaseModel):
    id: UUID
    tenant_id: UUID
    quote_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[dict[str, Any]]


class ApprovalActionRequest(BaseModel):
    action: Literal["APPROVE", "REJECT", "REQUEST_CHANGES"]
    comments: str | None = None


class AsyncJobResponse(BaseModel):
    task_id: str
    status: str


class DashboardMetricsRead(BaseModel):
    total_quotes: int
    draft_quotes: int
    pending_approvals: int
    finalized_quotes: int
    total_pipeline_value: float
    average_margin_pct: float


class DiscountOptimizationRequest(BaseModel):
    quote_id: UUID
    target_margin_pct: float = 20.0
