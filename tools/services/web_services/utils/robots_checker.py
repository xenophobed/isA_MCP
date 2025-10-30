#!/usr/bin/env python3
"""
Robots.txt Checker Utility
Ethical web scraping compliance using robots.txt parsing

Based on MCP Fetch Server pattern for respectful autonomous web access
"""

import asyncio
from typing import Dict, Tuple, Optional, TYPE_CHECKING
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timedelta
import httpx
from core.logging import get_logger

logger = get_logger(__name__)

try:
    from protego import Protego
    HAS_PROTEGO = True
except ImportError:
    HAS_PROTEGO = False
    Protego = None  # Define as None when not available
    logger.warning("⚠️ protego not installed - robots.txt checking disabled. Install: pip install protego")


class RobotsChecker:
    """
    Check robots.txt compliance for web scraping

    Features:
    - Caches robots.txt per domain
    - Respects cache expiry
    - Handles network errors gracefully
    - Clear error messages
    """

    def __init__(self, user_agent: str, cache_ttl_hours: int = 24):
        """
        Initialize robots.txt checker

        Args:
            user_agent: User-Agent string to check against
            cache_ttl_hours: How long to cache robots.txt (default 24h)
        """
        self.user_agent = user_agent
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Cache: {domain: {"parser": Protego, "cached_at": datetime}}
        self.cache: Dict[str, Dict] = {}

        logger.info(f"🤖 RobotsChecker initialized for UA: {user_agent[:50]}...")

    def _get_robots_txt_url(self, url: str) -> str:
        """
        Get robots.txt URL for a given website URL

        Args:
            url: Website URL

        Returns:
            URL of robots.txt file
        """
        parsed = urlparse(url)
        robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
        return robots_url

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for caching"""
        parsed = urlparse(url)
        return parsed.netloc

    async def _fetch_robots_txt(self, domain: str, robots_url: str) -> Optional[Protego]:
        """
        Fetch and parse robots.txt

        Args:
            domain: Domain name (for logging)
            robots_url: URL of robots.txt

        Returns:
            Protego parser or None if failed
        """
        if not HAS_PROTEGO:
            logger.warning("⚠️ protego not available - allowing all requests")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    robots_url,
                    follow_redirects=True,
                    headers={"User-Agent": self.user_agent}
                )

                # Handle HTTP errors
                if response.status_code in (401, 403):
                    logger.warning(
                        f"⚠️ robots.txt returned {response.status_code} for {domain} "
                        f"- assuming restrictive (blocking autonomous access)"
                    )
                    # Create restrictive robots.txt
                    restrictive_robots = "User-agent: *\nDisallow: /"
                    return Protego.parse(restrictive_robots)

                elif 400 <= response.status_code < 500:
                    # 404 or other client error - no robots.txt exists
                    logger.info(f"✅ No robots.txt found for {domain} (status {response.status_code}) - allowing all")
                    return None

                elif response.status_code >= 500:
                    logger.error(f"❌ Server error fetching robots.txt for {domain} (status {response.status_code})")
                    return None

                # Parse robots.txt
                robot_txt = response.text

                # Remove comments for cleaner parsing
                processed_robot_txt = "\n".join(
                    line for line in robot_txt.splitlines()
                    if not line.strip().startswith("#")
                )

                parser = Protego.parse(processed_robot_txt)
                logger.info(f"✅ Parsed robots.txt for {domain} ({len(robot_txt)} bytes)")

                return parser

        except httpx.TimeoutException:
            logger.warning(f"⚠️ Timeout fetching robots.txt for {domain} - allowing request")
            return None
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error fetching robots.txt for {domain}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching robots.txt for {domain}: {e}")
            return None

    def _is_cache_valid(self, domain: str) -> bool:
        """Check if cached robots.txt is still valid"""
        if domain not in self.cache:
            return False

        cached_at = self.cache[domain]["cached_at"]
        age = datetime.now() - cached_at

        return age < self.cache_ttl

    async def can_fetch(
        self,
        url: str,
        autonomous: bool = True,
        bypass_cache: bool = False
    ) -> Tuple[bool, str]:
        """
        Check if URL can be fetched according to robots.txt

        Args:
            url: URL to check
            autonomous: If True, enforce robots.txt. If False, allow all (user-directed)
            bypass_cache: Force refresh robots.txt from server

        Returns:
            Tuple of (can_fetch: bool, reason: str)
        """
        # Manual/user-directed requests bypass robots.txt
        if not autonomous:
            return True, "User-directed request bypasses robots.txt"

        # If protego not available, allow (with warning)
        if not HAS_PROTEGO:
            return True, "robots.txt checking disabled (protego not installed)"

        try:
            domain = self._get_domain(url)
            robots_url = self._get_robots_txt_url(url)

            # Check cache
            if not bypass_cache and self._is_cache_valid(domain):
                parser = self.cache[domain]["parser"]
                logger.debug(f"📦 Using cached robots.txt for {domain}")
            else:
                # Fetch fresh robots.txt
                parser = await self._fetch_robots_txt(domain, robots_url)

                # Cache result
                self.cache[domain] = {
                    "parser": parser,
                    "cached_at": datetime.now()
                }

            # No robots.txt found or error - allow
            if parser is None:
                return True, f"No robots.txt found for {domain}"

            # Check if allowed
            can_fetch = parser.can_fetch(url, self.user_agent)

            if can_fetch:
                return True, f"Allowed by robots.txt for {domain}"
            else:
                return False, (
                    f"Blocked by robots.txt for {domain}\n"
                    f"URL: {url}\n"
                    f"User-Agent: {self.user_agent}\n"
                    f"robots.txt: {robots_url}\n"
                    f"Hint: User can manually fetch via prompt/UI to bypass"
                )

        except Exception as e:
            logger.error(f"❌ Error checking robots.txt: {e}")
            # On error, allow (but log warning)
            return True, f"Error checking robots.txt (allowing request): {str(e)}"

    async def check_multiple(
        self,
        urls: list[str],
        autonomous: bool = True
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Check multiple URLs concurrently

        Args:
            urls: List of URLs to check
            autonomous: If True, enforce robots.txt

        Returns:
            Dictionary mapping URL to (can_fetch, reason) tuple
        """
        tasks = [self.can_fetch(url, autonomous) for url in urls]
        results = await asyncio.gather(*tasks)

        return dict(zip(urls, results))

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        valid_entries = sum(1 for domain in self.cache if self._is_cache_valid(domain))

        return {
            "total_cached_domains": len(self.cache),
            "valid_cached_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "cache_ttl_hours": self.cache_ttl.total_seconds() / 3600
        }

    def clear_cache(self, domain: Optional[str] = None):
        """
        Clear robots.txt cache

        Args:
            domain: Specific domain to clear, or None to clear all
        """
        if domain:
            if domain in self.cache:
                del self.cache[domain]
                logger.info(f"🗑️ Cleared robots.txt cache for {domain}")
        else:
            self.cache.clear()
            logger.info("🗑️ Cleared all robots.txt cache")


# Singleton instance for easy access
_default_checker: Optional[RobotsChecker] = None


def get_robots_checker(user_agent: str = None) -> RobotsChecker:
    """
    Get or create default robots checker

    Args:
        user_agent: User-Agent string (uses default if None)
    """
    global _default_checker

    if _default_checker is None or (user_agent and _default_checker.user_agent != user_agent):
        from tools.services.web_services.utils.user_agents import USER_AGENT_AUTONOMOUS
        ua = user_agent or USER_AGENT_AUTONOMOUS
        _default_checker = RobotsChecker(ua)

    return _default_checker
