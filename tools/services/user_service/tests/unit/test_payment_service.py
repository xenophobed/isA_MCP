"""
Unit tests for PaymentService

Tests Stripe payment integration functionality including:
- Payment intent creation
- Checkout session management
- Webhook handling
- Customer and subscription management
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import stripe

from tools.services.user_service.payment_service import PaymentService
from tools.services.user_service.models import (
    PaymentIntent, CheckoutSession, SubscriptionStatus
)


class TestPaymentService:
    """Test suite for PaymentService class"""

    @pytest.fixture
    def payment_service(self, mock_stripe_config):
        """Payment service instance for testing"""
        return PaymentService(
            secret_key=mock_stripe_config["secret_key"],
            webhook_secret=mock_stripe_config["webhook_secret"],
            pro_price_id=mock_stripe_config["pro_price_id"],
            enterprise_price_id=mock_stripe_config["enterprise_price_id"]
        )

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self, payment_service):
        """Test successful payment intent creation"""
        mock_intent = Mock()
        mock_intent.id = "pi_test123"
        mock_intent.client_secret = "pi_test123_secret"
        mock_intent.amount = 2000
        mock_intent.currency = "usd"
        mock_intent.status = "requires_payment_method"
        
        with patch('stripe.PaymentIntent.create', return_value=mock_intent):
            # Execute
            result = await payment_service.create_payment_intent(
                amount=2000,
                currency="usd",
                metadata={"user_id": "123"}
            )
            
            # Assert
            assert isinstance(result, PaymentIntent)
            assert result.id == "pi_test123"
            assert result.client_secret == "pi_test123_secret"
            assert result.amount == 2000
            assert result.currency == "usd"
            assert result.status == "requires_payment_method"

    @pytest.mark.asyncio
    async def test_create_payment_intent_default_currency(self, payment_service):
        """Test payment intent creation with default currency"""
        mock_intent = Mock()
        mock_intent.id = "pi_test123"
        mock_intent.client_secret = "pi_test123_secret"
        mock_intent.amount = 1000
        mock_intent.currency = "usd"
        mock_intent.status = "requires_payment_method"
        
        with patch('stripe.PaymentIntent.create', return_value=mock_intent) as mock_create:
            # Execute
            result = await payment_service.create_payment_intent(amount=1000)
            
            # Assert
            assert result.currency == "usd"
            mock_create.assert_called_once_with(
                amount=1000,
                currency="usd",
                metadata={},
                automatic_payment_methods={"enabled": True}
            )

    @pytest.mark.asyncio
    async def test_create_payment_intent_stripe_error(self, payment_service):
        """Test payment intent creation with Stripe error"""
        with patch('stripe.PaymentIntent.create', side_effect=stripe.error.CardError(
            message="Your card was declined.",
            param="card",
            code="card_declined"
        )):
            # Execute and Assert
            with pytest.raises(ValueError, match="Failed to create payment intent"):
                await payment_service.create_payment_intent(amount=2000)

    @pytest.mark.asyncio
    async def test_create_checkout_session_success(self, payment_service):
        """Test successful checkout session creation"""
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        
        with patch('stripe.checkout.Session.create', return_value=mock_session):
            # Execute
            result = await payment_service.create_checkout_session(
                price_id="price_test123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                customer_email="test@example.com"
            )
            
            # Assert
            assert isinstance(result, CheckoutSession)
            assert result.id == "cs_test123"
            assert result.url == "https://checkout.stripe.com/test"
            assert result.success_url == "https://example.com/success"
            assert result.cancel_url == "https://example.com/cancel"

    @pytest.mark.asyncio
    async def test_create_checkout_session_without_email(self, payment_service):
        """Test checkout session creation without customer email"""
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        
        with patch('stripe.checkout.Session.create', return_value=mock_session) as mock_create:
            # Execute
            result = await payment_service.create_checkout_session(
                price_id="price_test123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )
            
            # Assert
            assert isinstance(result, CheckoutSession)
            # Verify customer_email was not included in the call
            call_args = mock_create.call_args[1]
            assert "customer_email" not in call_args

    @pytest.mark.asyncio
    async def test_create_checkout_session_with_metadata(self, payment_service):
        """Test checkout session creation with metadata"""
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        
        metadata = {"user_id": "123", "plan": "pro"}
        
        with patch('stripe.checkout.Session.create', return_value=mock_session) as mock_create:
            # Execute
            result = await payment_service.create_checkout_session(
                price_id="price_test123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                metadata=metadata
            )
            
            # Assert
            call_args = mock_create.call_args[1]
            assert call_args["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_get_customer_success(self, payment_service):
        """Test successful customer retrieval"""
        mock_customer = {"id": "cus_test123", "email": "test@example.com"}
        
        with patch('stripe.Customer.retrieve', return_value=mock_customer):
            # Execute
            result = await payment_service.get_customer("cus_test123")
            
            # Assert
            assert result == mock_customer

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, payment_service):
        """Test customer retrieval for non-existent customer"""
        with patch('stripe.Customer.retrieve', side_effect=stripe.error.InvalidRequestError(
            message="No such customer: cus_nonexistent",
            param="id"
        )):
            # Execute
            result = await payment_service.get_customer("cus_nonexistent")
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_create_customer_success(self, payment_service):
        """Test successful customer creation"""
        mock_customer = Mock()
        mock_customer.id = "cus_test123"
        
        with patch('stripe.Customer.create', return_value=mock_customer):
            # Execute
            result = await payment_service.create_customer(
                email="test@example.com",
                name="Test User",
                metadata={"user_id": "123"}
            )
            
            # Assert
            assert result == "cus_test123"

    @pytest.mark.asyncio
    async def test_create_customer_minimal(self, payment_service):
        """Test customer creation with minimal data"""
        mock_customer = Mock()
        mock_customer.id = "cus_test123"
        
        with patch('stripe.Customer.create', return_value=mock_customer) as mock_create:
            # Execute
            result = await payment_service.create_customer(email="test@example.com")
            
            # Assert
            assert result == "cus_test123"
            call_args = mock_create.call_args[1]
            assert call_args["email"] == "test@example.com"
            assert "name" not in call_args
            assert "metadata" not in call_args

    @pytest.mark.asyncio
    async def test_get_subscription_success(self, payment_service):
        """Test successful subscription retrieval"""
        mock_subscription = {"id": "sub_test123", "status": "active"}
        
        with patch('stripe.Subscription.retrieve', return_value=mock_subscription):
            # Execute
            result = await payment_service.get_subscription("sub_test123")
            
            # Assert
            assert result == mock_subscription

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, payment_service):
        """Test successful subscription cancellation"""
        with patch('stripe.Subscription.delete') as mock_delete:
            # Execute
            result = await payment_service.cancel_subscription("sub_test123")
            
            # Assert
            assert result is True
            mock_delete.assert_called_once_with("sub_test123")

    @pytest.mark.asyncio
    async def test_cancel_subscription_error(self, payment_service):
        """Test subscription cancellation with error"""
        with patch('stripe.Subscription.delete', side_effect=stripe.error.InvalidRequestError(
            message="No such subscription: sub_nonexistent",
            param="id"
        )):
            # Execute
            result = await payment_service.cancel_subscription("sub_nonexistent")
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_success(self, payment_service):
        """Test successful webhook signature verification"""
        payload = b'{"type": "checkout.session.completed"}'
        signature = "t=1234567890,v1=signature"
        
        mock_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test123"}}
        }
        
        with patch('stripe.Webhook.construct_event', return_value=mock_event):
            # Execute
            result = await payment_service.verify_webhook_signature(payload, signature)
            
            # Assert
            assert result == mock_event

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_invalid(self, payment_service):
        """Test webhook signature verification with invalid signature"""
        payload = b'{"type": "checkout.session.completed"}'
        signature = "invalid_signature"
        
        with patch('stripe.Webhook.construct_event', side_effect=stripe.error.SignatureVerificationError(
            message="Invalid signature",
            sig_header=signature
        )):
            # Execute
            result = await payment_service.verify_webhook_signature(payload, signature)
            
            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_invalid_payload(self, payment_service):
        """Test webhook signature verification with invalid payload"""
        payload = b'invalid json'
        signature = "t=1234567890,v1=signature"
        
        with patch('stripe.Webhook.construct_event', side_effect=ValueError("Invalid payload")):
            # Execute
            result = await payment_service.verify_webhook_signature(payload, signature)
            
            # Assert
            assert result is None

    def test_determine_plan_from_price_id(self, payment_service):
        """Test plan determination from price ID"""
        # Test Pro plan
        result = payment_service.determine_plan_from_price_id("price_pro_123")
        assert result == SubscriptionStatus.PRO
        
        # Test Enterprise plan
        result = payment_service.determine_plan_from_price_id("price_enterprise_123")
        assert result == SubscriptionStatus.ENTERPRISE
        
        # Test unknown plan (defaults to FREE)
        result = payment_service.determine_plan_from_price_id("price_unknown_123")
        assert result == SubscriptionStatus.FREE

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_success(self, payment_service):
        """Test successful checkout completion handling"""
        mock_subscription = {
            "id": "sub_test123",
            "items": {"data": [{"price": {"id": "price_pro_123"}}]},
            "current_period_start": 1640995200,  # 2022-01-01
            "current_period_end": 1643673600     # 2022-02-01
        }
        
        event_data = {
            "customer": "cus_test123",
            "subscription": "sub_test123",
            "metadata": {
                "auth0_user_id": "auth0|test123",
                "user_email": "test@example.com"
            }
        }
        
        # Mock user service
        mock_user_service = Mock()
        mock_user = Mock()
        mock_user.id = 1
        mock_user_service.get_user_by_auth0_id.return_value = mock_user
        mock_user_service.db_service = Mock()
        
        with patch.object(payment_service, 'get_subscription', return_value=mock_subscription):
            # Execute
            result = await payment_service.handle_checkout_completed(event_data, mock_user_service)
            
            # Assert
            assert result["type"] == "checkout_completed"
            assert result["customer_id"] == "cus_test123"
            assert result["subscription_id"] == "sub_test123"
            assert result["plan_type"] == "pro"
            assert result["user_updated"] is True

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_no_subscription(self, payment_service):
        """Test checkout completion handling without subscription ID"""
        event_data = {
            "customer": "cus_test123",
            "subscription": None,  # No subscription ID
            "metadata": {"auth0_user_id": "auth0|test123"}
        }
        
        # Execute
        result = await payment_service.handle_checkout_completed(event_data)
        
        # Assert
        assert result["type"] == "checkout_completed"
        assert result["subscription_id"] is None
        assert result["status"] == "deferred_to_subscription_created"

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_missing_user_id(self, payment_service):
        """Test checkout completion handling with missing user ID"""
        event_data = {
            "customer": "cus_test123",
            "subscription": "sub_test123",
            "metadata": {}  # Missing auth0_user_id
        }
        
        mock_subscription = {
            "id": "sub_test123",
            "items": {"data": [{"price": {"id": "price_pro_123"}}]}
        }
        
        with patch.object(payment_service, 'get_subscription', return_value=mock_subscription):
            # Execute and Assert
            with pytest.raises(ValueError, match="Missing auth0_user_id in metadata"):
                await payment_service.handle_checkout_completed(event_data)

    @pytest.mark.asyncio
    async def test_handle_subscription_created_success(self, payment_service):
        """Test successful subscription creation handling"""
        event_data = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_pro_123"}}]},
            "current_period_start": 1640995200,
            "current_period_end": 1643673600
        }
        
        mock_customer = {"email": "test@example.com"}
        mock_user_service = Mock()
        mock_user = Mock()
        mock_user.id = 1
        mock_user_service.get_user_by_email.return_value = mock_user
        mock_user_service.db_service = Mock()
        
        with patch.object(payment_service, 'get_customer', return_value=mock_customer):
            # Execute
            result = await payment_service.handle_subscription_created(event_data, mock_user_service)
            
            # Assert
            assert result["type"] == "subscription_created"
            assert result["subscription_id"] == "sub_test123"
            assert result["customer_id"] == "cus_test123"
            assert result["status"] == "active"
            assert result["plan_type"] == "pro"
            assert result["database_updated"] is True

    @pytest.mark.asyncio
    async def test_handle_subscription_updated_success(self, payment_service):
        """Test successful subscription update handling"""
        event_data = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "status": "past_due",
            "items": {"data": [{"price": {"id": "price_pro_123"}}]},
            "current_period_start": 1640995200,
            "current_period_end": 1643673600
        }
        
        mock_user_service = Mock()
        mock_user_service.db_service = Mock()
        mock_subscription_record = {"user_id": 1}
        mock_user_service.db_service.get_subscription_by_stripe_id.return_value = mock_subscription_record
        
        # Execute
        result = await payment_service.handle_subscription_updated(event_data, mock_user_service)
        
        # Assert
        assert result["type"] == "subscription_updated"
        assert result["subscription_id"] == "sub_test123"
        assert result["status"] == "past_due"
        assert result["database_updated"] is True

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_success(self, payment_service):
        """Test successful subscription deletion handling"""
        event_data = {
            "id": "sub_test123",
            "customer": "cus_test123",
            "canceled_at": 1640995200
        }
        
        # Execute
        result = await payment_service.handle_subscription_deleted(event_data)
        
        # Assert
        assert result["type"] == "subscription_deleted"
        assert result["subscription_id"] == "sub_test123"
        assert result["customer_id"] == "cus_test123"

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded_success(self, payment_service):
        """Test successful payment handling"""
        event_data = {
            "id": "in_test123",
            "subscription": "sub_test123",
            "customer": "cus_test123",
            "amount_paid": 2000,
            "period_start": 1640995200,
            "period_end": 1643673600
        }
        
        # Execute
        result = await payment_service.handle_payment_succeeded(event_data)
        
        # Assert
        assert result["type"] == "payment_succeeded"
        assert result["subscription_id"] == "sub_test123"
        assert result["customer_id"] == "cus_test123"
        assert result["amount_paid"] == 2000
        assert result["invoice_id"] == "in_test123"

    @pytest.mark.asyncio
    async def test_handle_payment_failed_success(self, payment_service):
        """Test payment failure handling"""
        event_data = {
            "id": "in_test123",
            "subscription": "sub_test123",
            "customer": "cus_test123",
            "amount_due": 2000,
            "next_payment_attempt": 1641081600
        }
        
        # Execute
        result = await payment_service.handle_payment_failed(event_data)
        
        # Assert
        assert result["type"] == "payment_failed"
        assert result["subscription_id"] == "sub_test123"
        assert result["customer_id"] == "cus_test123"
        assert result["amount_due"] == 2000
        assert result["next_payment_attempt"] == 1641081600

    @pytest.mark.asyncio
    async def test_get_usage_records_success(self, payment_service):
        """Test successful usage records retrieval"""
        mock_usage_records = Mock()
        mock_usage_records.data = [
            {"id": "mbur_test1", "quantity": 100},
            {"id": "mbur_test2", "quantity": 150}
        ]
        
        with patch('stripe.UsageRecord.list', return_value=mock_usage_records):
            # Execute
            result = await payment_service.get_usage_records("si_test123")
            
            # Assert
            assert len(result) == 2
            assert result[0]["quantity"] == 100
            assert result[1]["quantity"] == 150

    @pytest.mark.asyncio
    async def test_create_usage_record_success(self, payment_service):
        """Test successful usage record creation"""
        with patch('stripe.UsageRecord.create') as mock_create:
            # Execute
            result = await payment_service.create_usage_record(
                subscription_item_id="si_test123",
                quantity=100
            )
            
            # Assert
            assert result is True
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_usage_record_with_timestamp(self, payment_service):
        """Test usage record creation with custom timestamp"""
        timestamp = datetime(2022, 1, 1, 12, 0, 0)
        
        with patch('stripe.UsageRecord.create') as mock_create:
            # Execute
            result = await payment_service.create_usage_record(
                subscription_item_id="si_test123",
                quantity=100,
                timestamp=timestamp
            )
            
            # Assert
            assert result is True
            call_args = mock_create.call_args[1]
            assert call_args["timestamp"] == int(timestamp.timestamp())

    @pytest.mark.asyncio
    async def test_error_handling_in_webhook_handlers(self, payment_service):
        """Test error handling in webhook event handlers"""
        # Test with invalid event data
        invalid_event_data = {"invalid": "data"}
        
        # Execute and Assert
        with pytest.raises(ValueError):
            await payment_service.handle_checkout_completed(invalid_event_data)