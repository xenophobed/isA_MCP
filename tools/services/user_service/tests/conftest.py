"""
Test configuration and fixtures for user service

Provides common fixtures, mocks, and test utilities
for all test modules in the user service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from tools.services.user_service.models import (
    User, SubscriptionStatus, StripeSubscriptionStatus,
    Subscription, Auth0UserInfo
)
from tools.services.user_service.user_service import UserService
from tools.services.user_service.auth_service import Auth0Service
from tools.services.user_service.subscription_service import SubscriptionService
from tools.services.user_service.payment_service import PaymentService


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_auth0_config():
    """Mock Auth0 configuration"""
    return {
        "domain": "test-domain.auth0.com",
        "audience": "https://test-domain.auth0.com/api/v2/",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret"
    }


@pytest.fixture
def mock_stripe_config():
    """Mock Stripe configuration"""
    return {
        "secret_key": "sk_test_123",
        "webhook_secret": "whsec_test_123",
        "pro_price_id": "price_pro_123",
        "enterprise_price_id": "price_enterprise_123"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": 1,
        "auth0_id": "auth0|test123",
        "email": "test@example.com",
        "name": "Test User",
        "credits_remaining": 1000,
        "credits_total": 1000,
        "subscription_status": SubscriptionStatus.FREE,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
def sample_user(sample_user_data):
    """Sample user model instance"""
    return User(**sample_user_data)


@pytest.fixture
def sample_subscription_data():
    """Sample subscription data for testing"""
    return {
        "id": 1,
        "user_id": 1,
        "stripe_subscription_id": "sub_test123",
        "stripe_customer_id": "cus_test123",
        "status": StripeSubscriptionStatus.ACTIVE,
        "plan_type": SubscriptionStatus.PRO,
        "current_period_start": datetime.utcnow(),
        "current_period_end": datetime.utcnow() + timedelta(days=30),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
def sample_subscription(sample_subscription_data):
    """Sample subscription model instance"""
    return Subscription(**sample_subscription_data)


@pytest.fixture
def sample_auth0_user_info():
    """Sample Auth0 user info"""
    return Auth0UserInfo(
        sub="auth0|test123",
        email="test@example.com",
        name="Test User",
        picture="https://example.com/avatar.jpg",
        email_verified=True
    )


@pytest.fixture
def mock_database_service():
    """Mock database service"""
    mock_db = AsyncMock()
    
    # Configure common return values
    mock_db.get_user_by_auth0_id.return_value = None
    mock_db.get_user_by_id.return_value = None
    mock_db.get_user_by_email.return_value = None
    mock_db.create_user.return_value = None
    mock_db.update_user.return_value = True
    mock_db.log_api_usage.return_value = True
    mock_db.create_subscription.return_value = True
    mock_db.get_subscription_by_stripe_id.return_value = None
    mock_db.update_subscription_by_stripe_id.return_value = True
    mock_db.update_user_subscription_status.return_value = True
    
    return mock_db


@pytest.fixture
def mock_auth_service(mock_auth0_config):
    """Mock Auth0 service"""
    mock_auth = AsyncMock(spec=Auth0Service)
    
    # Configure common return values
    mock_auth.verify_token.return_value = {
        "sub": "auth0|test123",
        "email": "test@example.com",
        "aud": mock_auth0_config["audience"]
    }
    mock_auth.get_user_info.return_value = Auth0UserInfo(
        sub="auth0|test123",
        email="test@example.com",
        name="Test User",
        email_verified=True
    )
    mock_auth.get_management_token.return_value = "mock_management_token"
    mock_auth.update_user_metadata.return_value = True
    mock_auth.create_user.return_value = "auth0|test123"
    mock_auth.delete_user.return_value = True
    
    return mock_auth


@pytest.fixture
def mock_subscription_service():
    """Mock subscription service"""
    mock_sub = AsyncMock(spec=SubscriptionService)
    
    # Configure common return values
    mock_sub.create_subscription.return_value = {
        "success": True,
        "subscription": {"id": 1, "plan_type": "pro"},
        "plan_config": {"credits": 10000}
    }
    mock_sub.get_subscription_by_user_id.return_value = {
        "subscription": {"plan_type": "free", "status": "active"},
        "plan_config": {"credits": 1000},
        "is_active": True
    }
    mock_sub.get_subscription_analytics.return_value = {
        "success": True,
        "analytics": {"days_remaining": 30}
    }
    mock_sub.plan_configs = {
        SubscriptionStatus.FREE: {"credits": 1000},
        SubscriptionStatus.PRO: {"credits": 10000},
        SubscriptionStatus.ENTERPRISE: {"credits": 50000}
    }
    
    return mock_sub


@pytest.fixture
def mock_payment_service(mock_stripe_config):
    """Mock payment service"""
    mock_payment = AsyncMock(spec=PaymentService)
    
    # Configure common return values
    mock_payment.create_payment_intent.return_value = Mock(
        id="pi_test123",
        client_secret="pi_test123_secret",
        amount=2000,
        currency="usd",
        status="requires_payment_method"
    )
    mock_payment.create_checkout_session.return_value = Mock(
        id="cs_test123",
        url="https://checkout.stripe.com/test",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel"
    )
    mock_payment.verify_webhook_signature.return_value = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test123"}}
    }
    mock_payment.determine_plan_from_price_id.return_value = SubscriptionStatus.PRO
    
    return mock_payment


@pytest.fixture
def user_service(mock_auth_service, mock_subscription_service, mock_payment_service):
    """User service with mocked dependencies"""
    service = UserService(
        auth_service=mock_auth_service,
        subscription_service=mock_subscription_service,
        payment_service=mock_payment_service,
        use_database=False  # Use cache for testing
    )
    return service


@pytest.fixture
def user_service_with_db(mock_auth_service, mock_subscription_service, 
                        mock_payment_service, mock_database_service):
    """User service with mocked database"""
    service = UserService(
        auth_service=mock_auth_service,
        subscription_service=mock_subscription_service,
        payment_service=mock_payment_service,
        use_database=True
    )
    service.db_service = mock_database_service
    return service


@pytest.fixture
def stripe_webhook_payload():
    """Sample Stripe webhook payload"""
    return {
        "id": "evt_test_webhook",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test123",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "metadata": {
                    "auth0_user_id": "auth0|test123",
                    "user_email": "test@example.com",
                    "plan_type": "pro"
                }
            }
        }
    }


@pytest.fixture
def auth_token():
    """Sample JWT token for testing"""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.token"


class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
    
    def json(self):
        return self.json_data


@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses"""
    return MockResponse


# Helper functions for tests
def assert_user_fields(user: User, expected_data: Dict[str, Any]):
    """Assert that user fields match expected data"""
    assert user.auth0_id == expected_data["auth0_id"]
    assert user.email == expected_data["email"]
    assert user.name == expected_data["name"]
    assert user.is_active == expected_data.get("is_active", True)


def create_mock_jwt_payload(auth0_id: str = "auth0|test123", 
                           email: str = "test@example.com") -> Dict[str, Any]:
    """Create a mock JWT payload"""
    return {
        "sub": auth0_id,
        "email": email,
        "aud": "https://test-domain.auth0.com/api/v2/",
        "iss": "https://test-domain.auth0.com/",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }