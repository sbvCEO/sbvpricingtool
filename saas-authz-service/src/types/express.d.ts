import type { MembershipRole } from '@prisma/client';

declare global {
  namespace Express {
    interface Request {
      user?: {
        userId: string;
        authSubject: string;
        email: string;
        isInternal: boolean;
      };
      tenant?: {
        tenantId: string;
        membershipRole: MembershipRole | null;
        viaBreakGlass: boolean;
        breakGlassSessionId?: string;
      };
    }
  }
}

export {};
