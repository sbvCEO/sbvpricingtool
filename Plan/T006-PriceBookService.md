# T006 Deliverable: Price Book Service

Implemented:
- Price book CRUD baseline (`create`, `list`, `publish`).
- Price book entries (`create`, `list`) with pricing model and guardrails.
- Tenant + RBAC protection (`pricebook:read`, `pricebook:write`).

Key files:
- `backend/app/routers/pricebooks.py`
- `backend/app/schemas.py`
- `backend/app/store.py`
