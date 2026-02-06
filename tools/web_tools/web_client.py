#!/usr/bin/env python3
"""
Web Service Client
Enterprise-grade client for web microservice with Consul service discovery
Supports SSE (Server-Sent Events) for real-time progress tracking
"""

import os
import aiohttp
import logging
from typing import Dict, Optional, Any, List, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

# Optional consul import for service discovery
try:
    import consul
    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class WebServiceConfig:
    """Web service configuration"""
    service_name: str = "web_service"
    consul_host: str = "localhost"
    consul_port: int = 8500
    api_timeout: int = 120  # Longer timeout for web operations
    max_retries: int = 3
    fallback_host: str = "localhost"
    fallback_port: int = 8083

    @classmethod
    def from_env(cls) -> 'WebServiceConfig':
        """Create config from environment variables"""
        return cls(
            service_name=os.getenv('WEB_SERVICE_NAME', 'web_service'),
            consul_host=os.getenv('CONSUL_HOST', 'localhost'),
            consul_port=int(os.getenv('CONSUL_PORT', '8500')),
            api_timeout=int(os.getenv('WEB_API_TIMEOUT', '120')),
            max_retries=int(os.getenv('WEB_MAX_RETRIES', '3')),
            fallback_host=os.getenv('WEB_FALLBACK_HOST', 'localhost'),
            fallback_port=int(os.getenv('WEB_FALLBACK_PORT', '8083'))
        )


