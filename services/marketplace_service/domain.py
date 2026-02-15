"""
Marketplace Service Domain Types.

Canonical enums and dataclasses for the marketplace service.
These are the production source of truth — test contracts re-export from here.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════


class RegistrySource(str, Enum):
    NPM = "npm"
    GITHUB = "github"
    ISA_CLOUD = "isa-cloud"
    PRIVATE = "private"
    LOCAL = "local"


class InstallStatus(str, Enum):
    INSTALLED = "installed"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"
    UNINSTALLING = "uninstalling"


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    LATEST = "latest"


class SyncType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    SINGLE_PACKAGE = "single_package"


class SyncStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# Service Contracts (Request/Response Types used by production code)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PackageSpec:
    """Package specification for installation."""

    name: str
    version: Optional[str] = None
    registry: Optional[RegistrySource] = None
    config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not re.match(r"^(@[a-z0-9-]+/)?[a-z0-9-]+$", self.name):
            raise ValueError(f"Invalid package name format: {self.name}")


@dataclass
class InstallResult:
    """Result of package installation."""

    success: bool
    package_id: str
    package_name: str
    version: str

    server_id: Optional[str] = None
    tools_discovered: int = 0
    skills_assigned: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
class UpdateInfo:
    """Information about available package update."""

    package_id: str
    package_name: str
    current_version: str
    latest_version: str
    update_channel: UpdateChannel
    changelog: Optional[str] = None
    breaking_changes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "package_name": self.package_name,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_channel": self.update_channel.value,
            "changelog": self.changelog,
            "breaking_changes": self.breaking_changes,
        }


@dataclass
class SearchResult:
    """
    Search result from marketplace.

    Returned by MarketplaceService.search()

    Note: packages field uses List[Dict[str, Any]] to avoid dependency on
    test-only PackageRecordContract. Each dict should have keys like:
    id, name, display_name, description, author, etc.
    """

    total: int
    packages: List[Dict[str, Any]]
    query: str
    limit: int
    offset: int

    # Search metadata
    search_time_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "total": self.total,
            "packages": self.packages,
            "query": self.query,
            "limit": self.limit,
            "offset": self.offset,
            "search_time_ms": self.search_time_ms,
        }
