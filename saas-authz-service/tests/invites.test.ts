import { describe, expect, it, vi } from 'vitest';
import { acceptInvite } from '../src/services/inviteService.js';
import { hashToken } from '../src/lib/crypto.js';

describe('invite acceptance', () => {
  it('creates membership with invite role', async () => {
    const rawToken = 'tok_1234567890';
    const invite = {
      id: 'invite-1',
      tenantId: 'tenant-1',
      email: 'admin@customer.com',
      role: 'TENANT_ADMIN',
      acceptedAt: null,
      expiresAt: new Date(Date.now() + 60_000),
      tokenHash: hashToken(rawToken),
    };

    const prisma: any = {
      tenantInvite: {
        findFirst: vi.fn().mockResolvedValue(invite),
        update: vi.fn().mockResolvedValue({ ...invite, acceptedAt: new Date() }),
      },
      membership: {
        findUnique: vi.fn().mockResolvedValue(null),
        create: vi.fn().mockResolvedValue({ id: 'm1', role: 'TENANT_ADMIN' }),
      },
    };

    const result = await acceptInvite({
      prisma,
      token: rawToken,
      userId: 'user-1',
      userEmail: 'admin@customer.com',
    });

    expect(result.membership.role).toBe('TENANT_ADMIN');
    expect(prisma.membership.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ tenantId: 'tenant-1', role: 'TENANT_ADMIN' }),
      }),
    );
  });
});
