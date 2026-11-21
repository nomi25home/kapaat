FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
RUN apk add --no-cache openssl
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY generate-tls-cert.sh /docker-entrypoint.d/10-generate-tls-cert.sh
RUN chmod +x /docker-entrypoint.d/10-generate-tls-cert.sh
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD wget --no-check-certificate -qO- https://127.0.0.1:8080/ >/dev/null || exit 1
