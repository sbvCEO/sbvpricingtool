import type { NextFunction, Request, Response } from 'express';
import type { PrismaClient } from '@prisma/client';
import { verifyAndDecodeJwt } from '../lib/jwt.js';

export function authenticateJWT(prisma: PrismaClient) {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const auth = req.header('Authorization');
      if (!auth?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Missing bearer token' });
      }

      const token = auth.substring('Bearer '.length);
      const identity = verifyAndDecodeJwt(token);

      const user = await prisma.user.upsert({
        where: { authSubject: identity.sub },
        update: {
          email: identity.email,
          name: identity.name,
        },
        create: {
          authSubject: identity.sub,
          email: identity.email,
          name: identity.name,
        },
      });

      req.user = {
        userId: user.id,
        authSubject: user.authSubject,
        email: user.email,
        isInternal: user.isInternal,
      };

      next();
    } catch (error) {
      console.error('JWT Auth Error:', error);
      return res.status(401).json({ error: 'Invalid token' });
    }
  };
}
