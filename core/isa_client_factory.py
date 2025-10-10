#!/usr/bin/env python3
"""
ISA Model Client Factory
Centralized ISA client creation with optional authentication
Provides backward-compatible client instances
"""

import os
import asyncio
from typing import Optional
from core.logging import get_logger

logger = get_logger(__name__)


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
        """Create ISA client with authentication if configured"""
        try:
            from isa_model.client import ISAModelClient
            
            # Get configuration from environment or config
            isa_service_url = os.getenv('ISA_SERVICE_URL')
            isa_api_key = os.getenv('ISA_API_KEY')
            require_auth = os.getenv('REQUIRE_ISA_AUTH', 'false').lower() == 'true'
            
            # Try to get from config if environment variables not set
            try:
                from core.config import get_settings
                settings = get_settings()
                isa_service_url = isa_service_url or settings.isa_service_url
                isa_api_key = isa_api_key or settings.isa_api_key
                require_auth = require_auth or settings.require_isa_auth
            except Exception as e:
                logger.debug(f"Could not load config settings: {e}")
            
            # Build client parameters
            client_params = {}
            
            # Add service endpoint if configured
            if isa_service_url:
                client_params['service_endpoint'] = isa_service_url
                logger.info(f"Using ISA service endpoint: {isa_service_url}")
            
            # Add API key if configured and required
            if isa_api_key and require_auth:
                client_params['api_key'] = isa_api_key
                logger.info("Using ISA API key authentication")
            elif require_auth and not isa_api_key:
                logger.warning("ISA authentication required but no API key configured")
            
            # Override with any additional kwargs
            client_params.update(kwargs)
            
            # Create client - use direct URL initialization like isa_agent
            if isa_service_url:
                client = ISAModelClient(isa_service_url)
                logger.info(f"ISA client created with direct URL: {isa_service_url}")
            else:
                client = ISAModelClient(**client_params)
                logger.info(f"ISA client created with params: {list(client_params.keys())}")
            
            # Wrap client to ensure consistent response format for JSON mode
            wrapped_client = _JSONCompatibleClientWrapper(client)
            
            # Create concurrent-safe client wrapper
            return _ConcurrentSafeClientWrapper(wrapped_client)
            
        except Exception as e:
            logger.error(f"Failed to create ISA client: {e}")
            # Fallback to basic client
            from isa_model.client import ISAModelClient
            wrapped_client = _JSONCompatibleClientWrapper(ISAModelClient())
            return _ConcurrentSafeClientWrapper(wrapped_client)
    
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