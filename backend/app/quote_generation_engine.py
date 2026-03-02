from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.store import price_book_store


class PriceBookResolver(Protocol):
    def resolve(self, commercial_item_id: UUID) -> dict | None:
        ...


@dataclass
class StorePriceBookResolver:
    tenant_id: UUID
    price_book_id: UUID
    region: str | None = None
    currency: str | None = None

    def resolve(self, commercial_item_id: UUID) -> dict | None:
        return price_book_store.find_entry_by_item(
            self.tenant_id,
            self.price_book_id,
            commercial_item_id,
            region=self.region,
            currency=self.currency,
        )


@dataclass
class QuoteGeneralInput:
    duration_type: str  # ONETIME | YEARS | MONTHS
    duration_value: int
    overall_discount_pct: float = 0.0

    def periods(self) -> int:
        if self.duration_type == "ONETIME":
            return 1
        return max(1, int(self.duration_value))


@dataclass
class QuoteLineInput:
    commercial_item_id: UUID
    quantity_schedule: dict[int, float] = field(default_factory=dict)
    line_discount_pct: float = 0.0

    def total_quantity(self) -> float:
        if not self.quantity_schedule:
            return 0.0
        return round(sum(float(value) for value in self.quantity_schedule.values()), 6)


@dataclass
class QuoteComputedLine:
    commercial_item_id: UUID
    quantity_total: float
    base_price: float
    list_total: float
    line_discount_pct: float
    line_discount_amount: float
    net_total: float
    max_discount_pct: float
    quantity_schedule: dict[int, float]


@dataclass
class QuoteComputationResult:
    lines: list[QuoteComputedLine]
    subtotal: float
    line_discount_total: float
    overall_discount_pct: float
    overall_discount_amount: float
    grand_total: float
    margin_pct: float

    def to_dict(self) -> dict:
        return {
            "lines": [
                {
                    "commercial_item_id": str(line.commercial_item_id),
                    "quantity_total": line.quantity_total,
                    "base_price": line.base_price,
                    "list_total": line.list_total,
                    "line_discount_pct": line.line_discount_pct,
                    "line_discount_amount": line.line_discount_amount,
                    "net_total": line.net_total,
                    "max_discount_pct": line.max_discount_pct,
                    "quantity_schedule": line.quantity_schedule,
                }
                for line in self.lines
            ],
            "subtotal": self.subtotal,
            "line_discount_total": self.line_discount_total,
            "overall_discount_pct": self.overall_discount_pct,
            "overall_discount_amount": self.overall_discount_amount,
            "grand_total": self.grand_total,
            "margin_pct": self.margin_pct,
        }


class QuoteComputationEngine:
    """Guided quote computation engine with explicit, testable pricing steps."""

    def __init__(self, resolver: PriceBookResolver) -> None:
        self.resolver = resolver

    @staticmethod
    def _bounded_discount(requested: float, max_allowed: float) -> float:
        requested_val = max(0.0, float(requested))
        return round(min(requested_val, max_allowed), 4)

    def compute(self, general: QuoteGeneralInput, line_inputs: list[QuoteLineInput]) -> QuoteComputationResult:
        computed_lines: list[QuoteComputedLine] = []
        subtotal = 0.0
        line_discount_total = 0.0

        for line in line_inputs:
            entry = self.resolver.resolve(line.commercial_item_id)
            if not entry:
                raise ValueError(f"Missing price book entry for item {line.commercial_item_id}")

            base_price = float(entry.get("base_price") or 0.0)
            max_discount_pct = float(entry.get("max_discount_pct") or 100.0)
            quantity_total = line.total_quantity()
            if quantity_total <= 0:
                raise ValueError(f"Quantity must be > 0 for item {line.commercial_item_id}")

            list_total = round(base_price * quantity_total, 6)
            applied_discount_pct = self._bounded_discount(line.line_discount_pct, max_discount_pct)
            discount_amount = round((list_total * applied_discount_pct) / 100.0, 6)
            net_total = round(list_total - discount_amount, 6)

            subtotal += list_total
            line_discount_total += discount_amount
            computed_lines.append(
                QuoteComputedLine(
                    commercial_item_id=line.commercial_item_id,
                    quantity_total=quantity_total,
                    base_price=base_price,
                    list_total=list_total,
                    line_discount_pct=applied_discount_pct,
                    line_discount_amount=discount_amount,
                    net_total=net_total,
                    max_discount_pct=max_discount_pct,
                    quantity_schedule={int(k): float(v) for k, v in line.quantity_schedule.items()},
                )
            )

        post_line_total = round(subtotal - line_discount_total, 6)
        overall_discount_pct = max(0.0, float(general.overall_discount_pct))
        overall_discount_amount = round((post_line_total * overall_discount_pct) / 100.0, 6)
        grand_total = round(post_line_total - overall_discount_amount, 6)
        margin_pct = round(((grand_total * 0.28) / grand_total) * 100.0, 4) if grand_total > 0 else 0.0

        return QuoteComputationResult(
            lines=computed_lines,
            subtotal=round(subtotal, 6),
            line_discount_total=round(line_discount_total, 6),
            overall_discount_pct=overall_discount_pct,
            overall_discount_amount=overall_discount_amount,
            grand_total=grand_total,
            margin_pct=margin_pct,
        )
