# Railway 部署指南

## 🚀 快速部署到Railway

Railway是最适合你当前技术栈的部署方案：
- ✅ 与Vercel前端无缝集成
- ✅ 原生支持Supabase数据库
- ✅ 自动SSL和域名管理
- ✅ 简单的环境变量配置

## 📋 部署步骤

### 1. 连接GitHub仓库

```bash
# 1. 安装Railway CLI
npm install -g @railway/cli

# 2. 登录Railway
railway login

# 3. 初始化项目
railway init
```

### 2. 配置环境变量

在Railway Dashboard中设置以下环境变量：

```bash
# 数据库 (Supabase)
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# AI服务
OPENAI_API_KEY=sk-...

# 安全密钥
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# 缓存 (Railway Redis addon)
REDIS_URL=redis://default:[password]@[host]:6379
```

### 3. 添加服务依赖

```bash
# 添加Redis服务
railway add redis

# 部署服务
railway up
```

### 4. 验证部署

```bash
# 获取服务URL
railway status

# 测试健康检查
curl https://your-service-url.railway.app/health
```

## 🔧 与现有架构集成

### Vercel前端配置

在你的Vercel项目中添加环境变量：

```bash
# .env.local (Vercel)
NEXT_PUBLIC_MCP_API_URL=https://your-mcp-service.railway.app
MCP_API_KEY=your-api-key
```

### API调用示例

```javascript
// 在Vercel应用中调用MCP服务
const response = await fetch(`${process.env.NEXT_PUBLIC_MCP_API_URL}/discover`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${process.env.MCP_API_KEY}`
  },
  body: JSON.stringify({
    request: "帮我搜索关于Claude的信息"
  })
});

const capabilities = await response.json();
console.log('发现的能力:', capabilities);
```

## 📊 监控和日志

### Railway内置监控

```bash
# 查看实时日志
railway logs

# 查看服务指标
railway status --json
```

### 自定义健康检查

Railway会自动使用 `/health` 端点进行健康检查：

```json
{
  "status": "healthy",
  "service": "Smart MCP Server",
  "server_info": {
    "server_name": "Smart MCP Server",
    "ai_selectors": {
      "tool_selector": true,
      "prompt_selector": true, 
      "resource_selector": true
    },
    "capabilities_count": {
      "tools": 31,
      "prompts": 14,
      "resources": 18
    }
  }
}
```

## 💰 成本估算

### Railway定价 (生产环境)

| 资源 | 配置 | 月费用 |
|------|------|--------|
| **MCP服务** | 1GB RAM, 1 vCPU | $5-20 |
| **Redis缓存** | 256MB | $5 |
| **总计** | | **$10-25/月** |

### 扩展配置

```toml
# railway.toml - 生产环境配置
[deploy]
replicas = 2  # 双实例高可用
healthcheckPath = "/health"
healthcheckTimeout = 30

[resources]
memory = "1GB"
cpu = "1000m"
```

## 🚀 自动部署配置

### GitHub Actions集成

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        uses: railway/cli@v2
        with:
          command: up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## 🔒 生产环境安全

### HTTPS和域名

```bash
# 配置自定义域名
railway domain add yourdomain.com

# Railway自动提供SSL证书
```

### 环境隔离

```bash
# 创建staging环境
railway environment create staging

# 部署到staging
railway up --environment staging
```

## 📋 部署检查清单

### 部署前检查

- [ ] Supabase数据库已配置pgvector扩展
- [ ] 所有环境变量已在Railway设置
- [ ] Redis缓存服务已添加
- [ ] 健康检查端点正常工作

### 部署后验证

- [ ] 服务健康检查通过
- [ ] AI选择器正常工作 (3/3)
- [ ] RAG搜索功能正常
- [ ] 与Vercel前端连接成功
- [ ] 日志监控正常

### 性能优化

- [ ] 数据库连接池配置
- [ ] Redis缓存策略优化
- [ ] API响应时间监控
- [ ] 错误率告警设置

## 🎯 下一步行动

1. **立即部署**: 按照上述步骤部署到Railway
2. **前端集成**: 更新Vercel应用连接MCP服务
3. **用户测试**: 邀请测试用户验证功能
4. **监控优化**: 根据实际使用情况调优

Railway + Supabase + Vercel 的组合是现代全栈应用的最佳实践，具有以下优势：

- 🚀 **快速部署**: 几分钟内完成部署
- 🔄 **自动扩展**: 根据流量自动调整资源
- 💰 **成本可控**: 按需付费，起步成本低
- 🛡️ **安全可靠**: 企业级安全和可用性
- 🔧 **易于维护**: 简单的配置和监控