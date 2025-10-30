# Composio Integration Guide for MCP

## 概述 (Overview)

Composio 是一个提供 745+ 应用集成的平台，通过我们的 MCP 系统，你可以轻松连接和操作 Gmail、Slack、GitHub、Notion 等数百个应用。每个用户都有独立的应用连接，确保数据隔离和安全。

## 快速开始 (Quick Start)

### 1. 环境配置

确保在 `deployment/dev/.env` 中配置了 Composio API Key：

```bash
# External Services Configuration
COMPOSIO_API_KEY="your-composio-api-key"
```

### 2. 验证集成状态

```python
import asyncio
from tools.mcp_client import MCPClient

async def check_composio():
    client = MCPClient()
    
    # 获取所有可用工具
    capabilities = await client.get_capabilities()
    tools = capabilities.get('capabilities', {}).get('tools', {}).get('available', [])
    
    # 筛选 Composio 工具
    composio_tools = [t for t in tools if 'composio' in t.lower()]
    print(f"找到 {len(composio_tools)} 个 Composio 工具")
    
    for tool in composio_tools:
        print(f"  - {tool}")

asyncio.run(check_composio())
```

## 核心功能 (Core Features)

### 可用的 Composio 工具

当前系统中注册了 13 个 Composio 工具：

#### 管理工具 (Management Tools)
1. **composio_connect_app** - 连接用户账户到应用
2. **composio_list_user_connections** - 列出用户已连接的应用
3. **composio_list_available_apps** - 显示所有可用的 745+ 应用

#### 应用集成工具 (App Integration Tools)
- **Gmail**: `composio_gmail_send_message`, `composio_gmail_get_data`
- **Slack**: `composio_slack_send_message`, `composio_slack_get_data`
- **GitHub**: `composio_github_send_message`, `composio_github_get_data`
- **Notion**: `composio_notion_send_message`, `composio_notion_get_data`
- **Google Calendar**: `composio_googlecalendar_send_message`, `composio_googlecalendar_get_data`

## 使用示例 (Usage Examples)

### 1. 列出所有可用应用

```python
import asyncio
from tools.mcp_client import MCPClient

async def list_apps():
    client = MCPClient()
    result = await client.call_tool_and_parse('composio_list_available_apps', {})
    
    if result.get('status') == 'success':
        print(f"总共有 {result.get('total_apps')} 个可用应用")
        
        categories = result.get('categories', {})
        for category, apps in categories.items():
            if apps:
                print(f"\n{category.upper()} ({len(apps)} apps):")
                for app in apps[:5]:  # 显示前5个
                    print(f"  - {app}")

asyncio.run(list_apps())
```

**实际输出示例：**
```
总共有 745 个可用应用

COMMUNICATION (5 apps):
  - gmail
  - slack
  - slackbot
  - discord
  - telegram

PRODUCTIVITY (4 apps):
  - googlecalendar
  - notion
  - asana
  - trello

DEVELOPMENT (2 apps):
  - github
  - jira

CRM (2 apps):
  - hubspot
  - salesforce
```

### 2. 连接用户账户到应用 (真正的OAuth流程)

```python
async def connect_app_oauth(app_name: str, user_id: str = "default"):
    client = MCPClient()
    
    # 发起OAuth连接 - 返回真正的授权URL
    result = await client.call_tool_and_parse(
        'composio_connect_app',
        {
            'app_name': app_name,
            'user_id': user_id
        }
    )
    
    if result.get('status') == 'oauth_required':
        oauth_url = result.get('oauth_url')
        request_id = result.get('connection_request_id')
        
        print(f"🔗 {app_name} OAuth授权URL:")
        print(f"   {oauth_url}")
        print(f"📋 授权步骤:")
        print(f"   1. 复制上面的URL并在浏览器中打开")
        print(f"   2. 使用你的{app_name}账户登录并授权")
        print(f"   3. 授权完成后即可使用{app_name}工具")
        print(f"🆔 请求ID: {request_id}")
        
        return {
            "oauth_url": oauth_url,
            "request_id": request_id,
            "instructions": result.get("instructions")
        }
    else:
        print(f"❌ OAuth启动失败: {result}")
        return None

# 示例：为用户连接 Gmail
asyncio.run(connect_app_oauth('gmail'))
```

**实际运行结果示例:**
```
🔗 gmail OAuth授权URL:
   https://backend.composio.dev/api/v3/s/99eNGaTI
📋 授权步骤:
   1. 复制上面的URL并在浏览器中打开
   2. 使用你的gmail账户登录并授权
   3. 授权完成后即可使用gmail工具
🆔 请求ID: ca_BzrLTnllhttd
```

