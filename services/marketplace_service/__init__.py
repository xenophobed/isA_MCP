"""
Marketplace Service - MCP Package Marketplace for isA Context Portal.

Provides:
- MarketplaceService: Main service for package discovery and installation
- RegistryFetcher: Fetches packages from npm, GitHub, and other registries
- PackageResolver: Resolves package versions and dependencies
- InstallManager: Handles package installation with aggregator integration
- UpdateManager: Manages package updates
- PackageRepository: Data access for marketplace tables
- create_marketplace_service: Factory function with all dependencies wired

Example:
    >>> from services.marketplace_service import create_marketplace_service, PackageSpec
    >>> marketplace = await create_marketplace_service()
    >>> result = await marketplace.install(PackageSpec(name="pencil"))
    >>> print(f"Installed {result.package_name} with {result.tools_discovered} tools")
"""

import logging
from typing import Optional  # noqa: F401

from .marketplace_service import MarketplaceService
from .package_repository import PackageRepository
from .registry_fetcher import RegistryFetcher
from .package_resolver import PackageResolver
from .install_manager import InstallManager
from .update_manager import UpdateManager

# Re-export domain types for convenience
from .domain import (
    RegistrySource,
    InstallStatus,
    UpdateChannel,
    PackageSpec,
    InstallResult,
    SearchResult,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Service classes
    "MarketplaceService",
    "PackageRepository",
    "RegistryFetcher",
    "PackageResolver",
    "InstallManager",
    "UpdateManager",
    # Factory function
    "create_marketplace_service",
    # Contracts
    "RegistrySource",
    "InstallStatus",
    "UpdateChannel",
    "PackageSpec",
    "InstallResult",
    "SearchResult",
]


async def create_marketplace_service(
    db_pool=None,
    aggregator_service=None,
    skill_service=None,
    search_service=None,
    model_client=None,
    tool_repository=None,
    vector_repository=None,
) -> MarketplaceService:
    """
    Factory function to create a fully configured MarketplaceService.

    Creates all required dependencies:
    - PackageRepository for PostgreSQL storage
    - RegistryFetcher for npm/GitHub sync
    - PackageResolver for version resolution
    - InstallManager for installation
    - UpdateManager for updates
    - AggregatorService for MCP server management
    - SkillService for tool classification
    - ToolRepository for unified tool storage (mcp.tools)
    - VectorRepository for semantic search embeddings

    Args:
        db_pool: Optional asyncpg connection pool (creates one if not provided)
        aggregator_service: Optional AggregatorService instance
        skill_service: Optional SkillService instance
        search_service: Optional HierarchicalSearchService instance
        model_client: Optional model client for embeddings
        tool_repository: Optional ToolRepository for unified tool storage
        vector_repository: Optional VectorRepository for embeddings

    Returns:
        Configured MarketplaceService instance

    Example:
        >>> import asyncpg
        >>> from services.marketplace_service import create_marketplace_service
        >>>
        >>> # Create with new pool
        >>> marketplace = await create_marketplace_service()
        >>>
        >>> # Or with existing pool
        >>> pool = await asyncpg.create_pool(...)
        >>> marketplace = await create_marketplace_service(db_pool=pool)
    """
    from core.config import get_settings

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
        logger.info("Created asyncpg pool for MarketplaceService")

    # Create repository
    package_repo = PackageRepository(db_pool=db_pool)

    # Create registry fetcher
    registry_fetcher = RegistryFetcher(repository=package_repo)

    # Create package resolver
    package_resolver = PackageResolver(
        repository=package_repo,
        fetcher=registry_fetcher,
    )

    # Get or create aggregator service
    if aggregator_service is None:
        try:
            from services.aggregator_service import create_aggregator_service

            aggregator_service = await create_aggregator_service(
                db_pool=db_pool,
                model_client=model_client,
            )
            logger.info("Created AggregatorService for MarketplaceService")
        except Exception as e:
            logger.warning(f"Failed to create AggregatorService: {e}")
            aggregator_service = None

    # Get or create skill service
    if skill_service is None:
        try:
            from services.skill_service import SkillService
            from services.skill_service.skill_repository import SkillRepository

            skill_repo = SkillRepository(db_pool=db_pool)
            skill_service = SkillService(
                repository=skill_repo,
                model_client=model_client,
            )
            logger.info("Created SkillService for MarketplaceService")
        except Exception as e:
            logger.warning(f"Failed to create SkillService: {e}")
            skill_service = None

    # Get or create search service
    if search_service is None:
        try:
            from services.search_service.hierarchical_search_service import (
                HierarchicalSearchService,
            )

            search_service = HierarchicalSearchService(
                model_client=model_client,
            )
            logger.info("Created HierarchicalSearchService for MarketplaceService")
        except Exception as e:
            logger.warning(f"Failed to create HierarchicalSearchService: {e}")
            search_service = None

    # Get or create tool repository for unified tool storage
    if tool_repository is None:
        try:
            from services.tool_service.tool_repository import ToolRepository

            tool_repository = ToolRepository()
            logger.info("Created ToolRepository for MarketplaceService")
        except Exception as e:
            logger.warning(f"Failed to create ToolRepository: {e}")
            tool_repository = None

    # Get or create vector repository for embeddings
    if vector_repository is None:
        try:
            from services.vector_service.vector_repository import VectorRepository

            vector_repository = VectorRepository()
            logger.info("Created VectorRepository for MarketplaceService")
        except Exception as e:
            logger.warning(f"Failed to create VectorRepository: {e}")
            vector_repository = None

    # Create install manager with all integrations
    install_manager = InstallManager(
        repository=package_repo,
        aggregator=aggregator_service,
        skill_service=skill_service,
        tool_repository=tool_repository,
        vector_repository=vector_repository,
    )

    # Create update manager
    update_manager = UpdateManager(
        repository=package_repo,
        resolver=package_resolver,
        installer=install_manager,
    )

    # Create and return marketplace service
    service = MarketplaceService(
        package_repository=package_repo,
        registry_fetcher=registry_fetcher,
        package_resolver=package_resolver,
        install_manager=install_manager,
        update_manager=update_manager,
        aggregator_service=aggregator_service,
        skill_service=skill_service,
        search_service=search_service,
    )

    logger.info(
        f"MarketplaceService created ("
        f"aggregator={'enabled' if aggregator_service else 'disabled'}, "
        f"skills={'enabled' if skill_service else 'disabled'}, "
        f"search={'enabled' if search_service else 'disabled'})"
    )

    return service
