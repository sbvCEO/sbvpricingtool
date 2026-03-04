import type { NextFunction, Request, Response } from 'express';
import { MembershipStatus, type PrismaClient } from '@prisma/client';
import { auditLog } from '../lib/audit.js';

const TENANT_OPTIONAL_PATHS = new Set([
  '/api/selfserve/tenants',
  '/api/invites/accept',
]);

export function resolveTenantContext(prisma: PrismaClient) {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthenticated' });
    }

    const memberships = await prisma.membership.findMany({
      where: {
        userId: req.user.userId,
        status: MembershipStatus.ACTIVE,
        tenant: { status: 'ACTIVE' },
      },
      include: { tenant: true },
    });

    const requestedTenantId = req.header('X-Tenant-Id');
    if (requestedTenantId) {
      const membership = memberships.find((m) => m.tenantId === requestedTenantId);
      if (!membership) {
        await auditLog(prisma, {
          actorUserId: req.user.userId,
          actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
          tenantId: requestedTenantId,
          action: 'TENANT_CONTEXT_RESOLUTION_FAILED',
          targetType: 'tenant',
          targetId: requestedTenantId,
          metadata: { reason: 'Missing active membership for tenant header' },
          ipAddress: req.ip,
          userAgent: req.get('user-agent'),
        });
        return res.status(403).json({ error: 'Invalid tenant context' });
      }

      req.tenant = {
        tenantId: membership.tenantId,
        membershipRole: membership.role,
        viaBreakGlass: false,
      };
      return next();
    }

    if (memberships.length === 1) {
      req.tenant = {
        tenantId: memberships[0].tenantId,
        membershipRole: memberships[0].role,
        viaBreakGlass: false,
      };
      return next();
    }

    if (memberships.length === 0 && TENANT_OPTIONAL_PATHS.has(req.path)) {
      return next();
    }

    if (req.path.startsWith('/api/internal')) {
      return next();
    }

    return res.status(409).json({
      error: memberships.length > 1 ? 'Multiple tenants. Select X-Tenant-Id.' : 'No tenant membership.',
    });
  };
}
