# Human-in-Loop (HIL) for Web Automation

## 概述 (Overview)

Web Automation 集成了 Human-in-Loop (HIL) 机制，当遇到需要人工干预的场景时，会返回特定的 HIL 动作给 Agent 处理。

## 两种 HIL 动作 (Two HIL Actions)

### 1. `request_authorization` - 请求授权使用已存储凭证

**触发条件：**
- Vault 中已存储相关凭证
- 需要用户授权才能使用

**使用场景：**
- 登录页面检测到 Vault 有 Google 账号凭证
- 支付页面检测到 Vault 有 Stripe 支付方式
- 钱包连接检测到 Vault 有 MetaMask 钱包

**响应格式：**
```json
{
  "hil_required": true,
  "status": "authorization_required",
  "action": "request_authorization",
  "message": "Found stored credentials for Google. Do you authorize using them for login?",
  "data": {
    "auth_type": "social",
    "provider": "google",
    "url": "https://accounts.google.com/...",
    "credential_preview": {
      "provider": "google",
      "vault_id": "vault_xxx",
      "stored_at": "2025-01-15T10:30:00Z"
    },
    "screenshot": "/tmp/screenshot.png",
    "details": "Google OAuth login page detected"
  }
}
```

### 2. `ask_human` - 请求用户提供新凭证

**触发条件：**
- Vault 中没有找到相关凭证
- 遇到无法自动化的场景（如 CAPTCHA）

**使用场景：**
- 登录页面但 Vault 没有该账号
- CAPTCHA 验证码
- 年龄验证、Cookie 同意等
- 首次连接钱包或支付方式

**响应格式：**
```json
{
  "hil_required": true,
  "status": "credential_required",
  "action": "ask_human",
  "message": "No stored credentials found for Google. Please provide login credentials.",
  "data": {
    "auth_type": "social",
    "provider": "google",
    "url": "https://accounts.google.com/...",
    "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "screenshot": "/tmp/screenshot.png",
    "details": "Google OAuth login page detected",
    "instructions": "Please click the OAuth button or enter credentials manually"
  }
}
```

## 检测场景 (Detection Scenarios)

### 1. Login 登录检测
- 检测到用户名/密码输入框
- 检测到社交登录按钮（Google, Facebook, GitHub 等）
- 检测到 OAuth 授权页面

**HIL 流程：**
```
检测到登录页 → 查询 Vault
  ↓
有凭证 → request_authorization（请求授权使用）
  ↓
无凭证 → ask_human（请求用户提供）
```

### 2. CAPTCHA 验证码检测
- reCAPTCHA
- hCaptcha
- 图片验证码
- 滑块验证

**HIL 流程：**
```
检测到 CAPTCHA → ask_human（无法自动化，必须人工处理）
```

### 3. Payment 支付检测
- 信用卡输入框
- PayPal 授权
- Stripe 支付确认
- Apple Pay / Google Pay

**HIL 流程：**
```
检测到支付页 → 查询 Vault
  ↓
有支付方式 → request_authorization（请求授权支付）
  ↓
无支付方式 → ask_human（请求添加支付信息）
```

### 4. Wallet 钱包连接检测
- MetaMask 连接
- Coinbase Wallet
- WalletConnect
- Phantom（Solana）

**HIL 流程：**
```
检测到钱包连接 → 查询 Vault
  ↓
有钱包 → request_authorization（请求授权连接）
  ↓
无钱包 → ask_human（请求连接钱包）
```

### 5. Verification 验证检测
- 年龄验证
- Cookie 同意
- 地区确认
- 服务条款同意

**HIL 流程：**
```
检测到验证页 → ask_human（需要人工确认）
```

## 技术架构 (Technical Architecture)

### 工作流程
```
1. web_automation 工具被调用
   ↓
2. WebAutomationService.execute_task()
   ↓
3. 截图并进行 HIL 检测 (_check_hil_required)
   ↓
4a. 检测到需要 HIL → 返回 HIL 响应给 Agent
   ↓
4b. 无需 HIL → 继续 5 步原子工作流
```

### HIL 检测实现

**使用 Vision Model 检测页面类型：**
```python
detection_prompt = """Analyze this screenshot to detect if human intervention is needed.

Check for:
1. Login page (username/password fields, social login buttons)
2. CAPTCHA or verification challenge
3. Payment confirmation page (credit card, PayPal, etc.)
4. Wallet connection (MetaMask, Coinbase, etc.)
5. Cookie consent or age verification

Return JSON:
{
    "intervention_required": true/false,
    "intervention_type": "login|captcha|payment|wallet|verification|none",
    "provider": "google|facebook|metamask|stripe|etc",
    "details": "description of what's needed",
    "confidence": 0.9
}"""
```

