# ShotFlow — 后端 Dockerfile
# 构建上下文为仓库根目录（以便复用 08_Automation 脚本）

FROM python:3.12-slim

WORKDIR /app

# 系统依赖：git(同步) / ffmpeg(音视频处理) / curl(健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存）
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 创建非 root 用户（生产最小权限）
RUN useradd -m -u 1000 appuser

# 复制整个项目（含 08_Automation 脚本，供后端 P1 阶段复用）
COPY --chown=appuser:appuser . /app

# 切换到非 root 用户（最小权限原则）
USER appuser

WORKDIR /app/backend

EXPOSE 8000

# 健康检查：调用 /api/v1/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 默认启动 API 服务；worker 服务通过 docker-compose 覆盖 command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
