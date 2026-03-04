import express from 'express';
import type { PrismaClient } from '@prisma/client';
import { authenticateJWT } from './middleware/authenticateJWT.js';
import { resolveTenantContext } from './middleware/resolveTenantContext.js';
import { selfserveRouter } from './routes/selfserve.js';
import { invitesRouter } from './routes/invites.js';
import { internalRouter } from './routes/internal.js';
import { projectsRouter } from './routes/projects.js';
import { tenantAdminRouter } from './routes/tenantAdmin.js';

export function createApp(prisma: PrismaClient) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => res.json({ ok: true }));

  app.use(authenticateJWT(prisma));
  app.use(resolveTenantContext(prisma));

  app.use('/api/selfserve', selfserveRouter(prisma));
  app.use('/api/invites', invitesRouter(prisma));
  app.use('/api/internal', internalRouter(prisma));
  app.use('/api/projects', projectsRouter(prisma));
  app.use('/api/tenant', tenantAdminRouter(prisma));

  app.use((err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    // eslint-disable-next-line no-console
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
