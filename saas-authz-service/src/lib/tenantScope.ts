import type { PrismaClient } from '@prisma/client';

export async function setTenantRlsContext(
  prisma: PrismaClient,
  tenantId: string,
  breakGlassTenantId?: string,
): Promise<void> {
  await prisma.$executeRawUnsafe(`SELECT set_config('app.tenant_id', $1, true)`, tenantId);
  await prisma.$executeRawUnsafe(
    `SELECT set_config('app.break_glass_tenant_id', $1, true)`,
    breakGlassTenantId ?? '',
  );
}
