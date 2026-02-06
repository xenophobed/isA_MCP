"""
Marketplace Data Contracts.

Defines the data structures and types for marketplace package management.
These contracts serve as the single source of truth for:
- Database schemas
- API request/response types
- Service interfaces
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class RegistrySource(str, Enum):
    """
    Supported package registry sources.

    Database column: mcp.marketplace_packages.registry_source
    """
    NPM = "npm"              # npm registry (npmjs.com)
    GITHUB = "github"        # GitHub releases
    ISA_CLOUD = "isa-cloud"  # isA Cloud marketplace
    PRIVATE = "private"      # Private enterprise registry
    LOCAL = "local"          # Local file-based package


class InstallStatus(str, Enum):
    """
    Package installation status.

    Database column: mcp.installed_packages.status
    """
    INSTALLED = "installed"        # Package installed and active
    DISABLED = "disabled"          # Package disabled but not removed
    ERROR = "error"                # Installation/connection error
    UPDATING = "updating"          # Update in progress
    UNINSTALLING = "uninstalling"  # Uninstall in progress


class UpdateChannel(str, Enum):
    """
    Update channel for packages.

    Database column: mcp.installed_packages.update_channel
    """
    STABLE = "stable"   # Stable releases only
    BETA = "beta"       # Include beta releases
    LATEST = "latest"   # Always use latest (including prereleases)


class SyncType(str, Enum):
    """
    Registry synchronization type.

    Database column: mcp.registry_sync_log.sync_type
    """
    FULL = "full"                    # Full registry sync
    INCREMENTAL = "incremental"      # Only changed packages
    SINGLE_PACKAGE = "single_package"  # Single package update


class SyncStatus(str, Enum):
    """
    Registry synchronization status.

    Database column: mcp.registry_sync_log.status
    """
    RUNNING = "running"      # Sync in progress
    COMPLETED = "completed"  # Sync completed successfully
    FAILED = "failed"        # Sync failed


# ═══════════════════════════════════════════════════════════════════════════════
# Database Record Contracts
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PackageRecordContract:
    """
    Contract for marketplace_packages table record.

    Represents an available MCP package from any registry source.
    """
    # Primary key
    id: str  # UUID

    # Package identification
    name: str                    # e.g., "@pencil/ui-design" or "remotion"
    display_name: str            # e.g., "Pencil UI Design"

    # Registry source
    registry_source: RegistrySource

    # Optional metadata
    description: Optional[str] = None
    author: Optional[str] = None
    author_email: Optional[str] = None
    homepage_url: Optional[str] = None
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    license: Optional[str] = None

    # Categorization
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Registry URL
    registry_url: Optional[str] = None

    # Popularity metrics
    download_count: int = 0
    weekly_downloads: int = 0
    star_count: int = 0

    # Trust indicators
    verified: bool = False
    official: bool = False
    security_score: Optional[int] = None

    # Latest version info (denormalized)
    latest_version: Optional[str] = None
    latest_version_id: Optional[str] = None

    # Status
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "author": self.author,
            "author_email": self.author_email,
            "homepage_url": self.homepage_url,
            "repository_url": self.repository_url,
            "documentation_url": self.documentation_url,
            "license": self.license,
            "category": self.category,
            "tags": self.tags,
            "registry_source": self.registry_source.value if isinstance(self.registry_source, RegistrySource) else self.registry_source,
            "registry_url": self.registry_url,
            "download_count": self.download_count,
            "weekly_downloads": self.weekly_downloads,
            "star_count": self.star_count,
            "verified": self.verified,
            "official": self.official,
            "security_score": self.security_score,
            "latest_version": self.latest_version,
            "latest_version_id": self.latest_version_id,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_synced_at": self.last_synced_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageRecordContract":
        """Create from dictionary (e.g., database row)."""
        registry_source = data.get("registry_source")
        if isinstance(registry_source, str):
            registry_source = RegistrySource(registry_source)

        return cls(
            id=str(data["id"]),
            name=data["name"],
            display_name=data["display_name"],
            description=data.get("description"),
            author=data.get("author"),
            author_email=data.get("author_email"),
            homepage_url=data.get("homepage_url"),
            repository_url=data.get("repository_url"),
            documentation_url=data.get("documentation_url"),
            license=data.get("license"),
            category=data.get("category"),
            tags=data.get("tags") or [],
            registry_source=registry_source,
            registry_url=data.get("registry_url"),
            download_count=data.get("download_count", 0),
            weekly_downloads=data.get("weekly_downloads", 0),
            star_count=data.get("star_count", 0),
            verified=data.get("verified", False),
            official=data.get("official", False),
            security_score=data.get("security_score"),
            latest_version=data.get("latest_version"),
            latest_version_id=str(data["latest_version_id"]) if data.get("latest_version_id") else None,
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_synced_at=data.get("last_synced_at"),
        )


@dataclass
class PackageVersionContract:
    """
    Contract for package_versions table record.

    Represents a specific version of an MCP package.
    """
    # Primary key
    id: str  # UUID
    package_id: str  # Foreign key to marketplace_packages

    # Version info (semver)
    version: str
    version_major: int
    version_minor: int
    version_patch: int
    prerelease: Optional[str] = None

    # MCP Configuration
    mcp_config: Dict[str, Any] = field(default_factory=dict)

    # Tool metadata
    declared_tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_count: int = 0

    # Requirements
    min_mcp_version: Optional[str] = None
    required_env_vars: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)

    # Release info
    changelog: Optional[str] = None
    release_notes_url: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None

    # Status
    deprecated: bool = False
    yanked: bool = False

    # Timestamps
    created_at: Optional[datetime] = None

    @classmethod
    def parse_semver(cls, version: str) -> tuple:
        """Parse semver string into components."""
        import re

        # Match: major.minor.patch[-prerelease]
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version)
        if not match:
            # Fallback for non-standard versions
            parts = version.split('.')
            major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch = int(parts[2].split('-')[0]) if len(parts) > 2 and parts[2].split('-')[0].isdigit() else 0
            prerelease = None
            return major, minor, patch, prerelease

        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            match.group(4),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "id": self.id,
            "package_id": self.package_id,
            "version": self.version,
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "version_patch": self.version_patch,
            "prerelease": self.prerelease,
            "mcp_config": self.mcp_config,
            "declared_tools": self.declared_tools,
            "tool_count": self.tool_count,
            "min_mcp_version": self.min_mcp_version,
            "required_env_vars": self.required_env_vars,
            "dependencies": self.dependencies,
            "changelog": self.changelog,
            "release_notes_url": self.release_notes_url,
            "published_at": self.published_at,
            "published_by": self.published_by,
            "deprecated": self.deprecated,
            "yanked": self.yanked,
            "created_at": self.created_at,
        }


@dataclass
class InstalledPackageContract:
    """
    Contract for installed_packages table record.

    Represents a package installation for a user or organization.
    """
    # Primary key
    id: str  # UUID

    # What's installed
    package_id: str
    version_id: str

    # Links to aggregator
    server_id: Optional[str] = None

    # Ownership
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    team_id: Optional[str] = None

    # Configuration
    install_config: Dict[str, Any] = field(default_factory=dict)
    env_overrides: Dict[str, str] = field(default_factory=dict)

    # Update policy
    auto_update: bool = True
    update_channel: UpdateChannel = UpdateChannel.STABLE
    pinned_version: bool = False

    # Status
    status: InstallStatus = InstallStatus.INSTALLED
    error_message: Optional[str] = None

    # Usage
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    # Timestamps
    installed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "id": self.id,
            "package_id": self.package_id,
            "version_id": self.version_id,
            "server_id": self.server_id,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "team_id": self.team_id,
            "install_config": self.install_config,
            "env_overrides": self.env_overrides,
            "auto_update": self.auto_update,
            "update_channel": self.update_channel.value if isinstance(self.update_channel, UpdateChannel) else self.update_channel,
            "pinned_version": self.pinned_version,
            "status": self.status.value if isinstance(self.status, InstallStatus) else self.status,
            "error_message": self.error_message,
            "last_used_at": self.last_used_at,
            "use_count": self.use_count,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "last_sync_at": self.last_sync_at,
        }


@dataclass
class PackageToolMappingContract:
    """
    Contract for package_tool_mappings table record.

    Maps discovered tools to their source package.
    """
    installed_package_id: str
    tool_id: int

    original_name: str
    namespaced_name: str

    skill_ids: List[str] = field(default_factory=list)
    primary_skill_id: Optional[str] = None

    discovered_at: Optional[datetime] = None


@dataclass
class RegistrySyncLogContract:
    """
    Contract for registry_sync_log table record.

    Tracks registry synchronization history.
    """
    id: Optional[int] = None

    registry_source: str = ""
    sync_type: SyncType = SyncType.INCREMENTAL

    packages_discovered: int = 0
    packages_updated: int = 0
    packages_deprecated: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    status: SyncStatus = SyncStatus.RUNNING
    error_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Service Contracts (Request/Response Types)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PackageSpec:
    """
    Package specification for installation.

    Used as input to MarketplaceService.install()
    """
    name: str                                    # Package name
    version: Optional[str] = None                # Specific version (None = latest)
    registry: Optional[RegistrySource] = None    # Specific registry
    config: Optional[Dict[str, Any]] = None      # User configuration (API keys, etc.)

    def __post_init__(self):
        """Validate package name format."""
        import re
        if not re.match(r'^(@[a-z0-9-]+/)?[a-z0-9-]+$', self.name):
            raise ValueError(f"Invalid package name format: {self.name}")


@dataclass
class InstallResult:
    """
    Result of package installation.

    Returned by MarketplaceService.install()
    """
    success: bool
    package_id: str
    package_name: str
    version: str

    server_id: Optional[str] = None
    tools_discovered: int = 0
    skills_assigned: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "success": self.success,
            "package_id": self.package_id,
            "package_name": self.package_name,
            "version": self.version,
            "server_id": self.server_id,
            "tools_discovered": self.tools_discovered,
            "skills_assigned": self.skills_assigned,
            "error": self.error,
        }


@dataclass
class SearchResult:
    """
    Search result from marketplace.

    Returned by MarketplaceService.search()
    """
    total: int
    packages: List[PackageRecordContract]
    query: str
    limit: int
    offset: int

    # Search metadata
    search_time_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "total": self.total,
            "packages": [p.to_dict() for p in self.packages],
            "query": self.query,
            "limit": self.limit,
            "offset": self.offset,
            "search_time_ms": self.search_time_ms,
        }


@dataclass
class UpdateInfo:
    """
    Information about available package update.

    Returned by MarketplaceService.check_updates()
    """
    package_id: str
    package_name: str
    current_version: str
    latest_version: str
    update_channel: UpdateChannel
    changelog: Optional[str] = None
    breaking_changes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_channel": self.update_channel.value,
            "changelog": self.changelog,
            "breaking_changes": self.breaking_changes,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Configuration Contract
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MCPConfigContract:
    """
    Contract for MCP server configuration.

    Stored in package_versions.mcp_config
    """
    transport: str  # "stdio", "sse", "http", "streamable_http"

    # For stdio transport
    command: Optional[str] = None
    args: Optional[List[str]] = None
    cwd: Optional[str] = None

    # For http/sse transport
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    # Environment variables (with placeholders)
    env: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {"transport": self.transport}

        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.cwd:
            result["cwd"] = self.cwd
        if self.url:
            result["url"] = self.url
        if self.headers:
            result["headers"] = self.headers
        if self.env:
            result["env"] = self.env

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPConfigContract":
        """Create from dictionary."""
        return cls(
            transport=data.get("transport", "stdio"),
            command=data.get("command"),
            args=data.get("args"),
            cwd=data.get("cwd"),
            url=data.get("url"),
            headers=data.get("headers"),
            env=data.get("env"),
        )

    def resolve_env_placeholders(self, user_config: Dict[str, str]) -> Dict[str, str]:
        """
        Resolve environment variable placeholders with user config.

        Placeholders are in format: {{VAR_NAME}}

        Args:
            user_config: User-provided configuration values

        Returns:
            Resolved environment variables
        """
        import re

        if not self.env:
            return {}

        resolved = {}
        placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')

        for key, value in self.env.items():
            if isinstance(value, str):
                # Find all placeholders
                matches = placeholder_pattern.findall(value)
                resolved_value = value

                for match in matches:
                    if match in user_config:
                        resolved_value = resolved_value.replace(
                            f"{{{{{match}}}}}",
                            user_config[match]
                        )

                resolved[key] = resolved_value
            else:
                resolved[key] = value

        return resolved
