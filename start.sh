#!/bin/bash
# ===================================
# AAA-StoryMaker 一键启动脚本 (Linux/Mac)
# ===================================

echo "🎭 AAA-StoryMaker - Infinite Story Engine"
echo "=========================================="
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 配置文件"
    echo "   正在从模板创建..."
    cp template.env .env
    echo ""
    echo "📝 请编辑 .env 文件，填入你的 API 密钥："
    echo "   - OPENROUTER_API_KEY（推荐）"
    echo "   - 或 ZHIPU_API_KEY"
    echo ""
    echo "   然后重新运行此脚本。"
    exit 1
fi

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未安装 Docker"
    echo "   请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 未安装 Docker Compose"
    echo "   请先安装 Docker Compose"
    exit 1
fi

echo "🚀 正在启动服务..."
echo ""

# 启动服务
docker-compose up --build -d

echo ""
echo "✅ 服务启动成功！"
echo ""
echo "🌐 前端地址: http://localhost:3000"
echo "🔌 后端API: http://localhost:8000"
echo ""
echo "📋 常用命令："
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo ""