### 3. 查看用户已连接的应用

```python
async def check_connections(user_id: str):
    client = MCPClient()
    
    result = await client.call_tool_and_parse(
        'composio_list_user_connections',
        {'user_id': user_id}
    )
    
    if result.get('status') == 'success':
        count = result.get('count', 0)
        print(f"用户 {user_id} 已连接 {count} 个应用")
        
        for app in result.get('connected_apps', []):
            print(f"  - {app}")
    else:
        print(f"查询失败: {result.get('message')}")

asyncio.run(check_connections('user123'))
```

### 4. 使用已连接的应用

#### 发送 Gmail 邮件

```python
async def send_gmail(user_id: str):
    client = MCPClient()
    
    # 首先确保用户已连接 Gmail
    # 然后发送邮件
    result = await client.call_tool_and_parse(
        'composio_gmail_send_message',
        {
            'parameters': {
                'to': 'recipient@example.com',
                'subject': 'Hello from MCP + Composio',
                'body': 'This email was sent via Composio integration!'
            },
            'user_id': user_id
        }
    )
    
    if result.get('status') == 'success':
        print("✅ 邮件发送成功")
    else:
        print(f"❌ 发送失败: {result.get('message')}")
        if "has not connected" in result.get('message', ''):
            print("提示：用户需要先连接 Gmail 账户")

asyncio.run(send_gmail('user123'))
```

#### 发送 Slack 消息

```python
async def send_slack_message(user_id: str, channel: str, message: str):
    client = MCPClient()
    
    result = await client.call_tool_and_parse(
        'composio_slack_send_message',
        {
            'parameters': {
                'channel': channel,
                'text': message
            },
            'user_id': user_id
        }
    )
    
    return result

# 示例
asyncio.run(send_slack_message(
    'user123',
    '#general',
    'Hello from MCP + Composio!'
))
```

### 5. 完整的OAuth工作流程示例

```python
async def complete_oauth_workflow():
    """演示完整的Composio OAuth集成工作流程"""
    client = MCPClient()
    
    print("🚀 Composio OAuth 完整工作流程演示")
    print("=" * 50)
    
    # 步骤 1: 查看所有可用应用
    print("\n📋 步骤 1: 查看可用应用")
    apps_result = await client.call_tool_and_parse('composio_list_available_apps')
    if apps_result.get('status') == 'success':
        print(f"   ✅ 总共有 {apps_result.get('total_apps')} 个可用应用")
        categories = apps_result.get('categories', {})
        for category, apps in list(categories.items())[:3]:  # 显示前3个分类
            print(f"   - {category}: {', '.join(apps[:3])}...")
    
    # 步骤 2: 发起Gmail OAuth连接
    print("\n🔗 步骤 2: 发起Gmail OAuth连接")
    oauth_result = await client.call_tool_and_parse(
        'composio_connect_app', 
        {'app_name': 'gmail'}
    )
    
    if oauth_result.get('status') == 'oauth_required':
        oauth_url = oauth_result.get('oauth_url')
        print(f"   ✅ OAuth URL生成成功: {oauth_url}")
        print(f"   📝 请求ID: {oauth_result.get('connection_request_id')}")
        print(f"   🌐 请在浏览器中打开OAuth URL完成授权")
    else:
        print(f"   ❌ OAuth启动失败: {oauth_result}")
        return
    
    # 步骤 3: 等待用户完成授权（实际使用中可能需要轮询或回调）
    print("\n⏳ 步骤 3: 等待用户完成浏览器授权...")
    print("   (在真实应用中，这里可以通过回调URL或轮询检查授权状态)")
    
    # 步骤 4: 检查连接状态
    print("\n🔍 步骤 4: 检查用户连接状态")
    connections = await client.call_tool_and_parse('composio_list_user_connections')
    if connections.get('status') == 'success':
        count = connections.get('count', 0)
        connected_apps = connections.get('connected_apps', [])
        print(f"   ✅ 用户已连接 {count} 个应用")
        if connected_apps:
            print(f"   📱 已连接应用: {', '.join(connected_apps)}")
    
    # 步骤 5: 尝试使用Gmail工具（如果已授权）
    print("\n📧 步骤 5: 尝试发送测试邮件")
    if 'gmail' in connections.get('connected_apps', []):
        email_result = await client.call_tool_and_parse(
            'composio_gmail_send_message',
            {
                'parameters': {
                    'to': 'test@example.com',
                    'subject': 'Test from Composio OAuth',
                    'body': 'This email was sent successfully via Composio OAuth integration!'
                }
            }
        )
        print(f"   ✅ 邮件发送结果: {email_result.get('status')}")
    else:
        print("   ⚠️  Gmail未授权，无法发送邮件")
        print("   💡 请完成步骤2中的OAuth授权")
    
    print("\n🎉 OAuth工作流程演示完成！")

# 运行完整工作流程
asyncio.run(complete_oauth_workflow())
```

