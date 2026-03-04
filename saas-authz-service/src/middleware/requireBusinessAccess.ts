import type { NextFunction, Request, Response } from 'express';
import { type PrismaClient } from '@prisma/client';
import { auditLog } from '../lib/audit.js';

export function requireBusinessDataAccess(prisma: PrismaClient) {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthenticated' });
    }

    if (!req.tenant?.tenantId) {
      return res.status(400).json({ error: 'Tenant context required' });
    }

    if (!req.user.isInternal) {
      return next();
    }

    const sessionId = req.header('X-Break-Glass-Session-Id');
    if (!sessionId) {
      await auditLog(prisma, {
        actorUserId: req.user.userId,
        actorType: 'INTERNAL',
        tenantId: req.tenant.tenantId,
        action: 'BREAK_GLASS_REQUIRED',
        targetType: 'business_route',
        targetId: req.path,
        metadata: { reason: 'missing_session_header' },
        ipAddress: req.ip,
        userAgent: req.get('user-agent'),
      });
      return res.status(403).json({ error: 'Break-glass session required for internal user' });
    }

    const now = new Date();
    const session = await prisma.breakGlassSession.findFirst({
      where: {
        id: sessionId,
        internalUserId: req.user.userId,
        tenantId: req.tenant.tenantId,
        startsAt: { lte: now },
        expiresAt: { gt: now },
        revokedAt: null,
      },
    });

    if (!session) {
      await auditLog(prisma, {
        actorUserId: req.user.userId,
        actorType: 'INTERNAL',
        tenantId: req.tenant.tenantId,
        action: 'BREAK_GLASS_INVALID',
        targetType: 'break_glass_session',
        targetId: sessionId,
        metadata: { path: req.path },
        ipAddress: req.ip,
        userAgent: req.get('user-agent'),
      });
      return res.status(403).json({ error: 'Invalid or expired break-glass session' });
    }

    req.tenant.viaBreakGlass = true;
    req.tenant.breakGlassSessionId = session.id;

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: req.tenant.tenantId,
      action: 'BREAK_GLASS_ROUTE_ACCESS',
      targetType: 'route',
      targetId: req.path,
      metadata: { method: req.method, breakGlassSessionId: session.id },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return next();
  };
}
