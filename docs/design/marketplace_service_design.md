# Marketplace Service Technical Design

**Version:** 1.0.0
**Status:** Draft
**Author:** isA Team
**Date:** 2026-01-24

---

## 1. Executive Summary

The Marketplace Service enables users to discover, install, and manage MCP packages from public registries and private sources. It transforms isA Context Portal from a standalone MCP server into a **unified skill marketplace** that aggregates capabilities from the entire MCP ecosystem.

### Key Value Propositions

| Capability | Without Marketplace | With Marketplace |
|------------|---------------------|------------------|
| Installing MCPs | Manual JSON config editing | `isa install pencil` |
| Discovery | Browse GitHub manually | Semantic search across registries |
| Classification | N/A | Auto-classify into skill taxonomy |
| Updates | Manual version tracking | Automatic update notifications |
| Unified Search | Separate per-MCP | One search across all installed |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          isA Context Portal                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Marketplace Service (NEW)                          │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────────┐  │ │
│  │  │   Registry   │ │   Package    │ │  Install     │ │    Update     │  │ │
│  │  │   Fetcher    │ │   Resolver   │ │  Manager     │ │    Manager    │  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Aggregator Service (EXISTING)                      │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────────┐  │ │
│  │  │   Server     │ │   Session    │ │    Tool      │ │   Request     │  │ │
│  │  │   Registry   │ │   Manager    │ │  Aggregator  │ │   Router      │  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Skill Service (EXISTING)                          │ │
│  │         Auto-classification │ Hierarchical Search │ Embeddings         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          External Registries                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────────────┐   │
│  │   npm (MCP   │ │  GitHub      │ │  isA Cloud   │ │  Private          │   │
│  │   packages)  │ │  Releases    │ │  Registry    │ │  Enterprise       │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 Entity Relationship Diagram

```
┌─────────────────────────┐       ┌─────────────────────────┐
│   marketplace_packages  │       │  package_versions       │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │───┐   │ id (PK)                 │
│ name (unique)           │   │   │ package_id (FK)         │──┐
│ display_name            │   │   │ version                 │  │
│ description             │   │   │ mcp_config (JSONB)      │  │
│ author                  │   │   │ changelog               │  │
│ homepage_url            │   │   │ published_at            │  │
│ repository_url          │   │   │ deprecated              │  │
│ license                 │   │   └─────────────────────────┘  │
│ category                │   │                                │
│ tags[]                  │   │                                │
│ registry_source         │   │   ┌─────────────────────────┐  │
│ download_count          │   └──▶│  installed_packages     │  │
│ star_count              │       ├─────────────────────────┤  │
│ verified                │       │ id (PK)                 │  │
│ created_at              │       │ package_id (FK)         │──┘
│ updated_at              │       │ version_id (FK)         │
└─────────────────────────┘       │ server_id (FK)          │──▶ external_servers
                                  │ installed_at            │
                                  │ auto_update             │
                                  │ user_id (for personal)  │
                                  │ org_id (for enterprise) │
                                  │ status                  │
                                  │ last_sync_at            │
                                  └─────────────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────┐
                                  │  package_tool_mappings  │
                                  ├─────────────────────────┤
                                  │ installed_pkg_id (FK)   │
                                  │ tool_id (FK)            │──▶ mcp.tools
                                  │ original_name           │
                                  │ namespaced_name         │
                                  │ skill_ids[]             │──▶ skill_categories
                                  └─────────────────────────┘
```

### 3.2 Core Tables

#### `mcp.marketplace_packages` - Package Catalog

```sql
-- Registry of available MCP packages from all sources
CREATE TABLE mcp.marketplace_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Package identification (npm-style naming)
    name VARCHAR(255) NOT NULL UNIQUE,  -- e.g., "@pencil/ui-design"
    display_name VARCHAR(255) NOT NULL, -- e.g., "Pencil UI Design"

    -- Metadata
    description TEXT,
    author VARCHAR(255),
    author_email VARCHAR(255),
    homepage_url TEXT,
    repository_url TEXT,
    documentation_url TEXT,
    license VARCHAR(50),

    -- Categorization
    category VARCHAR(100),  -- "design", "video", "productivity", etc.
    tags TEXT[] DEFAULT '{}',

    -- Registry source
    registry_source VARCHAR(50) NOT NULL,  -- "npm", "github", "isa-cloud", "private"
    registry_url TEXT,  -- Full URL to package in registry

    -- Popularity metrics
    download_count INTEGER DEFAULT 0,
    weekly_downloads INTEGER DEFAULT 0,
    star_count INTEGER DEFAULT 0,

    -- Trust indicators
    verified BOOLEAN DEFAULT FALSE,  -- isA verified publisher
    official BOOLEAN DEFAULT FALSE,  -- Official from service provider
    security_score INTEGER,  -- 0-100 security audit score

    -- Latest version info (denormalized for performance)
    latest_version VARCHAR(50),
    latest_version_id UUID,

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT pkg_name_format CHECK (name ~ '^(@[a-z0-9-]+/)?[a-z0-9-]+$'),
    CONSTRAINT pkg_registry_check CHECK (registry_source IN ('npm', 'github', 'isa-cloud', 'private', 'local'))
);
```

#### `mcp.package_versions` - Version History

