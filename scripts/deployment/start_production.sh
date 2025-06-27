#!/bin/bash
# 生产环境启动脚本

set -e

echo "🚀 启动MCP智能服务 (生产环境)"

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    echo "❌ 错误: DATABASE_URL 环境变量未设置"
    exit 1
fi

# 启动服务
echo "📦 启动服务容器..."
cd deployment/production
docker-compose up -d

# 健康检查
echo "🔍 检查服务健康状态..."
sleep 30

if curl -f http://localhost:4321/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo "🌐 服务地址: http://localhost:4321"
    echo "📊 监控地址: http://localhost:3000"
else
    echo "❌ 服务启动失败"
    docker-compose logs mcp-service
    exit 1
fi
