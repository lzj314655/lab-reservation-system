# syntax=docker/dockerfile:1

# ============================================================
# 阶段1: 构建 —— node 22 与本地开发环境一致
# VITE_API_BASE_URL 留空 = 前端同源请求，/api 与 /uploads 由 nginx 反代到后端
# ============================================================
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ============================================================
# 阶段2: 运行时 —— nginx 托管静态文件 + 反代
# ============================================================
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