```sql
-- Version history for each package
CREATE TABLE mcp.package_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id) ON DELETE CASCADE,

    -- Version info (semver)
    version VARCHAR(50) NOT NULL,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_patch INTEGER NOT NULL,
    prerelease VARCHAR(50),

    -- MCP Configuration (the actual MCP server config)
    mcp_config JSONB NOT NULL,
    -- Example mcp_config:
    -- {
    --   "transport": "stdio",
    --   "command": "npx",
    --   "args": ["-y", "@anthropic/pencil-mcp"],
    --   "env": {"PENCIL_API_KEY": "{{PENCIL_API_KEY}}"}
    -- }

    -- Tool metadata (discovered or declared)
    declared_tools JSONB DEFAULT '[]',  -- Tools declared in package manifest
    tool_count INTEGER DEFAULT 0,

    -- Requirements
    min_mcp_version VARCHAR(20),
    required_env_vars TEXT[] DEFAULT '{}',
    dependencies JSONB DEFAULT '{}',

    -- Release info
    changelog TEXT,
    release_notes_url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    published_by VARCHAR(255),

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    yanked BOOLEAN DEFAULT FALSE,  -- Security issue, don't allow install

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE (package_id, version)
);

-- Index for version lookup
CREATE INDEX idx_pkg_versions_package ON mcp.package_versions(package_id, version_major DESC, version_minor DESC, version_patch DESC);
```

#### `mcp.installed_packages` - User Installations

```sql
-- Tracks which packages are installed for which user/org
CREATE TABLE mcp.installed_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What's installed
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id),
    version_id UUID NOT NULL REFERENCES mcp.package_versions(id),

    -- Links to aggregator
    server_id UUID REFERENCES mcp.external_servers(id) ON DELETE SET NULL,

    -- Ownership (multi-tenant support)
    user_id UUID,      -- Personal installation
    org_id UUID,       -- Enterprise organization
    team_id UUID,      -- Enterprise team (optional)

    -- Installation configuration
    install_config JSONB DEFAULT '{}',  -- User-provided config (API keys, etc.)
    env_overrides JSONB DEFAULT '{}',   -- Environment variable overrides

    -- Update policy
    auto_update BOOLEAN DEFAULT TRUE,
    update_channel VARCHAR(20) DEFAULT 'stable',  -- "stable", "beta", "latest"
    pinned_version BOOLEAN DEFAULT FALSE,

    -- Status
    status VARCHAR(20) DEFAULT 'installed',  -- "installed", "disabled", "error", "updating"
    error_message TEXT,

    -- Usage tracking
    last_used_at TIMESTAMPTZ,
    use_count INTEGER DEFAULT 0,

    -- Timestamps
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT installed_pkg_owner CHECK (
        (user_id IS NOT NULL AND org_id IS NULL) OR
        (user_id IS NULL AND org_id IS NOT NULL) OR
        (user_id IS NULL AND org_id IS NULL)  -- System-wide
    ),
    CONSTRAINT installed_pkg_status CHECK (status IN ('installed', 'disabled', 'error', 'updating', 'uninstalling'))
);

-- Unique constraint: one installation per package per user/org
CREATE UNIQUE INDEX idx_installed_pkg_user ON mcp.installed_packages(package_id, user_id)
    WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX idx_installed_pkg_org ON mcp.installed_packages(package_id, org_id)
    WHERE org_id IS NOT NULL AND team_id IS NULL;
CREATE UNIQUE INDEX idx_installed_pkg_team ON mcp.installed_packages(package_id, org_id, team_id)
    WHERE org_id IS NOT NULL AND team_id IS NOT NULL;
```

#### `mcp.package_tool_mappings` - Tool Discovery Results

```sql
-- Maps discovered tools back to their source package
CREATE TABLE mcp.package_tool_mappings (
    installed_package_id UUID NOT NULL REFERENCES mcp.installed_packages(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES mcp.tools(id) ON DELETE CASCADE,

    -- Name mapping
    original_name VARCHAR(255) NOT NULL,      -- Tool name from MCP server
    namespaced_name VARCHAR(255) NOT NULL,    -- Prefixed name: "pencil:create_design"

    -- Skill classification results
    skill_ids TEXT[] DEFAULT '{}',            -- Assigned skill IDs
    primary_skill_id VARCHAR(100),

    -- Timestamps
    discovered_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (installed_package_id, tool_id)
);
```

#### `mcp.registry_sync_log` - Sync History

```sql
-- Tracks registry synchronization history
CREATE TABLE mcp.registry_sync_log (
    id SERIAL PRIMARY KEY,

    registry_source VARCHAR(50) NOT NULL,
    sync_type VARCHAR(20) NOT NULL,  -- "full", "incremental", "single_package"

    -- Results
    packages_discovered INTEGER DEFAULT 0,
    packages_updated INTEGER DEFAULT 0,
    packages_deprecated INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',

    -- Timing
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Status
    status VARCHAR(20) DEFAULT 'running',  -- "running", "completed", "failed"
    error_message TEXT
);
```

---

## 4. Service Architecture

### 4.1 Component Overview

```python
# services/marketplace_service/__init__.py

from .marketplace_service import MarketplaceService
from .registry_fetcher import RegistryFetcher
from .package_resolver import PackageResolver
from .install_manager import InstallManager
from .update_manager import UpdateManager
from .package_repository import PackageRepository

__all__ = [
    'MarketplaceService',
    'RegistryFetcher',
    'PackageResolver',
    'InstallManager',
    'UpdateManager',
    'PackageRepository',
    'create_marketplace_service',
]
```

### 4.2 MarketplaceService - Main Entry Point

