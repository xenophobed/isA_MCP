#!/usr/bin/env python
"""
Twilio Tools for MCP Server
Handles SMS, Voice, and communication operations with security
"""
import json
import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Twilio SDK
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Play, Record
from twilio.twiml.messaging_response import MessagingResponse
from twilio.base.exceptions import TwilioRestException

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager

logger = get_logger(__name__)

# Global Twilio client and configuration
_twilio_client = None
_twilio_config = {
    "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "phone_number": os.getenv("TWILIO_PHONE_NUMBER", ""),
    "webhook_url": os.getenv("TWILIO_WEBHOOK_URL"),
    "default_voice": os.getenv("TWILIO_DEFAULT_VOICE", "alice"),
    "default_language": os.getenv("TWILIO_DEFAULT_LANGUAGE", "en-US")
}

def _initialize_twilio_client():
    """Initialize Twilio client if not already done"""
    global _twilio_client
    
    if _twilio_client:
        return _twilio_client
    
    if not _twilio_config["account_sid"] or not _twilio_config["auth_token"]:
        raise ValueError("Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.")
    
    try:
        _twilio_client = Client(_twilio_config["account_sid"], _twilio_config["auth_token"])
        logger.info("Twilio client initialized successfully")
        return _twilio_client
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}")
        raise

