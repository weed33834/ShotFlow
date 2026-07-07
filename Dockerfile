# 这个 Dockerfile 构建的是 CLI 预检镜像（跑 preflight_check.py 检查项目结构）。
# 起 Web 平台全栈请用根目录的 docker-compose.yml，它会分别构建 backend/ 和 frontend/ 镜像。

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存）
COPY 08_Automation/requirements.txt /app/08_Automation/requirements.txt
RUN pip install --no-cache-dir -r /app/08_Automation/requirements.txt

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 复制项目文件
COPY --chown=appuser:appuser . /app
USER appuser

CMD ["python", "08_Automation/preflight_check.py"]
