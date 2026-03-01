from celery import Celery

from app.config import settings

celery_app = Celery(
    "sancnida",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="default",
    task_routes={
        "app.tasks.publish_outbox_events": {"queue": "integration"},
        "app.tasks.send_approval_reminder": {"queue": "workflow"},
        "app.tasks.generate_quote_pdf": {"queue": "calc"},
        "app.tasks.escalate_approval_timeout": {"queue": "workflow"},
        "app.tasks.crm_sync_quote": {"queue": "integration"},
    },
)
