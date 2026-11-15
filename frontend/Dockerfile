# syntax=docker/dockerfile:1
# Dental-IQ web app: build with Node, serve the static bundle with nginx (which also proxies /api).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Optional extra CA for TLS-inspecting networks (build secret; see backend/Dockerfile).
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi \
    && npm ci --no-audit --no-fund
COPY . .
ENV VITE_API_URL=/api
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
