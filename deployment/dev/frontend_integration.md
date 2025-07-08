# Next.js 前端集成指南

## User Service API 集成

基于你已配置好的 Auth0 和 Stripe 后端服务，本指南将帮助你在 Next.js 前端中完成集成。

### 基础配置

#### 步骤 1: 安装必要依赖

```bash
# 安装 Auth0 React SDK
npm install @auth0/auth0-react

# 安装 Stripe (可选，用于支付页面)
npm install @stripe/stripe-js
```

#### 步骤 2: 配置 API 工具类

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8100';

export const userServiceAPI = {
  baseURL: `${API_BASE_URL}/api/v1`,
  
  // 获取认证 token 的方法
  async getAuthHeaders(getAccessTokenSilently: any) {
    try {
      const token = await getAccessTokenSilently({
        audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
        scope: 'read:users update:users create:users'
      });
      
      return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
    } catch (error) {
      console.error('Failed to get token:', error);
      throw error;
    }
  }
};
```

### 主要 API 端点

#### 步骤 3: 配置 Auth0 Provider

```typescript
// pages/_app.tsx 或 app/layout.tsx
import { Auth0Provider } from '@auth0/auth0-react';

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <Auth0Provider
      domain={process.env.NEXT_PUBLIC_AUTH0_DOMAIN!}
      clientId={process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID!}
      authorizationParams={{
        redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
        audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
        scope: 'openid profile email read:users update:users create:users'
      }}
    >
      <Component {...pageProps} />
    </Auth0Provider>
  );
}
```

#### 步骤 4: 用户管理 API

```typescript
// lib/userService.ts
import { userServiceAPI } from './api';

// 确保用户存在
export const ensureUserExists = async (userData: {email: string, name: string}, getAccessTokenSilently: any) => {
  const headers = await userServiceAPI.getAuthHeaders(getAccessTokenSilently);
  
  const response = await fetch(`${userServiceAPI.baseURL}/users/ensure`, {
    method: 'POST',
    headers,
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
};

// 获取当前用户信息
export const getCurrentUser = async (getAccessTokenSilently: any) => {
  const headers = await userServiceAPI.getAuthHeaders(getAccessTokenSilently);
  
  const response = await fetch(`${userServiceAPI.baseURL}/users/me`, {
    method: 'GET',
    headers
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
};

// 消费积分
export const consumeCredits = async (userId: number, amount: number, reason: string, getAccessTokenSilently: any) => {
  const headers = await userServiceAPI.getAuthHeaders(getAccessTokenSilently);
  
  const response = await fetch(`${userServiceAPI.baseURL}/users/${userId}/credits/consume`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ amount, reason })
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
};
```

#### 步骤 5: 订阅管理 API

```typescript
// 获取订阅计划
export const getSubscriptionPlans = async () => {
  const response = await fetch(`${userServiceAPI.baseURL}/subscriptions/plans`);
  return response.json();
};

// 创建 Stripe Checkout 会话
export const createCheckoutSession = async (planType: string, getAccessTokenSilently: any) => {
  const headers = await userServiceAPI.getAuthHeaders(getAccessTokenSilently);
  
  const response = await fetch(`${userServiceAPI.baseURL}/payments/create-checkout`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      plan_type: planType,
      success_url: `${window.location.origin}/subscription/success`,
      cancel_url: `${window.location.origin}/subscription/cancel`
    })
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
};
```

#### 3. 用户分析

```typescript
// 获取用户分析数据
export const getUserAnalytics = async (userId: number) => {
  const headers = await userServiceAPI.getAuthHeaders();
  
  const response = await fetch(`${userServiceAPI.baseURL}/users/${userId}/analytics`, {
    method: 'GET',
    headers
  });
  
  return response.json();
};
```

#### 步骤 6: 创建自定义 Hook

```typescript
// hooks/useUserService.ts
import { useAuth0 } from '@auth0/auth0-react';
import { useState, useEffect } from 'react';
import { ensureUserExists, getCurrentUser, consumeCredits, getSubscriptionPlans, createCheckoutSession } from '../lib/userService';

export const useUserService = () => {
  const { user, isAuthenticated, getAccessTokenSilently } = useAuth0();
  const [userInfo, setUserInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated && user) {
      initializeUser();
    }
  }, [isAuthenticated, user]);

  const initializeUser = async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (!user?.email || !user?.name) {
        throw new Error('User email or name is missing');
      }
      
      // 确保用户存在
      await ensureUserExists({
        email: user.email,
        name: user.name
      }, getAccessTokenSilently);
      
      // 获取用户完整信息
      const userResponse = await getCurrentUser(getAccessTokenSilently);
      setUserInfo(userResponse);
      
    } catch (err: any) {
      console.error('Failed to initialize user:', err);
      setError(err.message || 'Failed to initialize user');
    } finally {
      setLoading(false);
    }
  };
  
  const handleConsumeCredits = async (userId: number, amount: number, reason: string) => {
    try {
      return await consumeCredits(userId, amount, reason, getAccessTokenSilently);
    } catch (err: any) {
      console.error('Failed to consume credits:', err);
      throw err;
    }
  };
  
  const handleCreateCheckout = async (planType: string) => {
    try {
      const session = await createCheckoutSession(planType, getAccessTokenSilently);
      // 重定向到 Stripe Checkout
      if (session.url) {
        window.location.href = session.url;
      }
      return session;
    } catch (err: any) {
      console.error('Failed to create checkout session:', err);
      throw err;
    }
  };

  return {
    userInfo,
    loading,
    error,
    initializeUser,
    consumeCredits: handleConsumeCredits,
    createCheckoutSession: handleCreateCheckout,
    getSubscriptionPlans: () => getSubscriptionPlans(),
    refreshUser: () => initializeUser()
  };
};
```

#### 步骤 7: 环境变量配置

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8100
NEXT_PUBLIC_AUTH0_DOMAIN=dev-47zcqarlxizdkads.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ
NEXT_PUBLIC_AUTH0_AUDIENCE=https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/
```

