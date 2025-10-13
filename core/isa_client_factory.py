#!/usr/bin/env python3
"""
ISA Model Client Factory
Centralized ISA client creation with optional authentication
Provides backward-compatible client instances
"""

import os
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any, Union
from core.logging import get_logger

logger = get_logger(__name__)


class ISAServiceClient:
    """
    HTTP client for ISA Model Service API
    Based on /Users/xenodennis/Documents/Fun/isA_Model/examples/isa_service_client.py
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 60, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper headers."""
        if self._session is None or self._session.closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ISA-Service-Client/1.0"
            }

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["X-API-Key"] = self.api_key

            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout_obj)

        return self._session

    async def close(self):
        """Close the HTTP session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def invoke(
        self,
        input_data: Union[str, Dict[str, Any]],
        task: str,
        service_type: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Universal invoke method - makes HTTP POST to /api/v1/invoke

        Args:
            input_data: Input data (text, image path, etc.)
            task: Task to perform (chat, analyze, transcribe, etc.)
            service_type: Service type (text, vision, audio, image, embedding)
            model: Optional model name
            provider: Optional provider name
            stream: Enable streaming (for text services)
            **kwargs: Additional parameters

        Returns:
            Response dictionary with success, result and metadata
        """
        payload = {
            "input_data": input_data,
            "task": task,
            "service_type": service_type,
            "stream": stream,
            **kwargs
        }

        if model:
            payload["model"] = model
        if provider:
            payload["provider"] = provider

        session = await self._get_session()
        url = f"{self.base_url}/api/v1/invoke"

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "result": None,
                        "error": f"HTTP {response.status}: {error_text}",
                        "metadata": {}
                    }

                # Handle non-streaming response
                if not stream:
                    result = await response.json()
                    return result

                # Handle streaming response (SSE format)
                full_text = ""
                metadata = {}

                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if not line_str or not line_str.startswith('data: '):
                        continue

                    data_str = line_str[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break

                    try:
                        event_data = json.loads(data_str)
                        if 'token' in event_data:
                            full_text += event_data['token']
                        elif 'metadata' in event_data:
                            metadata = event_data['metadata']
                        elif event_data.get('done'):
                            break
                    except json.JSONDecodeError:
                        continue

                return {
                    "success": True,
                    "result": full_text,
                    "metadata": metadata
                }

        except Exception as e:
            logger.error(f"ISAServiceClient invoke failed: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "metadata": {}
            }


class _ResponseWrapper:
    """Wrapper to provide .content attribute for JSON responses"""
    def __init__(self, content):
        self.content = content
        
    def __str__(self):
        return str(self.content)
        
    def __repr__(self):
        return f"ResponseWrapper({repr(self.content)})"


class _JSONCompatibleClientWrapper:
    """
    Wrapper for ISAModelClient to ensure consistent response format
    that matches llm.md documentation specifications
    """
    
    def __init__(self, client):
        self._client = client
        
    async def invoke(self, input_data, task, service_type, **kwargs):
        """
        Invoke the wrapped client and ensure response format consistency
        
        When response_format={"type": "json_object"} is used, the result
        should have a .content attribute as per llm.md documentation.
        """
        try:
            # Call the underlying client
            response = await self._client.invoke(
                input_data=input_data,
                task=task, 
                service_type=service_type,
                **kwargs
            )
            
            # Check if this is a JSON mode request
            response_format = kwargs.get('response_format')
            if response_format and response_format.get('type') == 'json_object':
                # For JSON mode, wrap the result to provide .content attribute
                if response.get('success') and 'result' in response:
                    result = response['result']
                    # If result is already a string, wrap it to provide .content
                    if isinstance(result, str):
                        response['result'] = _ResponseWrapper(result)
                        logger.debug("Wrapped JSON response result with .content attribute")
            
            return response
            
        except Exception as e:
            logger.error(f"JSON-compatible client wrapper error: {e}")
            return {
                'success': False,
                'error': str(e),
                'result': None,
                'metadata': {}
            }
    
    def __getattr__(self, name):
        """Delegate other methods to the wrapped client"""
        return getattr(self._client, name)


class _ConcurrentSafeClientWrapper:
    """
    Concurrent-safe wrapper for ISAModelClient to handle race conditions
    Uses per-request isolation instead of global locking for better performance
    """
    
    def __init__(self, client):
        self._client = client
        
    async def invoke(self, input_data, task, service_type, **kwargs):
        """
        Concurrent-safe invoke method with per-request isolation
        """
        try:
            # Create a deep copy of kwargs to prevent shared state mutation
            import copy
            safe_kwargs = copy.deepcopy(kwargs)
            
            # Ensure streaming is handled per-request
            # Only set default stream value if not explicitly provided
            stream = safe_kwargs.get('stream', None)
            if stream is None and service_type == "text":
                if task in ["chat", "generate"]:
                    # Default to False for better compatibility and debugging
                    safe_kwargs['stream'] = False
                else:
                    safe_kwargs['stream'] = False
            
            # Call the underlying client
            response = await self._client.invoke(
                input_data=input_data,
                task=task, 
                service_type=service_type,
                **safe_kwargs
            )
            
            return response
                
        except Exception as e:
            logger.error(f"Concurrent-safe client wrapper error: {e}")
            return {
                'success': False,
                'error': str(e),
                'result': None,
                'metadata': {}
            }
    
    def __getattr__(self, name):
        """Delegate other methods to the wrapped client"""
        return getattr(self._client, name)

class ISAClientFactory:
    """
    Factory for creating ISA model clients with centralized configuration
    Handles optional authentication transparently
    """
    
    _instance = None
    _client = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_client(cls, **kwargs):
        """
        Get ISA client instance with optional authentication (async version)
        
        Args:
            **kwargs: Additional parameters for ISAModelClient
            
        Returns:
            ISAModelClient instance configured with optional auth
        """
        async with cls._lock:
            if cls._client is None:
                cls._client = cls._create_client(**kwargs)
            return cls._client
    
    @classmethod
    def get_client_sync(cls, **kwargs):
        """
        Get ISA client instance with optional authentication (sync version for backward compatibility)
        
        Args:
            **kwargs: Additional parameters for ISAModelClient
            
        Returns:
            ISAModelClient instance configured with optional auth
        """
        if cls._client is None:
            cls._client = cls._create_client(**kwargs)
        return cls._client
    
    @classmethod
    def _create_client(cls, **kwargs):
        """Create ISA client with API mode (preferred) or local mode fallback"""
        try:
            # Get configuration from environment
            isa_api_url = os.getenv('ISA_API_URL') or os.getenv('ISA_SERVICE_URL')
            isa_api_key = os.getenv('ISA_API_KEY')
            use_api_mode = os.getenv('ISA_USE_API_MODE', 'true').lower() == 'true'

            # Try to get from config if environment variables not set
            try:
                from core.config import get_settings
                settings = get_settings()
                isa_api_url = isa_api_url or getattr(settings, 'isa_api_url', None) or getattr(settings, 'isa_service_url', None)
                isa_api_key = isa_api_key or getattr(settings, 'isa_api_key', None)
            except Exception as e:
                logger.debug(f"Could not load config settings: {e}")

            # Try Consul service discovery for ISA Model service
            try:
                from core.consul_discovery import discover_service
                # Use 'model_service' as the service name in Consul
                consul_discovered_url = discover_service('model_service', default_url=isa_api_url)
                if consul_discovered_url and consul_discovered_url != isa_api_url:
                    logger.info(f"🔍 Consul discovered ISA Model service: {consul_discovered_url}")
                    isa_api_url = consul_discovered_url
                elif consul_discovered_url:
                    logger.info(f"📍 Using ISA Model service from Consul: {isa_api_url}")
                else:
                    logger.debug("Consul service discovery not available, using environment/config URL")
            except Exception as consul_error:
                logger.debug(f"Consul discovery failed, using fallback URL: {consul_error}")

            # Use ISAServiceClient for HTTP-based API mode
            if use_api_mode and isa_api_url:
                # API mode: Use HTTP client for remote service
                client = ISAServiceClient(
                    base_url=isa_api_url,
                    api_key=isa_api_key,
                    timeout=kwargs.get('timeout', 60),
                    max_retries=kwargs.get('max_retries', 3)
                )
                logger.info(f"✅ ISA client created in API mode (HTTP): {isa_api_url}")
                logger.info(f"   Authentication: {'Enabled' if isa_api_key else 'Disabled'}")
            elif isa_api_url:
                # Use HTTP client even if API mode not explicitly enabled
                client = ISAServiceClient(
                    base_url=isa_api_url,
                    api_key=isa_api_key,
                    timeout=kwargs.get('timeout', 60),
                    max_retries=kwargs.get('max_retries', 3)
                )
                logger.info(f"ISA client with service URL (HTTP): {isa_api_url}")
            else:
                # Local mode: Use ISAModelClient for local inference
                from isa_model.client import ISAModelClient
                client = ISAModelClient(**kwargs)
                logger.info("ISA client in LOCAL mode with default configuration")

            # Wrap client
            wrapped_client = _JSONCompatibleClientWrapper(client)
            return _ConcurrentSafeClientWrapper(wrapped_client)

        except Exception as e:
            logger.error(f"Failed to create ISA client: {e}")
            # Last resort fallback
            try:
                from isa_model.client import ISAModelClient
                wrapped_client = _JSONCompatibleClientWrapper(ISAModelClient())
                logger.warning("Using fallback ISA client with default configuration")
                return _ConcurrentSafeClientWrapper(wrapped_client)
            except Exception as fallback_error:
                logger.error(f"Fatal: Could not create any ISA client: {fallback_error}")
                raise
    
    @classmethod
    def reset_client(cls):
        """Reset client instance (useful for testing or config changes)"""
        cls._client = None
        logger.info("ISA client instance reset")


# Backward compatibility function
def get_isa_client(**kwargs):
    """
    Get configured ISA client instance
    
    This function can be used to replace direct ISAModelClient() calls
    while maintaining backward compatibility.
    
    Args:
        **kwargs: Additional parameters for ISAModelClient
        
    Returns:
        ISAModelClient instance with optional authentication
    """
    return ISAClientFactory.get_client_sync(**kwargs)


# Global factory instance
isa_client_factory = ISAClientFactory()