"""
User Service Data Models

定义用户、订阅、API使用记录等数据模型
使用 Pydantic 进行数据验证和序列化
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# 导入用户ID验证工具
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.user_id_utils import UserIdValidator, validate_user_id


class SubscriptionStatus(str, Enum):
    """订阅状态枚举"""
    FREE = "free"
    PRO = "pro" 
    ENTERPRISE = "enterprise"


class StripeSubscriptionStatus(str, Enum):
    """Stripe 订阅状态枚举"""
    ACTIVE = "active"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"
    INACTIVE = "inactive"


class User(BaseModel):
    """用户模型"""
    id: Optional[int] = None
    user_id: str = Field(..., description="用户业务ID（通常是Auth0 ID）", max_length=255)
    auth0_id: Optional[str] = Field(None, description="Auth0 用户ID", max_length=255)
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    credits_remaining: int = Field(default=1000, description="剩余积分")
    credits_total: int = Field(default=1000, description="总积分")
    subscription_status: SubscriptionStatus = Field(default=SubscriptionStatus.FREE, description="订阅状态")
    is_active: bool = Field(default=True, description="用户是否激活")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """验证用户ID格式"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)
    
    @validator('auth0_id')
    def validate_auth0_id_format(cls, v):
        """验证Auth0 ID格式"""
        if v is None:
            return v
        
        # Auth0 ID可以为空，但如果提供了必须格式正确
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid auth0_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """创建用户请求模型"""
    user_id: str = Field(..., description="用户业务ID")
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    auth0_id: Optional[str] = Field(None, description="Auth0 用户ID")
    
    @validator('user_id')
    def validate_user_id_format(cls, v):
        """验证用户ID格式"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)


class UserEnsureRequest(BaseModel):
    """确保用户存在请求模型（前端调用）"""
    auth0_id: str = Field(..., description="Auth0 用户ID")
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    
    @validator('auth0_id')
    def validate_auth0_id_format(cls, v):
        """验证Auth0 ID格式"""
        if not v:
            raise ValueError('auth0_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid auth0_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    email: Optional[EmailStr] = Field(None, description="用户邮箱")
    name: Optional[str] = Field(None, description="用户姓名")
    credits_remaining: Optional[int] = Field(None, description="剩余积分")
    subscription_status: Optional[SubscriptionStatus] = Field(None, description="订阅状态")
    is_active: Optional[bool] = Field(None, description="用户是否激活")


class UserResponse(BaseModel):
    """用户响应模型"""
    user_id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    credits: int = Field(..., description="剩余积分")
    credits_total: int = Field(..., description="总积分")
    plan: SubscriptionStatus = Field(..., description="订阅计划")
    is_active: bool = Field(..., description="用户是否激活")


class Subscription(BaseModel):
    """订阅模型"""
    id: Optional[int] = None
    user_id: str = Field(..., description="用户业务ID")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe 订阅ID")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe 客户ID")
    status: StripeSubscriptionStatus = Field(..., description="订阅状态")
    plan_type: SubscriptionStatus = Field(..., description="订阅类型")
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """创建订阅请求模型"""
    user_id: int = Field(..., description="用户ID")
    plan_type: SubscriptionStatus = Field(..., description="订阅类型")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe 订阅ID")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe 客户ID")


class ApiUsage(BaseModel):
    """API使用记录模型"""
    id: Optional[int] = None
    user_id: int = Field(..., description="用户ID")
    endpoint: str = Field(..., description="API端点")
    tokens_used: int = Field(default=1, description="使用的token数量")
    request_data: Optional[str] = Field(None, description="请求数据JSON")
    response_data: Optional[str] = Field(None, description="响应数据JSON")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiUsageCreate(BaseModel):
    """创建API使用记录请求模型"""
    user_id: int = Field(..., description="用户ID")
    endpoint: str = Field(..., description="API端点")
    tokens_used: int = Field(default=1, description="使用的token数量")
    request_data: Optional[Dict[str, Any]] = Field(None, description="请求数据")
    response_data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class PaymentIntent(BaseModel):
    """支付意图模型"""
    id: str = Field(..., description="支付意图ID")
    client_secret: str = Field(..., description="客户端密钥")
    amount: int = Field(..., description="支付金额（分）")
    currency: str = Field(default="usd", description="货币类型")
    status: str = Field(..., description="支付状态")


class CheckoutSession(BaseModel):
    """结账会话模型"""
    id: str = Field(..., description="会话ID")
    url: str = Field(..., description="结账URL")
    success_url: str = Field(..., description="成功跳转URL")
    cancel_url: str = Field(..., description="取消跳转URL")


class CreditConsumption(BaseModel):
    """积分消费模型"""
    user_id: str = Field(..., description="用户ID") 
    amount: float = Field(..., description="消费数量")
    reason: str = Field(default="api_call", description="消费原因")
    endpoint: Optional[str] = Field(None, description="API端点")


class CreditConsumptionResponse(BaseModel):
    """积分消费响应模型"""
    success: bool = Field(..., description="是否成功")
    remaining_credits: int = Field(..., description="剩余积分")
    consumed_amount: int = Field(..., description="消费数量")
    message: str = Field(..., description="响应消息")


class WebhookEvent(BaseModel):
    """Webhook事件模型"""
    id: str = Field(..., description="事件ID")
    type: str = Field(..., description="事件类型")
    data: Dict[str, Any] = Field(..., description="事件数据")
    created: int = Field(..., description="创建时间戳")


class Auth0UserInfo(BaseModel):
    """Auth0 user information model"""
    sub: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User name")
    picture: Optional[str] = Field(None, description="User avatar")
    email_verified: bool = Field(default=False, description="Email verified status")


# ============ Usage Record Models ============

class UsageRecord(BaseModel):
    """User usage record model"""
    id: Optional[int] = None
    user_id: str = Field(..., description="User ID", max_length=255)
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    endpoint: str = Field(..., description="API endpoint")
    event_type: str = Field(..., description="Event type")
    credits_charged: float = Field(default=0.0, description="Credits charged")
    cost_usd: float = Field(default=0.0, description="USD cost")
    calculation_method: Optional[str] = Field(default="unknown", description="Calculation method")
    tokens_used: Optional[int] = Field(default=0, description="Tokens used")
    prompt_tokens: Optional[int] = Field(default=0, description="Prompt tokens")
    completion_tokens: Optional[int] = Field(default=0, description="Completion tokens")
    model_name: Optional[str] = Field(None, description="Model name")
    provider: Optional[str] = Field(None, description="Service provider")
    tool_name: Optional[str] = Field(None, description="Tool name")
    operation_name: Optional[str] = Field(None, description="Operation name")
    billing_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Billing metadata")
    request_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request data")
    response_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response data")
    created_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class UsageRecordCreate(BaseModel):
    """Create usage record request model"""
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    endpoint: str = Field(..., description="API endpoint")
    event_type: str = Field(..., description="Event type")
    credits_charged: float = Field(default=0.0, description="Credits charged")
    cost_usd: float = Field(default=0.0, description="USD cost")
    calculation_method: Optional[str] = Field(default="unknown", description="Calculation method")
    tokens_used: Optional[int] = Field(default=0, description="Tokens used")
    prompt_tokens: Optional[int] = Field(default=0, description="Prompt tokens")
    completion_tokens: Optional[int] = Field(default=0, description="Completion tokens")
    model_name: Optional[str] = Field(None, description="Model name")
    provider: Optional[str] = Field(None, description="Service provider")
    tool_name: Optional[str] = Field(None, description="Tool name")
    operation_name: Optional[str] = Field(None, description="Operation name")
    billing_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Billing metadata")
    request_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request data")
    response_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response data")


class UsageStatistics(BaseModel):
    """Usage statistics model"""
    total_records: int = Field(..., description="Total record count")
    total_credits_charged: float = Field(..., description="Total credits charged")
    total_cost_usd: float = Field(..., description="Total USD cost")
    total_tokens_used: int = Field(..., description="Total tokens used")
    by_event_type: Dict[str, int] = Field(default_factory=dict, description="Statistics by event type")
    by_model: Dict[str, int] = Field(default_factory=dict, description="Statistics by model")
    by_provider: Dict[str, int] = Field(default_factory=dict, description="Statistics by provider")
    date_range: Dict[str, Optional[datetime]] = Field(default_factory=dict, description="Date range")


# ============ Session Models ============

class Session(BaseModel):
    """Session model"""
    id: Optional[int] = None
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID", max_length=255)
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation data")
    status: str = Field(default="active", description="Session status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")
    is_active: bool = Field(default=True, description="Is session active")
    message_count: int = Field(default=0, description="Message count")
    total_tokens: int = Field(default=0, description="Total tokens")
    total_cost: float = Field(default=0.0, description="Total cost")
    session_summary: str = Field(default="", description="Session summary")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @validator('created_at', pre=True)
    def parse_created_at(cls, v):
        """Parse created_at from string if needed"""
        if isinstance(v, str):
            from datetime import datetime
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
    
    @validator('updated_at', pre=True)
    def parse_updated_at(cls, v):
        """Parse updated_at from string if needed"""
        if isinstance(v, str):
            from datetime import datetime
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionCreate(BaseModel):
    """Create session request model"""
    user_id: str = Field(..., description="User ID")
    conversation_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Conversation data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class SessionMemory(BaseModel):
    """Session memory model"""
    id: Optional[int] = None
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID", max_length=255)
    memory_type: str = Field(..., description="Memory type")
    content: str = Field(..., description="Memory content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Memory metadata")
    created_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class SessionMessage(BaseModel):
    """Session message model"""
    id: Optional[str] = None  # UUID in database
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID", max_length=255)
    message_type: str = Field(default="chat", description="Message type")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tool calls data")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID")
    message_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")
    tokens_used: Optional[int] = Field(default=0, description="Tokens used")
    cost_usd: Optional[float] = Field(default=0.0, description="Cost in USD")
    is_summary_candidate: Optional[bool] = Field(default=True, description="Is summary candidate")
    importance_score: Optional[float] = Field(default=0.5, description="Importance score")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


# ============ Organization Models ============

class OrganizationStatus(str, Enum):
    """Organization status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended" 
    TRIAL = "trial"
    INACTIVE = "inactive"


