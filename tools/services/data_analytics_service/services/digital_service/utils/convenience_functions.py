#!/usr/bin/env python3
"""
Convenience Functions Module

Global convenience functions for easy access to Digital Analytics Service
"""

from typing import Dict, Any, List, Optional
from ..config.analytics_config import AnalyticsConfig, VectorDBPolicy, ProcessingMode
from ..enhanced_digital_service import DigitalAnalyticsService

# Global service instance
_digital_analytics_service = None


def get_digital_analytics_service(config: Optional[AnalyticsConfig] = None) -> DigitalAnalyticsService:
    """Get singleton instance of Digital Analytics Service"""
    global _digital_analytics_service
    if _digital_analytics_service is None:
        _digital_analytics_service = DigitalAnalyticsService(config)
    return _digital_analytics_service


def create_digital_analytics_service(config: Optional[AnalyticsConfig] = None) -> DigitalAnalyticsService:
    """Create new instance of Digital Analytics Service"""
    global _digital_analytics_service
    _digital_analytics_service = DigitalAnalyticsService(config)
    return _digital_analytics_service


# === KNOWLEDGE MANAGEMENT CONVENIENCE FUNCTIONS ===

async def store_knowledge(
    user_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Store knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.store_knowledge(user_id, text, metadata)


async def search_knowledge(
    user_id: str,
    query: str,
    top_k: int = 5,
    enable_rerank: bool = False,
    search_mode: str = "hybrid",
    rag_mode: str = None
) -> Dict[str, Any]:
    """Search knowledge using integrated RAG service"""
    service = get_digital_analytics_service()
    return await service.search_knowledge(user_id, query, top_k, enable_rerank, search_mode, rag_mode)


async def generate_rag_response(
    user_id: str,
    query: str,
    context_limit: int = 3,
    rag_mode: str = None,
    enable_inline_citations: bool = True
) -> Dict[str, Any]:
    """Generate RAG response using integrated service"""
    service = get_digital_analytics_service()
    return await service.generate_rag_response(user_id, query, context_limit, rag_mode, enable_inline_citations)


# === MULTI-MODE RAG CONVENIENCE FUNCTIONS ===

async def query_with_mode(
    user_id: str,
    query: str,
    mode: str = "simple",
    **kwargs
) -> Dict[str, Any]:
    """Query using specific RAG mode"""
    service = get_digital_analytics_service()
    return await service.query_with_mode(user_id, query, mode, **kwargs)


async def hybrid_query(
    user_id: str,
    query: str,
    modes: List[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Execute hybrid query across multiple RAG modes"""
    service = get_digital_analytics_service()
    return await service.hybrid_query(user_id, query, modes, **kwargs)


async def recommend_mode(
    query: str,
    user_id: str
) -> Dict[str, Any]:
    """Recommend best RAG mode for a query"""
    service = get_digital_analytics_service()
    return await service.recommend_mode(query, user_id)


async def get_rag_capabilities() -> Dict[str, Any]:
    """Get comprehensive RAG capabilities"""
    service = get_digital_analytics_service()
    return await service.get_rag_capabilities()


# === SERVICE MANAGEMENT CONVENIENCE FUNCTIONS ===

async def get_service_stats() -> Dict[str, Any]:
    """Get comprehensive service statistics"""
    service = get_digital_analytics_service()
    return await service.get_service_stats()


async def configure_policy(
    policy: VectorDBPolicy,
    additional_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Dynamically reconfigure vector database policy"""
    service = get_digital_analytics_service()
    return await service.configure_policy(policy, additional_config)











