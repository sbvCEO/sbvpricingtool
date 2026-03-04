import type { NextFunction, Request, Response } from 'express';
import { MembershipRole, type PrismaClient } from '@prisma/client';
import { auditLog } from '../lib/audit.js';

export function authorizeInternalOperator(prisma: PrismaClient) {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthenticated' });
    }

    const internalRole = await prisma.internalRoleAssignment.findUnique({
      where: { userId: req.user.userId },
    });

    if (!req.user.isInternal || !internalRole || internalRole.role !== 'INTERNAL_SAAS_OPERATOR') {
      await auditLog(prisma, {
        actorUserId: req.user.userId,
        actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
        action: 'INTERNAL_AUTHZ_DENIED',
        targetType: 'internal_endpoint',
        targetId: req.path,
        metadata: {},
        ipAddress: req.ip,
        userAgent: req.get('user-agent'),
      });
      return res.status(403).json({ error: 'Internal operator role required' });
    }

    return next();
  };
}

export function authorizeTenantAdmin(prisma: PrismaClient) {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.user || !req.tenant?.tenantId) {
      return res.status(401).json({ error: 'Missing tenant context' });
    }

    const membership = await prisma.membership.findUnique({
      where: {
        tenantId_userId: {
          tenantId: req.tenant.tenantId,
          userId: req.user.userId,
        },
      },
    });

    if (!membership || membership.status !== 'ACTIVE' || membership.role !== MembershipRole.TENANT_ADMIN) {
      return res.status(403).json({ error: 'Tenant admin required' });
    }

    return next();
  };
}

export function authorizeTenantUser() {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.tenant?.tenantId || !req.tenant.membershipRole) {
      return res.status(403).json({ error: 'Tenant membership required' });
    }
    return next();
  };
}
