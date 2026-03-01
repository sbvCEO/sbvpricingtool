from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.async_dispatch import dispatch_task
from app.rbac import require_permission
from app.schemas import ApprovalActionRequest, ApprovalInstanceRead, AuthContext, QuoteRead
from app.tasks import send_approval_reminder
from app.store import quote_store

router = APIRouter(prefix="/api", tags=["approvals"])


class ApprovalPolicyCreate(BaseModel):
    name: str
    conditions: dict = {}
    route: dict = {"levels": 1}


def _route_levels(tenant_id: UUID, quote: dict) -> int:
    for policy in quote_store.list_approval_policies(tenant_id):
        conditions = policy.get("conditions", {})
        min_value = float(conditions.get("min_grand_total", 0))
        max_margin = conditions.get("max_margin_pct")
        value_ok = float(quote.get("grand_total", 0)) >= min_value
        margin_ok = True if max_margin is None else float(quote.get("margin_pct", 0)) <= float(max_margin)
        if value_ok and margin_ok:
            return int(policy.get("route", {}).get("levels", 1))
    return 2 if float(quote.get("grand_total", 0)) >= 100000 else 1


@router.post("/quotes/{quote_id}/submit", response_model=ApprovalInstanceRead)
def submit_quote(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote["status"] not in {"DRAFT", "REVIEW"}:
        raise HTTPException(status_code=400, detail="Quote not in submittable status")

    levels = _route_levels(ctx.tenant_id, quote)
    approval = quote_store.start_approval(ctx.tenant_id, quote_id, levels)
    quote_store.set_status(ctx.tenant_id, quote_id, "APPROVAL_PENDING")
    quote_store.emit_event(ctx.tenant_id, "quote.submitted", quote_id, {"approval_id": str(approval["id"])})
    return ApprovalInstanceRead(**approval)


@router.post("/approval-policies")
def create_approval_policy(
    payload: ApprovalPolicyCreate,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:write"))],
):
    return quote_store.create_approval_policy(ctx.tenant_id, payload.model_dump())


@router.get("/approval-policies")
def list_approval_policies(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return quote_store.list_approval_policies(ctx.tenant_id)


@router.post("/approvals/{approval_id}/actions", response_model=ApprovalInstanceRead)
def act_approval(
    approval_id: UUID,
    payload: ApprovalActionRequest,
    ctx: Annotated[AuthContext, Depends(require_permission("approval:act"))],
):
    if payload.action == "REJECT" and not (payload.comments or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    if payload.action == "REQUEST_CHANGES" and not (payload.comments or "").strip():
        raise HTTPException(status_code=400, detail="Request changes reason is required")

    try:
        approval = quote_store.act_approval(
            ctx.tenant_id,
            approval_id,
            payload.action,
            payload.comments,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    quote_id = approval["quote_id"]
    if approval["status"] == "APPROVED":
        quote_store.set_status(ctx.tenant_id, quote_id, "FINALIZED")
        quote_store.emit_event(ctx.tenant_id, "quote.finalized", quote_id, {"approval_id": str(approval_id)})
    elif approval["status"] == "REJECTED":
        quote_store.set_status(ctx.tenant_id, quote_id, "REJECTED")
        quote_store.emit_event(ctx.tenant_id, "quote.rejected", quote_id, {"approval_id": str(approval_id)})
    elif approval["status"] == "CHANGES_REQUESTED":
        quote_store.set_status(ctx.tenant_id, quote_id, "REJECTED")
        quote_store.emit_event(ctx.tenant_id, "quote.changes_requested", quote_id, {"approval_id": str(approval_id)})

    return ApprovalInstanceRead(**approval)


@router.get("/quotes/{quote_id}/approval", response_model=ApprovalInstanceRead)
def get_quote_approval(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    approval = quote_store.get_approval_for_quote(ctx.tenant_id, quote_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval instance not found")
    return ApprovalInstanceRead(**approval)


@router.get("/approvals/{approval_id}/sla-status")
def approval_sla_status(
    approval_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("approval:act"))],
):
    approval = quote_store.get_approval(ctx.tenant_id, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    overdue = []
    for step in approval["steps"]:
        if step["status"] == "PENDING":
            overdue.append(
                {
                    "step_id": str(step["id"]),
                    "seq_no": step["seq_no"],
                    "sla_due_at": step["sla_due_at"].isoformat(),
                }
            )
    return {"approval_id": str(approval_id), "pending_steps": overdue}




@router.get("/approvals/{approval_id}/timeline")
def approval_timeline(
    approval_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("approval:act"))],
):
    approval = quote_store.get_approval(ctx.tenant_id, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    timeline = []
    for step in approval["steps"]:
        timeline.append({
            "step_id": str(step["id"]),
            "seq_no": step["seq_no"],
            "status": step["status"],
            "approver_role": step.get("approver_role"),
            "sla_due_at": step["sla_due_at"].isoformat() if step.get("sla_due_at") else None,
            "acted_at": step["acted_at"].isoformat() if step.get("acted_at") else None,
            "comments": step.get("comments"),
        })

    return {
        "approval_id": str(approval_id),
        "status": approval["status"],
        "timeline": timeline,
    }

@router.post("/approvals/{approval_id}/remind")
def queue_approval_reminder(
    approval_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("approval:act"))],
):
    return dispatch_task(send_approval_reminder, str(ctx.tenant_id), str(approval_id))


@router.get("/outbox/events")
def list_outbox_events(
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    return quote_store.list_outbox(ctx.tenant_id)


@router.get("/quotes/{quote_id}/state", response_model=QuoteRead)
def get_quote_state(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("quote:read"))],
):
    quote = quote_store.get_quote(ctx.tenant_id, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteRead(**quote)
