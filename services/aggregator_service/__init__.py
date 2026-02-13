"""
Aggregator Service - MCP Server Aggregation for External Tools.

Provides:
- AggregatorService: Main service for managing external MCP servers
- ServerRegistry: Data access for server registrations
- SessionManager: MCP ClientSession management
- ToolAggregator: Tool discovery and indexing
- RequestRouter: Routing requests to external servers
- create_aggregator_service: Factory function with all dependencies wired
"""

import logging
from typing import Optional

from .aggregator_service import AggregatorService
from .server_registry import ServerRegistry
from .session_manager import SessionManager
from .tool_aggregator import ToolAggregator
from .request_router import RequestRouter

logger = logging.getLogger(__name__)

__all__ = [
    "AggregatorService",
    "ServerRegistry",
    "SessionManager",
    "ToolAggregator",
    "RequestRouter",
    "create_aggregator_service",
]


async def create_aggregator_service(
    db_pool=None, enable_classification: bool = True, model_client=None
) -> AggregatorService:
    """
    Factory function to create a fully configured AggregatorService.

    Creates all required dependencies:
    - ToolRepository for PostgreSQL storage
    - VectorRepository for Qdrant indexing
    - SkillService for automatic tool classification (optional)
    - ModelClient for embeddings

    Args:
        db_pool: Optional asyncpg connection pool (creates one if not provided)
        enable_classification: Enable automatic skill classification (default: True)
        model_client: Optional model client for embeddings

    Returns:
        Configured AggregatorService instance

    Example:
        ```python
        import asyncpg
        from services.aggregator_service import create_aggregator_service

        # Create with new pool
        aggregator = await create_aggregator_service()

        # Or with existing pool
        pool = await asyncpg.create_pool(...)
        aggregator = await create_aggregator_service(db_pool=pool)
        ```
    """
    from core.config import get_settings
    from services.tool_service.tool_repository import ToolRepository
    from services.vector_service.vector_repository import VectorRepository

    settings = get_settings()

    # Create database pool if not provided
    if db_pool is None:
        import asyncpg

        db_pool = await asyncpg.create_pool(
            host=settings.infrastructure.postgres_host,
            port=settings.infrastructure.postgres_port,
            user=settings.infrastructure.postgres_user,
            password=settings.infrastructure.postgres_password,
            database=settings.infrastructure.postgres_db,
            min_size=2,
            max_size=10,
        )
        logger.info("Created asyncpg pool for AggregatorService")

    # Create repositories
    tool_repo = ToolRepository()
    vector_repo = VectorRepository()

    # Create skill classifier if enabled
    skill_classifier = None
    if enable_classification:
        try:
            from services.skill_service import SkillService
            from services.skill_service.skill_repository import SkillRepository

            skill_repo = SkillRepository()
            skill_classifier = SkillService(repository=skill_repo, model_client=model_client)
            logger.info("SkillService initialized for automatic tool classification")
        except Exception as e:
            logger.warning(f"Failed to initialize SkillService: {e}. Classification disabled.")

    # Create model client if not provided
    if model_client is None:
        try:
            from core.clients.model_client import get_model_client

            model_client = await get_model_client()
        except Exception as e:
            logger.warning(f"Failed to get model client: {e}. Using mock embeddings.")

    # Create and return the aggregator service
    service = AggregatorService(
        tool_repository=tool_repo,
        vector_repository=vector_repo,
        skill_classifier=skill_classifier,
        model_client=model_client,
        db_pool=db_pool,
    )

    logger.info(
        f"AggregatorService created (classification={'enabled' if skill_classifier else 'disabled'})"
    )

    return service
