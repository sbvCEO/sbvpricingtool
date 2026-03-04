import type { PrismaClient } from '@prisma/client';
import { hashToken } from '../lib/crypto.js';

export async function acceptInvite(params: {
  prisma: PrismaClient;
  token: string;
  userId: string;
  userEmail: string;
}) {
  const tokenHash = hashToken(params.token);
  const now = new Date();

  const invite = await params.prisma.tenantInvite.findFirst({
    where: {
      tokenHash,
      acceptedAt: null,
      expiresAt: { gt: now },
    },
  });

  if (!invite) {
    throw new Error('INVITE_INVALID');
  }

  if (invite.email.toLowerCase() !== params.userEmail.toLowerCase()) {
    throw new Error('INVITE_EMAIL_MISMATCH');
  }

  const existing = await params.prisma.membership.findUnique({
    where: {
      tenantId_userId: {
        tenantId: invite.tenantId,
        userId: params.userId,
      },
    },
  });

  const membership = existing
    ? await params.prisma.membership.update({
        where: { id: existing.id },
        data: { role: invite.role, status: 'ACTIVE' },
      })
    : await params.prisma.membership.create({
        data: {
          tenantId: invite.tenantId,
          userId: params.userId,
          role: invite.role,
          status: 'ACTIVE',
        },
      });

  const updatedInvite = await params.prisma.tenantInvite.update({
    where: { id: invite.id },
    data: { acceptedAt: now },
  });

  return { invite: updatedInvite, membership };
}
