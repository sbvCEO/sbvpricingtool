# T003 Deliverable: Tenant Model, RLS, and Session Context

Task ID: T003  
Status: DONE  
Date: 2026-02-25

## Scope Delivered

1. Tenant-aware database security baseline
- Added migration: `backend/db/migrations/0002_tenant_rls.sql`
- Introduced `app_current_tenant()` and `app_set_tenant(uuid)` helpers.
- Enabled RLS for tenant-owned tables.
- Created per-table tenant isolation policies using `tenant_id = app_current_tenant()`.

2. API request tenant context plumbing
- Updated `backend/main.py` with `X-Tenant-Id` middleware enforcement.
- Public paths excluded: `/`, `/api/health`.
- Added `/api/tenant-context` for context validation.

3. Verification artifacts
- Added `backend/db/tests/rls_verification.sql` for tenant isolation checks.
- Added automated API tests in `backend/tests/test_auth_catalog.py` covering tenant header and tenant mismatch handling.

## How Session Context Works

Application layer (FastAPI):
- Every protected request must include `X-Tenant-Id` (UUID).
- Middleware validates and stores tenant in `request.state.tenant_id`.

Database layer (PostgreSQL):
- Before running tenant-scoped queries in a DB session/transaction, call:
  - `SELECT app_set_tenant('<tenant-uuid>'::uuid);`
- RLS policies filter records automatically by `app.current_tenant`.

## Integration Note for Next Step
When DB access layer is introduced/expanded, enforce this sequence per request:
1. Open transaction.
2. `SELECT app_set_tenant(:tenant_id);`
3. Execute all tenant queries within same transaction/session.

## Security Notes
- RLS protects data even if app query accidentally omits tenant predicate.
- `FORCE ROW LEVEL SECURITY` is intentionally deferred until platform admin workflows are finalized.
- Reference tables (`ref_*`, `permissions`) remain global and do not use tenant RLS.
