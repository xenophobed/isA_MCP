# 统一用户数据管理服务架构设计

## 1. 架构问题分析

### 当前问题
- **数据访问分散**: 其他服务直接写入用户相关表（user_usage_records, sessions, user_credit_transactions等）
- **服务边界混乱**: 违反了微服务的数据边界原则
- **数据一致性风险**: 没有统一的数据验证和业务逻辑
- **难以维护**: 用户相关的业务逻辑分散在多个服务中

### 涉及的表
- `users` - 用户基础信息
- `user_usage_records` - AI使用记录（331条记录）
- `sessions` - 会话管理（696条记录）
- `user_credit_transactions` - 积分交易记录（331条记录）
- `session_memories` - 会话记忆
- `session_messages` - 会话消息

## 2. 统一架构设计

### 2.1 服务分层

```
┌─────────────────────────────────────────────────┐
│                Other Services                   │
│    (Memory Service, Terminal Service, etc.)    │
└─────────────────┬──────────────────────────────┘
                  │ HTTP API Calls
                  ▼
┌─────────────────────────────────────────────────┐
│              User Service API                   │
│         (FastAPI REST Endpoints)               │
└─────────────────┬──────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Service Layer                      │
│  • UserServiceV2     • UsageService            │
│  • SessionService    • CreditService           │
└─────────────────┬──────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│            Repository Layer                     │
│  • UserRepository    • UsageRepository         │
│  • SessionRepository • CreditRepository        │
└─────────────────┬──────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Database Layer                     │
│           (PostgreSQL/Supabase)                │
└─────────────────────────────────────────────────┘
```

### 2.2 核心服务模块

#### A. 用户基础管理服务 (UserServiceV2)
- 用户注册/登录/认证
- 用户信息管理
- 用户状态管理
- 积分余额管理

#### B. 使用记录服务 (UsageService)
- AI使用记录跟踪
- 使用统计分析
- 配额管理
- 使用历史查询

#### C. 会话管理服务 (SessionService)
- 会话创建/管理
- 会话记忆存储
- 消息历史管理
- 会话状态跟踪

#### D. 积分交易服务 (CreditService)
- 积分消费记录
- 积分充值记录
- 交易历史查询
- 余额计算

### 2.3 数据访问原则

1. **单一数据源**: 所有用户相关数据只能通过user_service访问
2. **API优先**: 其他服务必须通过HTTP API调用user_service
3. **事务一致性**: 复杂操作在user_service内部保证事务完整性
4. **数据验证集中**: 所有数据验证逻辑在Repository层统一实现

## 3. 新增Repository和Service设计

### 3.1 UsageRepository
```python
class UsageRepository(BaseRepository):
    """用户使用记录仓库"""
    
    async def create_usage_record(self, user_id: str, usage_data: dict) -> UsageRecord
    async def get_user_usage_history(self, user_id: str, limit: int = 50) -> List[UsageRecord]
    async def get_usage_statistics(self, user_id: str, start_date: datetime, end_date: datetime) -> dict
    async def get_total_usage_by_type(self, user_id: str, usage_type: str) -> int
```

### 3.2 SessionRepository
```python
class SessionRepository(BaseRepository):
    """会话管理仓库"""
    
    async def create_session(self, user_id: str, session_data: dict) -> Session
    async def get_user_sessions(self, user_id: str, active_only: bool = False) -> List[Session]
    async def update_session_status(self, session_id: str, status: str) -> bool
    async def add_session_memory(self, session_id: str, memory_data: dict) -> SessionMemory
    async def add_session_message(self, session_id: str, message_data: dict) -> SessionMessage
```

### 3.3 CreditRepository
```python
class CreditRepository(BaseRepository):
    """积分交易仓库"""
    
    async def create_transaction(self, user_id: str, transaction_data: dict) -> CreditTransaction
    async def get_user_transactions(self, user_id: str, transaction_type: str = None) -> List[CreditTransaction]
    async def calculate_current_balance(self, user_id: str) -> int
    async def get_transaction_summary(self, user_id: str, start_date: datetime, end_date: datetime) -> dict
```

## 4. API接口设计

### 4.1 使用记录API
```
POST   /api/v1/users/{user_id}/usage          # 记录使用
GET    /api/v1/users/{user_id}/usage          # 获取使用历史
GET    /api/v1/users/{user_id}/usage/stats    # 使用统计
```

### 4.2 会话管理API
```
POST   /api/v1/users/{user_id}/sessions       # 创建会话
GET    /api/v1/users/{user_id}/sessions       # 获取会话列表
PUT    /api/v1/sessions/{session_id}/status   # 更新会话状态
POST   /api/v1/sessions/{session_id}/memories # 添加会话记忆
POST   /api/v1/sessions/{session_id}/messages # 添加会话消息
```

### 4.3 积分交易API
```
POST   /api/v1/users/{user_id}/credits/consume    # 消费积分
POST   /api/v1/users/{user_id}/credits/recharge   # 充值积分
GET    /api/v1/users/{user_id}/credits/balance    # 获取余额
GET    /api/v1/users/{user_id}/credits/transactions # 交易历史
```

## 5. 迁移策略

### 5.1 分阶段迁移
1. **Phase 1**: 实现新的Repository和Service层
2. **Phase 2**: 添加新的API端点
3. **Phase 3**: 更新其他服务使用新API
4. **Phase 4**: 移除直接数据库访问代码

### 5.2 兼容性保证
- 保持现有数据库结构不变
- 新API与现有数据格式兼容
- 渐进式迁移，避免服务中断

### 5.3 数据一致性
- 在迁移期间保证数据一致性
- 使用数据库事务确保操作原子性
- 实现幂等性API防止重复操作

## 6. 实施计划

1. **实现UsageRepository和UsageService** - 处理AI使用记录
2. **实现SessionRepository和SessionService** - 处理会话管理
3. **实现CreditRepository和CreditService** - 处理积分交易
4. **添加对应的API端点** - 提供REST接口
5. **更新其他服务** - 使用新的API接口
6. **移除直接数据库访问** - 清理旧代码

这个架构确保了：
- **数据边界清晰**: 用户数据只能通过user_service访问
- **业务逻辑集中**: 所有用户相关逻辑在一个服务中
- **可维护性高**: 统一的数据访问和业务规则
- **扩展性好**: 新的用户相关功能可以轻松添加