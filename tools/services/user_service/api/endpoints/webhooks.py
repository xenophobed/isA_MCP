"""
Webhook Endpoints

Webhook-related functionality extracted from api_server.py
Handles Stripe webhooks and other external service webhooks
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def handle_stripe_webhook(
    request: Request,
    payment_service=None,
    subscription_service=None,
    user_service=None
):
    """Handle Stripe webhook - Original: api_server.py lines 551-654"""
    try:
        if not payment_service or not subscription_service or not user_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        # Get the raw body
        body = await request.body()
        
        # Get the Stripe signature header
        sig_header = request.headers.get('stripe-signature')
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
            
        # Verify the webhook signature
        try:
            event = await payment_service.verify_webhook_signature(body, sig_header)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid signature")
            
        # Handle different event types
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        try:
            if event_type == 'payment_intent.succeeded':
                # Handle successful payment
                result = await payment_service.handle_payment_success(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle payment success: {result.message}")
                    
            elif event_type == 'payment_intent.payment_failed':
                # Handle failed payment
                result = await payment_service.handle_payment_failure(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle payment failure: {result.message}")
                    
            elif event_type == 'customer.subscription.created':
                # Handle new subscription
                result = await subscription_service.handle_subscription_created(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle subscription created: {result.message}")
                    
            elif event_type == 'customer.subscription.updated':
                # Handle subscription update
                result = await subscription_service.handle_subscription_updated(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle subscription updated: {result.message}")
                    
            elif event_type == 'customer.subscription.deleted':
                # Handle subscription cancellation
                result = await subscription_service.handle_subscription_cancelled(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle subscription cancelled: {result.message}")
                    
            elif event_type == 'invoice.payment_succeeded':
                # Handle successful invoice payment
                result = await subscription_service.handle_invoice_paid(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle invoice paid: {result.message}")
                    
            elif event_type == 'invoice.payment_failed':
                # Handle failed invoice payment
                result = await subscription_service.handle_invoice_failed(event_data)
                if not result.is_success:
                    logger.error(f"Failed to handle invoice failed: {result.message}")
                    
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {str(e)}")
            # Don't raise exception here - we want to acknowledge receipt
            
        # Always return 200 to acknowledge receipt
        return {
            "status": "received",
            "event_type": event_type,
            "event_id": event.get('id', 'unknown')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")