"""
User Service FastAPI Server

提供用户管理的 REST API 服务
包含认证、用户管理、订阅管理、支付处理等功能
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .models import (
    User, UserCreate, UserUpdate, UserResponse, UserEnsureRequest,
    SubscriptionStatus, CreditConsumption, CreditConsumptionResponse,
    PaymentIntent, CheckoutSession, WebhookEvent,
    # New unified service models
    UsageRecord, UsageRecordCreate, UsageStatistics,
    Session, SessionCreate, SessionMemory, SessionMessage,
    CreditTransaction, CreditTransactionCreate,
    # Organization models
    Organization, OrganizationCreate, OrganizationUpdate,
    OrganizationMember, OrganizationMemberCreate, OrganizationMemberUpdate,
    OrganizationUsage, OrganizationUsageCreate,
    OrganizationCreditTransaction,
    # Invitation models
    OrganizationInvitation, OrganizationInvitationCreate, AcceptInvitationRequest
)
from .services.auth_service import Auth0Service
from .services.supabase_auth_service import SupabaseAuthService
from .services.unified_auth_service import UnifiedAuthService
from .subscription_service_legacy import SubscriptionService
from .services.payment_service import PaymentService
# 使用新的 ServiceV2 和 Repository 模式
from .services import UserServiceV2, SubscriptionServiceV2, OrganizationService
from .services.usage_service import UsageService
from .services.session_service import SessionService  
from .services.credit_service import CreditService
from .services.invitation_service import InvitationService
from .repositories import UserRepository, SubscriptionRepository, OrganizationRepository
from .config import get_config


# 获取配置
config = get_config()

# 配置日志
logging.basicConfig(level=getattr(logging, config.log_level.upper()))
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=config.app_name,
    description="提供用户认证、订阅管理和支付处理的综合服务",
    version=config.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    debug=config.debug
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=config.cors_allow_methods,
    allow_headers=config.cors_allow_headers,
)

# 安全配置
security = HTTPBearer()

# 认证服务实例（支持多种认证提供者）
auth0_service = None
supabase_service = None
unified_auth_service = None

# 初始化Auth0服务（如果配置可用）
if config.auth_provider in ["auth0", "both"]:
    try:
        auth0_service = Auth0Service(
            domain=config.auth0_domain,
            audience=config.auth0_audience,
            client_id=config.auth0_client_id,
            client_secret=config.auth0_client_secret
        )
        logger.info("Auth0 service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Auth0 service: {e}")

# 初始化Supabase服务（如果配置可用）
if config.auth_provider in ["supabase", "both"]:
    try:
        supabase_service = SupabaseAuthService(
            supabase_url=config.supabase_url,
            jwt_secret=config.supabase_jwt_secret,
            anon_key=config.supabase_anon_key,
            service_role_key=config.supabase_service_role_key
        )
        logger.info("Supabase auth service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase auth service: {e}")

# 创建统一认证服务
if auth0_service or supabase_service:
    unified_auth_service = UnifiedAuthService(
        auth0_service=auth0_service,
        supabase_service=supabase_service,
        default_provider=config.auth_provider
    )
    logger.info(f"Unified auth service initialized with providers: {unified_auth_service.get_available_providers()}")
else:
    logger.error("No authentication services available!")

# 向后兼容的auth_service别名
auth_service = auth0_service or supabase_service

subscription_service = SubscriptionService()

payment_service = PaymentService(
    secret_key=config.stripe_secret_key,
    webhook_secret=config.stripe_webhook_secret,
    pro_price_id=config.stripe_pro_price_id,
    enterprise_price_id=config.stripe_enterprise_price_id
)

# 初始化 Repository 层
user_repository = UserRepository()
subscription_repository = SubscriptionRepository()
organization_repository = OrganizationRepository()

# 初始化新的 Service V2 层
user_service = UserServiceV2(user_repository=user_repository)
subscription_service_v2 = SubscriptionServiceV2(
    subscription_repository=subscription_repository, 
    user_repository=user_repository
)

# 初始化新的统一数据管理服务
usage_service = UsageService()
session_service = SessionService()
credit_service = CreditService()
organization_service = OrganizationService()
invitation_service = InvitationService()

# 初始化文件存储服务
try:
    from .services.file_storage_service import FileStorageService
    file_storage_service = FileStorageService()
    logger.info("File storage service initialized")
except Exception as e:
    logger.warning(f"Failed to initialize file storage service: {e}")
    file_storage_service = None

# 启动事件处理
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await organization_service.initialize()
        logger.info("Organization service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize organization service: {e}")


# 依赖函数
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    获取当前认证用户
    
    Args:
        credentials: HTTP Bearer token
        
    Returns:
        验证后的用户 payload
        
    Raises:
        HTTPException: 认证失败时抛出
    """
    try:
        token = credentials.credentials
        
        if unified_auth_service:
            # 使用统一认证服务，自动检测认证提供者
            payload, provider = await unified_auth_service.verify_token(token)
            logger.debug(f"Token verified using {provider.value}")
            return payload
        elif auth_service:
            # 后备方案：使用单一认证服务
            payload = await auth_service.verify_token(token)
            return payload
        else:
            raise Exception("No authentication service available")
            
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# API 路由

