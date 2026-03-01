# T005 Deliverable: Catalog Service Core (Products/Services/Bundles)

Task ID: T005  
Status: DONE  
Date: 2026-02-25

## Implemented
- Catalog API for commercial items:
  - `POST /api/catalog/items`
  - `GET /api/catalog/items`
  - `GET /api/catalog/items/{item_id}`
- Bundle composition API:
  - `POST /api/catalog/bundles/{bundle_item_id}/items`
- Tenant-scoped in-memory repository baseline for service wiring.
- Permission enforcement:
  - Read endpoints require `catalog:read`
  - Write endpoints require `catalog:write`

## Files
- `backend/app/schemas.py`
- `backend/app/store.py`
- `backend/app/routers/catalog.py`
- `backend/main.py`

## Notes
- API/service contracts are now established.
- Repository can be swapped to PostgreSQL implementation without changing API contract.
