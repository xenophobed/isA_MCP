#!/usr/bin/env python3
"""
Memory Service Client
Enterprise-grade client for memory microservice with Consul service discovery
"""

import os
import aiohttp
import logging
import consul
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class MemoryServiceConfig:
    """Memory service configuration"""
    service_name: str = "memory_service"
    consul_host: str = "localhost"
    consul_port: int = 8500
    api_timeout: int = 30
    max_retries: int = 3
    fallback_host: str = "localhost"
    fallback_port: int = 8223

    @classmethod
    def from_env(cls) -> 'MemoryServiceConfig':
        """Create config from environment variables"""
        return cls(
            service_name=os.getenv('MEMORY_SERVICE_NAME', 'memory_service'),
            consul_host=os.getenv('CONSUL_HOST', 'localhost'),
            consul_port=int(os.getenv('CONSUL_PORT', '8500')),
            api_timeout=int(os.getenv('MEMORY_API_TIMEOUT', '30')),
            max_retries=int(os.getenv('MEMORY_MAX_RETRIES', '3')),
            fallback_host=os.getenv('MEMORY_FALLBACK_HOST', 'localhost'),
            fallback_port=int(os.getenv('MEMORY_FALLBACK_PORT', '8223'))
        )


class MemoryServiceClient:
    """
    Memory service client with:
    - Consul service discovery
    - Environment configuration
    - Retry logic
    - Proper error handling
    """

    def __init__(self, config: Optional[MemoryServiceConfig] = None):
        self.config = config or MemoryServiceConfig.from_env()
        self.consul_client = None
        self.service_url = None
        self._session = None

    async def _discover_service(self) -> Optional[str]:
        """Discover memory service URL via Consul"""
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
                logger.info(f"Discovered memory service at: {service_url}")
                return service_url
            else:
                logger.warning(f"No healthy {self.config.service_name} instances found in Consul")
                return None

        except Exception as e:
            logger.warning(f"Memory service discovery failed: {str(e)}")
            return None

    async def _get_service_url(self) -> str:
        """Get service URL with fallback"""
        if not self.service_url:
            # Try Consul discovery first
            self.service_url = await self._discover_service()

            # Fallback to configured host/port
            if not self.service_url:
                self.service_url = f"http://{self.config.fallback_host}:{self.config.fallback_port}"
                logger.info(f"Using fallback memory service URL: {self.service_url}")

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
                        return await response.json()
                    elif response.status == 404:
                        error_detail = await response.text()
                        raise Exception(f"Not found: {error_detail}")
                    else:
                        error_detail = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_detail}")

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    # Reset service URL to trigger re-discovery
                    self.service_url = None
                continue

        raise Exception(f"All retry attempts failed. Last error: {last_error}")

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ==================== Health Check ====================

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._request("GET", "/health")

    # ==================== AI-Powered Memory Storage ====================

    async def store_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store factual memories from dialog using AI"""
        return await self._request(
            "POST",
            "/memories/factual/extract",
            json={
                "user_id": user_id,
                "dialog_content": dialog_content,
                "importance_score": importance_score
            }
        )

    async def store_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store episodic memories from dialog using AI"""
        return await self._request(
            "POST",
            "/memories/episodic/extract",
            json={
                "user_id": user_id,
                "dialog_content": dialog_content,
                "importance_score": importance_score
            }
        )

    async def store_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store procedural memories from dialog using AI"""
        return await self._request(
            "POST",
            "/memories/procedural/extract",
            json={
                "user_id": user_id,
                "dialog_content": dialog_content,
                "importance_score": importance_score
            }
        )

    async def store_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store semantic memories from dialog using AI"""
        return await self._request(
            "POST",
            "/memories/semantic/extract",
            json={
                "user_id": user_id,
                "dialog_content": dialog_content,
                "importance_score": importance_score
            }
        )

    async def store_working_memory(
        self,
        user_id: str,
        dialog_content: str,
        ttl_seconds: int = 3600,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Store working memory from dialog"""
        return await self._request(
            "POST",
            "/memories/working/store",
            json={
                "user_id": user_id,
                "dialog_content": dialog_content,
                "ttl_seconds": ttl_seconds,
                "importance_score": importance_score
            }
        )

    async def store_session_message(
        self,
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user"
    ) -> Dict[str, Any]:
        """Store session message"""
        return await self._request(
            "POST",
            "/memories/session/store",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message_content": message_content,
                "message_type": message_type,
                "role": role
            }
        )

    # ==================== Search Operations ====================

    async def search_memories(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.4
    ) -> Dict[str, Any]:
        """Search across memory types using semantic similarity"""
        params = {
            "user_id": user_id,
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold
        }
        if memory_types:
            params["memory_types"] = ",".join(memory_types)

        return await self._request("GET", "/memories/search", params=params)

    async def search_facts_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search facts by subject"""
        return await self._request(
            "GET",
            "/memories/factual/search/subject",
            params={"user_id": user_id, "subject": subject, "limit": limit}
        )

    async def search_concepts_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search concepts by category

        NOTE: This endpoint does not exist on the memory service yet.
        This method is a placeholder for future implementation.
        """
        return await self._request(
            "GET",
            "/memories/semantic/search/category",
            params={"user_id": user_id, "category": category, "limit": limit}
        )

    async def search_episodes_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search episodic memories by event type"""
        return await self._request(
            "GET",
            "/memories/episodic/search/event_type",
            params={"user_id": user_id, "event_type": event_type, "limit": limit}
        )

    # ==================== Session Operations ====================

    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive session context"""
        return await self._request(
            "GET",
            f"/memories/session/{session_id}/context",
            params={
                "user_id": user_id,
                "include_summaries": include_summaries,
                "max_recent_messages": max_recent_messages
            }
        )

    async def summarize_session(
        self,
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> Dict[str, Any]:
        """Summarize session conversation"""
        return await self._request(
            "POST",
            f"/memories/session/{session_id}/summarize",
            json={
                "user_id": user_id,
                "force_update": force_update,
                "compression_level": compression_level
            }
        )

    # ==================== Working Memory Operations ====================

    async def get_active_working_memories(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get active working memories"""
        return await self._request(
            "GET",
            "/memories/working/active",
            params={"user_id": user_id}
        )

    # ==================== Utility Operations ====================

    async def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        return await self._request(
            "GET",
            "/memories/statistics",
            params={"user_id": user_id}
        )


# Global client instance
_client_instance = None


def get_memory_client() -> MemoryServiceClient:
    """Get global memory client instance (singleton)"""
    global _client_instance
    if _client_instance is None:
        _client_instance = MemoryServiceClient()
    return _client_instance
