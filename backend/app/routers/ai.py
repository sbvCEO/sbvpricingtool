from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.rbac import require_permission
from app.schemas import AuthContext, DiscountOptimizationRequest
from app.store import quote_store

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/pricing-suggestions/{quote_id}")
def pricing_suggestions(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    margin = float(quote.get("margin_pct", 0.0))
    suggestion = "Maintain current discount" if margin >= 20 else "Reduce discount by 3%"
    return {
        "quote_id": str(quote_id),
        "suggestion": suggestion,
        "explainability": f"Current margin is {margin:.2f}%",
    }


@router.post("/quote-risk/{quote_id}")
def quote_risk(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    total = float(quote.get("grand_total", 0.0))
    margin = float(quote.get("margin_pct", 0.0))

    score = 0.2
    if total > 100000:
        score += 0.25
    if margin < 15:
        score += 0.35

    return {
        "quote_id": str(quote_id),
        "risk_score": round(min(score, 1.0), 2),
        "drivers": {
            "deal_size": total,
            "margin_pct": margin,
        },
    }


@router.get("/anomalies")
def anomalies(
    ctx: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    anomalies_found = []
    for quote in quote_store.list_quotes(ctx.tenant_id):
        if float(quote.get("margin_pct", 0)) < 10 and float(quote.get("grand_total", 0)) > 50000:
            anomalies_found.append(
                {
                    "quote_id": str(quote["id"]),
                    "type": "LOW_MARGIN_HIGH_VALUE",
                    "margin_pct": quote.get("margin_pct"),
                    "grand_total": quote.get("grand_total"),
                }
            )
    return {"count": len(anomalies_found), "items": anomalies_found}


@router.post("/discount-optimization")
def discount_optimization(
    payload: DiscountOptimizationRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, payload.quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    current_margin = float(quote.get("margin_pct", 0.0))
    delta = payload.target_margin_pct - current_margin
    recommended_adjustment = -min(max(delta / 2.0, -10.0), 10.0)

    return {
        "quote_id": str(payload.quote_id),
        "current_margin_pct": current_margin,
        "target_margin_pct": payload.target_margin_pct,
        "recommended_discount_adjustment_pct": round(recommended_adjustment, 2),
    }
