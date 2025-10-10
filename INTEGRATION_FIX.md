# Session Service 与 Memory Service 集成修复方案

## 问题根源

Memory Service 直接使用 `session_id` 创建 session memories，但没有确保这个 session 在 Session Service 中存在。

## 解决方案

### 方案1: Memory Service 调用 Session Service (推荐)

在 `tools/services/memory_service/memory_service.py` 中添加 Session Service 集成：

```python
import requests
from core.consul_registry import ConsulRegistry

class MemoryService:
    def __init__(self):
        # ... 现有代码 ...
        
        # 添加 Consul registry 用于服务发现
        self.consul_registry = ConsulRegistry(
            service_name="memory_service",
            service_port=8080,  # MCP服务端口
            consul_host="localhost",
            consul_port=8500
        )
    
    async def store_session_message(
        self,
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user",
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store session message with Session Service integration"""
        
        # 1. 确保 session 在 Session Service 中存在
        session_exists = await self._ensure_session_exists(user_id, session_id)
        
        if not session_exists:
            logger.warning(f"Session {session_id} does not exist, creating it")
            await self._create_session_in_service(user_id, session_id)
        
        # 2. 存储 session memory
        engine = self.engines[MemoryType.SESSION]
        return await engine.store_session_memory(
            user_id, session_id, message_content, message_count=1
        )
    
    async def _ensure_session_exists(self, user_id: str, session_id: str) -> bool:
        """Check if session exists in Session Service"""
        try:
            # 通过 Consul 发现 Session Service
            session_service_url = self.consul_registry.get_service_address(
                "session_service",
                fallback_url="http://localhost:8205"
            )
            
            # 查询 session 是否存在
            response = requests.get(
                f"{session_service_url}/api/v1/sessions/{session_id}",
                params={"user_id": user_id},
                timeout=2
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Cannot verify session existence: {e}")
            return False  # Assume session doesn't exist
    
    async def _create_session_in_service(self, user_id: str, session_id: str) -> bool:
        """Create session in Session Service"""
        try:
            session_service_url = self.consul_registry.get_service_address(
                "session_service",
                fallback_url="http://localhost:8205"
            )
            
            # 创建 session
            response = requests.post(
                f"{session_service_url}/api/v1/sessions",
                json={
                    "user_id": user_id,
                    "conversation_data": {},
                    "metadata": {"source": "memory_service"}
                },
                timeout=2
            )
            
            if response.status_code == 201:
                logger.info(f"✅ Created session {session_id} in Session Service")
                return True
            else:
                logger.error(f"❌ Failed to create session: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating session: {e}")
            return False
```

### 方案2: 使用统一的Session ID生成规则

在 `core/user_id_utils.py` 中添加统一的 session_id 生成器：

```python
import uuid
from datetime import datetime

class SessionIdGenerator:
    """统一的 Session ID 生成器"""
    
    @staticmethod
    def generate_session_id() -> str:
        """生成 UUID 格式的 session ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_user_session_id(user_id: str) -> str:
        """为特定用户生成 session ID (带用户前缀，便于调试)"""
        # 生成格式: user_prefix_uuid
        # 例如: user_abc123_550e8400-e29b-41d4-a716-446655440000
        return f"{user_id[:12]}_{uuid.uuid4()}"
    
    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        """验证 session ID 格式"""
        try:
            # 尝试解析为 UUID
            uuid.UUID(session_id)
            return True
        except ValueError:
            # 如果不是 UUID，检查是否是带前缀的格式
            parts = session_id.split('_')
            if len(parts) >= 2:
                try:
                    uuid.UUID(parts[-1])
                    return True
                except ValueError:
                    pass
            return False
```

### 方案3: 在主服务入口处统一管理

在 `main.py` 的 chat endpoint 中统一处理：

```python
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Chat endpoint with session management"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        message = data.get("message")
        
        # 1. 验证并规范化 user_id
        if not UserIdValidator.is_uuid(user_id):
            # 如果不是 UUID，尝试转换
            user_id = await convert_to_uuid_user_id(user_id)
        
        # 2. 验证并规范化 session_id
        if not SessionIdGenerator.is_valid_session_id(session_id):
            # 生成新的 UUID session_id
            new_session_id = SessionIdGenerator.generate_session_id()
            logger.warning(f"Invalid session_id {session_id}, generated new one: {new_session_id}")
            session_id = new_session_id
        
        # 3. 确保 session 在 Session Service 中存在
        await ensure_session_exists(user_id, session_id)
        
        # 4. 处理消息
        # ... 现有的 chat 处理逻辑 ...
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise
```

## 推荐实施顺序

### 第一步：修复 user_id 和 session_id 格式

1. 统一使用 UUID 格式的 user_id
2. 统一使用 UUID 或规范格式的 session_id
3. 在所有入口点进行验证和转换

### 第二步：集成 Session Service

1. Memory Service 在存储前检查 session 是否存在
2. 如果不存在，调用 Session Service 创建
3. 添加适当的错误处理和日志

### 第三步：更新数据库 Schema

确保两个表的兼容性：

```sql
-- Session Service 的 sessions 表
CREATE TABLE dev.sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,  -- 或改为 UUID
    user_id VARCHAR(255),  -- 或改为 UUID
    ...
);

-- Memory Service 的 session_memories 表
CREATE TABLE dev.session_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id character varying(64) NOT NULL,
    user_id uuid,  -- 需要匹配 sessions.user_id 的类型
    ...
);
```

**推荐修改：**
- 将 `sessions.user_id` 改为 UUID 类型
- 将 `sessions.session_id` 改为 UUID 类型
- 或者将 `session_memories.user_id` 改为 VARCHAR 类型

## 测试流程

```python
# 1. 创建 session
POST /api/v1/sessions
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_data": {},
  "metadata": {}
}

# 响应: session_id = "7c9e6679-7425-40de-944b-e07fc1f90ae7"

# 2. 存储 session message (Memory Service)
store_session_message(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    session_id="7c9e6679-7425-40de-944b-e07fc1f90ae7",
    message_content="Hello, how are you?"
)

# 3. 查询 session context
get_session_context(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    session_id="7c9e6679-7425-40de-944b-e07fc1f90ae7"
)
```

## 总结

关键点：
1. ✅ Session Service 负责创建和管理 sessions
2. ✅ Memory Service 使用 Session Service 的 session_id
3. ✅ 统一使用 UUID 格式的 user_id 和 session_id
4. ✅ 两个服务通过 Consul 进行服务发现和通信
5. ✅ 数据库 schema 保持类型一致

这样可以确保两个服务正确协作，避免"session not found"错误。

