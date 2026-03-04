import jwt from 'jsonwebtoken';

export type JwtIdentity = {
  sub: string;
  email: string;
  name?: string;
};

export function verifyAndDecodeJwt(token: string): JwtIdentity {
  const secret = process.env.JWT_SECRET;
  let payload: string | jwt.JwtPayload | null;

  if (secret) {
    payload = jwt.verify(token, secret) as jwt.JwtPayload;
  } else {
    payload = jwt.decode(token) as jwt.JwtPayload;
  }

  if (!payload || typeof payload === 'string') {
    throw new Error('Invalid token payload');
  }

  const sub = payload.sub;
  const email = payload.email as string | undefined;

  if (!sub || !email) {
    throw new Error('Token missing sub/email');
  }

  return {
    sub,
    email,
    name: typeof payload.name === 'string' ? payload.name : undefined,
  };
}
