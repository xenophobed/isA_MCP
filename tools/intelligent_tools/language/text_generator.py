#!/usr/bin/env python3
"""
Text Generator Service
Simple wrapper around ISA client for text generation
"""

from typing import Optional
from core.logging import get_logger

logger = get_logger(__name__)


class TextGenerator:
    """Simple text generation service using ISA client"""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """Lazy load ISA client with optional authentication"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    async def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs
    ) -> str:
        """
        Generate text from a prompt

        Args:
            prompt: The input prompt
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text string
        """
        try:
            # Prepare parameters
            params = {"temperature": temperature}
            if max_tokens:
                params["max_tokens"] = max_tokens
            params.update(kwargs)

            # Call ISA client with default OpenAI model using new API
            logger.info(f"Calling ISA with prompt length: {len(prompt)}, params: {params}")
            client = await self._get_client()

            # Use OpenAI-compatible chat.completions.create()
            response = await client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                **params,
            )

            logger.info(f"ISA response received, model: {response.model}")

            # Extract text from response
            result_text = response.choices[0].message.content
            billing_info = {}  # New API doesn't expose billing in same way

            # Check for empty result and retry if needed
            if not result_text or not result_text.strip():
                logger.warning(f"Empty result on first attempt")

                # Retry once
                logger.info("Retrying ISA call once...")
                retry_client = await self._get_client()
                retry_response = await retry_client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                    **params,
                )

                retry_result_text = retry_response.choices[0].message.content

                if retry_result_text and retry_result_text.strip():
                    logger.info("✅ Retry successful")
                    result_text = retry_result_text
                else:
                    logger.error(f"Retry also failed - empty result")
                    raise Exception("No result found in response after retry")

            # Log billing info
            if billing_info:
                logger.info(f"💰 Text generation cost: ${billing_info.get('cost_usd', 0.0):.6f}")

            return result_text

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise

    async def generate_playwright_actions(
        self, prompt: str, temperature: float = 0.3, **kwargs
    ) -> str:
        """
        Generate Playwright actions from a reasoning prompt (atomic function)

        Args:
            prompt: Prompt describing UI analysis and requesting action sequence
            temperature: Lower temperature for more consistent action generation
            **kwargs: Additional parameters

        Returns:
            Raw text response from LLM (caller handles parsing)
        """
        try:
            # Call the atomic generate function with lower temperature for actions
            response = await self.generate(prompt, temperature, **kwargs)
            return response

        except Exception as e:
            logger.error(f"❌ Playwright action generation failed: {e}")
            raise


# Global instance for easy import
text_generator = TextGenerator()


# Convenience functions
async def generate(prompt: str, **kwargs) -> str:
    """Generate text from prompt"""
    return await text_generator.generate(prompt, **kwargs)


async def generate_playwright_actions(prompt: str, temperature: float = 0.3, **kwargs) -> str:
    """Generate Playwright actions from reasoning prompt (atomic function)"""
    return await text_generator.generate_playwright_actions(prompt, temperature, **kwargs)
