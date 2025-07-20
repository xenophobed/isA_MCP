#!/usr/bin/env python3
"""
ISA Model Client Factory
Centralized ISA client creation with optional authentication
Provides backward-compatible client instances
"""

import os
from typing import Optional
from core.logging import get_logger

logger = get_logger(__name__)

class ISAClientFactory:
    """
    Factory for creating ISA model clients with centralized configuration
    Handles optional authentication transparently
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_client(cls, **kwargs):
        """
        Get ISA client instance with optional authentication
        
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
            
            # Create client
            client = ISAModelClient(**client_params)
            logger.info(f"ISA client created with params: {list(client_params.keys())}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create ISA client: {e}")
            # Fallback to basic client
            from isa_model.client import ISAModelClient
            return ISAModelClient()
    
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
    return ISAClientFactory.get_client(**kwargs)


# Global factory instance
isa_client_factory = ISAClientFactory()