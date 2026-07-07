# ShotFlow — 前端 Dockerfile（多阶段构建）
# 阶段1: 构建产物；阶段2: Nginx 托管

# ===== 构建阶段 =====
FROM node:20-alpine AS builder
WORKDIR /app

# 先装依赖（利用层缓存）；用 npm ci 按 lockfile 精确安装，保证可重现
# NPM_REGISTRY 可用 --build-arg 覆盖（国内构建可设为 https://registry.npmmirror.com）
ARG NPM_REGISTRY=https://registry.npmjs.org
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry ${NPM_REGISTRY} && \
    npm ci

# 复制源码并构建
COPY frontend/ ./
RUN npm run build

# ===== 运行阶段 =====
FROM nginx:alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
