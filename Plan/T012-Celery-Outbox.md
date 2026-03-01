# T012 Deliverable: Celery + Redis + Outbox Publisher Setup

Implemented:
- Celery app configuration with Redis broker/backend.
- Queue routes (`default`, `workflow`, `calc`, `integration`).
- Outbox publish task scaffold.
- Docker compose worker + redis services.

Key files:
- `backend/app/celery_app.py`
- `backend/app/tasks.py`
- `docker-compose.yml`
