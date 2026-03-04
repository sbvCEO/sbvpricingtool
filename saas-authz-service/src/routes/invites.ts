import { Router } from 'express';
import { z } from 'zod';
import type { PrismaClient } from '@prisma/client';
import { createOpaqueToken, hashToken } from '../lib/crypto.js';
import { auditLog } from '../lib/audit.js';
import { authorizeTenantAdmin } from '../middleware/authorize.js';
import { acceptInvite } from '../services/inviteService.js';

const acceptSchema = z.object({ token: z.string().min(10) });
const createInviteSchema = z.object({
  email: z.string().email(),
  role: z.enum(['TENANT_ADMIN', 'TENANT_USER']),
});

export function invitesRouter(prisma: PrismaClient) {
  const router = Router();

  router.post('/accept', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = acceptSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    let result: Awaited<ReturnType<typeof acceptInvite>>;
    try {
      result = await acceptInvite({
        prisma,
        token: parsed.data.token,
        userId: req.user.userId,
        userEmail: req.user.email,
      });
    } catch (err) {
      if (err instanceof Error && err.message === 'INVITE_INVALID') {
        return res.status(400).json({ error: 'Invalid or expired invite token' });
      }
      if (err instanceof Error && err.message === 'INVITE_EMAIL_MISMATCH') {
        return res.status(403).json({ error: 'Invite email does not match authenticated user' });
      }
      throw err;
    }

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
      tenantId: result.invite.tenantId,
      action: 'INVITE_ACCEPTED',
      targetType: 'tenant_invite',
      targetId: result.invite.id,
      metadata: {},
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: req.user.isInternal ? 'INTERNAL' : 'TENANT',
      tenantId: result.invite.tenantId,
      action: 'MEMBERSHIP_CREATED',
      targetType: 'membership',
      targetId: result.membership.id,
      metadata: { role: result.membership.role, source: 'invite_accept' },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(200).json({ tenant_id: result.invite.tenantId, role: result.membership.role });
  });

  router.post('/tenant', authorizeTenantAdmin(prisma), async (req, res) => {
    if (!req.user || !req.tenant?.tenantId) return res.status(401).json({ error: 'Missing context' });

    const parsed = createInviteSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const token = createOpaqueToken();
    const tokenHash = hashToken(token);
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

    const invite = await prisma.tenantInvite.create({
      data: {
        tenantId: req.tenant.tenantId,
        email: parsed.data.email,
        role: parsed.data.role,
        tokenHash,
        expiresAt,
        createdByUserId: req.user.userId,
      },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'TENANT',
      tenantId: req.tenant.tenantId,
      action: 'INVITE_CREATED_TENANT',
      targetType: 'tenant_invite',
      targetId: invite.id,
      metadata: { email: invite.email, role: invite.role },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(201).json({
      invite_id: invite.id,
      expires_at: invite.expiresAt,
      invite_token: token,
      warning: 'DEV_ONLY: token should be sent via email in production',
    });
  });

  return router;
}
