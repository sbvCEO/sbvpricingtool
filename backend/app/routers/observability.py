from fastapi import APIRouter

from app.observability import snapshot_metrics

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/metrics")
def metrics():
    return snapshot_metrics()