### Vault 集成

**检查 Vault 中是否有凭证：**
```python
async def _check_vault_credentials(user_id, auth_type, provider):
    # Query Vault Service (port 8214)
    response = await client.get(
        f"{vault_service_url}/api/v1/vault/secrets",
        headers={"X-User-Id": user_id},
        params={"tags": f"{auth_type},{provider}"}
    )
    # Return first matching credential if found
```

## Agent 处理 HIL 响应 (Agent HIL Handling)

### Agent 接收到 HIL 响应后的处理

#### 1. 处理 `request_authorization`

Agent 应该：
1. 向用户展示凭证预览信息
2. 询问用户是否授权使用
3. 如果用户同意：
   - 从 Vault 获取完整凭证
   - 调用 web_automation 继续执行（传入凭证）
4. 如果用户拒绝：
   - 停止任务或请求新凭证

**示例对话：**
```
Agent: "我发现您的 Vault 中已经存储了 Google 账号凭证（vault_xxx）。
       需要我使用这个账号登录吗？"

User: "是的，使用它"

Agent: [从 Vault 获取凭证] → [继续 web_automation]
```

#### 2. 处理 `ask_human`

Agent 应该：
1. 根据场景类型提示用户
2. 等待用户操作或提供信息
3. 将用户提供的信息存储到 Vault（如适用）
4. 继续执行任务

**CAPTCHA 场景：**
```
Agent: "遇到 CAPTCHA 验证码，需要您手动解决。
       请在浏览器中完成验证后告诉我。"

User: "已完成"

Agent: [继续 web_automation]
```

**新登录场景：**
```
Agent: "检测到 Google 登录页面，但 Vault 中没有找到凭证。
       您可以：
       1. 点击 OAuth 授权按钮
       2. 手动输入账号密码"

User: [选择并完成登录]

Agent: "是否将这个凭证保存到 Vault 以便下次使用？"

User: "是的"

Agent: [保存到 Vault] → [继续任务]
```

## 与 Composio HIL 的对比

### 相似点
- 都是在工具响应中返回 HIL 动作
- 都使用 `action` 字段标识 HIL 类型
- Agent 负责处理 HIL 流程

### 不同点

| 特性 | Composio | Web Automation |
|------|----------|----------------|
| HIL 触发 | OAuth 授权 | 多场景（登录、支付、CAPTCHA、钱包） |
| 凭证存储 | Composio 后端 | Vault Service (本地) |
| 检测方式 | API 返回 | Vision Model 页面检测 |
| HIL 动作数 | 1 (ask_human) | 2 (request_authorization + ask_human) |
| 支持场景 | OAuth 第三方应用 | Web 页面自动化 |

### Composio OAuth 模式
```json
{
  "action": "ask_human",
  "data": {
    "oauth_url": "https://accounts.google.com/oauth...",
    "message": "Please authorize the app"
  }
}
```

### Web Automation 双动作模式
```json
// 场景1: Vault 有凭证
{
  "action": "request_authorization",
  "data": {
    "credential_preview": {...},
    "message": "Use stored credentials?"
  }
}

// 场景2: Vault 无凭证
{
  "action": "ask_human",
  "data": {
    "oauth_url": "...",
    "instructions": "Please provide credentials"
  }
}
```

## 使用示例 (Usage Examples)

### 示例 1: Google 登录（Vault 有凭证）

**MCP Tool 调用：**
```json
{
  "tool": "web_automation",
  "arguments": {
    "url": "https://accounts.google.com/signin",
    "task": "login to gmail",
    "user_id": "user123"
  }
}
```

**HIL 响应：**
```json
{
  "status": "authorization_required",
  "action": "request_authorization",
  "message": "Found stored credentials for Google. Do you authorize using them for login?",
  "data": {
    "auth_type": "social",
    "provider": "google",
    "credential_preview": {
      "vault_id": "vault_abc123",
      "stored_at": "2025-01-15T10:30:00Z"
    }
  }
}
```

**Agent 处理：**
```python
# 1. Agent 接收到 request_authorization
# 2. 询问用户是否授权
# 3. 用户同意 → 从 Vault 获取凭证
# 4. 重新调用 web_automation，传入凭证数据
```

### 示例 2: CAPTCHA 检测

**MCP Tool 调用：**
```json
{
  "tool": "web_automation",
  "arguments": {
    "url": "https://www.google.com/search?q=automation",
    "task": "search for automation",
    "user_id": "user123"
  }
}
```

