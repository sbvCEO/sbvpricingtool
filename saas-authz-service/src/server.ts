import { prisma } from './lib/prisma.js';
import { createApp } from './app.js';

const port = Number(process.env.PORT ?? 4000);
const app = createApp(prisma);

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`saas-authz-service listening on :${port}`);
});
