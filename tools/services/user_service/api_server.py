"""
User Service FastAPI Server

提供用户管理的 REST API 服务
包含认证、用户管理、订阅管理、支付处理等功能
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .models import (
    User, UserCreate, UserUpdate, UserResponse,
    SubscriptionStatus, CreditConsumption, CreditConsumptionResponse,
    PaymentIntent, CheckoutSession, WebhookEvent
)
from .auth_service import Auth0Service
from .subscription_service import SubscriptionService
from .payment_service import PaymentService
from .user_service import UserService
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

# 服务实例（使用配置）
auth_service = Auth0Service(
    domain=config.auth0_domain,
    audience=config.auth0_audience,
    client_id=config.auth0_client_id,
    client_secret=config.auth0_client_secret
)

subscription_service = SubscriptionService()

payment_service = PaymentService(
    secret_key=config.stripe_secret_key,
    webhook_secret=config.stripe_webhook_secret,
    pro_price_id=config.stripe_pro_price_id,
    enterprise_price_id=config.stripe_enterprise_price_id
)

user_service = UserService(
    auth_service=auth_service,
    subscription_service=subscription_service,
    payment_service=payment_service,
    use_database=True
)


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
        payload = await auth_service.verify_token(token)
        return payload
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


# 用户管理路由
@app.post("/api/v1/users/ensure", response_model=Dict[str, Any], tags=["Users"])
async def ensure_user_exists(
    user_data: UserCreate,
    current_user = Depends(get_current_user)
):
    """
    确保用户存在，不存在则创建
    替换传统的 app/api/user/ensure/route.ts
    """
    try:
        auth0_id = current_user["sub"]
        
        user = await user_service.ensure_user_exists(
            auth0_id=auth0_id,
            email=user_data.email,
            name=user_data.name
        )
        
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
        user_response = await user_service.get_user_info(auth0_id)
        
        if not user_response:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return user_response
        
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
    user_id: int,
    consumption: CreditConsumption,
    current_user = Depends(get_current_user)
):
    """
    消费用户积分
    """
    try:
        # 验证用户权限
        user = await user_service.get_user_by_auth0_id(current_user["sub"])
        if not user or user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        # 消费积分（这里需要实现实际的积分消费逻辑）
        result = {
            "success": True,
            "remaining_credits": user.credits_remaining - consumption.amount,
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
        if event_type == 'checkout.session.completed':
            webhook_result = await payment_service.handle_checkout_completed(event_data)
            result.update(webhook_result)
            
        elif event_type == 'customer.subscription.updated':
            webhook_result = await payment_service.handle_subscription_updated(event_data)
            result.update(webhook_result)
            
        elif event_type == 'customer.subscription.deleted':
            webhook_result = await payment_service.handle_subscription_deleted(event_data)
            result.update(webhook_result)
            
        elif event_type == 'invoice.payment_succeeded':
            webhook_result = await payment_service.handle_payment_succeeded(event_data)
            result.update(webhook_result)
            
        elif event_type == 'invoice.payment_failed':
            webhook_result = await payment_service.handle_payment_failed(event_data)
            result.update(webhook_result)
            
        else:
            result["message"] = f"Unhandled event type: {event_type}"
            result["unhandled"] = True
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {str(e)}"
        )


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
def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
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