```python
"""
Marketplace Service - Main service for MCP package management.

Coordinates package discovery, installation, and lifecycle management.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RegistrySource(str, Enum):
    """Supported package registry sources."""
    NPM = "npm"
    GITHUB = "github"
    ISA_CLOUD = "isa-cloud"
    PRIVATE = "private"
    LOCAL = "local"


class InstallStatus(str, Enum):
    """Package installation status."""
    INSTALLED = "installed"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"
    UNINSTALLING = "uninstalling"


class UpdateChannel(str, Enum):
    """Update channel for packages."""
    STABLE = "stable"
    BETA = "beta"
    LATEST = "latest"


@dataclass
class PackageSpec:
    """Package specification for installation."""
    name: str
    version: Optional[str] = None  # None = latest
    registry: Optional[RegistrySource] = None
    config: Optional[Dict[str, Any]] = None


@dataclass
class InstallResult:
    """Result of package installation."""
    success: bool
    package_id: str
    package_name: str
    version: str
    server_id: Optional[str] = None
    tools_discovered: int = 0
    skills_assigned: List[str] = None
    error: Optional[str] = None


class MarketplaceService:
    """
    Main service for MCP package marketplace operations.

    Provides:
    - Package discovery and search
    - One-command installation
    - Automatic skill classification
    - Update management
    - Multi-tenant support (personal/team/org)
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
        aggregator_service,
        skill_service,
        search_service,
    ):
        """Initialize MarketplaceService with all dependencies."""
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
    # Package Search & Discovery (Primary User Journey)
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
            category: Filter by category
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
        # Search local cache first
        results = await self._repo.search_packages(
            query=query,
            category=category,
            tags=tags,
            registry=registry,
            verified_only=verified_only,
            limit=limit,
            offset=offset,
        )

        # If few results, trigger background registry search
        if results["total"] < limit:
            asyncio.create_task(
                self._background_registry_search(query, category, tags)
            )

        return results

    async def get_package(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed package information.

        Args:
            name: Package name (e.g., "@pencil/ui-design")

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
    # Package Installation (Core Feature)
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
        1. Resolves the package and version
        2. Creates the MCP server configuration
        3. Registers with the aggregator service
        4. Discovers and classifies tools
        5. Updates the search index

        Args:
            spec: Package specification (name, optional version, optional config)
            user_id: User ID for personal installation
            org_id: Organization ID for enterprise installation
            auto_connect: Whether to connect immediately

        Returns:
            InstallResult with details of the installation

        Example:
            >>> result = await marketplace.install(PackageSpec(name="pencil"))
            >>> if result.success:
            ...     print(f"Installed {result.package_name} with {result.tools_discovered} tools")
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
            if existing and existing["status"] == InstallStatus.INSTALLED:
                return InstallResult(
                    success=True,
                    package_id=package["id"],
                    package_name=package["name"],
                    version=existing["version"],
                    server_id=existing.get("server_id"),
                    error="Package already installed",
                )

            # Step 3: Prepare MCP configuration
            mcp_config = await self._installer.prepare_config(
                version["mcp_config"],
                spec.config or {},
            )

            # Step 4: Register with aggregator service
            server_config = {
                "name": self._get_server_name(package["name"]),
                "description": package["description"],
                "transport_type": mcp_config["transport"],
                "connection_config": mcp_config,
                "auto_connect": auto_connect,
            }

            server = await self._aggregator.register_server(server_config)

            # Step 5: Create installation record
            installation = await self._repo.create_installation(
                package_id=package["id"],
                version_id=version["id"],
                server_id=server["id"],
                user_id=user_id,
                org_id=org_id,
                install_config=spec.config or {},
            )

            # Step 6: Discover tools (happens via aggregator connect)
            tools_discovered = 0
            skills_assigned = []

            if auto_connect and server["status"] == "connected":
                # Get discovered tools
                tools = await self._aggregator.discover_tools(server["id"])
                tools_discovered = len(tools)

                # Map tools to package
                await self._repo.create_tool_mappings(
                    installed_package_id=installation["id"],
                    tools=tools,
                    package_name=package["name"],
                )

                # Get assigned skills
                skill_ids = set()
                for tool in tools:
                    if tool.get("skill_ids"):
                        skill_ids.update(tool["skill_ids"])
                skills_assigned = list(skill_ids)

            # Step 7: Update package download count
            await self._repo.increment_download_count(package["id"])

            logger.info(
                f"Installed {package['name']}@{version['version']}: "
                f"{tools_discovered} tools, {len(skills_assigned)} skills"
            )

            return InstallResult(
                success=True,
                package_id=package["id"],
                package_name=package["name"],
                version=version["version"],
                server_id=server["id"],
                tools_discovered=tools_discovered,
                skills_assigned=skills_assigned,
            )

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
        """
        tasks = [
            self.install(spec, user_id=user_id, org_id=org_id)
            for spec in specs
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

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
            user_id: User ID for personal installation
            org_id: Organization ID for enterprise installation

        Returns:
            True if uninstalled successfully
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

        # Update status to uninstalling
        await self._repo.update_installation_status(
            installation["id"],
            InstallStatus.UNINSTALLING,
        )

        try:
            # Remove from aggregator
            if installation.get("server_id"):
                await self._aggregator.remove_server(installation["server_id"])

            # Delete tool mappings
            await self._repo.delete_tool_mappings(installation["id"])

            # Delete installation record
            await self._repo.delete_installation(installation["id"])

            logger.info(f"Uninstalled package: {package_name}")
            return True

        except Exception as e:
            # Revert status on error
            await self._repo.update_installation_status(
                installation["id"],
                InstallStatus.ERROR,
                error_message=str(e),
            )
            raise

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
            include_tools: Include discovered tools

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
        """
        Get installation details for a specific package.
        """
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
        if installation.get("server_id"):
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
        if installation.get("server_id"):
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
            Installation result
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

    def _get_server_name(self, package_name: str) -> str:
        """Convert package name to valid server name."""
        # "@pencil/ui-design" -> "pencil-ui-design"
        name = package_name.lstrip("@").replace("/", "-").replace("_", "-")
        return name.lower()

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


# ═══════════════════════════════════════════════════════════════════════════════
# Factory Function
# ═══════════════════════════════════════════════════════════════════════════════

async def create_marketplace_service(
    db_pool=None,
    aggregator_service=None,
    skill_service=None,
    search_service=None,
) -> MarketplaceService:
    """
    Factory function to create a fully configured MarketplaceService.

    Args:
        db_pool: Optional asyncpg connection pool
        aggregator_service: Optional AggregatorService instance
        skill_service: Optional SkillService instance
        search_service: Optional HierarchicalSearchService instance

    Returns:
        Configured MarketplaceService instance
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

    # Create dependencies
    from .package_repository import PackageRepository
    from .registry_fetcher import RegistryFetcher
    from .package_resolver import PackageResolver
    from .install_manager import InstallManager
    from .update_manager import UpdateManager

    package_repo = PackageRepository(db_pool=db_pool)
    registry_fetcher = RegistryFetcher(repository=package_repo)
    package_resolver = PackageResolver(
        repository=package_repo,
        fetcher=registry_fetcher,
    )

    # Get or create aggregator service
    if aggregator_service is None:
        from services.aggregator_service import create_aggregator_service
        aggregator_service = await create_aggregator_service(db_pool=db_pool)

    install_manager = InstallManager(
        repository=package_repo,
        aggregator=aggregator_service,
    )

    update_manager = UpdateManager(
        repository=package_repo,
        resolver=package_resolver,
        installer=install_manager,
    )

    return MarketplaceService(
        package_repository=package_repo,
        registry_fetcher=registry_fetcher,
        package_resolver=package_resolver,
        install_manager=install_manager,
        update_manager=update_manager,
        aggregator_service=aggregator_service,
        skill_service=skill_service,
        search_service=search_service,
    )
```

