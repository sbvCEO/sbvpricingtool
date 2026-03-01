# Build stage
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:stable-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=build /app/vite.config.ts /etc/nginx/conf.d/default.conf 
# Note: In a real world scenario, you'd provide a custom nginx.conf to handle SPA routing

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
