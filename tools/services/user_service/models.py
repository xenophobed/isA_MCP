"""
User Service Data Models

定义用户、订阅、API使用记录等数据模型
使用 Pydantic 进行数据验证和序列化
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


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
    auth0_id: str = Field(..., description="Auth0 用户ID")
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    credits_remaining: int = Field(default=1000, description="剩余积分")
    credits_total: int = Field(default=1000, description="总积分")
    subscription_status: SubscriptionStatus = Field(default=SubscriptionStatus.FREE, description="订阅状态")
    is_active: bool = Field(default=True, description="用户是否激活")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """创建用户请求模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    auth0_id: Optional[str] = Field(None, description="Auth0 用户ID")


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
    user_id: int = Field(..., description="用户ID")
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
    user_id: int = Field(..., description="用户ID")
    amount: int = Field(..., description="消费数量")
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
    """Auth0用户信息模型"""
    sub: str = Field(..., description="用户ID")
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    picture: Optional[str] = Field(None, description="用户头像")
    email_verified: bool = Field(default=False, description="邮箱是否验证") 