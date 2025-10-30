#!/usr/bin/env python3
"""
Enhanced Content Extractor
Clean content extraction using Readability + Markdown conversion

Based on MCP Fetch Server pattern for LLM-friendly content
"""

from typing import Dict, Any, Optional
from core.logging import get_logger

logger = get_logger(__name__)

# Check for readability and markdownify
try:
    import readabilipy.simple_json
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False
    readabilipy = None
    logger.warning("⚠️ readabilipy not installed - using BS4 fallback. Install: pip install readabilipy")

try:
    import markdownify
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False
    markdownify = None
    logger.warning("⚠️ markdownify not installed - using plain text. Install: pip install markdownify")


class ContentExtractor:
    """
    Multi-strategy content extraction

    Strategies (in order of preference):
    1. Readability + Markdown - Clean, article-focused extraction
    2. BeautifulSoup - Simple text extraction
    3. Raw HTML - Last resort
    """

    def __init__(self):
        self.strategies_available = {
            "readability": HAS_READABILITY and HAS_MARKDOWNIFY,
            "bs4": True,  # Always available (existing implementation)
            "raw": True   # Always available
        }
        logger.info(f"📄 ContentExtractor initialized. Available strategies: {self.strategies_available}")

    def extract_with_readability(self, html: str, url: str = "") -> Dict[str, Any]:
        """
        Extract content using Readability algorithm + Markdown conversion

        Args:
            html: Raw HTML content
            url: Optional URL for context

        Returns:
            Dictionary with extracted content and metadata
        """
        if not (HAS_READABILITY and HAS_MARKDOWNIFY):
            raise ImportError("readabilipy and markdownify required for this method")

        try:
            # Step 1: Extract main content with readability algorithm
            result = readabilipy.simple_json.simple_json_from_html_string(
                html,
                use_readability=True
            )

            # Check if content was successfully extracted
            if not result or not result.get('content'):
                logger.warning("⚠️ Readability extraction returned empty content")
                return {
                    "method": "readability",
                    "success": False,
                    "error": "No content extracted by readability algorithm"
                }

            # Step 2: Convert to clean markdown
            markdown_content = markdownify.markdownify(
                result['content'],
                heading_style=markdownify.ATX,  # Use # style headings
                bullets="-",                     # Use - for unordered lists
                strong_em_symbol="**",           # Use ** for bold
            )

            # Extract metadata
            return {
                "method": "readability",
                "success": True,
                "content": markdown_content,
                "title": result.get('title', ''),
                "byline": result.get('byline', ''),
                "author": result.get('byline', ''),  # Alias for author
                "excerpt": result.get('excerpt', ''),
                "length": len(markdown_content),
                "plain_content": result.get('plain_content', ''),
                "html_content": result.get('content', ''),
                "url": url
            }

        except Exception as e:
            logger.error(f"❌ Readability extraction failed: {e}")
            return {
                "method": "readability",
                "success": False,
                "error": str(e)
            }

    async def extract_with_bs4(self, html: str, url: str = "") -> Dict[str, Any]:
        """
        Extract content using BeautifulSoup (fallback)

        Args:
            html: Raw HTML content
            url: Optional URL for context

        Returns:
            Dictionary with extracted content
        """
        try:
            # Import existing BS4 service
            from tools.services.web_services.services.bs4_service import extract_text as bs4_extract

            # bs4_extract is async, need to await
            bs4_result = await bs4_extract(url, enhanced=False)

            return {
                "method": "bs4",
                "success": True,
                "content": bs4_result.content if bs4_result.success else "",
                "title": bs4_result.title if bs4_result.success else "",
                "length": len(bs4_result.content) if bs4_result.success else 0,
                "url": url
            }

        except Exception as e:
            logger.error(f"❌ BS4 extraction failed: {e}")
            return {
                "method": "bs4",
                "success": False,
                "error": str(e)
            }

    def extract_raw(self, html: str, url: str = "", content_type: str = "") -> Dict[str, Any]:
        """
        Return raw content (last resort)

        Args:
            html: Raw HTML content
            url: Optional URL for context
            content_type: Content-Type header

        Returns:
            Dictionary with raw content
        """
        return {
            "method": "raw",
            "success": True,
            "content": html,
            "content_type": content_type,
            "length": len(html),
            "url": url,
            "warning": f"Content type {content_type} cannot be simplified, returning raw content"
        }

    async def extract(
        self,
        html: str,
        url: str = "",
        content_type: str = "",
        force_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Smart content extraction with automatic strategy selection

        Args:
            html: Raw HTML content
            url: Optional URL for context
            content_type: Optional Content-Type header
            force_method: Force specific extraction method (readability, bs4, raw)

        Returns:
            Dictionary with extracted content and metadata
        """
        # Detect content type
        is_html = (
            "text/html" in content_type.lower() or
            "<html" in html[:100].lower() or
            not content_type
        )

        # If not HTML, return raw
        if not is_html and not force_method:
            logger.info(f"📄 Non-HTML content detected ({content_type}), returning raw")
            return self.extract_raw(html, url, content_type)

        # Force specific method if requested
        if force_method:
            if force_method == "readability" and self.strategies_available["readability"]:
                return self.extract_with_readability(html, url)
            elif force_method == "bs4":
                return await self.extract_with_bs4(html, url)
            elif force_method == "raw":
                return self.extract_raw(html, url, content_type)
            else:
                logger.warning(f"⚠️ Forced method '{force_method}' not available, using auto")

        # Auto-select best available strategy
        # Try readability first (best quality)
        if self.strategies_available["readability"]:
            logger.info("📄 Using readability + markdown extraction")
            result = self.extract_with_readability(html, url)

            if result["success"]:
                return result
            else:
                logger.warning("⚠️ Readability failed, falling back to BS4")

        # Fallback to BS4
        logger.info("📄 Using BS4 text extraction")
        result = await self.extract_with_bs4(html, url)

        if result["success"]:
            return result

        # Last resort: raw content
        logger.warning("⚠️ All extraction methods failed, returning raw HTML")
        return self.extract_raw(html, url, content_type)

    async def extract_with_pagination(
        self,
        html: str,
        url: str = "",
        max_length: int = 5000,
        start_index: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract content with automatic pagination

        Args:
            html: Raw HTML content
            url: Optional URL
            max_length: Maximum content length per chunk
            start_index: Starting character index
            **kwargs: Additional arguments for extract()

        Returns:
            Dictionary with paginated content
        """
        # First, extract full content
        result = await self.extract(html, url, **kwargs)

        if not result["success"]:
            return result

        content = result["content"]
        total_length = len(content)

        # Check if start_index is valid
        if start_index >= total_length:
            result["content"] = ""
            result["error"] = "No more content available (start_index beyond content length)"
            result["has_more"] = False
            return result

        # Extract chunk
        chunk = content[start_index:start_index + max_length]
        actual_length = len(chunk)
        remaining = total_length - (start_index + actual_length)

        # Add pagination metadata
        result["content"] = chunk
        result["pagination"] = {
            "start_index": start_index,
            "chunk_length": actual_length,
            "total_length": total_length,
            "has_more": remaining > 0,
            "next_start_index": start_index + actual_length if remaining > 0 else None,
            "remaining_chars": remaining
        }

        # Add continuation prompt if truncated
        if remaining > 0:
            continuation_prompt = (
                f"\n\n💡 **Content continues** ({remaining:,} characters remaining). "
                f"Use start_index={start_index + actual_length} to fetch more."
            )
            result["content"] += continuation_prompt

        return result


# Singleton instance
_default_extractor: Optional[ContentExtractor] = None


def get_content_extractor() -> ContentExtractor:
    """Get or create default content extractor"""
    global _default_extractor

    if _default_extractor is None:
        _default_extractor = ContentExtractor()

    return _default_extractor


# Convenience functions
async def extract_content(html: str, url: str = "", **kwargs) -> Dict[str, Any]:
    """Quick content extraction"""
    extractor = get_content_extractor()
    return await extractor.extract(html, url, **kwargs)


async def extract_content_paginated(
    html: str,
    url: str = "",
    max_length: int = 5000,
    start_index: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """Quick paginated extraction"""
    extractor = get_content_extractor()
    return await extractor.extract_with_pagination(html, url, max_length, start_index, **kwargs)
