#!/bin/bash
# Railway 部署自动化脚本
# 一键部署MCP智能服务到Railway

set -e

echo "🚀 开始部署MCP智能服务到Railway..."

# 检查依赖
echo "\n📋 检查部署依赖..."

# 检查Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI 未安装，正在安装..."
    npm install -g @railway/cli
    echo "✅ Railway CLI 安装完成"
else
    echo "✅ Railway CLI 已安装"
fi

# 检查git状态
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  发现未提交的更改，正在提交..."
    git add -A
    git commit -m "🚀 准备部署到Railway

    🤖 Generated with [Claude Code](https://claude.ai/code)
    
    Co-Authored-By: Claude <noreply@anthropic.com>"
    echo "✅ 代码已提交"
else
    echo "✅ 代码库状态干净"
fi

# 登录Railway
echo "\n🔑 连接Railway..."
if ! railway whoami &> /dev/null; then
    echo "请先登录Railway..."
    railway login
fi

# 检查项目是否已存在
PROJECT_NAME="mcp-smart-service"
if railway list | grep -q "$PROJECT_NAME"; then
    echo "✅ 项目 '$PROJECT_NAME' 已存在"
    railway link $PROJECT_NAME
else
    echo "🆕 创建新项目..."
    railway init $PROJECT_NAME
fi

# 添加Redis服务
echo "\n🔧 配置服务依赖..."
if ! railway services | grep -q "redis"; then
    echo "添加Redis服务..."
    railway add redis
    echo "✅ Redis服务已添加"
else
    echo "✅ Redis服务已存在"
fi

# 设置环境变量
echo "\n⚙️  配置环境变量..."

# 获取用户输入的敏感信息
read -p "请输入Supabase URL: " SUPABASE_URL
read -p "请输入Supabase Key: " SUPABASE_KEY
read -p "请输入OpenAI API Key: " OPENAI_API_KEY
read -p "请输入JWT Secret Key (或按回车使用随机生成): " JWT_SECRET_KEY

# 生成JWT密钥（如果没有提供）
if [ -z "$JWT_SECRET_KEY" ]; then
    JWT_SECRET_KEY=$(openssl rand -base64 32)
    echo "✅ 自动生成JWT密钥: $JWT_SECRET_KEY"
fi

# 构建DATABASE_URL
echo "请输入Supabase数据库连接信息:"
read -p "数据库密码: " DB_PASSWORD
DATABASE_URL="postgresql://postgres:$DB_PASSWORD@$(echo $SUPABASE_URL | sed 's/https:\/\///g').supabase.co:5432/postgres"

# 设置环境变量
echo "设置环境变量..."
railway variables set \
    DATABASE_URL="$DATABASE_URL" \
    SUPABASE_URL="$SUPABASE_URL" \
    SUPABASE_KEY="$SUPABASE_KEY" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    JWT_SECRET_KEY="$JWT_SECRET_KEY" \
    NODE_ENV="production" \
    PYTHONPATH="." \
    PYTHONUNBUFFERED="1"

echo "✅ 环境变量设置完成"

# 部署应用
echo "\n🚀 开始部署..."
railway up --detach

echo "\n⏳ 等待部署完成..."
sleep 60

# 获取部署URL
DEPLOY_URL=$(railway status --json | jq -r '.deployments[0].url')
if [ "$DEPLOY_URL" = "null" ]; then
    echo "⚠️  无法获取部署URL，请检查Railway仪表板"
    DEPLOY_URL="https://your-service.railway.app"
fi

echo "\n🎉 部署完成！"
echo "===================="
echo "🌐 服务地址: $DEPLOY_URL"
echo "📊 健康检查: $DEPLOY_URL/health"
echo "🔍 能力发现: $DEPLOY_URL/discover"
echo "📈 监控统计: $DEPLOY_URL/stats"
echo "===================="

# 验证部署
echo "\n🔍 验证部署状态..."
sleep 10

if curl -f "$DEPLOY_URL/health" > /dev/null 2>&1; then
    echo "✅ 服务运行正常！"
    
    # 测试AI能力发现
    echo "\n🧠 测试AI能力发现..."
    DISCOVER_RESULT=$(curl -s -X POST "$DEPLOY_URL/discover" \
        -H "Content-Type: application/json" \
        -d '{"request": "test deployment"}')
    
    if echo "$DISCOVER_RESULT" | jq -e '.status == "success"' > /dev/null; then
        echo "✅ AI能力发现功能正常"
        echo "🎯 发现的工具数量: $(echo "$DISCOVER_RESULT" | jq '.capabilities.tools | length')"
    else
        echo "⚠️  AI能力发现可能存在问题"
    fi
else
    echo "❌ 服务启动失败，请检查日志"
    railway logs
    exit 1
fi

# 显示后续步骤
echo "\n📋 后续步骤:"
echo "1. 在Vercel应用中配置MCP服务URL:"
echo "   NEXT_PUBLIC_MCP_API_URL=$DEPLOY_URL"
echo ""
echo "2. 生成API密钥用于认证:"
echo "   curl -X POST $DEPLOY_URL/auth/generate-key"
echo ""
echo "3. 查看Railway项目仪表板:"
echo "   railway open"
echo ""

# 保存部署信息
echo "📄 保存部署信息..."
cat > deployment_info.json << EOF
{
  "service_url": "$DEPLOY_URL",
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "project_name": "$PROJECT_NAME",
  "environment": "production",
  "features": [
    "31 智能工具",
    "14 动态提示词",
    "18 资源模块",
    "AI能力发现",
    "向量相似性匹配"
  ],
  "endpoints": {
    "health": "$DEPLOY_URL/health",
    "discover": "$DEPLOY_URL/discover",
    "stats": "$DEPLOY_URL/stats",
    "capabilities": "$DEPLOY_URL/capabilities"
  }
}
EOF

echo "✅ 部署信息已保存到 deployment_info.json"

echo "\n🎊 恭喜！MCP智能服务已成功部署到Railway！"
echo "现在可以开始使用AI驱动的工具发现和自动化功能了。"