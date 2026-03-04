import { Router } from 'express';
import { z } from 'zod';
import type { PrismaClient } from '@prisma/client';
import { createTenantWithAdmin } from '../services/tenantProvisioningService.js';
import { auditLog } from '../lib/audit.js';

const bodySchema = z.object({
  name: z.string().min(2),
  region: z.string().min(2),
});

export function selfserveRouter(prisma: PrismaClient) {
  const router = Router();

  router.post('/tenants', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = bodySchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }

    const { tenant, membership } = await createTenantWithAdmin({
      prisma,
      name: parsed.data.name,
      region: parsed.data.region,
      creatorUserId: req.user.userId,
      plan: 'TRIAL',
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
      tenantId: tenant.id,
      action: 'TENANT_CREATED',
      targetType: 'tenant',
      targetId: tenant.id,
      metadata: { flow: 'self_serve' },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
      tenantId: tenant.id,
      action: 'MEMBERSHIP_CREATED',
      targetType: 'membership',
      targetId: membership.id,
      metadata: { role: membership.role },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(201).json({
      tenant_id: tenant.id,
      next_steps: ['Set billing', 'Configure SSO (optional)', 'Invite teammates'],
    });
  });

  return router;
}
