# MCP 权限配置指南

## 权限配置的三种方式

### 1. 系统默认配置 (订阅级别)
通过数据库直接配置资源和对应的订阅级别要求：

```sql
-- 连接数据库
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

-- 添加新的资源配置
SET search_path TO dev;

INSERT INTO auth_permissions (
    permission_type, target_type, resource_type, resource_name,
    access_level, permission_source, subscription_tier_required,
    is_active, description
) VALUES (
    'resource_config', 'global', 'mcp_tool', 'new_tool',
    'read_write', 'system_default', 'pro',
    true, '新工具的描述'
);
```

**当前配置的资源层级**:
- **FREE** (免费): weather_api, store_knowledge, search_knowledge, basic_assistant 等
- **PRO** (专业): generate_rag_response, data_analytics_tools, image_generator 等  
- **ENTERPRISE** (企业): admin_manage_users, system_monitoring 等

### 2. 管理员手动授权
通过 API 给特定用户授予超出其订阅级别的权限：

```bash
# 授予权限
curl -X POST "http://localhost:8203/api/v1/authorization/grant" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resource_type": "mcp_tool",
  "resource_name": "generate_rag_response",
  "access_level": "read_write",
  "permission_source": "admin_grant",
  "granted_by": "admin_user",
  "expires_in_days": 30,
  "reason": "临时PRO功能访问"
}'
```

```bash
# 撤销权限  
curl -X POST "http://localhost:8203/api/v1/authorization/revoke" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resource_type": "mcp_tool", 
  "resource_name": "generate_rag_response",
  "revoked_by": "admin_user",
  "reason": "权限到期"
}'
```

### 3. 批量权限操作
一次性授予/撤销多个权限：

```bash
# 批量授权
curl -X POST "http://localhost:8203/api/v1/authorization/bulk-grant" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "permissions": [
    {
      "resource_type": "mcp_tool",
      "resource_name": "image_generator", 
      "access_level": "read_write"
    },
    {
      "resource_type": "prompt",
      "resource_name": "business_analysis_prompt",
      "access_level": "read_only"
    }
  ],
  "granted_by": "admin_user",
  "expires_in_days": 7,
  "reason": "临时试用期"
}'
```

## 权限查询

### 查看用户权限
```bash
# 查看用户所有权限
curl "http://localhost:8203/api/v1/authorization/user-permissions/test_user_2"

# 查看用户可访问的资源
curl "http://localhost:8203/api/v1/authorization/user-resources/test_user_2"
```

### 检查特定权限
```bash
curl -X POST "http://localhost:8203/api/v1/authorization/check-access" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resource_type": "mcp_tool",
  "resource_name": "weather_api", 
  "required_access_level": "read_only"
}'
```

## 权限优先级

权限检查按以下优先级顺序：

1. **管理员授予的权限** (最高优先级) - `admin_grant`
2. **组织权限** - `organization`  
3. **订阅级别权限** - `subscription`
4. **用户特定权限** - `user_specific`
5. **拒绝访问** (默认)

## 资源类型

支持的资源类型：
- `mcp_tool` - MCP 工具
- `prompt` - 提示词
- `resource` - 资源 
- `api_endpoint` - API 端点
- `database` - 数据库
- `file_storage` - 文件存储
- `compute` - 计算资源
- `ai_model` - AI 模型

## 访问级别

- `none` - 无权限
- `read_only` - 只读
- `read_write` - 读写
- `admin` - 管理员
- `owner` - 所有者

## 订阅级别

- `free` - 免费
- `pro` - 专业版
- `enterprise` - 企业版
- `custom` - 定制版

## 实际使用示例

### 在 MCP 服务中集成权限检查

```python
from core.auth.mcp_auth_service import MCPAuthService, ResourceType, AccessLevel

# 初始化服务
auth_service = MCPAuthService({
    'authz_service_url': 'http://localhost:8203'
})

# 检查权限
async def check_tool_access(user_context, tool_name):
    result = await auth_service.check_resource_access(
        user_context,
        ResourceType.MCP_TOOL,
        tool_name,
        AccessLevel.READ_WRITE
    )
    
    if not result.get('has_access'):
        raise PermissionDenied(f"Access denied: {result.get('reason')}")
```

### 权限配置最佳实践

1. **默认最小权限原则** - 新资源默认需要最高订阅级别
2. **临时权限使用过期时间** - 管理员授权建议设置过期时间
3. **定期清理过期权限** - 使用 `/cleanup-expired` 端点
4. **权限变更审计** - 记录所有权限变更的操作者和原因
5. **批量操作提高效率** - 大量权限变更使用批量 API

## 数据库直接操作 (高级)

```sql
-- 查看所有资源配置
SELECT resource_type, resource_name, access_level, subscription_tier_required 
FROM dev.auth_permissions 
WHERE permission_type = 'resource_config'
ORDER BY subscription_tier_required, resource_type;

-- 查看用户权限
SELECT * FROM dev.auth_permissions 
WHERE permission_type = 'user_permission' AND target_id = 'user_id';

-- 清理过期权限
DELETE FROM dev.auth_permissions 
WHERE expires_at IS NOT NULL AND expires_at < NOW();
```