class WebServiceClient:
    """
    Web service client with:
    - Consul service discovery
    - Environment configuration
    - Retry logic
    - SSE (Server-Sent Events) support for progress tracking
    - Proper error handling
    """

    def __init__(self, config: Optional[WebServiceConfig] = None):
        self.config = config or WebServiceConfig.from_env()
        self.consul_client = None
        self.service_url = None
        self._session = None

    async def _discover_service(self) -> Optional[str]:
        """Discover web service URL via Consul"""
        if not CONSUL_AVAILABLE:
            logger.debug("Consul not available, skipping service discovery")
            return None

        try:
            if not self.consul_client:
                self.consul_client = consul.Consul(
                    host=self.config.consul_host,
                    port=self.config.consul_port
                )

            # Get healthy service instances
            services = self.consul_client.health.service(
                self.config.service_name,
                passing=True
            )[1]

            if services:
                service = services[0]['Service']
                service_url = f"http://{service['Address']}:{service['Port']}"
                logger.info(f"Discovered web service at: {service_url}")
                return service_url
            else:
                logger.warning(f"No healthy {self.config.service_name} instances found in Consul")
                return None

        except Exception as e:
            logger.warning(f"Web service discovery failed: {str(e)}")
            return None

    async def _get_service_url(self) -> str:
        """Get service URL with fallback"""
        if not self.service_url:
            # Try Consul discovery first
            self.service_url = await self._discover_service()

            # Fallback to configured host/port
            if not self.service_url:
                self.service_url = f"http://{self.config.fallback_host}:{self.config.fallback_port}"
                logger.info(f"Using fallback web service URL: {self.service_url}")

        return self.service_url

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.api_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        base_url = await self._get_service_url()
        url = f"{base_url}{endpoint}"
        session = await self._get_session()

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Close session after successful request to prevent unclosed session warnings
                        await self.close()
                        return result
                    elif response.status == 404:
                        error_detail = await response.text()
                        await self.close()
                        raise Exception(f"Not found: {error_detail}")
                    else:
                        error_detail = await response.text()
                        await self.close()
                        raise Exception(f"HTTP {response.status}: {error_detail}")

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    # Reset service URL to trigger re-discovery
                    self.service_url = None
                    # Close and recreate session for retry
                    await self.close()
                continue

        await self.close()
        raise Exception(f"All retry attempts failed. Last error: {last_error}")

    async def _request_sse(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Make HTTP request and stream SSE (Server-Sent Events) responses

        Yields progress updates in real-time as they arrive from the server.
        Each SSE message is parsed and yielded as a dict.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Request parameters (json, params, etc.)

        Yields:
            Dict[str, Any]: Parsed SSE message containing progress/result data
        """
        base_url = await self._get_service_url()
        url = f"{base_url}{endpoint}"
        session = await self._get_session()

        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status != 200:
                    error_detail = await response.text()
                    await self.close()
                    raise Exception(f"HTTP {response.status}: {error_detail}")

                # Stream SSE messages
                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    # SSE format: "data: {...}"
                    if line.startswith('data: '):
                        try:
                            data_str = line[6:]  # Remove "data: " prefix
                            data = json.loads(data_str)
                            yield data

                            # Check if completed
                            if data.get('completed'):
                                break

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE data: {line}, error: {e}")
                            continue

        except Exception as e:
            logger.error(f"SSE request failed: {e}")
            raise
        finally:
            await self.close()

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ==================== Health Check ====================

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._request("GET", "/health")

    # ==================== Web Search Operations ====================

    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: Optional[str] = None,
        result_filter: Optional[str] = None,
        goggle_type: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Basic web search with SSE progress tracking

        Args:
            query: Search query
            count: Number of results (default 10)
            freshness: Freshness filter ("day", "week", "month", "year")
            result_filter: Result type filter ("news", "videos", etc.)
            goggle_type: Goggle filter ("academic", etc.)

        Yields:
            Progress updates and final results via SSE
        """
        payload = {"query": query, "count": count}

        if freshness:
            payload["freshness"] = freshness
        if result_filter:
            payload["result_filter"] = result_filter
        if goggle_type:
            payload["goggle_type"] = goggle_type

        async for message in self._request_sse("POST", "/api/v1/web/search", json=payload):
            yield message

    async def deep_search(
        self,
        query: str,
        user_id: str,
        depth: int = 2,
        rag_mode: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Deep search with multi-strategy approach and SSE progress

        Args:
            query: Search query
            user_id: User identifier
            depth: Search depth (default 2)
            rag_mode: Enable RAG mode (default True)

        Yields:
            Progress updates and final results via SSE
        """
        payload = {
            "query": query,
            "user_id": user_id,
            "depth": depth,
            "rag_mode": rag_mode
        }

        async for message in self._request_sse("POST", "/api/v1/web/search/deep", json=payload):
            yield message

    async def search_with_summary(
        self,
        query: str,
        user_id: str,
        count: int = 10,
        summarize_count: int = 5,
        include_citations: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search with AI-powered summary and SSE progress

        Args:
            query: Search query
            user_id: User identifier
            count: Total number of results (default 10)
            summarize_count: Number of results to summarize (default 5)
            include_citations: Include citations in summary (default True)

        Yields:
            Progress updates and final results via SSE
        """
        payload = {
            "query": query,
            "user_id": user_id,
            "count": count,
            "summarize_count": summarize_count,
            "include_citations": include_citations
        }

        async for message in self._request_sse("POST", "/api/v1/web/search/with-summary", json=payload):
            yield message

    # ==================== Web Crawl Operations ====================

    async def crawl(
        self,
        url: str,
        provider: str = "self_hosted_crawl",
        use_vlm: bool = False,
        analyze: bool = False,
        analysis_request: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Crawl and extract content from a web page with SSE progress

        Args:
            url: Target URL to crawl
            provider: Crawl provider (default "self_hosted_crawl")
            use_vlm: Use Vision Language Model for analysis (default False)
            analyze: Perform content analysis (default False)
            analysis_request: Specific analysis request (optional)

        Yields:
            Progress updates and final crawl results via SSE
        """
        payload = {
            "url": url,
            "provider": provider,
            "use_vlm": use_vlm
        }

        if analyze:
            payload["analyze"] = True
        if analysis_request:
            payload["analysis_request"] = analysis_request

        async for message in self._request_sse("POST", "/api/v1/web/crawl", json=payload):
            yield message

    # ==================== Web Automation Operations ====================

    async def automation_execute(
        self,
        url: str,
        task: str,
        provider: str = "self_hosted",
        routing_strategy: str = "dom_first",
        use_vlm: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute web automation task with SSE progress

        Args:
            url: Target URL
            task: Task description (e.g., "Click on the More information link")
            provider: Automation provider (default "self_hosted")
            routing_strategy: Strategy - "dom_first", "vlm_first", "hybrid" (default "dom_first")
            use_vlm: Use Vision Language Model (default False)

        Yields:
            Progress updates and automation results via SSE
        """
        payload = {
            "url": url,
            "task": task,
            "provider": provider,
            "routing_strategy": routing_strategy,
            "use_vlm": use_vlm
        }

        async for message in self._request_sse("POST", "/api/v1/web/automation/execute", json=payload):
            yield message

    async def automation_search(
        self,
        query: str,
        search_engine: str = "google",
        task: Optional[str] = None,
        provider: str = "self_hosted",
        use_vlm: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute search automation task with SSE progress

        Args:
            query: Search query
            search_engine: Search engine to use (default "google")
            task: Optional additional task after search
            provider: Automation provider (default "self_hosted")
            use_vlm: Use Vision Language Model (default False)

        Yields:
            Progress updates and search automation results via SSE
        """
        payload = {
            "query": query,
            "search_engine": search_engine,
            "provider": provider,
            "use_vlm": use_vlm
        }

        if task:
            payload["task"] = task

        async for message in self._request_sse("POST", "/api/v1/web/automation/search", json=payload):
            yield message


# Global client instance
_client_instance = None


def get_web_client() -> WebServiceClient:
    """Get global web client instance (singleton)"""
    global _client_instance
    if _client_instance is None:
        _client_instance = WebServiceClient()
    return _client_instance
