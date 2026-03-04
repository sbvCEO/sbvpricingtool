# SaaS Multi-Tenant AuthZ + Provisioning Service

Production-oriented Node.js + TypeScript + Express + Prisma implementation for strict tenant isolation with internal operator controls and audited break-glass access.

## 1) Project structure

```text
saas-authz-service/
  prisma/
    schema.prisma
    migrations/0001_init/migration.sql
  src/
    app.ts
    server.ts
    types/express.d.ts
    lib/
      prisma.ts
      jwt.ts
      audit.ts
      crypto.ts
      tenantScope.ts
    middleware/
      authenticateJWT.ts
      resolveTenantContext.ts
      authorize.ts
      requireBusinessAccess.ts
    services/
      tenantProvisioningService.ts
      inviteService.ts
    routes/
      selfserve.ts
      invites.ts
      internal.ts
      tenantAdmin.ts
      projects.ts
    queue/
      inMemoryQueue.ts
  tests/
    security-invariants.test.ts
    provisioning.test.ts
    invites.test.ts
  package.json
  tsconfig.json
  .env.example
```

## 2) Prisma schema + migration SQL

- Prisma schema: [`prisma/schema.prisma`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/prisma/schema.prisma)
- SQL migration (includes enums, tables, constraints, RLS policy setup): [`prisma/migrations/0001_init/migration.sql`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/prisma/migrations/0001_init/migration.sql)

### RLS pattern included

- `app.tenant_id` and `app.break_glass_tenant_id` session configs.
- Policy helper: `app_tenant_ok(row_tenant_id uuid)`.
- Tenant-scoped policies on `memberships`, `tenant_invites`, `tenant_settings`, `projects`, `tenant_usage`, `audit_logs`.
- Break-glass only works when application validates session and sets context.

## 3) Express server: routes + middleware + services

### Core middleware

- JWT auth + user upsert: [`src/middleware/authenticateJWT.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/middleware/authenticateJWT.ts)
- Tenant context resolution from membership (`X-Tenant-Id` validated server-side): [`src/middleware/resolveTenantContext.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/middleware/resolveTenantContext.ts)
- Role authorization (internal operator / tenant admin / tenant user): [`src/middleware/authorize.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/middleware/authorize.ts)
- Break-glass enforcement for business data routes (`X-Break-Glass-Session-Id`): [`src/middleware/requireBusinessAccess.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/middleware/requireBusinessAccess.ts)

### Route coverage

- Self-serve onboarding: `POST /api/selfserve/tenants`
- Invite acceptance: `POST /api/invites/accept`
- Tenant-admin invite: `POST /api/invites/tenant`
- Internal tenant ops:
  - `GET /api/internal/tenants`
  - `GET /api/internal/tenants/:id`
  - `POST /api/internal/tenants`
  - `PATCH /api/internal/tenants/:id`
  - `POST /api/internal/tenants/:id/suspend`
  - `POST /api/internal/tenants/:id/reactivate`
  - `POST /api/internal/tenants/:tenantId/invites`
  - `POST /api/internal/tenants/:id/reset-tenant-admin`
  - `GET /api/internal/tenants/:id/usage`
  - `POST /api/internal/tenants/:id/sso`
- Break-glass:
  - `POST /api/internal/break-glass/start`
  - `POST /api/internal/break-glass/revoke`
- Tenant business data example:
  - `GET /api/projects`
  - `POST /api/projects`

### Services + audit logging

- Tenant provisioning service: [`src/services/tenantProvisioningService.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/services/tenantProvisioningService.ts)
- Invite acceptance service: [`src/services/inviteService.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/services/inviteService.ts)
- Reusable audit logger: [`src/lib/audit.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/lib/audit.ts)

## 4) Security notes + concise threat model

- Tenant scope is never taken from body/query for business data.
- `X-Tenant-Id` is accepted only after membership validation; otherwise denied and audited.
- Internal operators can use only internal APIs by role check (`internal_roles` + `is_internal`).
- Internal operators cannot access tenant business routes unless an active, unrevoked, unexpired break-glass session exists for that exact tenant.
- Every break-glass business route access logs route-level audit entries.
- Invite tokens are stored as SHA-256 hashes; raw token returned only as dev-only placeholder.
- Reset tenant admin endpoint requires explicit reason and audits action.
- SSO metadata endpoint stores non-secret metadata; secret handling path explicitly marked with KMS/Vault TODO.

## 5) Minimal tests

Tests are under [`tests/`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/tests):

- `security-invariants.test.ts`
  - cannot access tenant A data with tenant B membership
  - internal operator cannot access business data without break-glass
  - break-glass expired/invalid session is denied
- `provisioning.test.ts`
  - self-serve provisioning creates tenant and TENANT_ADMIN membership
- `invites.test.ts`
  - invite acceptance creates membership with invite role

## Run

```bash
cd /Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service
cp .env.example .env
npm install
npx prisma generate
npx prisma migrate dev --name init
npm test
npm run dev
```

## Example requests (curl)

Assume `JWT` is a valid bearer token for authenticated user.

### Flow A: self-serve

```bash
curl -X POST http://localhost:4000/api/selfserve/tenants \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Inc","region":"us-east-1"}'
```

### Flow B: operator creates tenant + invite

```bash
curl -X POST http://localhost:4000/api/internal/tenants \
  -H "Authorization: Bearer $INTERNAL_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Globex","plan":"ENTERPRISE","region":"us-west-2","domain":"globex.example.com"}'
```

```bash
curl -X POST http://localhost:4000/api/internal/tenants/$TENANT_ID/invites \
  -H "Authorization: Bearer $INTERNAL_JWT" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@globex.com","role":"TENANT_ADMIN"}'
```

```bash
curl -X POST http://localhost:4000/api/invites/accept \
  -H "Authorization: Bearer $CUSTOMER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"token":"'$INVITE_TOKEN'"}'
```

### Tenant admin invite user

```bash
curl -X POST http://localhost:4000/api/invites/tenant \
  -H "Authorization: Bearer $TENANT_ADMIN_JWT" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@globex.com","role":"TENANT_USER"}'
```

### Break-glass start + access + revoke

```bash
curl -X POST http://localhost:4000/api/internal/break-glass/start \
  -H "Authorization: Bearer $INTERNAL_JWT" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"'$TENANT_ID'","reason":"Investigate sync failure"}'
```

```bash
curl http://localhost:4000/api/projects \
  -H "Authorization: Bearer $INTERNAL_JWT" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "X-Break-Glass-Session-Id: $BG_SESSION_ID"
```

```bash
curl -X POST http://localhost:4000/api/internal/break-glass/revoke \
  -H "Authorization: Bearer $INTERNAL_JWT" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"'$BG_SESSION_ID'"}'
```

## Background job tenant propagation pattern

- Queue implementation: [`src/queue/inMemoryQueue.ts`](/Users/vivek/Documents/smartbusinessvalue/SAICNIDA/sbvpricingtool/saas-authz-service/src/queue/inMemoryQueue.ts)
- Every job payload includes `tenantId` + optional `actorUserId`.
- Worker handlers apply writes only with explicit `tenantId` filters/upserts.
- Pattern can be swapped to BullMQ/SQS without changing payload contract.
