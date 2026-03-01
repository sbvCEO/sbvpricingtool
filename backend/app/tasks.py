from datetime import UTC, datetime
from uuid import UUID

from app.celery_app import celery_app
from app.store import quote_store


@celery_app.task(name="app.tasks.publish_outbox_events", bind=True, max_retries=3)
def publish_outbox_events(self, tenant_id: str) -> dict:
    # In a full implementation, this would dispatch to Kafka/webhooks/CRM connectors.
    published = 0
    tenant_uuid = UUID(tenant_id)
    for event in quote_store.list_pending_outbox(tenant_uuid):
        quote_store.mark_outbox_event_published(tenant_uuid, event["id"])
        published += 1
    return {"tenant_id": tenant_id, "published": published}


@celery_app.task(name="app.tasks.send_approval_reminder", bind=True, max_retries=5)
def send_approval_reminder(self, tenant_id: str, approval_id: str) -> dict:
    # Placeholder for email/slack integration.
    return {
        "tenant_id": tenant_id,
        "approval_id": approval_id,
        "status": "queued-reminder",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="app.tasks.generate_quote_pdf", bind=True, max_retries=2)
def generate_quote_pdf(self, tenant_id: str, quote_id: str) -> dict:
    # Placeholder document generation. In production this creates and stores a PDF artifact.
    return {
        "tenant_id": tenant_id,
        "quote_id": quote_id,
        "artifact_uri": f"s3://mock-bucket/quotes/{quote_id}.pdf",
        "status": "generated",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="app.tasks.escalate_approval_timeout", bind=True, max_retries=5)
def escalate_approval_timeout(self, tenant_id: str, approval_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "approval_id": approval_id,
        "status": "escalated",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="app.tasks.crm_sync_quote", bind=True, max_retries=4)
def crm_sync_quote(self, tenant_id: str, quote_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "quote_id": quote_id,
        "status": "synced_to_crm",
        "external_id": f"CRM-{quote_id[:8]}",
        "processed_at": datetime.now(UTC).isoformat(),
    }