## 多租户支持 (Multi-Tenant Support)

每个用户都有独立的应用连接，确保数据隔离：

```python
# 用户 A 连接自己的 Gmail
await connect_app('gmail', 'userA')

# 用户 B 连接自己的 Gmail
await connect_app('gmail', 'userB')

# 用户 A 发送邮件（使用自己的 Gmail 账户）
await send_gmail('userA')

# 用户 B 发送邮件（使用自己的 Gmail 账户）
await send_gmail('userB')
```

## 支持的应用分类 (Supported App Categories)

基于实际测试，745 个应用分为以下几类：

1. **通信类 (Communication)**
   - Gmail, Slack, Discord, Telegram, Microsoft Teams

2. **生产力工具 (Productivity)**
   - Notion, Asana, Trello, Google Calendar, Todoist

3. **开发工具 (Development)**
   - GitHub, GitLab, Jira, Linear, Bitbucket

4. **CRM 系统 (CRM)**
   - HubSpot, Salesforce, Pipedrive, Zoho CRM

5. **其他 (Other)**
   - Google Sheets, Supabase, Dropbox, Google Drive, 等等

## 故障排除 (Troubleshooting)

### 1. Composio 工具未出现在能力列表中

**问题表现：**
- 工具可以调用但不在 capabilities 列表中显示

**解决方案：**
- 确保在 `composio_mcp_bridge.py` 中正确注册工具
- 重启 MCP 服务：`~/Documents/Fun/isA_Cloud/scripts/service_manager.sh restart mcp`

### 2. API Key 未配置

**错误信息：**
```
WARNING  Composio API key not set, skipping bridge registration
```

**解决方案：**
在 `deployment/dev/.env` 中添加：
```bash
COMPOSIO_API_KEY="your-api-key"
```

### 3. 用户未连接应用 (需要OAuth授权)

**错误信息：**
```json
{
  "status": "authorization_requested",
  "action": "ask_human",
  "message": "To use Gmail for send_message, you need to authorize access. Would you like to connect your Gmail account?"
}
```

**解决方案：**
1. 调用 `composio_connect_app` 获取OAuth URL
2. 用户在浏览器中完成授权
3. 验证连接状态后重试操作

**示例修复流程：**
```python
# 1. 检测到需要授权
if result.get('status') == 'authorization_requested':
    # 2. 发起OAuth流程
    oauth_result = await client.call_tool_and_parse(
        'composio_connect_app', 
        {'app_name': 'gmail'}
    )
    # 3. 引导用户完成授权
    print(f"请访问: {oauth_result.get('oauth_url')}")
```

### 4. OAuth授权URL无法生成

**错误信息：**
```json
{
  "status": "error",
  "message": "No auth config found for gmail. Please configure OAuth credentials in Composio dashboard first."
}
```

**解决方案：**
- 确保在Composio控制台中已配置该应用的OAuth凭据
- 检查应用名称是否正确（小写，如 'gmail' 不是 'Gmail'）
- 验证COMPOSIO_API_KEY是否有效

## 技术架构 (Technical Architecture)

### 文件结构

```
tools/external_services/composio_service/
├── __init__.py
├── composio_connector.py      # Composio 服务连接器
└── composio_mcp_bridge.py     # MCP 工具桥接器

core/
├── auto_discovery.py          # 自动发现和注册
└── external_discovery.py      # 外部服务发现

config/external_services/
└── external_services.yaml     # 外部服务配置
```

### 工作流程

1. **服务初始化**
   - MCP 服务器启动时加载 Composio 配置
   - 检查 API Key 并连接 Composio 服务

2. **工具注册**
   - `composio_mcp_bridge.py` 动态创建 MCP 工具
   - 注册管理工具和应用工具

3. **用户连接应用 (真正的OAuth流程)**
   - 用户调用 `composio_connect_app`
   - 系统通过 `composio_client.connected_accounts.initiate()` 发起OAuth
   - 返回真正的Composio OAuth URL (例如: `https://backend.composio.dev/api/v3/s/xxxx`)
   - 用户在浏览器中访问OAuth URL并完成授权
   - Composio后台处理授权并建立连接
   - 连接状态可通过 `composio_list_user_connections` 查询