---

## 5. Registry Fetcher

### 5.1 Multi-Registry Support

```python
"""
Registry Fetcher - Fetches packages from multiple registry sources.

Supports:
- npm registry (MCP packages)
- GitHub releases
- isA Cloud registry
- Private enterprise registries
"""
import aiohttp
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class RegistryFetcher:
    """
    Fetches and normalizes package data from multiple registries.
    """

    # npm search for MCP packages
    NPM_SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
    NPM_PACKAGE_URL = "https://registry.npmjs.org"

    # isA Cloud (future)
    ISA_REGISTRY_URL = "https://marketplace.isa.dev/api/v1"

    # GitHub API
    GITHUB_API_URL = "https://api.github.com"

    def __init__(
        self,
        repository,
        http_timeout: int = 30,
        cache_ttl: int = 3600,
    ):
        self._repo = repository
        self._timeout = aiohttp.ClientTimeout(total=http_timeout)
        self._cache_ttl = cache_ttl
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # =========================================================================
    # npm Registry
    # =========================================================================

    async def search_npm(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search npm registry for MCP packages.

        Uses keywords: mcp-server, model-context-protocol, anthropic-mcp
        """
        session = await self._get_session()

        # Search with MCP-related keywords
        search_terms = f"{query} keywords:mcp-server"

        params = {
            "text": search_terms,
            "size": limit,
        }

        try:
            async with session.get(self.NPM_SEARCH_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"npm search failed: {resp.status}")
                    return []

                data = await resp.json()

                packages = []
                for obj in data.get("objects", []):
                    pkg = self._normalize_npm_package(obj["package"])
                    if pkg:
                        packages.append(pkg)

                return packages

        except Exception as e:
            logger.error(f"npm search error: {e}")
            return []

    async def fetch_npm_package(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed package info from npm."""
        session = await self._get_session()

        url = f"{self.NPM_PACKAGE_URL}/{name}"

        try:
            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    logger.warning(f"npm fetch failed for {name}: {resp.status}")
                    return None

                data = await resp.json()
                return self._normalize_npm_full_package(data)

        except Exception as e:
            logger.error(f"npm fetch error for {name}: {e}")
            return None

    def _normalize_npm_package(self, pkg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize npm package to our format."""
        # Filter: must have MCP-related keywords
        keywords = pkg.get("keywords", []) or []
        mcp_keywords = {"mcp-server", "model-context-protocol", "anthropic-mcp", "mcp"}

        if not any(kw.lower() in mcp_keywords for kw in keywords):
            return None

        return {
            "name": pkg["name"],
            "display_name": self._name_to_display(pkg["name"]),
            "description": pkg.get("description", ""),
            "author": pkg.get("author", {}).get("name") if isinstance(pkg.get("author"), dict) else pkg.get("author"),
            "homepage_url": pkg.get("homepage"),
            "repository_url": self._extract_repo_url(pkg.get("repository")),
            "license": pkg.get("license"),
            "tags": [kw for kw in keywords if kw.lower() not in mcp_keywords],
            "registry_source": "npm",
            "registry_url": f"https://www.npmjs.com/package/{pkg['name']}",
            "latest_version": pkg.get("version"),
        }

    def _normalize_npm_full_package(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize full npm package with versions."""
        latest_version = data.get("dist-tags", {}).get("latest")
        latest_data = data.get("versions", {}).get(latest_version, {})

        # Extract MCP config from package.json
        mcp_config = self._extract_mcp_config(latest_data)

        versions = []
        for version, version_data in data.get("versions", {}).items():
            versions.append({
                "version": version,
                "mcp_config": self._extract_mcp_config(version_data),
                "published_at": data.get("time", {}).get(version),
            })

        package = self._normalize_npm_package(latest_data)
        if package:
            package["versions"] = versions
            package["download_count"] = 0  # Would need separate API call

        return package

    def _extract_mcp_config(self, pkg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract MCP server configuration from npm package.

        Looks for:
        1. mcp field in package.json
        2. bin field for CLI commands
        3. Defaults to npx execution
        """
        name = pkg_data.get("name", "")

        # Check for explicit MCP config
        if "mcp" in pkg_data:
            return pkg_data["mcp"]

        # Check for bin entry
        if "bin" in pkg_data:
            bin_name = list(pkg_data["bin"].keys())[0] if pkg_data["bin"] else name
            return {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", name],
            }

        # Default: assume npx runnable
        return {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", name],
        }

    # =========================================================================
    # GitHub Registry
    # =========================================================================

    async def search_github(
        self,
        query: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search GitHub for MCP server repositories."""
        session = await self._get_session()

        # Search for MCP-related repos
        search_query = f"{query} topic:mcp-server OR topic:model-context-protocol"

        headers = {"Accept": "application/vnd.github.v3+json"}
        params = {
            "q": search_query,
            "sort": "stars",
            "per_page": limit,
        }

        try:
            async with session.get(
                f"{self.GITHUB_API_URL}/search/repositories",
                headers=headers,
                params=params,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"GitHub search failed: {resp.status}")
                    return []

                data = await resp.json()

                packages = []
                for repo in data.get("items", []):
                    pkg = self._normalize_github_repo(repo)
                    if pkg:
                        packages.append(pkg)

                return packages

        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []

    def _normalize_github_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize GitHub repo to package format."""
        return {
            "name": f"@github/{repo['full_name'].replace('/', '-')}",
            "display_name": repo["name"],
            "description": repo.get("description", ""),
            "author": repo["owner"]["login"],
            "homepage_url": repo.get("homepage") or repo["html_url"],
            "repository_url": repo["html_url"],
            "license": repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
            "tags": repo.get("topics", []),
            "registry_source": "github",
            "registry_url": repo["html_url"],
            "star_count": repo["stargazers_count"],
        }

    # =========================================================================
    # Registry Sync
    # =========================================================================

    async def sync_registries(
        self,
        registries: Optional[List[str]] = None,
        force_full: bool = False,
    ) -> Dict[str, Any]:
        """
        Synchronize with package registries.

        Returns:
            Sync results with counts
        """
        start_time = datetime.now(timezone.utc)
        results = {
            "packages_discovered": 0,
            "packages_updated": 0,
            "errors": [],
        }

        registries = registries or ["npm", "github"]

        # Sync npm
        if "npm" in registries:
            try:
                # Search for popular MCP packages
                npm_packages = await self.search_npm("mcp server", limit=100)
                for pkg in npm_packages:
                    existing = await self._repo.get_package_by_name(pkg["name"])
                    if existing:
                        await self._repo.update_package(existing["id"], pkg)
                        results["packages_updated"] += 1
                    else:
                        await self._repo.create_package(pkg)
                        results["packages_discovered"] += 1
            except Exception as e:
                results["errors"].append({"registry": "npm", "error": str(e)})

        # Sync GitHub
        if "github" in registries:
            try:
                gh_packages = await self.search_github("mcp server", limit=50)
                for pkg in gh_packages:
                    existing = await self._repo.get_package_by_name(pkg["name"])
                    if existing:
                        await self._repo.update_package(existing["id"], pkg)
                        results["packages_updated"] += 1
                    else:
                        await self._repo.create_package(pkg)
                        results["packages_discovered"] += 1
            except Exception as e:
                results["errors"].append({"registry": "github", "error": str(e)})

        results["duration_ms"] = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        return results

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _name_to_display(self, name: str) -> str:
        """Convert package name to display name."""
        # "@pencil/ui-design" -> "Pencil UI Design"
        display = name.lstrip("@").replace("/", " ").replace("-", " ").replace("_", " ")
        return " ".join(word.capitalize() for word in display.split())

    def _extract_repo_url(self, repo: Any) -> Optional[str]:
        """Extract repository URL from various formats."""
        if not repo:
            return None
        if isinstance(repo, str):
            return repo
        if isinstance(repo, dict):
            url = repo.get("url", "")
            # Normalize git URLs
            if url.startswith("git+"):
                url = url[4:]
            if url.endswith(".git"):
                url = url[:-4]
            return url
        return None
```

