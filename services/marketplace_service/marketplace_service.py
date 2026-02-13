"""
Marketplace Service - Main service for MCP package management.

Coordinates package discovery, installation, and lifecycle management.
Transforms isA Context Portal into a unified skill marketplace.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from tests.contracts.marketplace import (
    RegistrySource,
    InstallStatus,
    UpdateChannel,
    PackageSpec,
    InstallResult,
    SearchResult,
    PackageRecordContract,
)

logger = logging.getLogger(__name__)


class MarketplaceService:
    """
    Main service for MCP package marketplace operations.

    Provides:
    - Package discovery and search across registries
    - One-command installation with auto-classification
    - Automatic skill assignment via hierarchical search
    - Update management and version tracking
    - Multi-tenant support (personal/team/org)

    The marketplace is the key differentiator for isA Context Portal:
    - Install any MCP with `isa install <package>`
    - All tools automatically classified into skill taxonomy
    - Unified search across all installed packages
    - Context that evolves with usage
    """

    # Default registries to sync
    DEFAULT_REGISTRIES = [
        {
            "source": RegistrySource.NPM,
            "url": "https://registry.npmjs.org",
            "search_url": "https://registry.npmjs.org/-/v1/search",
            "keywords": ["mcp-server", "model-context-protocol"],
        },
        {
            "source": RegistrySource.ISA_CLOUD,
            "url": "https://marketplace.isa.dev/api/v1",
            "search_url": "https://marketplace.isa.dev/api/v1/search",
        },
    ]

    def __init__(
        self,
        package_repository,
        registry_fetcher,
        package_resolver,
        install_manager,
        update_manager,
        aggregator_service=None,
        skill_service=None,
        search_service=None,
    ):
        """
        Initialize MarketplaceService with all dependencies.

        Args:
            package_repository: PackageRepository for database operations
            registry_fetcher: RegistryFetcher for npm/GitHub sync
            package_resolver: PackageResolver for version resolution
            install_manager: InstallManager for installation
            update_manager: UpdateManager for updates
            aggregator_service: AggregatorService for MCP server management
            skill_service: SkillService for tool classification
            search_service: HierarchicalSearchService for unified search
        """
        self._repo = package_repository
        self._fetcher = registry_fetcher
        self._resolver = package_resolver
        self._installer = install_manager
        self._updater = update_manager
        self._aggregator = aggregator_service
        self._skill_service = skill_service
        self._search_service = search_service

        # Background sync task
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_interval = 3600  # 1 hour

    # =========================================================================
    # Package Search & Discovery
    # =========================================================================

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        registry: Optional[RegistrySource] = None,
        verified_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search for packages across all registries.

        Args:
            query: Search query (name, description, tags)
            category: Filter by category (design, video, productivity, etc.)
            tags: Filter by tags
            registry: Filter by registry source
            verified_only: Only show verified packages
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Search results with packages and metadata

        Example:
            >>> results = await marketplace.search("video editing")
            >>> for pkg in results["packages"]:
            ...     print(f"{pkg['name']}: {pkg['description']}")
        """
        start_time = datetime.now(timezone.utc)

        # Search local cache first
        results = await self._repo.search_packages(
            query=query,
            category=category,
            tags=tags,
            registry=registry.value if registry else None,
            verified_only=verified_only,
            limit=limit,
            offset=offset,
        )

        # If few results, trigger background registry search
        if results["total"] < limit:
            asyncio.create_task(self._background_registry_search(query, category, tags))

        # Calculate search time
        search_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        results["search_time_ms"] = search_time_ms
        results["query"] = query

        return results

    async def get_package(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed package information.

        Args:
            name: Package name (e.g., "@pencil/ui-design" or "remotion")

        Returns:
            Package details with versions, tools, and installation status
        """
        package = await self._repo.get_package_by_name(name)

        if not package:
            # Try fetching from registries
            package = await self._fetcher.fetch_package(name)
            if package:
                await self._repo.upsert_package(package)

        if package:
            # Enrich with versions and installation status
            package["versions"] = await self._repo.get_package_versions(package["id"])
            package["installed"] = await self._repo.get_installation_status(package["id"])
            package["tools"] = package.get("declared_tools", [])

        return package

    async def list_categories(self) -> List[Dict[str, Any]]:
        """
        List available package categories with counts.

        Returns:
            List of categories with package counts
        """
        return await self._repo.list_categories()

    async def get_featured(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get featured/recommended packages.

        Returns:
            List of featured packages (curated + popular)
        """
        # Combine curated picks with popular packages
        curated = await self._repo.get_curated_packages(limit=5)
        popular = await self._repo.get_popular_packages(limit=limit - len(curated))

        # Deduplicate
        seen = {p["id"] for p in curated}
        for pkg in popular:
            if pkg["id"] not in seen:
                curated.append(pkg)
                seen.add(pkg["id"])

        return curated[:limit]

    # =========================================================================
    # Package Installation
    # =========================================================================

    async def install(
        self,
        spec: PackageSpec,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        auto_connect: bool = True,
    ) -> InstallResult:
        """
        Install a package from the marketplace.

        This is the main entry point for installation. It:
        1. Resolves the package and version from registries
        2. Creates the MCP server configuration
        3. Registers with the aggregator service
        4. Discovers and classifies tools into skill taxonomy
        5. Updates the unified search index

        Args:
            spec: Package specification (name, optional version, optional config)
            user_id: User ID for personal installation
            org_id: Organization ID for enterprise installation
            auto_connect: Whether to connect immediately

        Returns:
            InstallResult with installation details

        Example:
            >>> result = await marketplace.install(PackageSpec(name="pencil"))
            >>> if result.success:
            ...     print(f"Installed with {result.tools_discovered} tools")
            ...     print(f"Skills: {', '.join(result.skills_assigned)}")
        """
        logger.info(f"Installing package: {spec.name} (version={spec.version})")

        try:
            # Step 1: Resolve package and version
            resolved = await self._resolver.resolve(spec)
            if not resolved:
                return InstallResult(
                    success=False,
                    package_id="",
                    package_name=spec.name,
                    version="",
                    error=f"Package not found: {spec.name}",
                )

            package, version = resolved

            # Step 2: Check if already installed
            existing = await self._repo.get_installation(
                package_id=package["id"],
                user_id=user_id,
                org_id=org_id,
            )
            if existing and existing.get("status") == InstallStatus.INSTALLED.value:
                return InstallResult(
                    success=True,
                    package_id=package["id"],
                    package_name=package["name"],
                    version=existing.get("version", version["version"]),
                    server_id=existing.get("server_id"),
                    error="Package already installed",
                )

            # Step 3: Delegate to install manager
            result = await self._installer.install(
                package=package,
                version=version,
                user_config=spec.config or {},
                user_id=user_id,
                org_id=org_id,
                auto_connect=auto_connect,
            )

            # Step 4: Update download count
            if result.success:
                await self._repo.increment_download_count(package["id"])

            logger.info(
                f"{'Installed' if result.success else 'Failed to install'} "
                f"{spec.name}: {result.tools_discovered} tools, "
                f"{len(result.skills_assigned or [])} skills"
            )

            return result

        except Exception as e:
            logger.error(f"Installation failed for {spec.name}: {e}")
            return InstallResult(
                success=False,
                package_id="",
                package_name=spec.name,
                version=spec.version or "",
                error=str(e),
            )

    async def install_multiple(
        self,
        specs: List[PackageSpec],
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[InstallResult]:
        """
        Install multiple packages concurrently.

        Args:
            specs: List of package specifications
            user_id: User ID for personal installation
            org_id: Organization ID for enterprise installation

        Returns:
            List of installation results

        Example:
            >>> results = await marketplace.install_multiple([
            ...     PackageSpec(name="pencil"),
            ...     PackageSpec(name="remotion"),
            ...     PackageSpec(name="notion"),
            ... ])
            >>> for r in results:
            ...     print(f"{r.package_name}: {'OK' if r.success else r.error}")
        """
        tasks = [self.install(spec, user_id=user_id, org_id=org_id) for spec in specs]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(
                    InstallResult(
                        success=False,
                        package_id="",
                        package_name=specs[i].name,
                        version="",
                        error=str(result),
                    )
                )
            else:
                processed.append(result)

        return processed

    async def uninstall(
        self,
        package_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """
        Uninstall a package.

        Args:
            package_name: Package name to uninstall
            user_id: User ID
            org_id: Organization ID

        Returns:
            True if uninstalled successfully

        Raises:
            ValueError: If package not found or not installed
        """
        package = await self._repo.get_package_by_name(package_name)
        if not package:
            raise ValueError(f"Package not found: {package_name}")

        installation = await self._repo.get_installation(
            package_id=package["id"],
            user_id=user_id,
            org_id=org_id,
        )
        if not installation:
            raise ValueError(f"Package not installed: {package_name}")

        return await self._installer.uninstall(installation)

    # =========================================================================
    # Installed Packages Management
    # =========================================================================

    async def list_installed(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        include_tools: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List installed packages for a user/org.

        Args:
            user_id: User ID
            org_id: Organization ID
            include_tools: Include discovered tools in response

        Returns:
            List of installed packages with status
        """
        installations = await self._repo.list_installations(
            user_id=user_id,
            org_id=org_id,
        )

        if include_tools:
            for inst in installations:
                inst["tools"] = await self._repo.get_tool_mappings(inst["id"])

        return installations

    async def get_installation(
        self,
        package_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get installation details for a specific package."""
        package = await self._repo.get_package_by_name(package_name)
        if not package:
            return None

        return await self._repo.get_installation(
            package_id=package["id"],
            user_id=user_id,
            org_id=org_id,
        )

    async def enable_package(
        self,
        package_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """Enable a disabled package."""
        installation = await self.get_installation(package_name, user_id, org_id)
        if not installation:
            raise ValueError(f"Package not installed: {package_name}")

        # Reconnect to aggregator
        if installation.get("server_id") and self._aggregator:
            await self._aggregator.connect_server(installation["server_id"])

        await self._repo.update_installation_status(
            installation["id"],
            InstallStatus.INSTALLED,
        )
        return True

    async def disable_package(
        self,
        package_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """Disable a package without uninstalling."""
        installation = await self.get_installation(package_name, user_id, org_id)
        if not installation:
            raise ValueError(f"Package not installed: {package_name}")

        # Disconnect from aggregator (but don't remove)
        if installation.get("server_id") and self._aggregator:
            await self._aggregator.disconnect_server(installation["server_id"])

        await self._repo.update_installation_status(
            installation["id"],
            InstallStatus.DISABLED,
        )
        return True

    # =========================================================================
    # Update Management
    # =========================================================================

    async def check_updates(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check for available updates for installed packages.

        Returns:
            List of packages with available updates
        """
        return await self._updater.check_updates(user_id=user_id, org_id=org_id)

    async def update_package(
        self,
        package_name: str,
        target_version: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> InstallResult:
        """
        Update a package to a new version.

        Args:
            package_name: Package to update
            target_version: Specific version (None = latest)
            user_id: User ID
            org_id: Organization ID

        Returns:
            Installation result for the update
        """
        return await self._updater.update_package(
            package_name=package_name,
            target_version=target_version,
            user_id=user_id,
            org_id=org_id,
        )

    async def update_all(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[InstallResult]:
        """Update all packages with available updates."""
        return await self._updater.update_all(user_id=user_id, org_id=org_id)

    # =========================================================================
    # Registry Synchronization
    # =========================================================================

    async def sync_registries(
        self,
        registries: Optional[List[RegistrySource]] = None,
        force_full: bool = False,
    ) -> Dict[str, Any]:
        """
        Synchronize with package registries.

        Args:
            registries: Specific registries to sync (None = all)
            force_full: Force full sync instead of incremental

        Returns:
            Sync results with counts and errors
        """
        return await self._fetcher.sync_registries(
            registries=registries,
            force_full=force_full,
        )

    async def start_background_sync(self) -> asyncio.Task:
        """Start background registry synchronization."""

        async def _sync_loop():
            while True:
                try:
                    await self.sync_registries()
                except Exception as e:
                    logger.error(f"Background sync error: {e}")
                await asyncio.sleep(self._sync_interval)

        self._sync_task = asyncio.create_task(_sync_loop())
        logger.info("Started background registry sync")
        return self._sync_task

    async def stop_background_sync(self):
        """Stop background registry synchronization."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
            logger.info("Stopped background registry sync")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def _background_registry_search(
        self,
        query: str,
        category: Optional[str],
        tags: Optional[List[str]],
    ) -> None:
        """Perform background search on registries to populate cache."""
        try:
            packages = await self._fetcher.search_registries(
                query=query,
                category=category,
                tags=tags,
            )
            for pkg in packages:
                await self._repo.upsert_package(pkg)
        except Exception as e:
            logger.debug(f"Background registry search failed: {e}")

    async def get_state(self) -> Dict[str, Any]:
        """
        Get current marketplace state.

        Returns:
            State with package and installation counts
        """
        return {
            "total_packages": await self._repo.count_packages(),
            "installed_packages": await self._repo.count_installations(),
            "registries": [r["source"].value for r in self.DEFAULT_REGISTRIES],
            "sync_enabled": self._sync_task is not None,
        }