4. **执行应用操作**
   - 用户调用应用工具（如 `composio_gmail_send_message`）
   - 桥接器验证用户连接
   - 通过 Composio API 执行操作
   - 返回结果给用户

## 最佳实践 (Best Practices)

1. **总是先检查连接状态**
   ```python
   # 在执行操作前检查用户是否已连接应用
   connections = await check_connections(user_id)
   if 'gmail' not in connections:
       await connect_app('gmail', user_id)
   ```

2. **使用唯一的用户 ID**
   ```python
   # 使用数据库中的用户 ID 或 UUID
   user_id = f"user_{user.id}"  # 不要使用 "default"
   ```

3. **处理错误情况**
   ```python
   result = await client.call_tool_and_parse(tool_name, params)
   
   if result.get('status') == 'error':
       if "has not connected" in result.get('message', ''):
           # 引导用户连接应用
           pass
       elif "rate limit" in result.get('message', ''):
           # 处理速率限制
           pass
       else:
           # 其他错误
           pass
   ```

4. **批量操作优化**
   ```python
   # 对于批量操作，考虑使用异步并发
   async def send_bulk_emails(user_id: str, emails: list):
       tasks = []
       for email in emails:
           task = send_gmail(user_id, email)
           tasks.append(task)
       
       results = await asyncio.gather(*tasks)
       return results
   ```

## 安全考虑 (Security Considerations)

1. **API Key 安全**
   - 永远不要在代码中硬编码 API Key
   - 使用环境变量存储敏感信息
   - 定期轮换 API Key

2. **用户数据隔离**
   - 每个用户只能访问自己连接的应用
   - 使用唯一的 user_id 确保数据隔离
   - 不要使用共享的 "default" 用户

3. **权限验证**
   - 所有 Composio 工具都有安全级别设置
   - 管理工具：`SecurityLevel.LOW`
   - 发送消息工具：`SecurityLevel.MEDIUM`
   - 确保用户有适当的权限

## 未来扩展 (Future Enhancements)

1. **更多应用支持**
   - 当前只注册了 5 个优先应用
   - 可以根据需求添加更多应用工具

2. **WebHook 支持**
   - 接收应用事件通知
   - 实时同步数据

3. **批量操作工具**
   - 批量发送邮件
   - 批量创建任务
   - 数据同步工具

4. **智能工作流**
   - 跨应用自动化工作流
   - 条件触发器
   - 定时任务

## 相关文档

- [MCP 使用指南](./how_to_mcp.md)
- [外部服务配置](../config/external_services/external_services.yaml)
- [Composio 官方文档](https://docs.composio.dev)

## 总结

Composio 集成为 MCP 系统带来了 745+ 应用的**真正OAuth连接**能力。通过完善的OAuth工作流程，用户可以：

- ✅ **真正的OAuth授权**: 获得浏览器OAuth URL，完成安全授权
- ✅ **745个应用支持**: Gmail, Slack, GitHub, Notion等数百个应用
- ✅ **多租户隔离**: 每个用户独立管理自己的应用连接
- ✅ **统一MCP接口**: 通过标准MCP工具调用所有功能
- ✅ **安全连接管理**: 所有token由Composio安全管理

### 🎯 OAuth工作流程成果：

**调用示例：**
```python
# 发起OAuth连接
result = await client.call_tool_and_parse('composio_connect_app', {'app_name': 'gmail'})

# 返回真正的OAuth URL
{
  "status": "oauth_required",
  "oauth_url": "https://backend.composio.dev/api/v3/s/99eNGaTI", 
  "connection_request_id": "ca_BzrLTnllhttd",
  "message": "Please authorize gmail by visiting the OAuth URL"
}
```

**技术实现：**
- 使用 `composio_client.connected_accounts.initiate()` 发起真正OAuth
- 返回Composio官方授权URL
- 支持多应用并发授权
- MCP Bridge正确处理OAuth响应格式

集成状态：**完全可用 + 真正OAuth支持** 🎉✅

**验证测试结果 (2025-09-29):**
- ✅ Gmail OAuth: `https://backend.composio.dev/api/v3/s/99eNGaTI`
- ✅ GitHub OAuth: `https://backend.composio.dev/api/v3/s/shm3M-Kq`
- ✅ Slack OAuth: `https://backend.composio.dev/api/v3/s/ODGDHkiO`