---

## 6. CLI Integration

### 6.1 Command-Line Interface

```python
"""
CLI commands for marketplace operations.

Usage:
    isa install <package>          Install a package
    isa install <pkg1> <pkg2>      Install multiple packages
    isa uninstall <package>        Remove a package
    isa search <query>             Search for packages
    isa list                       List installed packages
    isa update [package]           Update packages
    isa info <package>             Show package details
"""
import click
import asyncio
from typing import List, Optional


@click.group()
def marketplace():
    """Marketplace commands for managing MCP packages."""
    pass


@marketplace.command()
@click.argument("packages", nargs=-1, required=True)
@click.option("--version", "-v", help="Specific version to install")
@click.option("--no-connect", is_flag=True, help="Don't connect after install")
def install(packages: tuple, version: Optional[str], no_connect: bool):
    """
    Install one or more MCP packages.

    Examples:
        isa install pencil
        isa install @anthropic/claude-mcp --version 1.2.0
        isa install pencil remotion notion
    """
    async def _install():
        from services.marketplace_service import create_marketplace_service, PackageSpec

        marketplace = await create_marketplace_service()

        specs = [
            PackageSpec(name=pkg, version=version if len(packages) == 1 else None)
            for pkg in packages
        ]

        if len(specs) == 1:
            result = await marketplace.install(specs[0], auto_connect=not no_connect)
            if result.success:
                click.echo(f"✓ Installed {result.package_name}@{result.version}")
                click.echo(f"  Tools discovered: {result.tools_discovered}")
                if result.skills_assigned:
                    click.echo(f"  Skills: {', '.join(result.skills_assigned)}")
            else:
                click.echo(f"✗ Failed to install {result.package_name}: {result.error}")
        else:
            results = await marketplace.install_multiple(specs)
            for result in results:
                if isinstance(result, Exception):
                    click.echo(f"✗ Error: {result}")
                elif result.success:
                    click.echo(f"✓ {result.package_name}@{result.version} ({result.tools_discovered} tools)")
                else:
                    click.echo(f"✗ {result.package_name}: {result.error}")

    asyncio.run(_install())


@marketplace.command()
@click.argument("query")
@click.option("--category", "-c", help="Filter by category")
@click.option("--limit", "-n", default=10, help="Max results")
def search(query: str, category: Optional[str], limit: int):
    """
    Search for packages in the marketplace.

    Examples:
        isa search video
        isa search "ui design" --category design
    """
    async def _search():
        from services.marketplace_service import create_marketplace_service

        marketplace = await create_marketplace_service()
        results = await marketplace.search(query, category=category, limit=limit)

        if not results["packages"]:
            click.echo("No packages found.")
            return

        click.echo(f"Found {results['total']} packages:\n")
        for pkg in results["packages"]:
            verified = "✓" if pkg.get("verified") else " "
            stars = f"★{pkg.get('star_count', 0)}" if pkg.get("star_count") else ""
            click.echo(f"  {verified} {pkg['name']:<30} {stars}")
            click.echo(f"    {pkg.get('description', '')[:60]}...")

    asyncio.run(_search())


@marketplace.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Include disabled")
def list_packages(show_all: bool):
    """List installed packages."""
    async def _list():
        from services.marketplace_service import create_marketplace_service

        marketplace = await create_marketplace_service()
        packages = await marketplace.list_installed(include_tools=True)

        if not packages:
            click.echo("No packages installed.")
            return

        click.echo("Installed packages:\n")
        for pkg in packages:
            if not show_all and pkg["status"] == "disabled":
                continue

            status = "●" if pkg["status"] == "installed" else "○"
            tools = len(pkg.get("tools", []))
            click.echo(f"  {status} {pkg['package_name']:<25} v{pkg['version']:<10} ({tools} tools)")

    asyncio.run(_list())


@marketplace.command()
@click.argument("package", required=False)
@click.option("--all", "-a", "update_all", is_flag=True, help="Update all packages")
def update(package: Optional[str], update_all: bool):
    """Update installed packages."""
    async def _update():
        from services.marketplace_service import create_marketplace_service

        marketplace = await create_marketplace_service()

        if update_all:
            results = await marketplace.update_all()
            for result in results:
                if result.success:
                    click.echo(f"✓ Updated {result.package_name} to {result.version}")
                else:
                    click.echo(f"✗ Failed to update {result.package_name}: {result.error}")
        elif package:
            result = await marketplace.update_package(package)
            if result.success:
                click.echo(f"✓ Updated {result.package_name} to {result.version}")
            else:
                click.echo(f"✗ Failed: {result.error}")
        else:
            # Check for updates
            updates = await marketplace.check_updates()
            if not updates:
                click.echo("All packages up to date.")
            else:
                click.echo("Updates available:")
                for upd in updates:
                    click.echo(f"  {upd['name']}: {upd['current']} → {upd['latest']}")

    asyncio.run(_update())


@marketplace.command()
@click.argument("package")
def info(package: str):
    """Show detailed package information."""
    async def _info():
        from services.marketplace_service import create_marketplace_service

        marketplace = await create_marketplace_service()
        pkg = await marketplace.get_package(package)

        if not pkg:
            click.echo(f"Package not found: {package}")
            return

        click.echo(f"\n{pkg['display_name']}")
        click.echo(f"{'=' * len(pkg['display_name'])}")
        click.echo(f"\nName:        {pkg['name']}")
        click.echo(f"Version:     {pkg.get('latest_version', 'N/A')}")
        click.echo(f"Author:      {pkg.get('author', 'Unknown')}")
        click.echo(f"License:     {pkg.get('license', 'N/A')}")
        click.echo(f"Registry:    {pkg['registry_source']}")

        if pkg.get("description"):
            click.echo(f"\n{pkg['description']}")

        if pkg.get("installed"):
            inst = pkg["installed"]
            click.echo(f"\nInstalled:   v{inst['version']} ({inst['status']})")

        if pkg.get("tools"):
            click.echo(f"\nTools ({len(pkg['tools'])}):")
            for tool in pkg["tools"][:10]:
                click.echo(f"  • {tool.get('name', tool)}")

    asyncio.run(_info())


@marketplace.command()
@click.argument("package")
def uninstall(package: str):
    """Remove an installed package."""
    async def _uninstall():
        from services.marketplace_service import create_marketplace_service

        marketplace = await create_marketplace_service()

        if click.confirm(f"Uninstall {package}?"):
            try:
                await marketplace.uninstall(package)
                click.echo(f"✓ Uninstalled {package}")
            except Exception as e:
                click.echo(f"✗ Failed: {e}")

    asyncio.run(_uninstall())
```

