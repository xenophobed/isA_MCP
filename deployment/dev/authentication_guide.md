# User Service 认证机制详解

## 🔐 认证架构概览

User Service 采用 **Auth0 + JWT** 的认证架构，前端无需直接管理用户密码和认证逻辑。

```
前端应用 → Auth0 登录 → 获取 JWT Token → 携带 Token 调用 API → User Service 验证 Token
```

## 🔄 完整认证流程

### 1. 前端登录流程

```typescript
// 用户点击登录按钮
const { loginWithRedirect } = useAuth0();

// 重定向到 Auth0 登录页面
loginWithRedirect({
  audience: 'https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/',
  scope: 'openid profile email read:users update:users create:users'
});

// Auth0 认证成功后，用户被重定向回前端应用
// 前端自动获取 access_token
const { getAccessTokenSilently } = useAuth0();
const token = await getAccessTokenSilently();
```

### 2. Token 获取和使用

```typescript
// 每次 API 调用时获取最新 token
const makeAuthenticatedRequest = async (url: string, options = {}) => {
  const token = await getAccessTokenSilently({
    audience: 'https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/',
    scope: 'read:users update:users create:users'
  });
  
  return fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
};
```

### 3. User Service 验证流程

当 API 请求到达 User Service 时：

```python
# 1. 从请求头提取 Bearer Token
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...

# 2. 验证 JWT Token
async def get_current_user(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials
    
    # 使用 Auth0 公钥验证 token 签名
    payload = await auth_service.verify_token(token)
    
    # 验证成功，返回用户信息
    return payload  # 包含 user_id, email, name 等
```

## 🔑 Token 验证机制

### JWT Token 结构

User Service 使用的 JWT Token 包含以下信息：

```json
{
  "iss": "https://dev-47zcqarlxizdkads.us.auth0.com/",
  "sub": "auth0|user_id_here",
  "aud": "https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/",
  "iat": 1625097600,
  "exp": 1625184000,
  "email": "user@example.com",
  "name": "User Name",
  "email_verified": true,
  "scope": "read:users update:users create:users"
}
```

### 验证步骤

1. **签名验证**：使用 Auth0 的公钥验证 JWT 签名
2. **时间验证**：检查 token 是否过期 (`exp` 字段)
3. **发行者验证**：确认 token 由正确的 Auth0 域名签发 (`iss` 字段)
4. **受众验证**：确认 token 的目标受众正确 (`aud` 字段)
5. **权限验证**：检查 token 包含必要的权限范围 (`scope` 字段)

## 🛡️ 安全机制

### 1. Token 自动刷新

```typescript
// Auth0 SDK 自动处理 token 刷新
const token = await getAccessTokenSilently();
// 如果 token 即将过期，SDK 会自动获取新的 token
```

### 2. CORS 保护

User Service 配置了严格的 CORS 策略：

```python
allow_origins = [
    "http://localhost:3000",  # 开发环境
    "https://www.iapro.ai"    # 生产环境
]
```

### 3. HTTPS 强制

生产环境中，所有 API 调用必须使用 HTTPS。

## 🔧 前端认证实现

### 完整的认证 Hook

```typescript
// hooks/useAuth.ts
export const useAuth = () => {
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    getAccessTokenSilently,
    loginWithRedirect,
    logout 
  } = useAuth0();

  const getAuthHeaders = async () => {
    if (!isAuthenticated) {
      throw new Error('User not authenticated');
    }
    
    const token = await getAccessTokenSilently({
      audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
      scope: 'read:users update:users create:users'
    });
    
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const makeAuthenticatedRequest = async (url: string, options = {}) => {
    const headers = await getAuthHeaders();
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...options.headers
      }
    });
    
    if (response.status === 401) {
      // Token 可能过期，尝试重新登录
      loginWithRedirect();
      return;
    }
    
    return response;
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    getAuthHeaders,
    makeAuthenticatedRequest,
    login: () => loginWithRedirect({
      audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
      scope: 'openid profile email read:users update:users create:users'
    }),
    logout: () => logout({ returnTo: window.location.origin })
  };
};
```

## 🔍 错误处理

### 常见认证错误

| 状态码 | 错误原因 | 前端处理方式 |
|--------|----------|-------------|
| 401 | Token 无效或过期 | 重新登录 |
| 403 | 权限不足 | 显示权限错误提示 |
| 422 | Token 格式错误 | 检查 token 获取逻辑 |

### 错误处理实现

```typescript
const handleAuthError = (error: any) => {
  if (error.status === 401) {
    // Token 过期或无效
    toast.error('登录已过期，请重新登录');
    loginWithRedirect();
  } else if (error.status === 403) {
    // 权限不足
    toast.error('您没有执行此操作的权限');
  } else {
    // 其他错误
    toast.error('认证服务暂时不可用，请稍后重试');
  }
};
```

## 📋 API 端点权限

### 公开端点（无需认证）
- `GET /health` - 健康检查
- `GET /api/v1/subscriptions/plans` - 获取订阅计划
- `POST /api/v1/webhooks/stripe` - Stripe Webhook

### 受保护端点（需要认证）
- `POST /api/v1/users/ensure` - 确保用户存在
- `GET /api/v1/users/me` - 获取当前用户信息
- `POST /api/v1/users/{user_id}/credits/consume` - 消费积分
- `POST /api/v1/subscriptions` - 创建订阅
- `POST /api/v1/payments/create-checkout` - 创建支付会话

## 🧪 测试认证

### 检查认证状态

```bash
# 使用有效 token 测试
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8100/api/v1/users/me

# 使用无效 token 测试（应返回 401）
curl -H "Authorization: Bearer invalid_token" \
     http://localhost:8100/api/v1/users/me
```

### 前端测试代码

```typescript
// 测试认证状态
const testAuth = async () => {
  try {
    const response = await makeAuthenticatedRequest(
      'http://localhost:8100/api/v1/users/me'
    );
    
    if (response.ok) {
      console.log('认证成功');
      const userInfo = await response.json();
      console.log('用户信息:', userInfo);
    }
  } catch (error) {
    console.error('认证失败:', error);
  }
};
```

## 🔗 相关配置

### Auth0 应用配置
- **Domain**: `dev-47zcqarlxizdkads.us.auth0.com`
- **Client ID**: `Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ`
- **Audience**: `https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/`

### 前端环境变量
```bash
NEXT_PUBLIC_AUTH0_DOMAIN=dev-47zcqarlxizdkads.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ
NEXT_PUBLIC_AUTH0_AUDIENCE=https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/
NEXT_PUBLIC_API_BASE_URL=http://localhost:8100
```

## 💡 最佳实践

1. **Token 缓存**：Auth0 SDK 自动处理 token 缓存，无需手动管理
2. **权限最小化**：只请求必要的权限范围
3. **错误处理**：优雅处理认证错误，提供用户友好的提示
4. **安全存储**：永远不要在本地存储敏感的认证信息
5. **HTTPS**：生产环境必须使用 HTTPS

---

**总结**：User Service 使用业界标准的 JWT + Auth0 认证方案，前端只需要正确配置 Auth0 SDK 并在 API 调用时携带 Bearer Token 即可。所有的 token 验证和用户管理都由后端服务自动处理。