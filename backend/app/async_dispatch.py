from uuid import uuid4

from app.config import settings


def dispatch_task(task, *args):
    if settings.async_fallback_local:
        result = task.apply(args=args)
        return {
            "task_id": str(uuid4()),
            "status": "EXECUTED_LOCAL",
            "result": result.result,
        }

    try:
        queued = task.delay(*args)
        return {"task_id": queued.id, "status": "QUEUED"}
    except Exception:
        if not settings.async_fallback_local:
            raise
        result = task.apply(args=args)
        return {"task_id": str(uuid4()), "status": "EXECUTED_LOCAL", "result": result.result}
