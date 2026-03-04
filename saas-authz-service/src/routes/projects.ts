import { Router } from 'express';
import { z } from 'zod';
import type { PrismaClient } from '@prisma/client';
import { authorizeTenantUser } from '../middleware/authorize.js';
import { requireBusinessDataAccess } from '../middleware/requireBusinessAccess.js';

const createProjectSchema = z.object({
  name: z.string().min(2),
});

export function projectsRouter(prisma: PrismaClient) {
  const router = Router();

  router.use(authorizeTenantUser());
  router.use(requireBusinessDataAccess(prisma));

  router.get('/', async (req, res) => {
    const tenantId = req.tenant!.tenantId;
    const projects = await prisma.project.findMany({
      where: { tenantId },
      orderBy: { createdAt: 'desc' },
    });
    return res.json(projects);
  });

  router.post('/', async (req, res) => {
    const parsed = createProjectSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });

    const tenantId = req.tenant!.tenantId;
    const project = await prisma.project.create({
      data: {
        tenantId,
        name: parsed.data.name,
      },
    });

    await prisma.tenantUsage.upsert({
      where: { tenantId },
      update: {
        projectsCount: { increment: 1 },
        lastActivityAt: new Date(),
      },
      create: {
        tenantId,
        projectsCount: 1,
        usersCount: 0,
        storageUsedMb: 0,
        lastActivityAt: new Date(),
      },
    });

    return res.status(201).json(project);
  });

  return router;
}