@app.get("/", tags=["Health"])
async def root():
    """根路径健康检查"""
    return {
        "service": "User Management API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """详细的健康检查"""
    try:
        service_status = user_service.get_service_status()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_status,
            "uptime": "operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/auth/info", tags=["Auth"])
async def get_auth_info():
    """获取认证服务信息"""
    if unified_auth_service:
        return {
            "status": "multi-provider",
            "info": unified_auth_service.get_service_info(),
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "single-provider", 
            "auth0_available": auth0_service is not None,
            "supabase_available": supabase_service is not None,
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/auth/dev-token", tags=["Auth"])
async def generate_dev_token(user_id: str, email: str):
    """生成开发测试用的JWT token (仅Supabase)"""
    if not unified_auth_service or not unified_auth_service.supabase_service:
        raise HTTPException(
            status_code=404,
            detail="Development token generation not available (requires Supabase auth)"
        )
    
    try:
        token = await unified_auth_service.generate_dev_token(user_id, email)
        if token:
            return {
                "token": token,
                "user_id": user_id,
                "email": email,
                "expires_in": 3600,  # 1小时
                "provider": "supabase",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate token")
    except Exception as e:
        logger.error(f"Error generating dev token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")


# 用户管理路由
@app.post("/api/v1/users/ensure", response_model=Dict[str, Any], tags=["Users"])
async def ensure_user_exists(
    user_data: UserEnsureRequest,
    current_user = Depends(get_current_user)
):
    """
    确保用户存在，不存在则创建
    替换传统的 app/api/user/ensure/route.ts
    """
    try:
        # 验证 JWT token 中的用户ID与请求数据中的auth0_id是否匹配
        token_auth0_id = current_user["sub"]
        request_auth0_id = user_data.auth0_id
        
        if token_auth0_id != request_auth0_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token mismatch: token auth0_id ({token_auth0_id}) does not match request auth0_id ({request_auth0_id})"
            )
        
        # 使用 Auth0 ID 作为 user_id
        result = await user_service.ensure_user_exists(
            user_id=user_data.auth0_id,
            email=user_data.email,
            name=user_data.name,
            auth0_id=user_data.auth0_id
        )
        
        if not result.is_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to ensure user exists: {result.message}"
            )
        
        user = result.data
        return {
            "success": True,
            "user_id": user.id,
            "auth0_id": user.auth0_id,
            "email": user.email,
            "name": user.name,
            "credits": user.credits_remaining,
            "credits_total": user.credits_total,
            "plan": user.subscription_status.value,
            "is_active": user.is_active,
            "created": True
        }
        
    except Exception as e:
        logger.error(f"Error ensuring user exists: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ensure user exists: {str(e)}"
        )


@app.get("/api/v1/users/me", response_model=UserResponse, tags=["Users"])
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    获取当前用户信息
    替换传统的 hooks/useAuth0Supabase.ts
    """
    try:
        auth0_id = current_user["sub"]
        user_result = await user_service.get_user_info(auth0_id)
        
        if not user_result.is_success:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {auth0_id}"
            )
        
        return user_result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user info: {str(e)}"
        )