#### 步骤 8: 使用示例

```typescript
// pages/dashboard.tsx 或 app/dashboard/page.tsx
import { useAuth0 } from '@auth0/auth0-react';
import { useUserService } from '../hooks/useUserService';
import { useEffect } from 'react';

export default function Dashboard() {
  const { isAuthenticated, loginWithRedirect, logout } = useAuth0();
  const { userInfo, loading, error, consumeCredits, createCheckoutSession } = useUserService();
  
  if (!isAuthenticated) {
    return (
      <button onClick={() => loginWithRedirect()}>
        登录
      </button>
    );
  }
  
  if (loading) return <div>加载中...</div>;
  if (error) return <div>错误: {error}</div>;
  
  return (
    <div>
      <h1>欢迎, {userInfo?.name}</h1>
      <p>剩余积分: {userInfo?.credits}</p>
      <p>订阅状态: {userInfo?.subscription_status}</p>
      
      <button 
        onClick={() => consumeCredits(userInfo.id, 10, 'API 调用')}
      >
        消费 10 积分
      </button>
      
      <button 
        onClick={() => createCheckoutSession('pro')}
      >
        升级到 Pro
      </button>
      
      <button onClick={() => logout({ returnTo: window.location.origin })}>
        登出
      </button>
    </div>
  );
}
```

### 错误处理

```typescript
// utils/errorHandler.ts
export const handleAPIError = (error: any) => {
  if (error.status === 401) {
    // 重定向到登录
    window.location.href = '/login';
  } else if (error.status === 403) {
    // 显示权限错误
    console.error('Access denied');
  } else if (error.status >= 500) {
    // 显示服务器错误
    console.error('Server error:', error.message);
  }
  
  return error;
};
```

## 启动开发环境

1. 启动后端服务：
```bash
./deployment/scripts/start_dev.sh
```

2. 启动前端：
```bash
cd frontend
npm run dev
```

3. 验证集成：
- 前端: http://localhost:3000
- User Service API: http://localhost:8100/docs
- Health Check: http://localhost:8100/health

## Webhook 配置

对于生产环境，需要在 Stripe Dashboard 中配置 Webhook：

- URL: https://your-domain.com/api/v1/webhooks/stripe
- Events: 
  - checkout.session.completed
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.payment_succeeded
  - invoice.payment_failed