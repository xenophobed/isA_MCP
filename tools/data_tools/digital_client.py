#!/usr/bin/env python3
"""
Digital Analytics Service Client
Enterprise-grade client for digital analytics microservice with Consul service discovery
Supports SSE (Server-Sent Events) for real-time progress tracking
"""

import os
import aiohttp
import logging
from typing import Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass
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
class DigitalServiceConfig:
    """Digital analytics service configuration"""

    service_name: str = "data_service"
    consul_host: str = "localhost"
    consul_port: int = 8500
    api_timeout: int = 300  # Longer timeout for RAG operations
    max_retries: int = 3
    fallback_host: str = "localhost"
    fallback_port: int = 8083

    @classmethod
    def from_env(cls) -> "DigitalServiceConfig":
        """Create config from environment variables"""
        return cls(
            service_name=os.getenv("DATA_SERVICE_NAME", "data_service"),
            consul_host=os.getenv("CONSUL_HOST", "localhost"),
            consul_port=int(os.getenv("CONSUL_PORT", "8500")),
            api_timeout=int(os.getenv("DATA_API_TIMEOUT", "300")),
            max_retries=int(os.getenv("DATA_MAX_RETRIES", "3")),
            fallback_host=os.getenv("DATA_FALLBACK_HOST", "localhost"),
            fallback_port=int(os.getenv("DATA_FALLBACK_PORT", "8083")),
        )


class DigitalServiceClient:
    """
    Digital analytics service client with:
    - Consul service discovery
    - Environment configuration
    - Retry logic
    - SSE (Server-Sent Events) support for progress tracking
    - Proper error handling
    """

    def __init__(self, config: Optional[DigitalServiceConfig] = None):
        self.config = config or DigitalServiceConfig.from_env()
        self.consul_client = None
        self.service_url = None
        self._session = None

    async def _discover_service(self) -> Optional[str]:
        """Discover digital analytics service URL via Consul"""
        if not CONSUL_AVAILABLE:
            logger.debug("Consul not available, skipping service discovery")
            return None

        try:
            if not self.consul_client:
                self.consul_client = consul.Consul(
                    host=self.config.consul_host, port=self.config.consul_port
                )

            # Get healthy service instances
            services = self.consul_client.health.service(self.config.service_name, passing=True)[1]

            if services:
                service = services[0]["Service"]
                service_url = f"http://{service['Address']}:{service['Port']}"
                logger.info(f"Discovered data service at: {service_url}")
                return service_url
            else:
                logger.warning(f"No healthy {self.config.service_name} instances found in Consul")
                return None

        except Exception as e:
            logger.warning(f"Data service discovery failed: {str(e)}")
            return None

    async def _get_service_url(self) -> str:
        """Get service URL with fallback"""
        if not self.service_url:
            # Try Consul discovery first
            self.service_url = await self._discover_service()

            # Fallback to configured host/port
            if not self.service_url:
                self.service_url = f"http://{self.config.fallback_host}:{self.config.fallback_port}"
                logger.info(f"Using fallback data service URL: {self.service_url}")

        return self.service_url

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.api_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
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
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

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
        self, method: str, endpoint: str, **kwargs
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
                    line = line.decode("utf-8").strip()

                    # SSE format: "data: {...}"
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:]  # Remove "data: " prefix
                            data = json.loads(data_str)
                            yield data

                            # Check if completed
                            if data.get("type") == "result" or data.get("completed"):
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

    # ==================== Digital Analytics Operations ====================

    async def store(
        self,
        user_id: str,
        content: str,
        content_type: str = "text",
        mode: str = "simple",
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Store content to knowledge base with SSE progress tracking

        Args:
            user_id: User identifier
            content: Content to store (text, PDF URL, or image URL)
            content_type: Content type - "text", "pdf", "image" (default "text")
            mode: RAG mode - "simple", "crag", "self_rag", "hyde", "raptor",
                  "graph_rag", "rag_fusion" (default "simple")
            collection_name: Collection name for organizing content (optional)
            metadata: Additional metadata for the content (optional)

        Yields:
            Progress updates and final storage results via SSE
        """
        payload = {
            "user_id": user_id,
            "content": content,
            "content_type": content_type,
            "mode": mode,
        }

        if collection_name:
            payload["collection_name"] = collection_name
        if metadata:
            payload["metadata"] = metadata

        async for message in self._request_sse("POST", "/api/v1/digital/store", json=payload):
            yield message

    async def search(
        self,
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search knowledge base for relevant content

        Args:
            user_id: User identifier
            query: Search query
            mode: RAG mode (default "simple")
            collection_name: Collection to search in (optional)
            top_k: Number of results to return (default 5)
            options: Mode-specific options (optional)

        Returns:
            Search results with relevance scores
        """
        payload = {"user_id": user_id, "query": query, "mode": mode, "top_k": top_k}

        if collection_name:
            payload["collection_name"] = collection_name
        if options:
            payload["options"] = options

        return await self._request("POST", "/api/v1/digital/search", json=payload)

    async def generate_response(
        self,
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate AI response based on retrieved context with SSE progress

        Args:
            user_id: User identifier
            query: Query to generate response for
            mode: RAG mode (default "simple")
            collection_name: Collection to search in (optional)
            top_k: Number of context chunks to use (default 5)
            options: Mode-specific options (optional, can include "use_citations")

        Yields:
            Progress updates and final generated response via SSE
        """
        payload = {"user_id": user_id, "query": query, "mode": mode, "top_k": top_k}

        if collection_name:
            payload["collection_name"] = collection_name
        if options:
            payload["options"] = options

        async for message in self._request_sse("POST", "/api/v1/digital/response", json=payload):
            yield message


# Global client instance
_client_instance = None


def get_digital_client() -> DigitalServiceClient:
    """Get global digital client instance (singleton)"""
    global _client_instance
    if _client_instance is None:
        _client_instance = DigitalServiceClient()
    return _client_instance
