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
    
    @property
    def client(self):
        """Lazy load ISA client with optional authentication"""
        if self._client is None:
            from core.isa_client_factory import get_isa_client
            self._client = get_isa_client()
        return self._client
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
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
            
            # Call ISA client
            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                stream=False,  # 禁用流式输出，获取完整响应
                **params
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Text generation cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return result_text
                
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    async def generate_playwright_actions(
        self,
        prompt: str,
        temperature: float = 0.3,
        **kwargs
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