# Frontend Dockerfile
FROM node:24-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --frozen-lockfile

# Copy source
COPY frontend/ .

# Build
RUN npm run build

# Production stage
FROM nginx:alpine

# Create non-root user
RUN addgroup -g 1001 appuser && adduser -D -u 1001 -G appuser appuser

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Change ownership
RUN chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /etc/nginx

# Create writable temp and pid directories for non-root nginx
RUN mkdir -p /tmp/nginx /tmp/nginx_client /tmp/nginx_proxy /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi \
    && chown -R appuser:appuser /tmp/nginx /tmp/nginx_client /tmp/nginx_proxy /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi

# Switch to non-root user
USER appuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 -O /dev/null http://127.0.0.1:80/frontend-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
