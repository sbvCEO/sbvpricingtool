import { Router } from 'express';
import type { PrismaClient } from '@prisma/client';
import { authorizeTenantAdmin } from '../middleware/authorize.js';

export function tenantAdminRouter(prisma: PrismaClient) {
  const router = Router();

  router.use(authorizeTenantAdmin(prisma));

  router.get('/memberships', async (req, res) => {
    const tenantId = req.tenant!.tenantId;
    const memberships = await prisma.membership.findMany({
      where: { tenantId },
      include: { user: { select: { id: true, email: true, name: true } } },
    });
    return res.json(memberships);
  });

  return router;
}
