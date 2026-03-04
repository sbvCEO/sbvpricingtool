import { describe, expect, it, vi } from 'vitest';
import { resolveTenantContext } from '../src/middleware/resolveTenantContext.js';
import { requireBusinessDataAccess } from '../src/middleware/requireBusinessAccess.js';

type MockReq = {
  user?: { userId: string; isInternal: boolean };
  tenant?: { tenantId: string; membershipRole: 'TENANT_ADMIN' | 'TENANT_USER' | null; viaBreakGlass: boolean; breakGlassSessionId?: string };
  path: string;
  method: string;
  ip: string;
  header: (name: string) => string | undefined;
  get: (name: string) => string | undefined;
};

function createMockRes() {
  const res: any = {
    statusCode: 200,
    body: undefined,
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(payload: unknown) {
      this.body = payload;
      return this;
    },
  };
  return res;
}

describe('tenant and break-glass invariants', () => {
  it('cannot access tenant A data when only tenant B membership exists', async () => {
    const prisma: any = {
      membership: {
        findMany: vi.fn().mockResolvedValue([
          { tenantId: 'tenant-b', role: 'TENANT_ADMIN', tenant: { status: 'ACTIVE' } },
        ]),
      },
      auditLog: {
        create: vi.fn().mockResolvedValue(undefined),
      },
    };

    const middleware = resolveTenantContext(prisma);
    const req: MockReq = {
      user: { userId: 'u1', isInternal: false },
      path: '/api/projects',
      method: 'GET',
      ip: '127.0.0.1',
      header: (name: string) => (name === 'X-Tenant-Id' ? 'tenant-a' : undefined),
      get: () => undefined,
    };
    const res = createMockRes();
    const next = vi.fn();

    await middleware(req as any, res as any, next);

    expect(res.statusCode).toBe(403);
    expect(next).not.toHaveBeenCalled();
  });

  it('internal operator cannot access business data without break-glass', async () => {
    const prisma: any = {
      auditLog: { create: vi.fn().mockResolvedValue(undefined) },
      breakGlassSession: { findFirst: vi.fn() },
    };

    const middleware = requireBusinessDataAccess(prisma);
    const req: MockReq = {
      user: { userId: 'internal-1', isInternal: true },
      tenant: { tenantId: 'tenant-1', membershipRole: null, viaBreakGlass: false },
      path: '/api/projects',
      method: 'GET',
      ip: '127.0.0.1',
      header: () => undefined,
      get: () => undefined,
    };
    const res = createMockRes();
    const next = vi.fn();

    await middleware(req as any, res as any, next);

    expect(res.statusCode).toBe(403);
    expect(next).not.toHaveBeenCalled();
  });

  it('break-glass access is denied after expiry', async () => {
    const prisma: any = {
      auditLog: { create: vi.fn().mockResolvedValue(undefined) },
      breakGlassSession: { findFirst: vi.fn().mockResolvedValue(null) },
    };

    const middleware = requireBusinessDataAccess(prisma);
    const req: MockReq = {
      user: { userId: 'internal-1', isInternal: true },
      tenant: { tenantId: 'tenant-1', membershipRole: null, viaBreakGlass: false },
      path: '/api/projects',
      method: 'GET',
      ip: '127.0.0.1',
      header: (name: string) => (name === 'X-Break-Glass-Session-Id' ? 'expired-session' : undefined),
      get: () => undefined,
    };
    const res = createMockRes();
    const next = vi.fn();

    await middleware(req as any, res as any, next);

    expect(res.statusCode).toBe(403);
    expect(next).not.toHaveBeenCalled();
  });
});