---

## 7. Meta-Tools Integration

### 7.1 Marketplace Meta-Tools

```python
"""
Marketplace meta-tools for Claude interaction.

These tools allow Claude to discover and manage packages.
"""
from typing import Any, Dict, List, Optional


async def marketplace_search(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search the MCP package marketplace.

    Args:
        query: Search query (name, description, capabilities)
        category: Filter by category (design, video, productivity, etc.)
        limit: Maximum results to return

    Returns:
        Search results with package details

    Example:
        >>> await marketplace_search("video editing")
        {
            "total": 5,
            "packages": [
                {"name": "remotion", "description": "Create videos with React", ...},
                ...
            ]
        }
    """
    from services.marketplace_service import create_marketplace_service

    marketplace = await create_marketplace_service()
    return await marketplace.search(query, category=category, limit=limit)


async def marketplace_install(
    package_name: str,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Install a package from the marketplace.

    Args:
        package_name: Package to install (e.g., "pencil", "@anthropic/claude-mcp")
        version: Specific version (optional, defaults to latest)

    Returns:
        Installation result with tools discovered

    Example:
        >>> await marketplace_install("pencil")
        {
            "success": True,
            "package_name": "pencil",
            "version": "1.2.0",
            "tools_discovered": 15,
            "skills_assigned": ["design", "ui-prototyping"]
        }
    """
    from services.marketplace_service import create_marketplace_service, PackageSpec

    marketplace = await create_marketplace_service()
    result = await marketplace.install(PackageSpec(name=package_name, version=version))

    return {
        "success": result.success,
        "package_name": result.package_name,
        "version": result.version,
        "tools_discovered": result.tools_discovered,
        "skills_assigned": result.skills_assigned or [],
        "error": result.error,
    }


async def marketplace_list() -> List[Dict[str, Any]]:
    """
    List installed marketplace packages.

    Returns:
        List of installed packages with status and tools
    """
    from services.marketplace_service import create_marketplace_service

    marketplace = await create_marketplace_service()
    return await marketplace.list_installed(include_tools=True)


async def marketplace_uninstall(package_name: str) -> Dict[str, Any]:
    """
    Uninstall a marketplace package.

    Args:
        package_name: Package to uninstall

    Returns:
        Result of uninstallation
    """
    from services.marketplace_service import create_marketplace_service

    marketplace = await create_marketplace_service()

    try:
        await marketplace.uninstall(package_name)
        return {"success": True, "message": f"Uninstalled {package_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 8. Database Migrations

### 8.1 Migration: Create Marketplace Tables

```sql
-- Migration: 001_create_marketplace_tables.sql
-- Schema: mcp
-- Description: Creates tables for marketplace package management

