import { describe, expect, it, vi } from 'vitest';
import { createTenantWithAdmin } from '../src/services/tenantProvisioningService.js';

describe('self-serve provisioning', () => {
  it('creates tenant and TENANT_ADMIN membership', async () => {
    const tx = {
      tenant: {
        create: vi.fn().mockResolvedValue({ id: 'tenant-1', plan: 'TRIAL' }),
      },
      membership: {
        create: vi.fn().mockResolvedValue({ id: 'mem-1', role: 'TENANT_ADMIN' }),
      },
      tenantSetting: {
        create: vi.fn().mockResolvedValue({}),
      },
      tenantUsage: {
        create: vi.fn().mockResolvedValue({}),
      },
    };

    const prisma: any = {
      $transaction: vi.fn(async (cb: any) => cb(tx)),
    };

    const result = await createTenantWithAdmin({
      prisma,
      name: 'Acme',
      region: 'us-east-1',
      creatorUserId: 'user-1',
      plan: 'TRIAL',
    });

    expect(result.tenant.id).toBe('tenant-1');
    expect(result.membership.role).toBe('TENANT_ADMIN');
    expect(tx.membership.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ role: 'TENANT_ADMIN', tenantId: 'tenant-1' }),
      }),
    );
  });
});
