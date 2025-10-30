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
    """Create AsyncISAModel client with environment configuration"""
    try:
            # Get configuration from environment with fallbacks
            base_url = kwargs.get('base_url') or os.getenv('ISA_API_URL') or os.getenv('ISA_SERVICE_URL')
            api_key = kwargs.get('api_key') or os.getenv('ISA_API_KEY')

            # Try to get from config if not in environment
            if not base_url:
                try:
                    from core.config import get_settings
                    settings = get_settings()
                    base_url = getattr(settings, 'isa_api_url', None) or getattr(settings, 'isa_service_url', None)
                    if not api_key:
                        api_key = getattr(settings, 'isa_api_key', None)
                except Exception as e:
                    logger.debug(f"Could not load config settings: {e}")

            # Try Consul service discovery
            if base_url:
                try:
                    from core.consul_discovery import discover_service
                    consul_url = discover_service('model_service', default_url=base_url)
                    if consul_url and consul_url != base_url:
                        logger.info(f"🔍 Consul discovered ISA Model service: {consul_url}")
                        base_url = consul_url
                except Exception as consul_error:
                    logger.debug(f"Consul discovery failed: {consul_error}")

            # Default to localhost if still no URL
            if not base_url:
                base_url = "http://localhost:8082"
                logger.warning(f"No ISA_API_URL configured, using default: {base_url}")

            # Create AsyncISAModel client
            client = AsyncISAModel(
                base_url=base_url,
                api_key=api_key
            )

            logger.info(f"✅ AsyncISAModel client created: {base_url}")
            logger.info(f"   Authentication: {'Enabled' if api_key else 'Disabled'}")

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