from typing import Annotated

from fastapi import APIRouter, Depends

from app.rbac import require_permission
from app.schemas import AuthContext, DashboardMetricsRead
from app.store import quote_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardMetricsRead)
def dashboard_metrics(
    ctx: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    quotes = quote_store.list_quotes(ctx.tenant_id)
    total_quotes = len(quotes)
    draft_quotes = len([q for q in quotes if q["status"] == "DRAFT"])
    pending_approvals = len([q for q in quotes if q["status"] == "APPROVAL_PENDING"])
    finalized_quotes = len([q for q in quotes if q["status"] == "FINALIZED"])
    total_pipeline_value = round(sum(float(q.get("grand_total", 0.0)) for q in quotes), 2)

    margins = [float(q.get("margin_pct", 0.0)) for q in quotes if float(q.get("grand_total", 0.0)) > 0]
    average_margin = round(sum(margins) / len(margins), 2) if margins else 0.0

    return DashboardMetricsRead(
        total_quotes=total_quotes,
        draft_quotes=draft_quotes,
        pending_approvals=pending_approvals,
        finalized_quotes=finalized_quotes,
        total_pipeline_value=total_pipeline_value,
        average_margin_pct=average_margin,
    )


@router.get("/advanced")
def advanced_analytics(
    ctx: Annotated[AuthContext, Depends(require_permission("dashboard:read"))],
):
    quotes = quote_store.list_quotes(ctx.tenant_id)
    high_value = [q for q in quotes if float(q.get("grand_total", 0)) >= 100000]
    low_margin = [q for q in quotes if float(q.get("margin_pct", 0)) < 15 and float(q.get("grand_total", 0)) > 0]
    return {
        "cohorts": {
            "high_value_quote_count": len(high_value),
            "low_margin_quote_count": len(low_margin),
        },
        "pricing_leakage_estimate": round(sum(float(q.get("discount_total", 0)) for q in low_margin), 2),
        "approval_bottleneck_hint": "Use dynamic routing when low margin + high value overlap exceeds threshold.",
    }