-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: marketplace_packages
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.marketplace_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Package identification
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,

    -- Metadata
    description TEXT,
    author VARCHAR(255),
    author_email VARCHAR(255),
    homepage_url TEXT,
    repository_url TEXT,
    documentation_url TEXT,
    license VARCHAR(50),

    -- Categorization
    category VARCHAR(100),
    tags TEXT[] DEFAULT '{}',

    -- Registry source
    registry_source VARCHAR(50) NOT NULL,
    registry_url TEXT,

    -- Popularity metrics
    download_count INTEGER DEFAULT 0,
    weekly_downloads INTEGER DEFAULT 0,
    star_count INTEGER DEFAULT 0,

    -- Trust indicators
    verified BOOLEAN DEFAULT FALSE,
    official BOOLEAN DEFAULT FALSE,
    security_score INTEGER,

    -- Latest version (denormalized)
    latest_version VARCHAR(50),
    latest_version_id UUID,

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    deprecation_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT pkg_name_format CHECK (name ~ '^(@[a-z0-9-]+/)?[a-z0-9-]+$'),
    CONSTRAINT pkg_registry_check CHECK (
        registry_source IN ('npm', 'github', 'isa-cloud', 'private', 'local')
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_name ON mcp.marketplace_packages(name);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_category ON mcp.marketplace_packages(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_registry ON mcp.marketplace_packages(registry_source);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_downloads ON mcp.marketplace_packages(download_count DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_stars ON mcp.marketplace_packages(star_count DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_verified ON mcp.marketplace_packages(verified) WHERE verified = TRUE;
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_tags ON mcp.marketplace_packages USING GIN (tags);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_marketplace_pkg_search ON mcp.marketplace_packages
    USING GIN (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(display_name, '') || ' ' || coalesce(description, '')));


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: package_versions
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.package_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id) ON DELETE CASCADE,

    -- Version info (semver)
    version VARCHAR(50) NOT NULL,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_patch INTEGER NOT NULL,
    prerelease VARCHAR(50),

    -- MCP Configuration
    mcp_config JSONB NOT NULL,

    -- Tool metadata
    declared_tools JSONB DEFAULT '[]',
    tool_count INTEGER DEFAULT 0,

    -- Requirements
    min_mcp_version VARCHAR(20),
    required_env_vars TEXT[] DEFAULT '{}',
    dependencies JSONB DEFAULT '{}',

    -- Release info
    changelog TEXT,
    release_notes_url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    published_by VARCHAR(255),

    -- Status
    deprecated BOOLEAN DEFAULT FALSE,
    yanked BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE (package_id, version)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pkg_versions_package ON mcp.package_versions(package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_versions_semver ON mcp.package_versions(
    package_id, version_major DESC, version_minor DESC, version_patch DESC
);
CREATE INDEX IF NOT EXISTS idx_pkg_versions_published ON mcp.package_versions(published_at DESC);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: installed_packages
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.installed_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What's installed
    package_id UUID NOT NULL REFERENCES mcp.marketplace_packages(id),
    version_id UUID NOT NULL REFERENCES mcp.package_versions(id),

    -- Links to aggregator
    server_id UUID REFERENCES mcp.external_servers(id) ON DELETE SET NULL,

    -- Ownership (multi-tenant)
    user_id UUID,
    org_id UUID,
    team_id UUID,

    -- Configuration
    install_config JSONB DEFAULT '{}',
    env_overrides JSONB DEFAULT '{}',

    -- Update policy
    auto_update BOOLEAN DEFAULT TRUE,
    update_channel VARCHAR(20) DEFAULT 'stable',
    pinned_version BOOLEAN DEFAULT FALSE,

    -- Status
    status VARCHAR(20) DEFAULT 'installed',
    error_message TEXT,

    -- Usage
    last_used_at TIMESTAMPTZ,
    use_count INTEGER DEFAULT 0,

    -- Timestamps
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT installed_pkg_status CHECK (
        status IN ('installed', 'disabled', 'error', 'updating', 'uninstalling')
    ),
    CONSTRAINT installed_pkg_channel CHECK (
        update_channel IN ('stable', 'beta', 'latest')
    )
);

-- Unique constraints for ownership
CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_user
    ON mcp.installed_packages(package_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_org
    ON mcp.installed_packages(package_id, org_id) WHERE org_id IS NOT NULL AND team_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_installed_pkg_team
    ON mcp.installed_packages(package_id, org_id, team_id) WHERE org_id IS NOT NULL AND team_id IS NOT NULL;

-- Other indexes
CREATE INDEX IF NOT EXISTS idx_installed_pkg_server ON mcp.installed_packages(server_id);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_status ON mcp.installed_packages(status);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_user_id ON mcp.installed_packages(user_id);
CREATE INDEX IF NOT EXISTS idx_installed_pkg_org_id ON mcp.installed_packages(org_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: package_tool_mappings
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.package_tool_mappings (
    installed_package_id UUID NOT NULL REFERENCES mcp.installed_packages(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES mcp.tools(id) ON DELETE CASCADE,

    original_name VARCHAR(255) NOT NULL,
    namespaced_name VARCHAR(255) NOT NULL,

    skill_ids TEXT[] DEFAULT '{}',
    primary_skill_id VARCHAR(100),

    discovered_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (installed_package_id, tool_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_installed ON mcp.package_tool_mappings(installed_package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_tool ON mcp.package_tool_mappings(tool_id);
CREATE INDEX IF NOT EXISTS idx_pkg_tool_map_skills ON mcp.package_tool_mappings USING GIN (skill_ids);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Table: registry_sync_log
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mcp.registry_sync_log (
    id SERIAL PRIMARY KEY,

    registry_source VARCHAR(50) NOT NULL,
    sync_type VARCHAR(20) NOT NULL,

    packages_discovered INTEGER DEFAULT 0,
    packages_updated INTEGER DEFAULT 0,
    packages_deprecated INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',

    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,

    CONSTRAINT sync_log_type CHECK (sync_type IN ('full', 'incremental', 'single_package')),
    CONSTRAINT sync_log_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_sync_log_registry ON mcp.registry_sync_log(registry_source);
CREATE INDEX IF NOT EXISTS idx_sync_log_started ON mcp.registry_sync_log(started_at DESC);


-- ═══════════════════════════════════════════════════════════════════════════════
-- Triggers
-- ═══════════════════════════════════════════════════════════════════════════════

-- Updated_at trigger for marketplace_packages
CREATE OR REPLACE FUNCTION mcp.update_marketplace_pkg_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER marketplace_pkg_updated_at_trigger
    BEFORE UPDATE ON mcp.marketplace_packages
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_marketplace_pkg_updated_at();

-- Updated_at trigger for installed_packages
CREATE OR REPLACE FUNCTION mcp.update_installed_pkg_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER installed_pkg_updated_at_trigger
    BEFORE UPDATE ON mcp.installed_packages
    FOR EACH ROW
    EXECUTE FUNCTION mcp.update_installed_pkg_updated_at();


-- ═══════════════════════════════════════════════════════════════════════════════
-- Comments
-- ═══════════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE mcp.marketplace_packages IS 'Registry of available MCP packages from all sources';
COMMENT ON TABLE mcp.package_versions IS 'Version history for marketplace packages';
COMMENT ON TABLE mcp.installed_packages IS 'User/org package installations';
COMMENT ON TABLE mcp.package_tool_mappings IS 'Maps discovered tools to source packages';
COMMENT ON TABLE mcp.registry_sync_log IS 'Registry synchronization history';


-- ═══════════════════════════════════════════════════════════════════════════════
-- Permissions
-- ═══════════════════════════════════════════════════════════════════════════════

GRANT ALL ON TABLE mcp.marketplace_packages TO postgres;
GRANT ALL ON TABLE mcp.package_versions TO postgres;
GRANT ALL ON TABLE mcp.installed_packages TO postgres;
GRANT ALL ON TABLE mcp.package_tool_mappings TO postgres;
GRANT ALL ON TABLE mcp.registry_sync_log TO postgres;
GRANT ALL ON SEQUENCE mcp.registry_sync_log_id_seq TO postgres;
```

---

## 9. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Create database migration
- [ ] Implement PackageRepository
- [ ] Implement RegistryFetcher (npm only)
- [ ] Basic MarketplaceService

### Phase 2: Installation Flow (Week 2-3)
- [ ] Implement PackageResolver
- [ ] Implement InstallManager
- [ ] Integration with AggregatorService
- [ ] Integration with SkillService

### Phase 3: CLI & Meta-Tools (Week 3-4)
- [ ] CLI commands (install, search, list)
- [ ] Meta-tools for Claude
- [ ] Background sync task

### Phase 4: Polish & Testing (Week 4-5)
- [ ] UpdateManager implementation
- [ ] GitHub registry support
- [ ] Comprehensive tests
- [ ] Documentation

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Install success rate | >95% | Successful installs / attempts |
| Time to install | <30s | From command to tools available |
| Search relevance | >80% | User finds package in top 5 |
| Tool discovery rate | 100% | All MCP tools discovered and classified |
| Registry sync time | <5min | Full npm sync |

---

## 11. Security Considerations

1. **Package Verification**: Only install from trusted sources
2. **Environment Variables**: Securely store API keys
3. **Sandboxing**: Consider process isolation for untrusted MCPs
4. **Audit Logging**: Track all installations
5. **Dependency Scanning**: Check for known vulnerabilities

---

## Appendix A: Configuration Schema

```yaml
# Example package configuration (mcp.config.yaml)
name: "@example/my-mcp"
version: "1.0.0"
description: "My custom MCP server"

mcp:
  transport: stdio
  command: node
  args: ["dist/index.js"]
  env:
    MY_API_KEY: "{{MY_API_KEY}}"  # Placeholder for user config

tools:
  - name: my_tool
    description: "Does something useful"

requirements:
  min_mcp_version: "1.0.0"
  env_vars:
    - MY_API_KEY
```
