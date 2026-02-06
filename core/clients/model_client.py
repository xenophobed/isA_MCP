#!/usr/bin/env python3
"""
ISA Model Client
Singleton AsyncISAModel client with centralized configuration

Provides a single shared instance of AsyncISAModel for the entire application.
Uses the OpenAI-compatible API from isa-model package.

Based on: /Users/xenodennis/Documents/Fun/isA_Model/examples/model_client_examples_async.py
"""

import os
import asyncio
from typing import Optional, Dict, Any
from core.logging import get_logger

logger = get_logger(__name__)

# Internal service authentication headers
# These identify MCP as an internal service when calling isA_Model
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "dev-internal-secret-change-in-production")
INTERNAL_SERVICE_HEADERS = {
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
    "X-Service-Name": "mcp",
}

try:
    from isa_model.inference_client import AsyncISAModel
    ISA_MODEL_AVAILABLE = True
except ImportError:
    ISA_MODEL_AVAILABLE = False
    AsyncISAModel = None
    logger.warning("isa-model not available. Install with: pip install isa-model[cloud]")

# Global singleton state
_client_instance = None
_client_lock = asyncio.Lock()


async def get_model_client(**kwargs) -> AsyncISAModel:
    """
    Get AsyncISAModel client instance (singleton)

    Args:
        **kwargs: Override parameters (base_url, api_key, etc.)

    Returns:
        AsyncISAModel instance

    Usage:
        # Get singleton client
        client = await get_model_client()

        # Use OpenAI-compatible APIs
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        embedding = await client.embeddings.create(
            input="text to embed",
            model="text-embedding-3-small"
        )

        vision = await client.vision.completions.create(
            image="path/to/image.jpg",
            prompt="Describe this image",
            model="gpt-4o-mini"
        )
    """
    global _client_instance

    if not ISA_MODEL_AVAILABLE:
        raise ImportError("isa-model not available. Install with: pip install isa-model[cloud]")

    async with _client_lock:
        if _client_instance is None:
            _client_instance = _create_client(**kwargs)
        return _client_instance


def _create_client(**kwargs) -> AsyncISAModel:
    """
    Create AsyncISAModel client with centralized configuration.

    Priority:
    1. Explicit kwargs (base_url, api_key)
    2. MCPConfig settings (isa_service_url, isa_api_key)
    3. Consul discovery (only if no explicit config)
    4. Default localhost:8082
    """
    try:
            from core.config import get_settings
            settings = get_settings()

            # Priority 1: Explicit kwargs override everything
            base_url = kwargs.get('base_url')
            api_key = kwargs.get('api_key')

            # Priority 2: Use centralized MCPConfig settings
            if not base_url:
                base_url = settings.isa_service_url
            if not api_key:
                api_key = settings.isa_api_key

            # Priority 3: Consul discovery only if still no URL
            if not base_url:
                try:
                    from isa_common.consul_client import ConsulRegistry

                    consul_registry = ConsulRegistry(
                        service_name='model_service',
                        consul_host=settings.consul.host,
                        consul_port=settings.consul.port
                    )
                    consul_url = consul_registry.get_service_endpoint('model_service')
                    if consul_url:
                        logger.info(f"🔍 Consul discovered ISA Model service: {consul_url}")
                        base_url = consul_url
                except Exception as consul_error:
                    logger.debug(f"Consul discovery not available: {consul_error}")

            # Priority 4: Default fallback
            if not base_url:
                base_url = "http://localhost:8082"
                logger.warning(f"No ISA_SERVICE_URL configured, using default: {base_url}")

            # Create AsyncISAModel client with internal service headers
            # This identifies MCP as an internal service for billing bypass
            client = AsyncISAModel(
                base_url=base_url,
                api_key=api_key,
                extra_headers=INTERNAL_SERVICE_HEADERS
            )

            logger.debug(f"AsyncISAModel client created: {base_url}")

            return client

    except Exception as e:
        logger.error(f"Failed to create AsyncISAModel client: {e}")
        raise


async def reset_client():
    """Reset and cleanup client instance"""
    global _client_instance

    async with _client_lock:
        if _client_instance:
            try:
                # Close the client if it has cleanup methods
                if hasattr(_client_instance, '__aexit__'):
                    await _client_instance.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing client: {e}")
            finally:
                _client_instance = None
                logger.info("Model client instance reset")


# Backward compatibility - redirect to new function name
async def get_isa_client(**kwargs) -> AsyncISAModel:
    """
    Get configured AsyncISAModel client instance

    This is the primary way to get an ISA Model client with
    centralized configuration and singleton pattern.

    Args:
        **kwargs: Override parameters (base_url, api_key, etc.)

    Returns:
        AsyncISAModel instance

    Usage:
        # Get client
        client = await get_isa_client()

        # Use with context manager
        async with await get_isa_client() as client:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            print(response.choices[0].message.content)

        # For embeddings (OpenAI-compatible)
        async with await get_isa_client() as client:
            embedding = await client.embeddings.create(
                input="Your text here",
                model="text-embedding-3-small"
            )
            vector = embedding.data[0].embedding

        # For vision (OpenAI-compatible)
        async with await get_isa_client() as client:
            vision = await client.vision.completions.create(
                image="https://example.com/image.jpg",
                prompt="Describe this image",
                model="gpt-4o-mini"
            )

        # For image generation (OpenAI-compatible)
        async with await get_isa_client() as client:
            image = await client.images.generate(
                prompt="A sunset over mountains",
                model="dall-e-3"
            )
    """
    # Backward compatibility: redirect to new function
    return await get_model_client(**kwargs)


# Exports
__all__ = [
    'get_model_client',
    'get_isa_client',  # Backward compatibility
    'reset_client',
    'AsyncISAModel'
]