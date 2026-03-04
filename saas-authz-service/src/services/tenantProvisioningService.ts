import { Plan, type PrismaClient, type Prisma } from '@prisma/client';

const PLAN_LIMITS: Record<Plan, Prisma.InputJsonValue> = {
  FREE: { users_limit: 3, storage_limit_mb: 512, features: { sso: false } },
  TRIAL: { users_limit: 10, storage_limit_mb: 2048, features: { sso: false } },
  PRO: { users_limit: 100, storage_limit_mb: 20480, features: { sso: true } },
  ENTERPRISE: { users_limit: 1000, storage_limit_mb: 102400, features: { sso: true } },
};

export async function createTenantWithAdmin(params: {
  prisma: PrismaClient;
  name: string;
  region: string;
  creatorUserId: string;
  plan?: Plan;
  domain?: string;
}) {
  const plan = params.plan ?? Plan.TRIAL;

  return params.prisma.$transaction(async (tx) => {
    const tenant = await tx.tenant.create({
      data: {
        name: params.name,
        region: params.region,
        domain: params.domain,
        plan,
        limits: PLAN_LIMITS[plan],
      },
    });

    const membership = await tx.membership.create({
      data: {
        tenantId: tenant.id,
        userId: params.creatorUserId,
        role: 'TENANT_ADMIN',
        status: 'ACTIVE',
      },
    });

    await tx.tenantSetting.create({
      data: {
        tenantId: tenant.id,
        branding: { primaryColor: '#0057b8', logoUrl: null },
        integrations: {},
        ssoConfig: {},
      },
    });

    await tx.tenantUsage.create({
      data: {
        tenantId: tenant.id,
      },
    });

    return { tenant, membership };
  });
}

export { PLAN_LIMITS };
