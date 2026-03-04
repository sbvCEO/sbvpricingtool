import type { PrismaClient } from '@prisma/client';
import crypto from 'node:crypto';

type TenantJob = {
  id: string;
  type: 'PROJECT_CREATED' | 'USAGE_RECALC';
  tenantId: string;
  actorUserId?: string;
  payload: Record<string, unknown>;
};

type JobHandler = (job: TenantJob, prisma: PrismaClient) => Promise<void>;

export class InMemoryTenantQueue {
  private readonly jobs: TenantJob[] = [];
  private readonly handlers: Record<string, JobHandler>;

  constructor(private readonly prisma: PrismaClient) {
    this.handlers = {
      PROJECT_CREATED: this.handleProjectCreated.bind(this),
      USAGE_RECALC: this.handleUsageRecalc.bind(this),
    };
  }

  enqueue(job: Omit<TenantJob, 'id'>): TenantJob {
    const queued: TenantJob = { ...job, id: crypto.randomUUID() };
    this.jobs.push(queued);
    return queued;
  }

  async processNext(): Promise<void> {
    const job = this.jobs.shift();
    if (!job) return;

    const handler = this.handlers[job.type];
    if (!handler) throw new Error(`No handler for job type ${job.type}`);

    await handler(job, this.prisma);
  }

  private async handleProjectCreated(job: TenantJob, prisma: PrismaClient): Promise<void> {
    await prisma.tenantUsage.upsert({
      where: { tenantId: job.tenantId },
      update: {
        projectsCount: { increment: 1 },
        lastActivityAt: new Date(),
      },
      create: {
        tenantId: job.tenantId,
        projectsCount: 1,
        usersCount: 0,
        storageUsedMb: 0,
        lastActivityAt: new Date(),
      },
    });
  }

  private async handleUsageRecalc(job: TenantJob, prisma: PrismaClient): Promise<void> {
    const [usersCount, projectsCount] = await Promise.all([
      prisma.membership.count({ where: { tenantId: job.tenantId, status: 'ACTIVE' } }),
      prisma.project.count({ where: { tenantId: job.tenantId } }),
    ]);

    await prisma.tenantUsage.upsert({
      where: { tenantId: job.tenantId },
      update: {
        usersCount,
        projectsCount,
        lastActivityAt: new Date(),
      },
      create: {
        tenantId: job.tenantId,
        usersCount,
        projectsCount,
        storageUsedMb: 0,
        lastActivityAt: new Date(),
      },
    });
  }
}
