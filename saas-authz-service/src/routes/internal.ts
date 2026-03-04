import { Router } from 'express';
import { z } from 'zod';
import type { PrismaClient } from '@prisma/client';
import { auditLog } from '../lib/audit.js';
import { createOpaqueToken, hashToken } from '../lib/crypto.js';
import { authorizeInternalOperator } from '../middleware/authorize.js';
import { PLAN_LIMITS } from '../services/tenantProvisioningService.js';

const createTenantSchema = z.object({
  name: z.string().min(2),
  plan: z.enum(['FREE', 'TRIAL', 'PRO', 'ENTERPRISE']).default('TRIAL'),
  region: z.string().min(2),
  domain: z.string().optional(),
  limits: z.record(z.any()).optional(),
});

const patchTenantSchema = z.object({
  plan: z.enum(['FREE', 'TRIAL', 'PRO', 'ENTERPRISE']).optional(),
  status: z.enum(['ACTIVE', 'SUSPENDED', 'DELETED']).optional(),
  region: z.string().optional(),
  domain: z.string().nullable().optional(),
  limits: z.record(z.any()).optional(),
});

const inviteSchema = z.object({
  email: z.string().email(),
  role: z.literal('TENANT_ADMIN').default('TENANT_ADMIN'),
});

const resetAdminSchema = z.object({
  reason: z.string().min(5),
  newAdminEmail: z.string().email(),
});

const breakGlassStartSchema = z.object({
  tenant_id: z.string().uuid(),
  reason: z.string().min(5),
  duration_minutes: z.number().int().positive().max(60).optional(),
});

const breakGlassRevokeSchema = z.object({
  session_id: z.string().uuid(),
});

const ssoSchema = z.object({
  issuer: z.string().url(),
  domain: z.string().min(2),
  callback_urls: z.array(z.string().url()),
  secrets_ref: z.string().optional(),
});

