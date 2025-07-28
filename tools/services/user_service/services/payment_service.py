"""
Stripe Payment Service

提供 Stripe 支付集成服务，包括支付意图创建、订阅管理和 webhook 处理
严格遵循 MCP 协议规范和异步编程模式
"""

import stripe
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json

from ..models import (
    PaymentIntent, CheckoutSession, WebhookEvent, 
    SubscriptionStatus, StripeSubscriptionStatus
)


logger = logging.getLogger(__name__)


class PaymentService:
    """Stripe 支付服务类"""
    
    def __init__(self, secret_key: str, webhook_secret: str, 
                 pro_price_id: str, enterprise_price_id: str):
        """
        初始化支付服务
        
        Args:
            secret_key: Stripe 密钥
            webhook_secret: Webhook 签名密钥
            pro_price_id: Pro 计划价格ID
            enterprise_price_id: Enterprise 计划价格ID
        """
        stripe.api_key = secret_key
        self.webhook_secret = webhook_secret
        self.pro_price_id = pro_price_id
        self.enterprise_price_id = enterprise_price_id
        
        # 价格ID到计划类型的映射
        self.price_to_plan = {
            pro_price_id: SubscriptionStatus.PRO,
            enterprise_price_id: SubscriptionStatus.ENTERPRISE
        }
        
    async def create_payment_intent(self, amount: int, currency: str = "usd", 
                                  metadata: Optional[Dict[str, str]] = None) -> PaymentIntent:
        """
        创建支付意图
        
        Args:
            amount: 支付金额（分）
            currency: 货币类型，默认USD
            metadata: 元数据
            
        Returns:
            支付意图对象
            
        Raises:
            ValueError: 创建失败时抛出
            
        Example:
            >>> payment_service = PaymentService("sk_test_...", "whsec_...")
            >>> intent = await payment_service.create_payment_intent(2000)
            >>> print(intent.client_secret)
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True}
            )
            
            payment_intent = PaymentIntent(
                id=intent.id,
                client_secret=intent.client_secret,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status
            )
            
            logger.info(f"Payment intent created: {intent.id}")
            return payment_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise ValueError(f"Failed to create payment intent: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise ValueError(f"Error creating payment intent: {str(e)}")

    async def create_checkout_session(self, price_id: str, success_url: str, 
                                    cancel_url: str, customer_email: Optional[str] = None,
                                    metadata: Optional[Dict[str, str]] = None) -> CheckoutSession:
        """
        创建 Stripe Checkout 会话
        
        Args:
            price_id: 价格ID
            success_url: 成功跳转URL
            cancel_url: 取消跳转URL
            customer_email: 客户邮箱（可选）
            metadata: 元数据
            
        Returns:
            结账会话对象
            
        Example:
            >>> session = await payment_service.create_checkout_session(
            ...     "price_123", 
            ...     "https://app.com/success",
            ...     "https://app.com/cancel"
            ... )
        """
        try:
            session_params = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": price_id,
                    "quantity": 1,
                }],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {}
            }
            
            if customer_email:
                session_params["customer_email"] = customer_email
            
            session = stripe.checkout.Session.create(**session_params)
            
            checkout_session = CheckoutSession(
                id=session.id,
                url=session.url,
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            logger.info(f"Checkout session created: {session.id}")
            return checkout_session
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise ValueError(f"Failed to create checkout session: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise ValueError(f"Error creating checkout session: {str(e)}")

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        获取客户信息
        
        Args:
            customer_id: Stripe 客户ID
            
        Returns:
            客户信息字典，不存在返回None
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer if customer else None
        except stripe.error.InvalidRequestError:
            logger.warning(f"Customer not found: {customer_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting customer: {str(e)}")
            return None

    async def create_customer(self, email: str, name: Optional[str] = None,
                            metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        创建 Stripe 客户
        
        Args:
            email: 客户邮箱
            name: 客户姓名（可选）
            metadata: 元数据
            
        Returns:
            客户ID，创建失败返回None
        """
        try:
            customer_data = {"email": email}
            if name:
                customer_data["name"] = name
            if metadata:
                customer_data["metadata"] = metadata
                
            customer = stripe.Customer.create(**customer_data)
            
            logger.info(f"Customer created: {customer.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订阅信息
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            订阅信息字典，不存在返回None
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription if subscription else None
        except stripe.error.InvalidRequestError:
            logger.warning(f"Subscription not found: {subscription_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {str(e)}")
            return None

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否取消成功
        """
        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Subscription canceled: {subscription_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return False

    async def verify_webhook_signature(self, payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """
        验证 webhook 签名并解析事件
        
        Args:
            payload: 请求体
            sig_header: 签名头
            
        Returns:
            事件数据，验证失败返回None
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            logger.info(f"Webhook event verified: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return None

    def determine_plan_from_price_id(self, price_id: str) -> SubscriptionStatus:
        """
        根据价格ID确定订阅计划
        
        Args:
            price_id: Stripe 价格ID
            
        Returns:
            订阅计划类型
        """
        return self.price_to_plan.get(price_id, SubscriptionStatus.FREE)

    async def handle_checkout_completed(self, event_data: Dict[str, Any], 
                                      user_service=None) -> Dict[str, Any]:
        """
        处理订阅完成事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            session = event_data
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            metadata = session.get('metadata', {})

            # Checkout sessions may not include subscription data directly
            # We need to handle this case
            if not subscription_id:
                logger.warning(f"Checkout session has no subscription ID, will be handled by customer.subscription.created event")
                return {
                    "type": "checkout_completed",
                    "customer_id": customer_id,
                    "subscription_id": None,
                    "status": "deferred_to_subscription_created",
                    "metadata": metadata
                }

            # 获取订阅详情
            subscription = await self.get_subscription(subscription_id)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            # 确定计划类型
            price_id = subscription['items']['data'][0]['price']['id']
            plan_type = self.determine_plan_from_price_id(price_id)

            # 从metadata中获取用户信息
            auth0_user_id = metadata.get('auth0_user_id')
            user_email = metadata.get('user_email')

            if not auth0_user_id:
                raise ValueError("Missing auth0_user_id in metadata")

            # 更新数据库中的用户和订阅信息
            if user_service and user_service.db_service:
                # 获取用户
                user = await user_service.get_user_by_auth0_id(auth0_user_id)
                if not user:
                    raise ValueError(f"User not found: {auth0_user_id}")

                # 创建订阅记录
                await user_service.db_service.create_subscription(
                    user_id=user.id,
                    stripe_subscription_id=subscription_id,
                    stripe_customer_id=customer_id,
                    plan_type=plan_type.value,
                    status='active',
                    current_period_start=datetime.fromtimestamp(subscription.get('current_period_start', 0)),
                    current_period_end=datetime.fromtimestamp(subscription.get('current_period_end', 0))
                )

                # 获取计划配置并更新用户积分
                plan_configs = {
                    'free': {'credits': 1000},
                    'pro': {'credits': 10000},
                    'enterprise': {'credits': 50000}
                }
                plan_config = plan_configs.get(plan_type.value, plan_configs['free'])
                
                # 更新用户的订阅状态和积分
                await user_service.db_service.update_user_subscription_status(
                    user_id=user.id,
                    subscription_status=plan_type.value,
                    credits_total=plan_config['credits'],
                    credits_remaining=plan_config['credits']
                )

            result = {
                "type": "checkout_completed",
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "plan_type": plan_type.value,
                "metadata": metadata,
                "subscription": subscription,
                "user_updated": True
            }

            logger.info(f"Checkout completed processed: {subscription_id}, user: {auth0_user_id}")
            return result

        except Exception as e:
            logger.error(f"Error handling checkout completed: {str(e)}")
            raise ValueError(f"Failed to handle checkout completed: {str(e)}")

    async def handle_subscription_created(self, event_data: Dict[str, Any], 
                                        user_service=None) -> Dict[str, Any]:
        """
        处理订阅创建事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            subscription = event_data
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            status = subscription['status']
            
            # 确定计划类型
            price_id = subscription['items']['data'][0]['price']['id']
            plan_type = self.determine_plan_from_price_id(price_id)

            # 从 Stripe 获取客户信息来找到用户
            customer = await self.get_customer(customer_id)
            customer_email = customer.get('email') if customer else None

            # 更新数据库中的用户和订阅信息
            if user_service and user_service.db_service and customer_email:
                # 通过邮箱获取用户
                user = await user_service.get_user_by_email(customer_email)
                if user:
                    # 创建订阅记录
                    await user_service.db_service.create_subscription(
                        user_id=user.id,
                        stripe_subscription_id=subscription_id,
                        stripe_customer_id=customer_id,
                        plan_type=plan_type.value,
                        status=status,
                        current_period_start=datetime.fromtimestamp(subscription.get('current_period_start', 0)),
                        current_period_end=datetime.fromtimestamp(subscription.get('current_period_end', 0))
                    )

                    # 获取计划配置并更新用户积分
                    plan_configs = {
                        'free': {'credits': 1000},
                        'pro': {'credits': 10000},
                        'enterprise': {'credits': 50000}
                    }
                    plan_config = plan_configs.get(plan_type.value, plan_configs['free'])
                    
                    # 更新用户的订阅状态和积分
                    await user_service.db_service.update_user_subscription_status(
                        user_id=user.id,
                        subscription_status=plan_type.value,
                        credits_total=plan_config['credits'],
                        credits_remaining=plan_config['credits']
                    )

                    logger.info(f"Subscription created and user updated: {subscription_id}, user: {user.id}")

            result = {
                "type": "subscription_created",
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "status": status,
                "plan_type": plan_type.value,
                "customer_email": customer_email,
                "current_period_start": datetime.fromtimestamp(subscription.get('current_period_start', 0)),
                "current_period_end": datetime.fromtimestamp(subscription.get('current_period_end', 0)),
                "database_updated": True
            }

            return result

        except Exception as e:
            logger.error(f"Error handling subscription created: {str(e)}")
            raise ValueError(f"Failed to handle subscription created: {str(e)}")

    async def handle_subscription_updated(self, event_data: Dict[str, Any], 
                                        user_service=None) -> Dict[str, Any]:
        """
        处理订阅更新事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            subscription = event_data
            subscription_id = subscription['id']
            customer_id = subscription['customer']
            status = subscription['status']
            
            # 确定计划类型
            price_id = subscription['items']['data'][0]['price']['id']
            plan_type = self.determine_plan_from_price_id(price_id)

            # 更新数据库中的订阅信息
            if user_service and user_service.db_service:
                # 更新订阅状态
                await user_service.db_service.update_subscription_by_stripe_id(
                    stripe_subscription_id=subscription_id,
                    updates={
                        'status': status,
                        'plan_type': plan_type.value,
                        'current_period_start': datetime.fromtimestamp(subscription['current_period_start']).isoformat(),
                        'current_period_end': datetime.fromtimestamp(subscription['current_period_end']).isoformat()
                    }
                )

                # 如果订阅状态变为取消或过期，更新用户状态
                if status in ['canceled', 'unpaid', 'past_due']:
                    subscription_record = await user_service.db_service.get_subscription_by_stripe_id(subscription_id)
                    if subscription_record:
                        await user_service.db_service.update_user_subscription_status(
                            user_id=subscription_record['user_id'],
                            subscription_status='free',
                            credits_total=1000,
                            credits_remaining=1000
                        )

            result = {
                "type": "subscription_updated",
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "status": status,
                "plan_type": plan_type.value,
                "current_period_start": datetime.fromtimestamp(subscription['current_period_start']),
                "current_period_end": datetime.fromtimestamp(subscription['current_period_end']),
                "database_updated": True
            }

            logger.info(f"Subscription updated processed: {subscription_id}, status: {status}")
            return result

        except Exception as e:
            logger.error(f"Error handling subscription updated: {str(e)}")
            raise ValueError(f"Failed to handle subscription updated: {str(e)}")

    async def handle_subscription_deleted(self, event_data: Dict[str, Any], 
                                        user_service=None) -> Dict[str, Any]:
        """
        处理订阅删除事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            subscription = event_data
            subscription_id = subscription['id']
            customer_id = subscription['customer']

            result = {
                "type": "subscription_deleted",
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "canceled_at": datetime.fromtimestamp(subscription.get('canceled_at', 0))
            }

            logger.info(f"Subscription deleted processed: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error handling subscription deleted: {str(e)}")
            raise ValueError(f"Failed to handle subscription deleted: {str(e)}")

    async def handle_payment_succeeded(self, event_data: Dict[str, Any], 
                                      user_service=None) -> Dict[str, Any]:
        """
        处理支付成功事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            invoice = event_data
            subscription_id = invoice.get('subscription')
            customer_id = invoice['customer']
            amount_paid = invoice['amount_paid']

            result = {
                "type": "payment_succeeded",
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "amount_paid": amount_paid,
                "invoice_id": invoice['id'],
                "period_start": datetime.fromtimestamp(invoice['period_start']),
                "period_end": datetime.fromtimestamp(invoice['period_end'])
            }

            logger.info(f"Payment succeeded processed: {invoice['id']}")
            return result

        except Exception as e:
            logger.error(f"Error handling payment succeeded: {str(e)}")
            raise ValueError(f"Failed to handle payment succeeded: {str(e)}")

    async def handle_payment_failed(self, event_data: Dict[str, Any], 
                                   user_service=None) -> Dict[str, Any]:
        """
        处理支付失败事件
        
        Args:
            event_data: Stripe 事件数据
            user_service: 用户服务实例（用于数据库操作）
            
        Returns:
            处理结果
        """
        try:
            invoice = event_data
            subscription_id = invoice.get('subscription')
            customer_id = invoice['customer']
            amount_due = invoice['amount_due']

            result = {
                "type": "payment_failed",
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "amount_due": amount_due,
                "invoice_id": invoice['id'],
                "next_payment_attempt": invoice.get('next_payment_attempt')
            }

            logger.info(f"Payment failed processed: {invoice['id']}")
            return result

        except Exception as e:
            logger.error(f"Error handling payment failed: {str(e)}")
            raise ValueError(f"Failed to handle payment failed: {str(e)}")

    async def get_usage_records(self, subscription_item_id: str, 
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        获取使用记录（用于按量计费）
        
        Args:
            subscription_item_id: 订阅项目ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            使用记录列表
        """
        try:
            params = {"subscription_item": subscription_item_id}
            if start_date:
                params["starting_after"] = int(start_date.timestamp())
            if end_date:
                params["ending_before"] = int(end_date.timestamp())

            usage_records = stripe.UsageRecord.list(**params)
            return usage_records.data

        except stripe.error.StripeError as e:
            logger.error(f"Error getting usage records: {str(e)}")
            return []

    async def create_usage_record(self, subscription_item_id: str, quantity: int,
                                timestamp: Optional[datetime] = None) -> bool:
        """
        创建使用记录（用于按量计费）
        
        Args:
            subscription_item_id: 订阅项目ID
            quantity: 使用数量
            timestamp: 时间戳（可选）
            
        Returns:
            是否创建成功
        """
        try:
            params = {
                "quantity": quantity,
                "action": "increment"
            }
            if timestamp:
                params["timestamp"] = int(timestamp.timestamp())

            stripe.UsageRecord.create(
                subscription_item=subscription_item_id,
                **params
            )

            logger.info(f"Usage record created: {subscription_item_id}, quantity: {quantity}")
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Error creating usage record: {str(e)}")
            return False 