def _format_phone_number(phone: str, country_code: str = "+1") -> str:
    """Format phone number to E.164 format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if digits.startswith('1') and len(digits) == 11:
        return f"+{digits}"
    elif len(digits) == 10:
        return f"{country_code}{digits}"
    elif phone.startswith('+'):
        return phone
    else:
        return f"{country_code}{digits}"

def _validate_phone_number(phone: str) -> bool:
    """Validate phone number format (E.164)"""
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))

def _create_twiml_say(message: str, voice: str = None, language: str = None) -> str:
    """Create simple TwiML to say a message"""
    response = VoiceResponse()
    response.say(
        message, 
        voice=voice or _twilio_config["default_voice"],
        language=language or _twilio_config["default_language"]
    )
    return str(response)

def _create_twiml_gather(message: str, num_digits: int = 1, timeout: int = 5) -> str:
    """Create TwiML to gather user input"""
    response = VoiceResponse()
    gather = Gather(num_digits=num_digits, timeout=timeout)
    gather.say(message)
    response.append(gather)
    response.say("Sorry, I didn't get your input. Goodbye!")
    return str(response)

def register_twilio_tools(mcp):
    """Register all Twilio tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def send_sms(
        to: str,
        message: str,
        media_urls: str = "",  # JSON string of media URLs
        user_id: str = "default"
    ) -> str:
        """Send SMS/MMS message via Twilio
        
        This tool sends text messages and multimedia messages to phone
        numbers using the Twilio communication platform.
        
        Keywords: sms, text, message, phone, communication, twilio, mobile
        Category: communication
        """
        
        # Initialize client
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "send_sms",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate and format phone number
        try:
            formatted_to = _format_phone_number(to)
            if not _validate_phone_number(formatted_to):
                raise ValueError(f"Invalid phone number format: {to}")
        except Exception as e:
            result = {
                "status": "error",
                "action": "send_sms",
                "error": f"Phone number validation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate message length (SMS limit is 1600 characters)
        if len(message) > 1600:
            result = {
                "status": "error",
                "action": "send_sms",
                "error": "Message too long. Maximum 1600 characters allowed.",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Parse media URLs if provided
        media_list = None
        if media_urls and media_urls.strip():
            try:
                media_list = json.loads(media_urls)
                if not isinstance(media_list, list):
                    raise ValueError("Media URLs must be a JSON array")
            except json.JSONDecodeError as e:
                result = {
                    "status": "error",
                    "action": "send_sms",
                    "error_code": twilio_message.error_code,
                    "error_message": twilio_message.error_message,
                    "sent_by": user_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"SMS sent successfully to {formatted_to}, SID: {twilio_message.sid}")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "send_sms",
                "error": f"Twilio SMS error: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio SMS error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "send_sms",
                "error": f"SMS sending failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"SMS sending error: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def make_voice_call(
        to: str,
        message: str = "",
        twiml_url: str = "",
        voice: str = "",
        user_id: str = "default"
    ) -> str:
        """Make outbound voice call via Twilio
        
        This tool initiates voice calls to phone numbers with customizable
        voice messages and TwiML scripts for interactive experiences.
        
        Keywords: voice, call, phone, twilio, audio, communication, outbound
        Category: communication
        """
        
        # Initialize client
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "make_voice_call",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate phone number
        try:
            formatted_to = _format_phone_number(to)
            if not _validate_phone_number(formatted_to):
                raise ValueError(f"Invalid phone number format: {to}")
        except Exception as e:
            result = {
                "status": "error",
                "action": "make_voice_call",
                "error": f"Phone number validation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate that either message or twiml_url is provided
        if not message and not twiml_url:
            result = {
                "status": "error",
                "action": "make_voice_call",
                "error": "Either 'message' or 'twiml_url' must be provided",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            # Create call parameters
            call_params = {
                'to': formatted_to,
                'from_': _twilio_config["phone_number"]
            }
            
            # Use TwiML URL or generate simple message TwiML
            if twiml_url:
                call_params['url'] = twiml_url
            else:
                # Generate TwiML for simple message
                call_voice = voice or _twilio_config["default_voice"]
                twiml = _create_twiml_say(message, call_voice)
                call_params['twiml'] = twiml
            
            # Make the call
            call = client.calls.create(**call_params)
            
            result = {
                "status": "success",
                "action": "make_voice_call",
                "data": {
                    "sid": call.sid,
                    "to": call.to,
                    "from": call.from_,
                    "status": call.status,
                    "duration": call.duration,
                    "price": call.price,
                    "price_unit": call.price_unit,
                    "date_created": call.date_created.isoformat() if call.date_created else None,
                    "date_updated": call.date_updated.isoformat() if call.date_updated else None,
                    "start_time": call.start_time.isoformat() if call.start_time else None,
                    "end_time": call.end_time.isoformat() if call.end_time else None,
                    "answered_by": call.answered_by,
                    "initiated_by": user_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Voice call initiated to {formatted_to}, SID: {call.sid}")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "make_voice_call",
                "error": f"Twilio voice call error: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio voice call error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "make_voice_call",
                "error": f"Voice call failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Voice call error: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def get_message_status(message_sid: str, user_id: str = "default") -> str:
        """Get SMS message status and details
        
        This tool retrieves delivery status and detailed information
        about previously sent SMS/MMS messages.
        
        Keywords: sms, status, delivery, tracking, message, details
        Category: communication
        """
        
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_message_status",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            message = client.messages(message_sid).fetch()
            
            result = {
                "status": "success",
                "action": "get_message_status",
                "data": {
                    "sid": message.sid,
                    "to": message.to,
                    "from": message.from_,
                    "body": message.body,
                    "status": message.status,
                    "direction": message.direction,
                    "price": message.price,
                    "price_unit": message.price_unit,
                    "date_created": message.date_created.isoformat() if message.date_created else None,
                    "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                    "date_updated": message.date_updated.isoformat() if message.date_updated else None,
                    "error_code": message.error_code,
                    "error_message": message.error_message
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Message status retrieved for SID: {message_sid}")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "get_message_status",
                "error": f"Message status fetch failed: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio message status error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_message_status",
                "error": f"Message status fetch failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def get_call_status(call_sid: str, user_id: str = "default") -> str:
        """Get voice call status and details
        
        This tool retrieves status information and call details
        for previously initiated voice calls.
        
        Keywords: voice, call, status, tracking, details, duration
        Category: communication
        """
        
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_call_status",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            call = client.calls(call_sid).fetch()
            
            result = {
                "status": "success",
                "action": "get_call_status",
                "data": {
                    "sid": call.sid,
                    "to": call.to,
                    "from": call.from_,
                    "status": call.status,
                    "direction": call.direction,
                    "duration": call.duration,
                    "price": call.price,
                    "price_unit": call.price_unit,
                    "date_created": call.date_created.isoformat() if call.date_created else None,
                    "date_updated": call.date_updated.isoformat() if call.date_updated else None,
                    "start_time": call.start_time.isoformat() if call.start_time else None,
                    "end_time": call.end_time.isoformat() if call.end_time else None,
                    "answered_by": call.answered_by
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Call status retrieved for SID: {call_sid}")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "get_call_status",
                "error": f"Call status fetch failed: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio call status error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_call_status",
                "error": f"Call status fetch failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def send_bulk_sms(
        recipients: str,  # JSON string of phone numbers
        message: str,
        user_id: str = "default"
    ) -> str:
        """Send SMS to multiple recipients (max 50)
        
        This tool sends the same text message to multiple phone numbers
        simultaneously with rate limiting and batch processing.
        
        Keywords: sms, bulk, batch, multiple, recipients, broadcast
        Category: communication
        """
        
        # Parse recipients
        try:
            phone_list = json.loads(recipients)
            if not isinstance(phone_list, list):
                raise ValueError("Recipients must be a JSON array")
        except json.JSONDecodeError as e:
            result = {
                "status": "error",
                "action": "send_bulk_sms",
                "error": f"Invalid JSON format for recipients: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate limits
        if len(phone_list) > 50:
            result = {
                "status": "error",
                "action": "send_bulk_sms",
                "error": "Too many recipients. Maximum 50 allowed.",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        if len(message) > 1600:
            result = {
                "status": "error",
                "action": "send_bulk_sms",
                "error": "Message too long. Maximum 1600 characters allowed.",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        results = []
        successful = 0
        failed = 0
        
        for phone in phone_list:
            try:
                # Send individual SMS
                sms_result = await send_sms(phone, message, "", user_id)
                parsed_result = json.loads(sms_result)
                
                if parsed_result["status"] == "success":
                    results.append({
                        "phone": phone,
                        "success": True,
                        "sid": parsed_result["data"]["sid"],
                        "status": parsed_result["data"]["status"]
                    })
                    successful += 1
                else:
                    results.append({
                        "phone": phone,
                        "success": False,
                        "error": parsed_result["error"]
                    })
                    failed += 1
                
                # Rate limiting - small delay between messages
                await asyncio.sleep(0.1)
                
            except Exception as e:
                results.append({
                    "phone": phone,
                    "success": False,
                    "error": str(e)
                })
                failed += 1
        
        result = {
            "status": "completed",
            "action": "send_bulk_sms",
            "data": {
                "total_recipients": len(phone_list),
                "successful": successful,
                "failed": failed,
                "results": results
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Bulk SMS completed: {successful}/{len(phone_list)} successful")
        return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def list_recent_messages(
        limit: int = 20,
        days_back: int = 7,
        user_id: str = "default"
    ) -> str:
        """List recent SMS messages
        
        This tool retrieves a list of recently sent and received
        SMS messages with configurable time range and limits.
        
        Keywords: sms, list, recent, history, messages, log
        Category: communication
        """
        
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "list_recent_messages",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate limits
        if limit > 100:
            limit = 100  # Safety limit
        
        try:
            # Calculate date range
            date_sent_after = datetime.now() - timedelta(days=days_back)
            
            messages = client.messages.list(
                date_sent_after=date_sent_after,
                limit=limit
            )
            
            message_list = []
            for msg in messages:
                message_data = {
                    "sid": msg.sid,
                    "to": msg.to,
                    "from": msg.from_,
                    "body": msg.body,
                    "status": msg.status,
                    "direction": msg.direction,
                    "date_created": msg.date_created.isoformat() if msg.date_created else None,
                    "date_sent": msg.date_sent.isoformat() if msg.date_sent else None,
                    "price": msg.price,
                    "error_code": msg.error_code
                }
                message_list.append(message_data)
            
            result = {
                "status": "success",
                "action": "list_recent_messages",
                "data": {
                    "messages": message_list,
                    "count": len(message_list),
                    "limit": limit,
                    "days_back": days_back
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Listed {len(message_list)} recent messages")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "list_recent_messages",
                "error": f"List messages failed: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio list messages error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "list_recent_messages",
                "error": f"List messages failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def list_recent_calls(
        limit: int = 20,
        days_back: int = 7,
        user_id: str = "default"
    ) -> str:
        """List recent voice calls
        
        This tool retrieves a list of recent voice calls with
        details like duration, status, and timestamps.
        
        Keywords: voice, calls, list, recent, history, log
        Category: communication
        """
        
        try:
            client = _initialize_twilio_client()
        except Exception as e:
            result = {
                "status": "error",
                "action": "list_recent_calls",
                "error": f"Twilio client initialization failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate limits
        if limit > 100:
            limit = 100  # Safety limit
        
        try:
            # Calculate date range
            start_time_after = datetime.now() - timedelta(days=days_back)
            
            calls = client.calls.list(
                start_time_after=start_time_after,
                limit=limit
            )
            
            call_list = []
            for call in calls:
                call_data = {
                    "sid": call.sid,
                    "to": call.to,
                    "from": call.from_,
                    "status": call.status,
                    "direction": call.direction,
                    "duration": call.duration,
                    "price": call.price,
                    "date_created": call.date_created.isoformat() if call.date_created else None,
                    "start_time": call.start_time.isoformat() if call.start_time else None,
                    "end_time": call.end_time.isoformat() if call.end_time else None,
                    "answered_by": call.answered_by
                }
                call_list.append(call_data)
            
            result = {
                "status": "success",
                "action": "list_recent_calls",
                "data": {
                    "calls": call_list,
                    "count": len(call_list),
                    "limit": limit,
                    "days_back": days_back
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Listed {len(call_list)} recent calls")
            return json.dumps(result)
            
        except TwilioRestException as e:
            result = {
                "status": "error",
                "action": "list_recent_calls",
                "error": f"List calls failed: {e.msg}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Twilio list calls error: {e}")
            return json.dumps(result)
        except Exception as e:
            result = {
                "status": "error",
                "action": "list_recent_calls",
                "error": f"List calls failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def validate_phone_number(phone: str, user_id: str = "default") -> str:
        """Validate and format phone number
        
        This tool validates phone number formats and converts them
        to standard E.164 international format for consistency.
        
        Keywords: phone, validate, format, number, e164, international
        Category: communication
        """
        
        try:
            formatted = _format_phone_number(phone)
            is_valid = _validate_phone_number(formatted)
            
            result = {
                "status": "success",
                "action": "validate_phone_number",
                "data": {
                    "original": phone,
                    "formatted": formatted,
                    "is_valid": is_valid,
                    "format": "E.164" if is_valid else "invalid"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Phone number validated: {phone} -> {formatted} (valid: {is_valid})")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "validate_phone_number",
                "error": f"Phone validation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def generate_twiml(
        twiml_type: str,
        message: str = "",
        voice: str = "",
        num_digits: int = 1,
        timeout: int = 5,
        user_id: str = "default"
    ) -> str:
        """Generate TwiML for voice responses
        
        This tool creates TwiML markup for interactive voice responses,
        supporting speech synthesis and user input gathering.
        
        Keywords: twiml, voice, response, interactive, markup, ivr
        Category: communication
        """
        
        try:
            if twiml_type == "say":
                if not message:
                    message = "Hello from Twilio"
                call_voice = voice or _twilio_config["default_voice"]
                twiml = _create_twiml_say(message, call_voice)
                
            elif twiml_type == "gather":
                if not message:
                    message = "Please enter a digit"
                twiml = _create_twiml_gather(message, num_digits, timeout)
                
            else:
                result = {
                    "status": "error",
                    "action": "generate_twiml",
                    "error": f"Unsupported TwiML type: {twiml_type}. Supported types: 'say', 'gather'",
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(result)
            
            result = {
                "status": "success",
                "action": "generate_twiml",
                "data": {
                    "twiml_type": twiml_type,
                    "twiml": twiml,
                    "parameters": {
                        "message": message,
                        "voice": voice,
                        "num_digits": num_digits,
                        "timeout": timeout
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"TwiML generated: {twiml_type}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "generate_twiml",
                "error": f"TwiML generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"TwiML generation error: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def get_twilio_status(user_id: str = "admin") -> str:
        """Get Twilio service status and configuration (admin only)
        
        This tool provides administrative information about Twilio
        service configuration, credentials, and connection status.
        
        Keywords: admin, twilio, status, configuration, service, health
        Category: communication
        """
        
        if user_id != "admin":
            result = {
                "status": "error",
                "action": "get_twilio_status",
                "error": "Admin access required",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            client_initialized = _twilio_client is not None
            
            # Try to validate credentials if client is initialized
            account_info = None
            if client_initialized:
                try:
                    account = _twilio_client.api.accounts(_twilio_config["account_sid"]).fetch()
                    account_info = {
                        "friendly_name": account.friendly_name,
                        "status": account.status,
                        "type": account.type
                    }
                except:
                    account_info = {"error": "Could not fetch account info"}
            
            status_data = {
                "client_initialized": client_initialized,
                "configuration": {
                    "account_sid_configured": bool(_twilio_config["account_sid"]),
                    "auth_token_configured": bool(_twilio_config["auth_token"]),
                    "phone_number_configured": bool(_twilio_config["phone_number"]),
                    "webhook_url": _twilio_config["webhook_url"],
                    "default_voice": _twilio_config["default_voice"],
                    "default_language": _twilio_config["default_language"]
                },
                "account_info": account_info
            }
            
            result = {
                "status": "success",
                "action": "get_twilio_status",
                "data": status_data,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_twilio_status",
                "error": f"Status retrieval failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)": f"Invalid JSON format for media URLs: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(result)
        
        try:
            # Create message parameters
            message_params = {
                'body': message,
                'from_': _twilio_config["phone_number"],
                'to': formatted_to
            }
            
            # Add media URLs for MMS
            if media_list:
                message_params['media_url'] = media_list
            
            # Send message
            twilio_message = client.messages.create(**message_params)
            
            result = {
                "status": "success",
                "action": "send_sms",
                "data": {
                    "sid": twilio_message.sid,
                    "to": twilio_message.to,
                    "from": twilio_message.from_,
                    "body": twilio_message.body,
                    "status": twilio_message.status,
                    "price": twilio_message.price,
                    "price_unit": twilio_message.price_unit,
                    "date_created": twilio_message.date_created.isoformat() if twilio_message.date_created else None,
                    "date_sent": twilio_message.date_sent.isoformat() if twilio_message.date_sent else None,
                    "error