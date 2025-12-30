# ===================================
# AAA-StoryMaker 后端服务 Dockerfile
# ===================================
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn fastapi

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/data/novels /app/data/worlds /app/data/runtime /app/logs

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动API服务
CMD ["python", "api_server.py"]

