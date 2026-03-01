# T004 Deliverable: OIDC/JWT and RBAC Baseline

Task ID: T004  
Status: DONE  
Date: 2026-02-25

## Implemented
- JWT validation dependency with audience/issuer/signature checks.
- Tenant claim enforcement (`token.tenant_id` must match `X-Tenant-Id`).
- Role + scope based permission resolution.
- Permission guard dependency (`require_permission`).
- Auth endpoints:
  - `GET /api/auth/me`
  - `GET /api/auth/permissions-check`

## Files
- `backend/app/config.py`
- `backend/app/security.py`
- `backend/app/rbac.py`
- `backend/app/routers/auth.py`
- `backend/main.py`

## Notes
- This is a JWT/OIDC-compatible baseline.
- External OIDC JWKS key discovery is deferred to next auth hardening iteration.