export function internalRouter(prisma: PrismaClient) {
  const router = Router();

  router.use(authorizeInternalOperator(prisma));

  router.get('/tenants', async (_req, res) => {
    const tenants = await prisma.tenant.findMany({
      select: {
        id: true,
        name: true,
        status: true,
        plan: true,
        region: true,
        domain: true,
        limits: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });
    return res.json(tenants);
  });

  router.get('/tenants/:id', async (req, res) => {
    const tenant = await prisma.tenant.findUnique({
      where: { id: req.params.id },
      include: {
        settings: true,
        usage: true,
      },
    });
    if (!tenant) return res.status(404).json({ error: 'Tenant not found' });
    return res.json(tenant);
  });

  router.post('/tenants', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = createTenantSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const limits = parsed.data.limits ?? PLAN_LIMITS[parsed.data.plan];

    const tenant = await prisma.tenant.create({
      data: {
        name: parsed.data.name,
        plan: parsed.data.plan,
        region: parsed.data.region,
        domain: parsed.data.domain,
        limits,
      },
    });

    await prisma.tenantSetting.create({
      data: {
        tenantId: tenant.id,
        branding: {},
        integrations: {},
        ssoConfig: {},
      },
    });

    await prisma.tenantUsage.create({
      data: { tenantId: tenant.id },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: tenant.id,
      action: 'TENANT_CREATED_INTERNAL',
      targetType: 'tenant',
      targetId: tenant.id,
      metadata: { plan: tenant.plan },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(201).json(tenant);
  });

  router.patch('/tenants/:id', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = patchTenantSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const tenant = await prisma.tenant.update({
      where: { id: req.params.id },
      data: parsed.data,
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: tenant.id,
      action: 'TENANT_UPDATED_INTERNAL',
      targetType: 'tenant',
      targetId: tenant.id,
      metadata: parsed.data,
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.json(tenant);
  });

  router.post('/tenants/:id/suspend', async (req, res) => {
    const tenant = await prisma.tenant.update({
      where: { id: req.params.id },
      data: { status: 'SUSPENDED' },
    });

    await auditLog(prisma, {
      actorUserId: req.user?.userId,
      actorType: 'INTERNAL',
      tenantId: tenant.id,
      action: 'TENANT_SUSPENDED',
      targetType: 'tenant',
      targetId: tenant.id,
      metadata: {},
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(200).json({ id: tenant.id, status: tenant.status });
  });

  router.post('/tenants/:id/reactivate', async (req, res) => {
    const tenant = await prisma.tenant.update({
      where: { id: req.params.id },
      data: { status: 'ACTIVE' },
    });

    await auditLog(prisma, {
      actorUserId: req.user?.userId,
      actorType: 'INTERNAL',
      tenantId: tenant.id,
      action: 'TENANT_REACTIVATED',
      targetType: 'tenant',
      targetId: tenant.id,
      metadata: {},
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(200).json({ id: tenant.id, status: tenant.status });
  });

  router.post('/tenants/:tenantId/invites', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = inviteSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const token = createOpaqueToken();
    const invite = await prisma.tenantInvite.create({
      data: {
        tenantId: req.params.tenantId,
        email: parsed.data.email,
        role: parsed.data.role,
        tokenHash: hashToken(token),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        createdByUserId: req.user.userId,
      },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: req.params.tenantId,
      action: 'INVITE_CREATED_INTERNAL',
      targetType: 'tenant_invite',
      targetId: invite.id,
      metadata: { email: invite.email },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(201).json({
      invite_id: invite.id,
      invite_token: token,
      warning: 'DEV_ONLY: return token only in non-production.',
    });
  });

  router.post('/tenants/:id/reset-tenant-admin', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = resetAdminSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const token = createOpaqueToken();
    const txResult = await prisma.$transaction(async (tx) => {
      const invite = await tx.tenantInvite.create({
        data: {
          tenantId: req.params.id,
          email: parsed.data.newAdminEmail,
          role: 'TENANT_ADMIN',
          tokenHash: hashToken(token),
          expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
          createdByUserId: req.user!.userId,
        },
      });

      await tx.membership.updateMany({
        where: {
          tenantId: req.params.id,
          role: 'TENANT_ADMIN',
          status: 'ACTIVE',
        },
        data: {
          status: 'DISABLED',
        },
      });

      return invite;
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: req.params.id,
      action: 'TENANT_ADMIN_RESET_INITIATED',
      targetType: 'tenant',
      targetId: req.params.id,
      metadata: { reason: parsed.data.reason, newAdminEmail: parsed.data.newAdminEmail },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(200).json({
      invite_id: txResult.id,
      invite_token: token,
      warning: 'DEV_ONLY: deliver via secure email in production.',
    });
  });

  router.get('/tenants/:id/usage', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const [usersCount, projectsCount, usage] = await Promise.all([
      prisma.membership.count({ where: { tenantId: req.params.id, status: 'ACTIVE' } }),
      prisma.project.count({ where: { tenantId: req.params.id } }),
      prisma.tenantUsage.findUnique({ where: { tenantId: req.params.id } }),
    ]);

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: req.params.id,
      action: 'INTERNAL_VIEW_TENANT_USAGE',
      targetType: 'tenant_usage',
      targetId: req.params.id,
      metadata: {},
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.json({
      tenant_id: req.params.id,
      users_count: usersCount,
      projects_count: projectsCount,
      storage_used_mb: usage?.storageUsedMb ?? 0,
      last_activity_at: usage?.lastActivityAt ?? null,
    });
  });

  router.post('/tenants/:id/sso', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = ssoSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const ssoConfig = {
      issuer: parsed.data.issuer,
      domain: parsed.data.domain,
      callback_urls: parsed.data.callback_urls,
      secrets_ref: parsed.data.secrets_ref ?? null,
      secrets_storage: 'TODO: integrate KMS/Vault managed secret references',
    };

    const settings = await prisma.tenantSetting.upsert({
      where: { tenantId: req.params.id },
      update: { ssoConfig },
      create: {
        tenantId: req.params.id,
        branding: {},
        integrations: {},
        ssoConfig,
      },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: req.params.id,
      action: 'TENANT_SSO_METADATA_UPDATED',
      targetType: 'tenant_settings',
      targetId: req.params.id,
      metadata: { issuer: parsed.data.issuer, domain: parsed.data.domain },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.json({ tenant_id: req.params.id, sso_config: settings.ssoConfig });
  });

  router.post('/break-glass/start', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = breakGlassStartSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const now = new Date();
    const duration = parsed.data.duration_minutes ?? 60;
    const expiresAt = new Date(now.getTime() + duration * 60 * 1000);

    const session = await prisma.breakGlassSession.create({
      data: {
        internalUserId: req.user.userId,
        tenantId: parsed.data.tenant_id,
        reason: parsed.data.reason,
        startsAt: now,
        expiresAt,
      },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: parsed.data.tenant_id,
      action: 'BREAK_GLASS_STARTED',
      targetType: 'break_glass_session',
      targetId: session.id,
      metadata: { reason: parsed.data.reason, expiresAt },
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(201).json({
      session_id: session.id,
      tenant_id: session.tenantId,
      expires_at: session.expiresAt,
    });
  });

  router.post('/break-glass/revoke', async (req, res) => {
    if (!req.user) return res.status(401).json({ error: 'Unauthenticated' });

    const parsed = breakGlassRevokeSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const now = new Date();
    const updated = await prisma.breakGlassSession.update({
      where: { id: parsed.data.session_id },
      data: { revokedAt: now },
    });

    await auditLog(prisma, {
      actorUserId: req.user.userId,
      actorType: 'INTERNAL',
      tenantId: updated.tenantId,
      action: 'BREAK_GLASS_REVOKED',
      targetType: 'break_glass_session',
      targetId: updated.id,
      metadata: {},
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
    });

    return res.status(200).json({ session_id: updated.id, revoked_at: now });
  });

  return router;
}
