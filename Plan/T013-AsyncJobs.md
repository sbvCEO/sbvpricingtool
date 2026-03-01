# T013 Deliverable: Async Jobs (Approval Reminders + PDF)

Implemented:
- Async API to enqueue approval reminder tasks.
- Async API to enqueue quote PDF generation tasks.
- Async API to enqueue outbox publish.

Key files:
- `backend/app/routers/async_jobs.py`
- `backend/app/tasks.py`