@app.post("/api/v1/users/{user_id}/credits/consume", tags=["Users"])
async def consume_user_credits(
    user_id: str,
    consumption: CreditConsumption,
    current_user = Depends(get_current_user)
):
    """
    消费用户积分
    """
    try:
        # 验证用户权限
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: user_id mismatch"
            )
        
        # 使用统一的积分服务来实际扣费
        credit_result = await credit_service.consume_credits(
            user_id=user_id,
            amount=consumption.amount,
            description=f"Credit consumption via legacy API - {consumption.reason}",
            usage_record_id=None
        )
        
        if not credit_result.is_success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to consume credits: {credit_result.message}"
            )
        
        result = {
            "success": True,
            "remaining_credits": credit_result.data.credits_after,
            "consumed_amount": consumption.amount,
            "message": f"成功消费 {consumption.amount} 积分"
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming credits: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to consume credits: {str(e)}"
        )


# 订阅管理路由
@app.post("/api/v1/subscriptions", tags=["Subscriptions"])
async def create_subscription(
    plan_type: str,
    current_user = Depends(get_current_user)
):
    """创建订阅"""
    try:
        user = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 验证计划类型
        try:
            subscription_plan = SubscriptionStatus(plan_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan type: {plan_type}"
            )
        
        if user.id is None:
            raise HTTPException(status_code=500, detail="User ID is missing")
            
        result = await subscription_service.create_subscription(
            user_id=user.id,
            plan_type=subscription_plan
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}"
        )


@app.get("/api/v1/subscriptions/plans", tags=["Subscriptions"])
async def get_subscription_plans():
    """获取所有订阅计划"""
    try:
        plans = subscription_service.get_plan_comparison()
        return plans
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get subscription plans: {str(e)}"
        )


# 支付处理路由
@app.post("/api/v1/payments/create-intent", tags=["Payments"])
async def create_payment_intent(
    amount: int,
    currency: str = "usd",
    current_user = Depends(get_current_user)
):
    """创建支付意图"""
    try:
        user = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        metadata = {
            "auth0_user_id": current_user["sub"],
            "user_email": user.email
        }
        
        payment_intent = await payment_service.create_payment_intent(
            amount=amount,
            currency=currency,
            metadata=metadata
        )
        
        return {
            "success": True,
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create payment intent: {str(e)}"
        )


@app.post("/api/v1/payments/create-checkout", tags=["Payments"])
async def create_checkout_session(
    plan_type: str,
    success_url: str,
    cancel_url: str,
    current_user = Depends(get_current_user)
):
    """创建 Stripe Checkout 会话"""
    try:
        user = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 确定价格ID
        if plan_type.lower() == "pro":
            price_id = payment_service.pro_price_id
        elif plan_type.lower() == "enterprise":
            price_id = payment_service.enterprise_price_id
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan type: {plan_type}"
            )
        
        metadata = {
            "auth0_user_id": current_user["sub"],
            "user_email": user.email,
            "plan_type": plan_type.lower()
        }
        
        checkout_session = await payment_service.create_checkout_session(
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user.email,
            metadata=metadata
        )
        
        return {
            "success": True,
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url,
            "success_url": checkout_session.success_url,
            "cancel_url": checkout_session.cancel_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )


# Webhook 处理路由
@app.post("/api/v1/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request):
    """
    处理 Stripe Webhooks
    替换传统的 app/api/stripe/webhook/route.ts
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            raise HTTPException(
                status_code=400,
                detail="Missing stripe-signature header"
            )
        
        # 验证 webhook 签名并解析事件
        event = await payment_service.verify_webhook_signature(payload, sig_header)
        
        if not event:
            raise HTTPException(
                status_code=400,
                detail="Invalid webhook signature"
            )
        
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Processing webhook event: {event_type}")
        
        result = {"success": True, "processed": True, "event_type": event_type}
        
        # 处理不同类型的事件
        try:
            if event_type == 'checkout.session.completed':
                webhook_result = await payment_service.handle_checkout_completed(event_data, user_service)
                result.update(webhook_result)
                
            elif event_type == 'customer.subscription.created':
                webhook_result = await payment_service.handle_subscription_created(event_data, user_service)
                result.update(webhook_result)
                
            elif event_type == 'customer.subscription.updated':
                webhook_result = await payment_service.handle_subscription_updated(event_data, user_service)
                result.update(webhook_result)
                
            elif event_type == 'customer.subscription.deleted':
                webhook_result = await payment_service.handle_subscription_deleted(event_data, user_service)
                result.update(webhook_result)
                
            elif event_type == 'invoice.payment_succeeded':
                webhook_result = await payment_service.handle_payment_succeeded(event_data, user_service)
                result.update(webhook_result)
                
            elif event_type == 'invoice.payment_failed':
                webhook_result = await payment_service.handle_payment_failed(event_data, user_service)
                result.update(webhook_result)
                
            else:
                result["message"] = f"Unhandled event type: {event_type}"
                result["unhandled"] = True
                
            # 记录webhook处理结果
            if user_service and user_service.db_service:
                await user_service.db_service.log_webhook_event(
                    event_id=event['id'],
                    event_type=event_type,
                    processed=result.get('success', True),
                    user_id=webhook_result.get('user_id') if 'webhook_result' in locals() else None,
                    stripe_subscription_id=webhook_result.get('subscription_id') if 'webhook_result' in locals() else None
                )
        except Exception as webhook_error:
            logger.error(f"Error processing webhook event {event_type}: {str(webhook_error)}")
            result.update({
                "success": False,
                "error": str(webhook_error),
                "message": f"Failed to process {event_type}"
            })
            
            # 记录失败的webhook事件
            if user_service and user_service.db_service:
                await user_service.db_service.log_webhook_event(
                    event_id=event['id'],
                    event_type=event_type,
                    processed=False,
                    error_message=str(webhook_error)
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {str(e)}"
        )


# ============ UNIFIED DATA MANAGEMENT API ENDPOINTS ============
# These endpoints provide centralized access to user data for other services

# Usage Records API
@app.post("/api/v1/users/{user_id}/usage", response_model=Dict[str, Any], tags=["Usage Records"])
async def record_usage(
    user_id: str,
    usage_data: UsageRecordCreate,
    current_user = Depends(get_current_user)
):
    """
    Record user usage event
    For other services to log AI usage, API calls, etc.
    """
    try:
        # Validate user_id matches the usage data
        if usage_data.user_id != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch")
        
        result = await usage_service.record_usage(usage_data)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to record usage: {str(e)}")


@app.get("/api/v1/users/{user_id}/usage", response_model=Dict[str, Any], tags=["Usage Records"])
async def get_usage_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get user usage history
    """
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        result = await usage_service.get_user_usage_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage history: {str(e)}")


@app.get("/api/v1/users/{user_id}/usage/stats", response_model=Dict[str, Any], tags=["Usage Records"])
async def get_usage_statistics(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get usage statistics for user
    """
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        result = await usage_service.get_usage_statistics(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")


# Session Management API
@app.post("/api/v1/users/{user_id}/sessions", response_model=Dict[str, Any], tags=["Sessions"])
async def create_session(
    user_id: str,
    session_data: SessionCreate,
    current_user = Depends(get_current_user)
):
    """
    Create new session
    For other services to create conversation sessions
    """
    try:
        # Validate user_id matches the session data
        if session_data.user_id != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch")
        
        result = await session_service.create_session(session_data)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        # 手动构建响应以避免 datetime 序列化问题
        session = result.data
        response = {
            "success": True,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "status": session.status,
            "message_count": session.message_count,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "message": result.message
        }
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/api/v1/users/{user_id}/sessions", response_model=Dict[str, Any], tags=["Sessions"])
async def get_user_sessions(
    user_id: str,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user)
):
    """
    Get user sessions
    """
    try:
        result = await session_service.get_user_sessions(
            user_id=user_id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user sessions: {str(e)}")


@app.put("/api/v1/sessions/{session_id}/status", response_model=Dict[str, Any], tags=["Sessions"])
async def update_session_status(
    session_id: str,
    status: str,
    current_user = Depends(get_current_user)
):
    """
    Update session status
    """
    try:
        result = await session_service.update_session_status(session_id, status)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update session status: {str(e)}")


@app.post("/api/v1/sessions/{session_id}/messages", response_model=Dict[str, Any], tags=["Sessions"])
async def add_session_message(
    session_id: str,
    role: str,
    content: str,
    message_type: str = "chat",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    current_user = Depends(get_current_user)
):
    """
    Add message to session
    """
    try:
        result = await session_service.add_session_message(
            session_id=session_id,
            role=role,
            content=content,
            message_type=message_type,
            tokens_used=tokens_used,
            cost_usd=cost_usd
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding session message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add session message: {str(e)}")


@app.get("/api/v1/sessions/{session_id}/messages", response_model=Dict[str, Any], tags=["Sessions"])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_user)
):
    """
    Get session messages
    """
    try:
        result = await session_service.get_session_messages(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {str(e)}")


@app.delete("/api/v1/sessions/{session_id}", response_model=Dict[str, Any], tags=["Sessions"])
async def delete_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete session
    """
    try:
        # Get session to verify ownership
        session_result = await session_service.get_session(session_id)
        if not session_result.is_success:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        session = session_result.data
        
        # Verify user ownership
        token_user_id = current_user["sub"]
        if session.user_id != token_user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only delete your own sessions")
        
        # Delete session using repository directly (since service doesn't have delete method)
        success = await session_service.session_repo.delete(session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete session")
        
        return {
            "success": True,
            "status": "success",
            "message": f"Session {session_id} deleted successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"session_id": session_id, "deleted": True}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


# Credit Transaction API
@app.post("/api/v1/users/{user_id}/credits/consume", response_model=Dict[str, Any], tags=["Credits"])
async def consume_credits_v2(
    user_id: str,
    amount: float,
    description: Optional[str] = None,
    usage_record_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """
    Consume user credits (V2 - unified)
    Replaces the existing credits consumption endpoint
    """
    try:
        result = await credit_service.consume_credits(
            user_id=user_id,
            amount=amount,
            description=description,
            usage_record_id=usage_record_id
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming credits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to consume credits: {str(e)}")


@app.post("/api/v1/users/{user_id}/credits/recharge", response_model=Dict[str, Any], tags=["Credits"])
async def recharge_credits(
    user_id: str,
    amount: float,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Recharge user credits
    """
    try:
        result = await credit_service.recharge_credits(
            user_id=user_id,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recharging credits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to recharge credits: {str(e)}")


@app.get("/api/v1/users/{user_id}/credits/balance", response_model=Dict[str, Any], tags=["Credits"])
async def get_credit_balance(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get user credit balance
    """
    try:
        result = await credit_service.get_credit_balance(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit balance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get credit balance: {str(e)}")


@app.get("/api/v1/users/{user_id}/credits/transactions", response_model=Dict[str, Any], tags=["Credits"])
async def get_transaction_history(
    user_id: str,
    transaction_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get user credit transaction history
    """
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        result = await credit_service.get_transaction_history(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transaction history: {str(e)}")


# ============ END UNIFIED DATA MANAGEMENT API ============

# ============ ORGANIZATION MANAGEMENT API ============
# Organization and tenant management endpoints

@app.post("/api/v1/organizations", response_model=Dict[str, Any], tags=["Organizations"])
async def create_organization(
    org_data: OrganizationCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new organization
    The requesting user becomes the organization owner
    """
    try:
        owner_user_id = current_user["sub"]
        
        result = await organization_service.create_organization(org_data, owner_user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "organization_id": result.data.organization_id,
                "name": result.data.name,
                "domain": result.data.domain,
                "plan": result.data.plan.value,
                "billing_email": result.data.billing_email,
                "status": result.data.status.value,
                "credits_pool": result.data.credits_pool,
                "created_at": result.data.created_at.isoformat() if result.data.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")


@app.get("/api/v1/organizations/{organization_id}", response_model=Dict[str, Any], tags=["Organizations"])
async def get_organization(
    organization_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get organization details
    """
    try:
        user_id = current_user["sub"]
        
        # Check if user has access to this organization
        if not await organization_service.check_organization_access(organization_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied: You are not a member of this organization")
        
        result = await organization_service.get_organization(organization_id)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success", 
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "organization_id": result.data.organization_id,
                "name": result.data.name,
                "domain": result.data.domain,
                "plan": result.data.plan.value,
                "billing_email": result.data.billing_email,
                "status": result.data.status.value,
                "settings": result.data.settings,
                "credits_pool": result.data.credits_pool,
                "created_at": result.data.created_at.isoformat() if result.data.created_at else None,
                "updated_at": result.data.updated_at.isoformat() if result.data.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization: {str(e)}")


@app.put("/api/v1/organizations/{organization_id}", response_model=Dict[str, Any], tags=["Organizations"])
async def update_organization(
    organization_id: str,
    update_data: OrganizationUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update organization (requires admin/owner permissions)
    """
    try:
        user_id = current_user["sub"]
        
        result = await organization_service.update_organization(organization_id, update_data, user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "organization_id": result.data.organization_id,
                "name": result.data.name,
                "domain": result.data.domain,
                "plan": result.data.plan.value,
                "billing_email": result.data.billing_email,
                "status": result.data.status.value,
                "settings": result.data.settings,
                "credits_pool": result.data.credits_pool,
                "updated_at": result.data.updated_at.isoformat() if result.data.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update organization: {str(e)}")


@app.delete("/api/v1/organizations/{organization_id}", response_model=Dict[str, Any], tags=["Organizations"])
async def delete_organization(
    organization_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete organization (requires owner permissions)
    """
    try:
        user_id = current_user["sub"]
        
        result = await organization_service.delete_organization(organization_id, user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"organization_id": organization_id, "deleted": True}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete organization: {str(e)}")


@app.get("/api/v1/users/{user_id}/organizations", response_model=Dict[str, Any], tags=["Organizations"])
async def get_user_organizations(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get all organizations for a user
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only view your own organizations")
        
        result = await organization_service.get_user_organizations(user_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user organizations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user organizations: {str(e)}")


@app.post("/api/v1/users/{user_id}/switch-context", response_model=Dict[str, Any], tags=["Organizations"])
async def switch_user_context(
    user_id: str,
    organization_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Switch user context to organization or back to individual
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only switch your own context")
        
        result = await organization_service.switch_user_context(user_id, organization_id)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching user context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to switch user context: {str(e)}")


# ============ Organization Member Management ============

@app.post("/api/v1/organizations/{organization_id}/members", response_model=Dict[str, Any], tags=["Organizations"])
async def add_organization_member(
    organization_id: str,
    member_data: OrganizationMemberCreate,
    current_user = Depends(get_current_user)
):
    """
    Add member to organization
    """
    try:
        requesting_user_id = current_user["sub"]
        
        result = await organization_service.add_organization_member(organization_id, member_data, requesting_user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "already a member" in result.message.lower():
                raise HTTPException(status_code=409, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "user_id": result.data.user_id,
                "organization_id": result.data.organization_id,
                "role": result.data.role.value,
                "permissions": result.data.permissions,
                "status": result.data.status.value,
                "joined_at": result.data.joined_at.isoformat() if result.data.joined_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding organization member: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add organization member: {str(e)}")


@app.get("/api/v1/organizations/{organization_id}/members", response_model=Dict[str, Any], tags=["Organizations"])
async def get_organization_members(
    organization_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get all members of an organization
    """
    try:
        requesting_user_id = current_user["sub"]
        
        result = await organization_service.get_organization_members(organization_id, requesting_user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        members_data = []
        for member in result.data:
            members_data.append({
                "user_id": member.user_id,
                "organization_id": member.organization_id,
                "role": member.role.value,
                "permissions": member.permissions,
                "status": member.status.value,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "created_at": member.created_at.isoformat() if member.created_at else None,
                "updated_at": member.updated_at.isoformat() if member.updated_at else None
            })
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": members_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization members: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization members: {str(e)}")


@app.put("/api/v1/organizations/{organization_id}/members/{user_id}", response_model=Dict[str, Any], tags=["Organizations"])
async def update_organization_member(
    organization_id: str,
    user_id: str,
    update_data: OrganizationMemberUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update organization member role/permissions
    """
    try:
        requesting_user_id = current_user["sub"]
        
        result = await organization_service.update_organization_member(organization_id, user_id, update_data, requesting_user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "user_id": result.data.user_id,
                "organization_id": result.data.organization_id,
                "role": result.data.role.value,
                "permissions": result.data.permissions,
                "status": result.data.status.value,
                "updated_at": result.data.updated_at.isoformat() if result.data.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization member: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update organization member: {str(e)}")


@app.delete("/api/v1/organizations/{organization_id}/members/{user_id}", response_model=Dict[str, Any], tags=["Organizations"])
async def remove_organization_member(
    organization_id: str,
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    Remove member from organization
    """
    try:
        requesting_user_id = current_user["sub"]
        
        result = await organization_service.remove_organization_member(organization_id, user_id, requesting_user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"user_id": user_id, "organization_id": organization_id, "removed": True}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing organization member: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove organization member: {str(e)}")


@app.get("/api/v1/organizations/{organization_id}/stats", response_model=Dict[str, Any], tags=["Organizations"])
async def get_organization_stats(
    organization_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get organization statistics
    """
    try:
        requesting_user_id = current_user["sub"]
        
        result = await organization_service.get_organization_stats(organization_id, requesting_user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get organization stats: {str(e)}")

# ============ END ORGANIZATION MANAGEMENT API ============

# ============ ORGANIZATION INVITATION API ============

@app.post("/api/v1/organizations/{organization_id}/invitations", response_model=Dict[str, Any], tags=["Invitations"])
async def create_organization_invitation(
    organization_id: str,
    invitation_data: OrganizationInvitationCreate,
    current_user = Depends(get_current_user)
):
    """
    Send invitation to join organization via email
    """
    try:
        inviter_user_id = current_user["sub"]
        
        result = await invitation_service.create_invitation(organization_id, inviter_user_id, invitation_data)
        
        if not result.is_success:
            if "access denied" in result.message.lower() or "permission" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "already exists" in result.message.lower():
                raise HTTPException(status_code=409, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create invitation: {str(e)}")


@app.get("/api/v1/organizations/{organization_id}/invitations", response_model=Dict[str, Any], tags=["Invitations"])
async def get_organization_invitations(
    organization_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get all invitations for organization
    """
    try:
        user_id = current_user["sub"]
        
        result = await invitation_service.get_organization_invitations(organization_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization invitations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitations: {str(e)}")


@app.get("/api/v1/invitations/{invitation_token}", response_model=Dict[str, Any], tags=["Invitations"])
async def get_invitation_by_token(invitation_token: str):
    """
    Get invitation details by token (public endpoint for invitation links)
    """
    try:
        result = await invitation_service.get_invitation_by_token(invitation_token)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "expired" in result.message.lower():
                raise HTTPException(status_code=410, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation by token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get invitation: {str(e)}")


@app.post("/api/v1/invitations/accept", response_model=Dict[str, Any], tags=["Invitations"])
async def accept_invitation(
    accept_request: AcceptInvitationRequest,
    current_user = Depends(get_current_user)
):
    """
    Accept organization invitation
    """
    try:
        # Add user_id from token if not provided
        if not accept_request.user_id:
            accept_request.user_id = current_user["sub"]
        
        result = await invitation_service.accept_invitation(accept_request)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "expired" in result.message.lower():
                raise HTTPException(status_code=410, detail=result.message)
            elif "mismatch" in result.message.lower():
                raise HTTPException(status_code=400, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {str(e)}")


@app.delete("/api/v1/invitations/{invitation_id}", response_model=Dict[str, Any], tags=["Invitations"])
async def cancel_invitation(
    invitation_id: str,
    current_user = Depends(get_current_user)
):
    """
    Cancel organization invitation
    """
    try:
        user_id = current_user["sub"]
        
        result = await invitation_service.cancel_invitation(invitation_id, user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower() or "permission" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"cancelled": result.data}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel invitation: {str(e)}")


@app.post("/api/v1/invitations/{invitation_id}/resend", response_model=Dict[str, Any], tags=["Invitations"])
async def resend_invitation(
    invitation_id: str,
    current_user = Depends(get_current_user)
):
    """
    Resend organization invitation email
    """
    try:
        user_id = current_user["sub"]
        
        result = await invitation_service.resend_invitation(invitation_id, user_id)
        
        if not result.is_success:
            if "access denied" in result.message.lower() or "permission" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            elif "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to resend invitation: {str(e)}")

# ============ END ORGANIZATION INVITATION API ============

# ============ FILE MANAGEMENT API ============
# File upload, download, and management endpoints

@app.post("/api/v1/users/{user_id}/files/upload", response_model=Dict[str, Any], tags=["Files"])
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Upload user file to MinIO storage
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only upload files to your own account"
            )
        
        # Check if file storage service is available
        if not file_storage_service:
            raise HTTPException(
                status_code=503,
                detail="File storage service is not available"
            )
        
        # Upload file
        result = await file_storage_service.upload_file(user_id, file)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/api/v1/users/{user_id}/files", response_model=Dict[str, Any], tags=["Files"])
async def get_user_files(
    user_id: str,
    prefix: str = "",
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    Get user files list
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own files"
            )
        
        # Check if file storage service is available
        if not file_storage_service:
            raise HTTPException(
                status_code=503,
                detail="File storage service is not available"
            )
        
        # Get files list
        result = file_storage_service.list_user_files(user_id, prefix, limit)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user files: {str(e)}")


@app.get("/api/v1/users/{user_id}/files/info", response_model=Dict[str, Any], tags=["Files"])
async def get_file_info(
    user_id: str,
    file_path: str,
    current_user = Depends(get_current_user)
):
    """
    Get file information
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own files"
            )
        
        # Check if file storage service is available
        if not file_storage_service:
            raise HTTPException(
                status_code=503,
                detail="File storage service is not available"
            )
        
        # Get file info
        result = file_storage_service.get_file_info(user_id, file_path)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@app.delete("/api/v1/users/{user_id}/files", response_model=Dict[str, Any], tags=["Files"])
async def delete_file(
    user_id: str,
    file_path: str,
    current_user = Depends(get_current_user)
):
    """
    Delete user file
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only delete your own files"
            )
        
        # Check if file storage service is available
        if not file_storage_service:
            raise HTTPException(
                status_code=503,
                detail="File storage service is not available"
            )
        
        # Delete file
        result = file_storage_service.delete_file(user_id, file_path)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": True,
            "status": "success",
            "message": result.message,
            "timestamp": datetime.utcnow().isoformat(),
            "data": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@app.get("/api/v1/users/{user_id}/files/download", tags=["Files"])
async def download_file(
    user_id: str,
    file_path: str,
    current_user = Depends(get_current_user)
):
    """
    Get download URL for user file (redirect to presigned URL)
    """
    try:
        # Verify user permission
        token_user_id = current_user["sub"]
        if user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only download your own files"
            )
        
        # Check if file storage service is available
        if not file_storage_service:
            raise HTTPException(
                status_code=503,
                detail="File storage service is not available"
            )
        
        # Get download URL
        result = file_storage_service.get_download_url(user_id, file_path)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            elif "access denied" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            else:
                raise HTTPException(status_code=400, detail=result.message)
        
        # Redirect to presigned URL
        download_url = result.data["download_url"]
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")

# ============ END FILE MANAGEMENT API ============

# 分析和管理路由
@app.get("/api/v1/users/{user_id}/analytics", tags=["Analytics"])
async def get_user_analytics(
    user_id: int,
    current_user = Depends(get_current_user)
):
    """获取用户分析数据"""
    try:
        # 验证用户权限
        user = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user or user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        analytics = await user_service.get_user_analytics(user_id)
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user analytics: {str(e)}"
        )


# 异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# 启动函数
def start_server(host: str = "0.0.0.0", port: int = 8100, reload: bool = False):
    """
    启动 FastAPI 服务器
    
    Args:
        host: 监听地址
        port: 监听端口
        reload: 是否启用热重载
    """
    logger.info(f"Starting User Service API server on {host}:{port}")
    uvicorn.run(
        "tools.services.user_service.api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    start_server(reload=True) 