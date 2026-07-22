# ===== Backend =====
FROM python:3.10-slim AS backend

# 安装 ffmpeg（视频合成必需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY backend/ /app/

# 复制 flows 目录（编排器读取 SOP 流程文件）
COPY flows/ /app/flows/

# 复制 prompts 目录（电影级提示词词库）
COPY backend/app/prompts/ /app/app/prompts/

ENV PYTHONPATH=/app
ENV DEBUG=true
ENV SIMULATE_MODE=true
ENV DATABASE_URL=sqlite:///./shotflow.db

EXPOSE 8000

# 初始化数据库 + 启动服务
CMD ["sh", "-c", "PYTHONPATH=/app python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# ===== Frontend (build stage) =====
FROM node:22-slim AS frontend-builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ===== Frontend (serve stage) =====
FROM nginx:alpine AS frontend
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
