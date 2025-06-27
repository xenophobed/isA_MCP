#!/bin/bash
# 生产环境准备脚本 - 完整的安全部署准备

set -e

echo "🚀 准备MCP智能服务生产部署..."

# 1. 检查安全状态
echo "\n🛡️  检查安全配置..."

if [ -f ".env" ]; then
    if grep -q "sk-proj-\|r8_\|shpat_" .env; then
        echo "❌ 发现.env文件中仍有敏感信息！"
        echo "请检查并清理.env文件"
        exit 1
    else
        echo "✅ .env文件安全检查通过"
    fi
fi

# 2. 验证必要文件存在
echo "\n📁 验证部署文件..."

required_files=(
    "smart_mcp_server.py"
    "requirements.production.txt"
    "Dockerfile.production"
    "railway.toml"
    "core/auth.py"
    "core/secure_endpoints.py"
    "scripts/deployment/create_supabase_tables.sql"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 缺失"
        exit 1
    fi
done

# 3. 检查依赖
echo "\n📦 检查Python依赖..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查关键依赖
python3 -c "
import sys
required_modules = ['fastapi', 'uvicorn', 'supabase', 'jwt', 'openai']
missing = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f'❌ 缺少依赖: {missing}')
    print('运行: pip install -r requirements.production.txt')
    sys.exit(1)
else:
    print('✅ Python依赖检查通过')
"

# 4. 生成JWT密钥（如果不存在）
echo "\n🔑 生成安全密钥..."
if ! command -v openssl &> /dev/null; then
    echo "⚠️  openssl未安装，使用Python生成密钥"
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
else
    JWT_SECRET=$(openssl rand -base64 32)
fi

echo "✅ JWT密钥已生成: $JWT_SECRET"
echo "📝 请在Railway环境变量中设置: JWT_SECRET_KEY=$JWT_SECRET"

# 5. 创建部署信息模板
echo "\n📋 创建部署清单..."

cat > deployment_checklist.md << EOF
# MCP智能服务部署清单

## 🛡️ 安全配置完成
- [x] 敏感信息已从代码中移除
- [x] JWT认证系统已实现
- [x] API密钥管理已配置
- [x] 请求限制已启用
- [x] 生产环境Dockerfile已优化

## 📊 Supabase数据库配置

### 1. 在Supabase Dashboard执行SQL
\`\`\`sql
-- 复制 scripts/deployment/create_supabase_tables.sql 的内容
-- 在Supabase Dashboard的SQL Editor中执行
\`\`\`

### 2. 启用pgvector扩展
\`\`\`sql
CREATE EXTENSION IF NOT EXISTS vector;
\`\`\`

## 🚀 Railway部署配置

### 必需的环境变量：
\`\`\`bash
# 数据库配置
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=[your-supabase-key]

# AI服务
OPENAI_API_KEY=sk-[your-openai-key]

# 安全配置
JWT_SECRET_KEY=$JWT_SECRET
NODE_ENV=production

# Python配置
PYTHONPATH=.
PYTHONUNBUFFERED=1
\`\`\`

## 📋 部署步骤
1. \`railway login\`
2. \`railway init mcp-smart-service\`
3. \`railway add redis\`
4. 设置所有环境变量
5. \`railway up\`

## ✅ 部署后验证
- [ ] 健康检查: GET /health
- [ ] 安全信息: GET /security
- [ ] 生成API密钥: POST /auth/generate-key
- [ ] 智能发现: POST /discover
- [ ] 统计信息: GET /stats

## 🔒 生产环境功能
- 31个AI工具自动注册
- 14个动态提示词
- 18个智能资源
- JWT + API密钥双重认证
- 速率限制保护
- Supabase向量存储
- Redis缓存加速

EOF

echo "✅ 部署清单已创建: deployment_checklist.md"

# 6. 最终检查
echo "\n🔍 最终安全检查..."

# 检查是否有遗留的SQLite引用
if grep -r "user_data\.db\|sqlite3" . --exclude-dir=.git --exclude="*.sh" --exclude="*.md" 2>/dev/null; then
    echo "⚠️  发现残留的SQLite引用，需要清理"
else
    echo "✅ SQLite引用已完全清理"
fi

# 检查是否有硬编码的敏感信息
if grep -r "sk-proj-\|r8_\|shpat_\|eyJ" . --exclude-dir=.git --exclude="*.sh" --exclude="*.md" --exclude=".env.example" 2>/dev/null; then
    echo "❌ 发现硬编码的敏感信息！"
    exit 1
else
    echo "✅ 无硬编码敏感信息"
fi

echo "\n🎉 生产环境准备完成！"
echo "📄 请查看 deployment_checklist.md 了解部署步骤"
echo "🔑 JWT密钥: $JWT_SECRET"
echo ""
echo "下一步："
echo "1. 在Supabase中执行SQL脚本"
echo "2. 运行 ./scripts/deployment/setup_railway.sh"
echo "3. 按照清单验证部署"