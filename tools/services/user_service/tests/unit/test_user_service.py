"""
Unit tests for UserService

Tests all core user management functionality including:
- User creation and retrieval
- Credit consumption
- User analytics and status management
- Error handling and edge cases
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from tools.services.user_service.user_service import UserService
from tools.services.user_service.models import (
    User, UserUpdate, SubscriptionStatus, CreditConsumptionResponse
)
from tests.conftest import assert_user_fields


class TestUserService:
    """Test suite for UserService class"""

    @pytest.mark.asyncio
    async def test_get_user_by_auth0_id_cache_hit(self, user_service, sample_user):
        """Test getting user from cache when available"""
        # Setup: Add user to cache
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.get_user_by_auth0_id(sample_user.auth0_id)
        
        # Assert
        assert result is not None
        assert result.auth0_id == sample_user.auth0_id
        assert result.email == sample_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_auth0_id_cache_miss(self, user_service):
        """Test getting user when not in cache"""
        # Execute
        result = await user_service.get_user_by_auth0_id("nonexistent")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_auth0_id_with_database(self, user_service_with_db, sample_user_data):
        """Test getting user from database"""
        # Setup: Mock database response
        user_service_with_db.db_service.get_user_by_auth0_id.return_value = sample_user_data
        
        # Execute
        result = await user_service_with_db.get_user_by_auth0_id("auth0|test123")
        
        # Assert
        assert result is not None
        assert result.auth0_id == sample_user_data["auth0_id"]
        user_service_with_db.db_service.get_user_by_auth0_id.assert_called_once_with("auth0|test123")

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, sample_user):
        """Test getting user by internal ID"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.get_user_by_id(sample_user.id)
        
        # Assert
        assert result is not None
        assert result.id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, sample_user):
        """Test getting user by email"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.get_user_by_email(sample_user.email)
        
        # Assert
        assert result is not None
        assert result.email == sample_user.email

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service):
        """Test successful user creation"""
        # Execute
        result = await user_service.create_user(
            auth0_id="auth0|new123",
            email="new@example.com",
            name="New User"
        )
        
        # Assert
        assert result is not None
        assert result.auth0_id == "auth0|new123"
        assert result.email == "new@example.com"
        assert result.name == "New User"
        assert result.credits_remaining == 1000
        assert result.credits_total == 1000
        assert result.subscription_status == SubscriptionStatus.FREE
        assert result.is_active is True
        
        # Check user is in cache
        assert "auth0|new123" in user_service._users_cache

    @pytest.mark.asyncio
    async def test_create_user_with_database(self, user_service_with_db, sample_user_data):
        """Test user creation with database"""
        # Setup: Mock database response
        user_service_with_db.db_service.create_user.return_value = sample_user_data
        
        # Execute
        result = await user_service_with_db.create_user(
            auth0_id="auth0|new123",
            email="new@example.com", 
            name="New User"
        )
        
        # Assert
        assert result is not None
        user_service_with_db.db_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_user_exists_new_user(self, user_service):
        """Test ensure_user_exists creates new user when not found"""
        # Execute
        result = await user_service.ensure_user_exists(
            auth0_id="auth0|new123",
            email="new@example.com",
            name="New User"
        )
        
        # Assert
        assert result is not None
        assert result.auth0_id == "auth0|new123"
        assert "auth0|new123" in user_service._users_cache

    @pytest.mark.asyncio
    async def test_ensure_user_exists_existing_user(self, user_service, sample_user):
        """Test ensure_user_exists returns existing user"""
        # Setup: Add user to cache
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.ensure_user_exists(
            auth0_id=sample_user.auth0_id,
            email=sample_user.email,
            name=sample_user.name
        )
        
        # Assert
        assert result is not None
        assert result.auth0_id == sample_user.auth0_id

    @pytest.mark.asyncio
    async def test_ensure_user_exists_updates_info(self, user_service, sample_user):
        """Test ensure_user_exists updates user info when changed"""
        # Setup: Add user to cache
        user_service._users_cache[sample_user.auth0_id] = sample_user
        original_email = sample_user.email
        
        # Execute with different email/name
        result = await user_service.ensure_user_exists(
            auth0_id=sample_user.auth0_id,
            email="updated@example.com",
            name="Updated Name"
        )
        
        # Assert
        assert result.email == "updated@example.com"
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, sample_user):
        """Test successful user update"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        update_data = UserUpdate(
            email="updated@example.com",
            name="Updated Name",
            credits_remaining=500
        )
        result = await user_service.update_user(sample_user.id, update_data)
        
        # Assert
        assert result is not None
        assert result.email == "updated@example.com"
        assert result.name == "Updated Name"
        assert result.credits_remaining == 500

    @pytest.mark.asyncio
    async def test_consume_credits_success(self, user_service, sample_user):
        """Test successful credit consumption"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        original_credits = sample_user.credits_remaining
        
        # Execute
        result = await user_service.consume_credits(
            user_id=sample_user.id,
            amount=100,
            reason="test_api_call"
        )
        
        # Assert
        assert result.success is True
        assert result.consumed_amount == 100
        assert result.remaining_credits == original_credits - 100
        assert "成功消费 100 积分" in result.message

    @pytest.mark.asyncio
    async def test_consume_credits_insufficient_credits(self, user_service, sample_user):
        """Test credit consumption with insufficient credits"""
        # Setup
        sample_user.credits_remaining = 50
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.consume_credits(
            user_id=sample_user.id,
            amount=100,
            reason="test_api_call"
        )
        
        # Assert
        assert result.success is False
        assert result.consumed_amount == 0
        assert result.remaining_credits == 50
        assert "积分不足" in result.message

    @pytest.mark.asyncio
    async def test_consume_credits_user_not_found(self, user_service):
        """Test credit consumption for non-existent user"""
        # Execute
        result = await user_service.consume_credits(
            user_id=999,
            amount=100,
            reason="test_api_call"
        )
        
        # Assert
        assert result.success is False
        assert result.consumed_amount == 0
        assert "用户不存在" in result.message

    @pytest.mark.asyncio
    async def test_allocate_credits_by_plan(self, user_service, sample_user):
        """Test credit allocation by subscription plan"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.allocate_credits_by_plan(
            user_id=sample_user.id,
            plan=SubscriptionStatus.PRO
        )
        
        # Assert
        assert result is True
        
        # Check user was updated
        updated_user = user_service._users_cache[sample_user.auth0_id]
        assert updated_user.credits_total == 10000
        assert updated_user.credits_remaining == 10000
        assert updated_user.subscription_status == SubscriptionStatus.PRO

    @pytest.mark.asyncio
    async def test_log_api_usage_with_database(self, user_service_with_db):
        """Test API usage logging with database"""
        # Execute
        result = await user_service_with_db.log_api_usage(
            user_id=1,
            endpoint="/test/endpoint",
            tokens_used=5,
            request_data='{"test": true}',
            response_data='{"result": "success"}'
        )
        
        # Assert
        assert result is True
        user_service_with_db.db_service.log_api_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_api_usage_fallback(self, user_service):
        """Test API usage logging fallback when no database"""
        # Execute
        result = await user_service.log_api_usage(
            user_id=1,
            endpoint="/test/endpoint",
            tokens_used=5
        )
        
        # Assert
        assert result is True  # Should still return True for fallback logging

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, user_service, sample_user):
        """Test getting user info response"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.get_user_info(sample_user.auth0_id)
        
        # Assert
        assert result is not None
        assert result.user_id == sample_user.auth0_id
        assert result.email == sample_user.email
        assert result.name == sample_user.name
        assert result.credits == sample_user.credits_remaining
        assert result.plan == sample_user.subscription_status

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, user_service):
        """Test getting user info for non-existent user"""
        # Execute
        result = await user_service.get_user_info("nonexistent")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_analytics(self, user_service, sample_user, mock_subscription_service):
        """Test getting user analytics"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        mock_subscription_service.get_subscription_analytics.return_value = {
            "success": True,
            "analytics": {"days_remaining": 25, "plan": "free"}
        }
        
        # Execute
        result = await user_service.get_user_analytics(sample_user.id)
        
        # Assert
        assert "user_info" in result
        assert "credits" in result
        assert "subscription" in result
        assert result["credits"]["total"] == sample_user.credits_total
        assert result["credits"]["remaining"] == sample_user.credits_remaining

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, sample_user):
        """Test user deactivation"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.deactivate_user(
            user_id=sample_user.id,
            reason="test_deactivation"
        )
        
        # Assert
        assert result is True
        
        # Check user was deactivated
        updated_user = user_service._users_cache[sample_user.auth0_id]
        assert updated_user.is_active is False

    @pytest.mark.asyncio
    async def test_reactivate_user(self, user_service, sample_user):
        """Test user reactivation"""
        # Setup
        sample_user.is_active = False
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = await user_service.reactivate_user(user_id=sample_user.id)
        
        # Assert
        assert result is True
        
        # Check user was reactivated
        updated_user = user_service._users_cache[sample_user.auth0_id]
        assert updated_user.is_active is True

    @pytest.mark.asyncio
    async def test_verify_user_token_success(self, user_service, sample_user, mock_auth_service):
        """Test successful token verification"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        mock_auth_service.verify_token.return_value = {
            "sub": sample_user.auth0_id,
            "email": sample_user.email
        }
        
        # Execute
        result = await user_service.verify_user_token("valid_token")
        
        # Assert
        assert result is not None
        assert result["verified"] is True
        assert result["user"]["auth0_id"] == sample_user.auth0_id

    @pytest.mark.asyncio
    async def test_verify_user_token_invalid(self, user_service, mock_auth_service):
        """Test token verification with invalid token"""
        # Setup
        mock_auth_service.verify_token.side_effect = Exception("Invalid token")
        
        # Execute
        result = await user_service.verify_user_token("invalid_token")
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_user_token_inactive_user(self, user_service, sample_user, mock_auth_service):
        """Test token verification for inactive user"""
        # Setup
        sample_user.is_active = False
        user_service._users_cache[sample_user.auth0_id] = sample_user
        mock_auth_service.verify_token.return_value = {
            "sub": sample_user.auth0_id,
            "email": sample_user.email
        }
        
        # Execute
        result = await user_service.verify_user_token("valid_token")
        
        # Assert
        assert result is None

    def test_get_service_status(self, user_service, sample_user):
        """Test service status retrieval"""
        # Setup: Add some users to cache
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute
        result = user_service.get_service_status()
        
        # Assert
        assert result["service"] == "UserService"
        assert result["status"] == "operational"
        assert result["cached_users"] == 1
        assert "services" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_error_handling_database_failure(self, user_service_with_db):
        """Test error handling when database operations fail"""
        # Setup: Mock database to raise exception
        user_service_with_db.db_service.get_user_by_auth0_id.side_effect = Exception("Database error")
        
        # Execute
        result = await user_service_with_db.get_user_by_auth0_id("auth0|test123")
        
        # Assert: Should fall back to cache
        assert result is None  # No user in cache, so returns None

    @pytest.mark.asyncio 
    async def test_concurrent_credit_consumption(self, user_service, sample_user):
        """Test handling of concurrent credit consumption requests"""
        # Setup
        user_service._users_cache[sample_user.auth0_id] = sample_user
        
        # Execute multiple credit consumptions concurrently
        import asyncio
        tasks = [
            user_service.consume_credits(sample_user.id, 100, "test1"),
            user_service.consume_credits(sample_user.id, 200, "test2"),
            user_service.consume_credits(sample_user.id, 300, "test3")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Assert: Only one should succeed due to insufficient credits
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        # At least one should succeed, others should fail due to insufficient credits
        assert len(successful_results) >= 1
        assert any("积分不足" in r.message for r in failed_results)