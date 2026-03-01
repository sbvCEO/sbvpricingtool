from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.async_dispatch import dispatch_task
from app.rbac import require_permission
from app.schemas import AsyncJobResponse, AuthContext
from app.tasks import generate_quote_pdf, publish_outbox_events, send_approval_reminder

router = APIRouter(prefix="/api/async", tags=["async"])


@router.post("/outbox/publish", response_model=AsyncJobResponse)
def enqueue_outbox_publish(
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    dispatched = dispatch_task(publish_outbox_events, str(ctx.tenant_id))
    return AsyncJobResponse(task_id=dispatched["task_id"], status=dispatched["status"])


@router.post("/approval-reminder/{approval_id}", response_model=AsyncJobResponse)
def enqueue_approval_reminder(
    approval_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    dispatched = dispatch_task(send_approval_reminder, str(ctx.tenant_id), str(approval_id))
    return AsyncJobResponse(task_id=dispatched["task_id"], status=dispatched["status"])


@router.post("/quote-pdf/{quote_id}", response_model=AsyncJobResponse)
def enqueue_quote_pdf(
    quote_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_permission("async:run"))],
):
    dispatched = dispatch_task(generate_quote_pdf, str(ctx.tenant_id), str(quote_id))
    return AsyncJobResponse(task_id=dispatched["task_id"], status=dispatched["status"])