**HIL 响应：**
```json
{
  "status": "human_required",
  "action": "ask_human",
  "message": "CAPTCHA detected. Please solve the CAPTCHA manually.",
  "data": {
    "intervention_type": "captcha",
    "screenshot": "/tmp/captcha_screenshot.png",
    "instructions": "Please solve the CAPTCHA and notify when complete"
  }
}
```

**Agent 处理：**
```python
# 1. Agent 接收到 ask_human
# 2. 提示用户解决 CAPTCHA
# 3. 等待用户完成
# 4. 重新调用 web_automation 继续任务
```

### 示例 3: MetaMask 连接（Vault 无钱包）

**MCP Tool 调用：**
```json
{
  "tool": "web_automation",
  "arguments": {
    "url": "https://app.uniswap.org",
    "task": "connect wallet",
    "user_id": "user123"
  }
}
```

**HIL 响应：**
```json
{
  "status": "credential_required",
  "action": "ask_human",
  "message": "No wallet found for metamask. Please connect your wallet.",
  "data": {
    "auth_type": "wallet",
    "provider": "metamask",
    "instructions": "Please connect your wallet via browser extension"
  }
}
```

**Agent 处理：**
```python
# 1. Agent 接收到 ask_human
# 2. 提示用户通过浏览器扩展连接钱包
# 3. 用户完成连接
# 4. Agent 询问是否保存钱包信息到 Vault
# 5. 继续任务
```

## 实现文件 (Implementation Files)

### 核心文件
- `tools/services/web_services/services/web_automation_service.py`
  - `_check_hil_required()`: HIL 检测主函数
  - `_handle_login_hil()`: 处理登录 HIL
  - `_handle_payment_hil()`: 处理支付 HIL
  - `_handle_wallet_hil()`: 处理钱包 HIL
  - `_check_vault_credentials()`: 查询 Vault

- `tools/services/web_services/web_tools.py`
  - `web_automation()`: MCP 工具定义
  - HIL 响应格式化

- `tools/services/web_services/web_auth_bridge.py`
  - Web 认证桥接（Vault 集成）
  - 认证类型定义

## 最佳实践 (Best Practices)

### 1. 安全性
- ✅ 凭证只存储在加密的 Vault Service
- ✅ 每次使用前都需要用户授权
- ✅ 凭证预览不包含敏感信息
- ✅ Agent 负责用户交互和授权决策

### 2. 用户体验
- ✅ 清晰的提示信息（中英文）
- ✅ 提供截图帮助用户理解上下文
- ✅ 明确的操作指引
- ✅ 支持保存凭证以便下次使用

### 3. 错误处理
- ✅ Vault 服务不可用时优雅降级
- ✅ Vision Model 检测失败时继续正常流程
- ✅ 用户拒绝授权时正确停止任务
- ✅ CAPTCHA 多次失败时提供替代方案

### 4. 性能优化
- ✅ HIL 检测在 Step 1 完成（避免浪费计算）
- ✅ Vault 查询使用索引（tags）
- ✅ Vision Model 使用 GPT-4V（快速准确）
- ✅ 异步 HTTP 请求（httpx）

## 未来增强 (Future Enhancements)

### 短期 (Short-term)
1. **智能 CAPTCHA 识别**
   - 集成 2Captcha 或类似服务
   - 自动解决简单验证码

2. **凭证过期检测**
   - 检测凭证是否仍然有效
   - 自动刷新 OAuth tokens

3. **多账号支持**
   - 允许用户选择使用哪个账号
   - 账号优先级和标签

### 中期 (Mid-term)
1. **生物识别支持**
   - Face ID / Touch ID 集成
   - 指纹验证

2. **会话管理**
   - Cookie 和 Session 持久化
   - 跨页面状态保持

3. **审计日志**
   - 记录所有 HIL 请求和用户响应
   - 合规性报告

### 长期 (Long-term)
1. **AI 辅助决策**
   - 基于历史记录预测用户选择
   - 自动化常见授权场景

2. **分布式 Vault**
   - 多设备凭证同步
   - 团队凭证共享

3. **高级钱包集成**
   - Hardware wallet 支持
   - Multi-sig 交易

## 总结 (Summary)

HIL for Web Automation 实现了智能的人机交互模式：

1. **双动作模式**: `request_authorization` 和 `ask_human` 覆盖所有场景
2. **智能检测**: Vision Model 自动识别需要 HIL 的场景
3. **Vault 集成**: 安全的凭证存储和管理
4. **Agent 协调**: Agent 处理所有用户交互逻辑
5. **可扩展**: 支持登录、支付、钱包、CAPTCHA 等多种场景

**关键原则**:
- ✅ Tool 只负责检测和返回 HIL 信号
- ✅ Agent 负责用户交互和决策
- ✅ Vault 负责凭证安全存储
- ✅ 用户始终保持控制权