class OrganizationPlan(str, Enum):
    """Organization plan enumeration"""
    STARTUP = "startup"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class OrganizationRole(str, Enum):
    """Organization member role enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationMemberStatus(str, Enum):
    """Organization member status enumeration"""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"


class Organization(BaseModel):
    """Organization model"""
    id: Optional[int] = None
    organization_id: str = Field(..., description="Organization ID", max_length=255)
    name: str = Field(..., description="Organization name", max_length=255)
    domain: Optional[str] = Field(None, description="Organization domain", max_length=255)
    plan: OrganizationPlan = Field(default=OrganizationPlan.STARTUP, description="Organization plan")
    billing_email: EmailStr = Field(..., description="Billing email")
    status: OrganizationStatus = Field(default=OrganizationStatus.ACTIVE, description="Organization status")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Organization settings")
    credits_pool: float = Field(default=0.0, description="Shared organization credits")
    api_keys: Optional[List[str]] = Field(default_factory=list, description="Organization API keys")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrganizationCreate(BaseModel):
    """Create organization request model"""
    name: str = Field(..., description="Organization name", max_length=255)
    domain: Optional[str] = Field(None, description="Organization domain", max_length=255)
    plan: OrganizationPlan = Field(default=OrganizationPlan.STARTUP, description="Organization plan")
    billing_email: EmailStr = Field(..., description="Billing email")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Organization settings")


class OrganizationUpdate(BaseModel):
    """Update organization request model"""
    name: Optional[str] = Field(None, description="Organization name", max_length=255)
    domain: Optional[str] = Field(None, description="Organization domain", max_length=255)
    plan: Optional[OrganizationPlan] = Field(None, description="Organization plan")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email")
    status: Optional[OrganizationStatus] = Field(None, description="Organization status")
    settings: Optional[Dict[str, Any]] = Field(None, description="Organization settings")


class OrganizationMember(BaseModel):
    """Organization member model"""
    id: Optional[int] = None
    user_id: str = Field(..., description="User ID", max_length=255)
    organization_id: str = Field(..., description="Organization ID", max_length=255)
    role: OrganizationRole = Field(..., description="Member role")
    permissions: Optional[List[str]] = Field(default_factory=list, description="Member permissions")
    status: OrganizationMemberStatus = Field(default=OrganizationMemberStatus.ACTIVE, description="Member status")
    joined_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class OrganizationMemberCreate(BaseModel):
    """Create organization member request model"""
    user_id: Optional[str] = Field(None, description="User ID (if existing user)")
    email: Optional[EmailStr] = Field(None, description="Email (if inviting new user)")
    role: OrganizationRole = Field(..., description="Member role")
    permissions: Optional[List[str]] = Field(default_factory=list, description="Member permissions")


class OrganizationMemberUpdate(BaseModel):
    """Update organization member request model"""
    role: Optional[OrganizationRole] = Field(None, description="Member role")
    permissions: Optional[List[str]] = Field(None, description="Member permissions")
    status: Optional[OrganizationMemberStatus] = Field(None, description="Member status")


class OrganizationUsage(BaseModel):
    """Organization usage record model"""
    id: Optional[int] = None
    organization_id: str = Field(..., description="Organization ID", max_length=255)
    user_id: str = Field(..., description="User ID", max_length=255)
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    endpoint: str = Field(..., description="API endpoint")
    event_type: str = Field(..., description="Event type")
    credits_charged: float = Field(default=0.0, description="Credits charged")
    cost_usd: float = Field(default=0.0, description="USD cost")
    calculation_method: Optional[str] = Field(default="unknown", description="Calculation method")
    tokens_used: Optional[int] = Field(default=0, description="Tokens used")
    prompt_tokens: Optional[int] = Field(default=0, description="Prompt tokens")
    completion_tokens: Optional[int] = Field(default=0, description="Completion tokens")
    model_name: Optional[str] = Field(None, description="Model name")
    provider: Optional[str] = Field(None, description="Service provider")
    tool_name: Optional[str] = Field(None, description="Tool name")
    operation_name: Optional[str] = Field(None, description="Operation name")
    department: Optional[str] = Field(None, description="Department")
    project_id: Optional[str] = Field(None, description="Project ID")
    billing_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Billing metadata")
    request_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request data")
    response_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response data")
    created_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class OrganizationUsageCreate(BaseModel):
    """Create organization usage record request model"""
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    trace_id: Optional[str] = Field(None, description="Trace ID")
    endpoint: str = Field(..., description="API endpoint")
    event_type: str = Field(..., description="Event type")
    credits_charged: float = Field(default=0.0, description="Credits charged")
    cost_usd: float = Field(default=0.0, description="USD cost")
    calculation_method: Optional[str] = Field(default="unknown", description="Calculation method")
    tokens_used: Optional[int] = Field(default=0, description="Tokens used")
    prompt_tokens: Optional[int] = Field(default=0, description="Prompt tokens")
    completion_tokens: Optional[int] = Field(default=0, description="Completion tokens")
    model_name: Optional[str] = Field(None, description="Model name")
    provider: Optional[str] = Field(None, description="Service provider")
    tool_name: Optional[str] = Field(None, description="Tool name")
    operation_name: Optional[str] = Field(None, description="Operation name")
    department: Optional[str] = Field(None, description="Department")
    project_id: Optional[str] = Field(None, description="Project ID")
    billing_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Billing metadata")
    request_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request data")
    response_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response data")


class OrganizationCreditTransaction(BaseModel):
    """Organization credit transaction model"""
    id: Optional[int] = None
    organization_id: str = Field(..., description="Organization ID", max_length=255)
    transaction_type: str = Field(..., description="Transaction type (consume/recharge/refund)")
    credits_amount: float = Field(..., description="Transaction amount")
    credits_before: float = Field(..., description="Balance before transaction")
    credits_after: float = Field(..., description="Balance after transaction")
    user_id: Optional[str] = Field(None, description="User who triggered transaction", max_length=255)
    usage_record_id: Optional[int] = Field(None, description="Associated usage record ID")
    description: Optional[str] = Field(None, description="Transaction description")
    reference_id: Optional[str] = Field(None, description="Reference ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Transaction metadata")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            return v  # Allow None for system-level transactions
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


# ============ Credit Transaction Models ============

class CreditTransaction(BaseModel):
    """Credit transaction model"""
    id: Optional[int] = None
    user_id: str = Field(..., description="User ID", max_length=255)
    transaction_type: str = Field(..., description="Transaction type (consume/recharge/refund)")
    credits_amount: float = Field(..., description="Transaction amount")
    credits_before: float = Field(..., description="Balance before transaction")
    credits_after: float = Field(..., description="Balance after transaction")
    usage_record_id: Optional[int] = Field(None, description="Associated usage record ID")
    description: Optional[str] = Field(None, description="Transaction description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Transaction metadata")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        if not v:
            raise ValueError('user_id cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid user_id format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class CreditTransactionCreate(BaseModel):
    """Create credit transaction request model"""
    user_id: str = Field(..., description="User ID")
    transaction_type: str = Field(..., description="Transaction type (consume/recharge/refund)")
    amount: float = Field(..., description="Transaction amount")
    reference_type: Optional[str] = Field(None, description="Reference type")
    reference_id: Optional[str] = Field(None, description="Reference ID")
    usage_record_id: Optional[int] = Field(None, description="Associated usage record ID")
    description: Optional[str] = Field(None, description="Transaction description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Transaction metadata")


# ============ Organization Invitation Models ============

class InvitationStatus(str, Enum):
    """Organization invitation status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrganizationInvitation(BaseModel):
    """Organization invitation model"""
    id: Optional[int] = None
    invitation_id: str = Field(..., description="Unique invitation ID", max_length=255)
    organization_id: str = Field(..., description="Organization ID", max_length=255)
    email: EmailStr = Field(..., description="Invited user email")
    role: OrganizationRole = Field(..., description="Invited role")
    invited_by: str = Field(..., description="Inviter user ID", max_length=255)
    invitation_token: str = Field(..., description="Invitation token")
    status: InvitationStatus = Field(default=InvitationStatus.PENDING, description="Invitation status")
    expires_at: datetime = Field(..., description="Invitation expiry time")
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('invited_by')
    def validate_inviter_user_id_format(cls, v):
        """Validate inviter user ID format"""
        if not v:
            raise ValueError('invited_by cannot be empty')
        
        result = validate_user_id(v)
        if not result.is_valid:
            raise ValueError(f'Invalid invited_by format: {result.error_message}')
        
        return UserIdValidator.normalize(v)

    class Config:
        from_attributes = True


class OrganizationInvitationCreate(BaseModel):
    """Create organization invitation request model"""
    email: EmailStr = Field(..., description="Email to invite")
    role: OrganizationRole = Field(..., description="Role to assign")
    message: Optional[str] = Field(None, description="Personal message", max_length=500)


class OrganizationInvitationResponse(BaseModel):
    """Organization invitation response model"""
    invitation_id: str = Field(..., description="Invitation ID")
    organization_name: str = Field(..., description="Organization name")
    email: str = Field(..., description="Invited email")
    role: str = Field(..., description="Invited role")
    status: str = Field(..., description="Invitation status")
    expires_at: datetime = Field(..., description="Expiry time")
    created_at: datetime = Field(..., description="Creation time")


class AcceptInvitationRequest(BaseModel):
    """Accept invitation request model"""
    invitation_token: str = Field(..., description="Invitation token")
    user_id: Optional[str] = Field(None, description="User ID (if existing user)")
    user_data: Optional[Dict[str, Any]] = Field(None, description="New user data (if creating account)") 