# Auth0 & Stripe 集成设置清单

## 🔐 Auth0 配置

### ✅ 必需步骤

1. **登录 Auth0 Dashboard**
   - 访问: https://manage.auth0.com/dashboard/us/dev-47zcqarlxizdkads/
   
2. **配置应用设置**
   - 应用 ID: `Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ`
   - 应用类型: `Single Page Application`
   - 允许的回调 URLs: 
     ```
     http://localhost:3000/callback
     https://www.iapro.ai/callback
     ```
   - 允许的登出 URLs:
     ```
     http://localhost:3000
     https://www.iapro.ai
     ```
   - 允许的 Web Origins:
     ```
     http://localhost:3000
     https://www.iapro.ai
     ```
   - 允许的 Origins (CORS):
     ```
     http://localhost:3000
     http://localhost:8100
     https://www.iapro.ai
     ```

3. **配置 API 权限**
   - API 标识符: `https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/`
   - 确保应用有 Management API 访问权限
   - 授权 Scopes:
     - `read:users`
     - `update:users` 
     - `create:users`
     - `read:user_metadata`
     - `update:user_metadata`

4. **创建测试用户**
   - 在 Users & Roles > Users 中创建测试账户
   - 或者启用社交登录（Google、GitHub 等）

## 💳 Stripe 配置

### ✅ 必需步骤

1. **登录 Stripe Dashboard** 
   - 访问: https://dashboard.stripe.com/
   - 确保在 **测试模式** 下操作

2. **验证/创建产品和价格**
   ```bash
   # 运行验证脚本
   cd deployment/dev
   python verify_stripe_config.py
   ```
   
   如果价格不存在，手动创建：
   
   **Pro 计划**:
   - 产品名: Pro Plan
   - 价格: $20.00 USD
   - 计费周期: 月付
   - 记录价格 ID 并更新配置

   **Enterprise 计划**:
   - 产品名: Enterprise Plan  
   - 价格: $100.00 USD
   - 计费周期: 月付
   - 记录价格 ID 并更新配置

3. **设置 Webhook (选择一种方式)**

   **方式 A: Stripe CLI (推荐用于开发)**
   ```bash
   # 安装并设置 Stripe CLI
   ./deployment/dev/setup_stripe_cli.sh
   
   # 启动本地转发
   stripe listen --forward-to localhost:8100/api/v1/webhooks/stripe
   ```
   
   **方式 B: 配置生产 Webhook**
   - 进入 Developers > Webhooks
   - 添加端点: `http://localhost:8100/api/v1/webhooks/stripe`
   - 选择事件:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

4. **复制 Webhook 签名密钥**
   - 更新 `deployment/dev/.env.user_service` 文件中的 `STRIPE_WEBHOOK_SECRET`

## 🚀 启动和测试

### ✅ 启动服务

1. **启动开发环境**
   ```bash
   # 在项目根目录执行
   ./deployment/scripts/start_dev.sh
   ```

2. **验证服务运行**
   ```bash
   # 运行集成测试
   cd deployment/dev
   python test_integration.py
   ```

3. **检查服务状态**
   - User Service: http://localhost:8100/health
   - API 文档: http://localhost:8100/docs
   - Swagger UI: http://localhost:8100/redoc

### ✅ 测试流程

1. **Auth0 登录测试**
   - 启动前端应用
   - 测试登录流程
   - 确认 JWT token 正确传递

2. **用户管理测试**
   - 测试用户创建/获取
   - 验证积分分配
   - 检查用户数据同步

3. **Stripe 支付测试**
   - 创建 Checkout 会话
   - 使用测试卡号: `4242 4242 4242 4242`
   - 验证 Webhook 事件处理

4. **端到端测试**
   - 完整的注册 → 登录 → 订阅 → 使用流程

## 🔧 环境变量检查

确保以下环境变量正确配置：

```bash
# Auth0
AUTH0_DOMAIN=dev-47zcqarlxizdkads.us.auth0.com
AUTH0_CLIENT_ID=Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ  
AUTH0_CLIENT_SECRET=kk6n0zkaavCzd5FuqpoTeWudnQBNQvhXneb-LI3TPWunhUkJNim9FEZeWXKRJd7m
AUTH0_AUDIENCE=https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/

# Stripe  
STRIPE_SECRET_KEY=your_stripe_test_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_k8dE6GlLG6lShA3Dm8HE0f11VSzZCa8a
STRIPE_PRO_PRICE_ID=price_1RbchvL7y127fTKemRuw8Elz
STRIPE_ENTERPRISE_PRICE_ID=price_1RbciEL7y127fTKexyDAX9JA
```

## 🐛 常见问题排查

1. **Auth0 401 错误**
   - 检查 token 格式和过期时间
   - 验证 audience 配置
   - 确认 CORS 设置

2. **Stripe Webhook 失败**
   - 验证签名密钥正确
   - 检查端点 URL 可访问性
   - 确认事件类型匹配

3. **服务启动失败**
   - 检查端口占用 (`lsof -i :8100`)
   - 验证数据库连接
   - 查看日志文件 `logs/user_service.log`

## ✅ 完成确认

- [ ] Auth0 应用配置完成
- [ ] Stripe 产品和价格创建
- [ ] Webhook 设置并测试  
- [ ] 环境变量配置正确
- [ ] 服务成功启动
- [ ] 集成测试通过
- [ ] 前端可以正常调用 API

完成所有步骤后，你的 User Service 就可以进行完整的前端集成测试了！