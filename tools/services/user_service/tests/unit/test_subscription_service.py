"""
Unit tests for SubscriptionService

Tests subscription management functionality including:
- Subscription creation and retrieval
- Plan upgrades and downgrades
- Subscription analytics
- Plan configuration management
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from tools.services.user_service.subscription_service import SubscriptionService
from tools.services.user_service.models import (
    Subscription, SubscriptionStatus, StripeSubscriptionStatus
)


class TestSubscriptionService:
    """Test suite for SubscriptionService class"""

    @pytest.fixture
    def subscription_service(self):
        """Subscription service instance for testing"""
        return SubscriptionService()

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, subscription_service):
        """Test successful subscription creation"""
        # Execute
        result = await subscription_service.create_subscription(
            user_id=1,
            plan_type=SubscriptionStatus.PRO,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123"
        )
        
        # Assert
        assert result["success"] is True
        assert result["subscription"]["user_id"] == 1
        assert result["subscription"]["plan_type"] == SubscriptionStatus.PRO
        assert result["subscription"]["stripe_subscription_id"] == "sub_test123"
        assert result["subscription"]["stripe_customer_id"] == "cus_test123"
        assert result["plan_config"]["credits"] == 10000

    @pytest.mark.asyncio
    async def test_create_subscription_free_plan(self, subscription_service):
        """Test free plan subscription creation"""
        # Execute
        result = await subscription_service.create_subscription(
            user_id=1,
            plan_type=SubscriptionStatus.FREE
        )
        
        # Assert
        assert result["success"] is True
        assert result["subscription"]["plan_type"] == SubscriptionStatus.FREE
        assert result["plan_config"]["credits"] == 1000
        assert result["plan_config"]["price"] == 0

    @pytest.mark.asyncio
    async def test_create_subscription_enterprise_plan(self, subscription_service):
        """Test enterprise plan subscription creation"""
        # Execute
        result = await subscription_service.create_subscription(
            user_id=1,
            plan_type=SubscriptionStatus.ENTERPRISE
        )
        
        # Assert
        assert result["success"] is True
        assert result["subscription"]["plan_type"] == SubscriptionStatus.ENTERPRISE
        assert result["plan_config"]["credits"] == 50000
        assert result["plan_config"]["price"] == 10000

    @pytest.mark.asyncio
    async def test_get_subscription_by_user_id_success(self, subscription_service):
        """Test successful subscription retrieval by user ID"""
        # Execute
        result = await subscription_service.get_subscription_by_user_id(1)
        
        # Assert
        assert result is not None
        assert result["subscription"]["user_id"] == 1
        assert result["subscription"]["plan_type"] == SubscriptionStatus.FREE
        assert result["is_active"] is True
        assert "plan_config" in result

    @pytest.mark.asyncio
    async def test_get_subscription_by_user_id_not_found(self, subscription_service):
        """Test subscription retrieval for non-existent user"""
        # Execute
        result = await subscription_service.get_subscription_by_user_id(None)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_subscription_by_stripe_id(self, subscription_service):
        """Test subscription retrieval by Stripe ID"""
        # Execute
        result = await subscription_service.get_subscription_by_stripe_id("sub_test123")
        
        # Assert
        assert result is None  # Currently returns None in implementation

    @pytest.mark.asyncio
    async def test_update_subscription_status_success(self, subscription_service):
        """Test successful subscription status update"""
        # Execute
        result = await subscription_service.update_subscription_status(
            subscription_id=1,
            status=StripeSubscriptionStatus.CANCELED,
            stripe_data={
                "current_period_start": 1640995200,
                "current_period_end": 1643673600
            }
        )
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_update_subscription_status_without_stripe_data(self, subscription_service):
        """Test subscription status update without Stripe data"""
        # Execute
        result = await subscription_service.update_subscription_status(
            subscription_id=1,
            status=StripeSubscriptionStatus.PAST_DUE
        )
        
        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediate(self, subscription_service):
        """Test immediate subscription cancellation"""
        # Execute
        result = await subscription_service.cancel_subscription(
            subscription_id=1,
            immediate=True
        )
        
        # Assert
        assert result["success"] is True
        assert result["canceled_immediately"] is True
        assert "订阅取消成功" in result["message"]

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self, subscription_service):
        """Test subscription cancellation at period end"""
        # Execute
        result = await subscription_service.cancel_subscription(
            subscription_id=1,
            immediate=False
        )
        
        # Assert
        assert result["success"] is True
        assert result["canceled_immediately"] is False
        assert "当前周期结束时取消" in result["message"]

    @pytest.mark.asyncio
    async def test_upgrade_subscription_success(self, subscription_service):
        """Test successful subscription upgrade"""
        # Mock current subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = {
                "subscription": {"plan_type": SubscriptionStatus.FREE.value},
                "plan_config": {"credits": 1000}
            }
            
            # Execute
            result = await subscription_service.upgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.PRO
            )
            
            # Assert
            assert result["success"] is True
            assert result["old_plan"] == "free"
            assert result["new_plan"] == "pro"
            assert result["new_config"]["credits"] == 10000

    @pytest.mark.asyncio
    async def test_upgrade_subscription_no_current_subscription(self, subscription_service):
        """Test subscription upgrade with no current subscription"""
        # Mock no current subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = None
            
            # Execute
            result = await subscription_service.upgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.PRO
            )
            
            # Assert
            assert result["success"] is False
            assert "未找到当前订阅" in result["error"]

    @pytest.mark.asyncio
    async def test_upgrade_subscription_invalid_upgrade(self, subscription_service):
        """Test invalid subscription upgrade (downgrade attempt)"""
        # Mock current PRO subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = {
                "subscription": {"plan_type": SubscriptionStatus.PRO.value},
                "plan_config": {"credits": 10000}
            }
            
            # Execute - try to "upgrade" to FREE (which is actually a downgrade)
            result = await subscription_service.upgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.FREE
            )
            
            # Assert
            assert result["success"] is False
            assert "无效的升级" in result["error"]

    @pytest.mark.asyncio
    async def test_upgrade_subscription_same_plan(self, subscription_service):
        """Test upgrade to same plan"""
        # Mock current PRO subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = {
                "subscription": {"plan_type": SubscriptionStatus.PRO.value},
                "plan_config": {"credits": 10000}
            }
            
            # Execute - try to "upgrade" to same plan
            result = await subscription_service.upgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.PRO
            )
            
            # Assert
            assert result["success"] is False
            assert "只能升级到更高级的计划" in result["message"]

    @pytest.mark.asyncio
    async def test_downgrade_subscription_success(self, subscription_service):
        """Test successful subscription downgrade"""
        # Mock current PRO subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = {
                "subscription": {"plan_type": SubscriptionStatus.PRO.value},
                "plan_config": {"credits": 10000}
            }
            
            # Execute
            result = await subscription_service.downgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.FREE
            )
            
            # Assert
            assert result["success"] is True
            assert result["old_plan"] == "pro"
            assert result["new_plan"] == "free"
            assert result["new_config"]["credits"] == 1000
            assert "下个周期" in result["effective_date"]

    @pytest.mark.asyncio
    async def test_downgrade_subscription_no_current_subscription(self, subscription_service):
        """Test subscription downgrade with no current subscription"""
        # Mock no current subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = None
            
            # Execute
            result = await subscription_service.downgrade_subscription(
                user_id=1,
                new_plan=SubscriptionStatus.FREE
            )
            
            # Assert
            assert result["success"] is False
            assert "未找到当前订阅" in result["error"]

    @pytest.mark.asyncio
    async def test_get_subscription_analytics_success(self, subscription_service):
        """Test successful subscription analytics retrieval"""
        # Mock subscription with proper datetime strings
        mock_subscription = {
            "subscription": {
                "id": 1,
                "plan_type": SubscriptionStatus.PRO,
                "status": StripeSubscriptionStatus.ACTIVE,
                "current_period_start": "2022-01-01T00:00:00+00:00",
                "current_period_end": "2022-02-01T00:00:00+00:00"
            },
            "plan_config": {
                "credits": 10000,
                "features": ["advanced_ai", "priority_support"],
                "price": 2000
            },
            "is_active": True
        }
        
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get, \
             patch('datetime.datetime') as mock_datetime:
            
            mock_get.return_value = mock_subscription
            # Mock current time to be in the middle of the subscription period
            mock_datetime.utcnow.return_value = datetime(2022, 1, 15)
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            # Execute
            result = await subscription_service.get_subscription_analytics(user_id=1)
            
            # Assert
            assert result["success"] is True
            analytics = result["analytics"]
            assert analytics["subscription_id"] == 1
            assert analytics["plan_type"] == SubscriptionStatus.PRO
            assert analytics["status"] == StripeSubscriptionStatus.ACTIVE
            assert analytics["credits_allocated"] == 10000
            assert analytics["monthly_value"] == 20.0  # 2000 cents -> $20
            assert analytics["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_subscription_analytics_no_subscription(self, subscription_service):
        """Test subscription analytics for non-existent subscription"""
        # Mock no subscription
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = None
            
            # Execute
            result = await subscription_service.get_subscription_analytics(user_id=1)
            
            # Assert
            assert result["success"] is False
            assert "未找到订阅信息" in result["message"]

    def test_get_plan_comparison(self, subscription_service):
        """Test plan comparison retrieval"""
        # Execute
        result = subscription_service.get_plan_comparison()
        
        # Assert
        assert "plans" in result
        assert "currency" in result
        assert "billing_cycle" in result
        
        plans = result["plans"]
        assert "free" in plans
        assert "pro" in plans
        assert "enterprise" in plans
        
        # Check FREE plan
        free_plan = plans["free"]
        assert free_plan["price_monthly"] == 0.0
        assert free_plan["credits"] == 1000
        assert free_plan["recommended"] is False
        
        # Check PRO plan
        pro_plan = plans["pro"]
        assert pro_plan["price_monthly"] == 20.0
        assert pro_plan["credits"] == 10000
        assert pro_plan["recommended"] is True
        
        # Check ENTERPRISE plan
        enterprise_plan = plans["enterprise"]
        assert enterprise_plan["price_monthly"] == 100.0
        assert enterprise_plan["credits"] == 50000
        assert enterprise_plan["recommended"] is False

    @pytest.mark.asyncio
    async def test_check_subscription_expiry_active(self, subscription_service):
        """Test subscription expiry check for active subscription"""
        # Mock subscription expiring in 15 days
        future_date = datetime.utcnow() + timedelta(days=15)
        mock_subscription = {
            "subscription": {
                "plan_type": SubscriptionStatus.PRO,
                "current_period_end": future_date.isoformat() + "Z"
            }
        }
        
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = mock_subscription
            
            # Execute
            result = await subscription_service.check_subscription_expiry(user_id=1)
            
            # Assert
            assert result["has_subscription"] is True
            assert result["status"] == "active"
            assert result["days_remaining"] == 15
            assert result["needs_renewal"] is False
            assert result["is_expired"] is False

    @pytest.mark.asyncio
    async def test_check_subscription_expiry_warning(self, subscription_service):
        """Test subscription expiry check for subscription in warning period"""
        # Mock subscription expiring in 5 days
        future_date = datetime.utcnow() + timedelta(days=5)
        mock_subscription = {
            "subscription": {
                "plan_type": SubscriptionStatus.PRO,
                "current_period_end": future_date.isoformat() + "Z"
            }
        }
        
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = mock_subscription
            
            # Execute
            result = await subscription_service.check_subscription_expiry(user_id=1)
            
            # Assert
            assert result["has_subscription"] is True
            assert result["status"] == "warning"
            assert result["days_remaining"] == 5
            assert result["needs_renewal"] is True
            assert result["is_expired"] is False

    @pytest.mark.asyncio
    async def test_check_subscription_expiry_critical(self, subscription_service):
        """Test subscription expiry check for subscription in critical period"""
        # Mock subscription expiring in 2 days
        future_date = datetime.utcnow() + timedelta(days=2)
        mock_subscription = {
            "subscription": {
                "plan_type": SubscriptionStatus.PRO,
                "current_period_end": future_date.isoformat() + "Z"
            }
        }
        
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = mock_subscription
            
            # Execute
            result = await subscription_service.check_subscription_expiry(user_id=1)
            
            # Assert
            assert result["has_subscription"] is True
            assert result["status"] == "critical"
            assert result["days_remaining"] == 2
            assert result["needs_renewal"] is True
            assert result["is_expired"] is False

    @pytest.mark.asyncio
    async def test_check_subscription_expiry_expired(self, subscription_service):
        """Test subscription expiry check for expired subscription"""
        # Mock subscription that expired 2 days ago
        past_date = datetime.utcnow() - timedelta(days=2)
        mock_subscription = {
            "subscription": {
                "plan_type": SubscriptionStatus.PRO,
                "current_period_end": past_date.isoformat() + "Z"
            }
        }
        
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = mock_subscription
            
            # Execute
            result = await subscription_service.check_subscription_expiry(user_id=1)
            
            # Assert
            assert result["has_subscription"] is True
            assert result["status"] == "expired"
            assert result["days_remaining"] == 0
            assert result["needs_renewal"] is True
            assert result["is_expired"] is True

    @pytest.mark.asyncio
    async def test_check_subscription_expiry_no_subscription(self, subscription_service):
        """Test subscription expiry check for user with no subscription"""
        with patch.object(subscription_service, 'get_subscription_by_user_id') as mock_get:
            mock_get.return_value = None
            
            # Execute
            result = await subscription_service.check_subscription_expiry(user_id=1)
            
            # Assert
            assert result["has_subscription"] is False
            assert "用户没有有效订阅" in result["message"]

    @pytest.mark.asyncio
    async def test_error_handling_in_create_subscription(self, subscription_service):
        """Test error handling in subscription creation"""
        # Mock an exception in the creation process
        with patch('tools.services.user_service.subscription_service.Subscription', side_effect=Exception("Database error")):
            
            # Execute
            result = await subscription_service.create_subscription(
                user_id=1,
                plan_type=SubscriptionStatus.PRO
            )
            
            # Assert
            assert result["success"] is False
            assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_plan_config_structure(self, subscription_service):
        """Test that all plan configurations have required fields"""
        # Execute
        plan_configs = subscription_service.plan_configs
        
        # Assert
        for plan, config in plan_configs.items():
            assert isinstance(plan, SubscriptionStatus)
            assert "credits" in config
            assert "features" in config
            assert "price" in config
            assert "duration_days" in config
            assert isinstance(config["credits"], int)
            assert isinstance(config["features"], list)
            assert isinstance(config["price"], int)
            assert isinstance(config["duration_days"], int)

    @pytest.mark.asyncio
    async def test_subscription_hierarchy_validation(self, subscription_service):
        """Test subscription plan hierarchy validation"""
        # Test the plan hierarchy used in upgrades/downgrades
        plan_hierarchy = [SubscriptionStatus.FREE, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]
        
        # Assert hierarchy order
        assert plan_hierarchy.index(SubscriptionStatus.FREE) < plan_hierarchy.index(SubscriptionStatus.PRO)
        assert plan_hierarchy.index(SubscriptionStatus.PRO) < plan_hierarchy.index(SubscriptionStatus.ENTERPRISE)
        
        # Test that all plans in config are in hierarchy
        for plan in subscription_service.plan_configs.keys():
            assert plan in plan_hierarchy