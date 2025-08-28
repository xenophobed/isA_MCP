# Event Service CORS 配置指南

## 概述

Event Service 现在已经配置了 CORS 支持，允许前端应用（如 `localhost:5173`）访问 API 端点。

## 配置详情

### 1. 默认允许的 Origins

```python
# 开发环境默认允许的 origins
DEFAULT_ORIGINS = [
    "http://localhost:5173",  # Vite 默认端口
    "http://localhost:3000",  # React 默认端口
    "http://127.0.0.1:5173", # 替代 localhost 格式
    "http://127.0.0.1:3000", # 替代 localhost 格式
]
```

### 2. 环境变量配置

你可以通过环境变量自定义 CORS 设置：

```bash
# 设置自定义 origins
export CORS_ORIGINS="http://localhost:5173,http://localhost:3000,http://custom.com"

# 设置环境
export ENV=production

# 启动服务
python event_server.py
```

### 3. 支持的 HTTP 方法

- GET
- POST
- PUT
- DELETE
- OPTIONS (预检请求)

### 4. 支持的 Headers

- 所有 headers (`allow_headers=["*"]`)
- 支持 credentials (`allow_credentials=True`)

## 使用方法

### 前端 JavaScript 示例

```javascript
// 从 localhost:5173 访问 Event Service
const eventServiceUrl = 'http://localhost:8101';

// 获取健康状态
async function checkHealth() {
    try {
        const response = await fetch(`${eventServiceUrl}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Event Service Health:', data);
        }
    } catch (error) {
        console.error('Error checking health:', error);
    }
}

// 获取最近事件
async function getRecentEvents() {
    try {
        const response = await fetch(`${eventServiceUrl}/events/recent?limit=5`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Recent Events:', data);
        }
    } catch (error) {
        console.error('Error getting events:', error);
    }
}

// 发送事件反馈
async function sendEventFeedback(eventData) {
    try {
        const response = await fetch(`${eventServiceUrl}/process_background_feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(eventData),
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Event processed:', result);
        }
    } catch (error) {
        console.error('Error sending event:', error);
    }
}
```

### 使用 fetch 的替代方案

```javascript
// 使用 axios
import axios from 'axios';

const eventService = axios.create({
    baseURL: 'http://localhost:8101',
    headers: {
        'Content-Type': 'application/json',
    },
});

// 获取健康状态
const health = await eventService.get('/health');

// 获取最近事件
const events = await eventService.get('/events/recent?limit=10');

// 发送事件
const result = await eventService.post('/process_background_feedback', eventData);
```

## 测试 CORS 配置

运行测试脚本来验证 CORS 配置：

```bash
cd tools/services/event_service
python test_cors.py
```

测试脚本会：
1. 测试预检请求 (OPTIONS)
2. 测试实际请求 (GET)
3. 验证有效和无效 origins 的处理
4. 检查 CORS 响应头

## 故障排除

### 常见问题

1. **CORS 错误仍然出现**
   - 确保 Event Service 已重启
   - 检查浏览器控制台的错误信息
   - 验证 origin 是否在允许列表中

2. **预检请求失败**
   - 检查 OPTIONS 请求是否返回正确的 CORS 头
   - 验证 `Access-Control-Allow-Origin` 头

3. **Credentials 问题**
   - 确保 `allow_credentials=True`
   - 前端不要设置 `credentials: 'include'`（除非需要）

### 调试步骤

1. 检查 Event Service 日志：
   ```bash
   tail -f logs/event_feedback.log
   ```

2. 检查浏览器网络面板：
   - 查看预检请求 (OPTIONS)
   - 检查响应头中的 CORS 信息

3. 使用 curl 测试：
   ```bash
   # 测试预检请求
   curl -X OPTIONS -H "Origin: http://localhost:5173" \
        -H "Access-Control-Request-Method: GET" \
        http://localhost:8101/health -v
   ```

## 生产环境配置

在生产环境中，建议：

1. 限制允许的 origins 到实际的前端域名
2. 使用 HTTPS
3. 设置适当的 CORS 策略
4. 监控 CORS 错误日志

```bash
# 生产环境配置
export ENV=production
export CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
```

## 相关文件

- `event_server.py` - 主服务器文件，包含 CORS 中间件
- `cors_config.py` - CORS 配置文件
- `test_cors.py` - CORS 测试脚本
- `CORS_SETUP.md` - 本文档
