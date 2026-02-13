"""
Unit tests for MarketplaceService.

Tests:
- Package search and discovery
- Version resolution
- Installation workflow
- Update management
- Registry fetching
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.marketplace_service.marketplace_service import MarketplaceService
from services.marketplace_service.package_repository import PackageRepository
from services.marketplace_service.registry_fetcher import RegistryFetcher
from services.marketplace_service.package_resolver import PackageResolver
from services.marketplace_service.install_manager import InstallManager
from services.marketplace_service.update_manager import UpdateManager
from tests.contracts.marketplace import (
    PackageSpec,
    InstallStatus,
    RegistrySource,
    UpdateChannel,
)

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_package():
    """Sample package data."""
    return {
        "id": "pkg-001",
        "name": "@anthropic/mcp-server-filesystem",
        "display_name": "Filesystem MCP Server",
        "description": "Access local filesystem through MCP",
        "author": "Anthropic",
        "latest_version": "1.2.0",
        "registry_source": RegistrySource.NPM.value,
        "tags": ["filesystem", "io", "files"],
        "verified": True,
        "download_count": 15000,
    }


@pytest.fixture
def mock_version():
    """Sample version data."""
    return {
        "id": "ver-001",
        "package_id": "pkg-001",
        "version": "1.2.0",
        "version_major": 1,
        "version_minor": 2,
        "version_patch": 0,
        "prerelease": None,
        "mcp_config": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-server-filesystem"],
            "env": {
                "ALLOWED_PATHS": "{{ALLOWED_PATHS}}",
            },
        },
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_installation():
    """Sample installation data."""
    return {
        "id": "inst-001",
        "package_id": "pkg-001",
        "version_id": "ver-001",
        "version": "1.2.0",
        "server_id": "srv-001",
        "status": InstallStatus.INSTALLED.value,
        "install_config": {"ALLOWED_PATHS": "/home/user"},
        "package_name": "@anthropic/mcp-server-filesystem",
    }


@pytest.fixture
def mock_repository():
    """Mock PackageRepository."""
    repo = MagicMock(spec=PackageRepository)
    repo._db_pool = None
    repo._packages = {}
    repo._versions = {}
    repo._installations = {}
    repo._tool_mappings = {}
    return repo


@pytest.fixture
def mock_aggregator():
    """Mock AggregatorService."""
    aggregator = AsyncMock()
    aggregator.register_server = AsyncMock(
        return_value={
            "id": "srv-001",
            "name": "anthropic-mcp-server-filesystem",
            "status": "connected",
        }
    )
    aggregator.discover_tools = AsyncMock(
        return_value=[
            {
                "name": "read_file",
                "description": "Read file contents",
                "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            },
            {
                "name": "write_file",
                "description": "Write file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                },
            },
        ]
    )
    aggregator.remove_server = AsyncMock()
    aggregator.connect_server = AsyncMock()
    aggregator.disconnect_server = AsyncMock()
    return aggregator


@pytest.fixture
def mock_skill_service():
    """Mock SkillService."""
    skill_service = AsyncMock()
    skill_service.classify_tool = AsyncMock(return_value=["skill-filesystem"])
    return skill_service


@pytest.fixture
def mock_tool_repository():
    """Mock ToolRepository."""
    tool_repo = AsyncMock()
    tool_repo.upsert_external_tool = AsyncMock(return_value=1)
    tool_repo.delete_tools_by_server = AsyncMock(return_value=2)
    return tool_repo


@pytest.fixture
def mock_vector_repository():
    """Mock VectorRepository."""
    vector_repo = AsyncMock()
    vector_repo.batch_upsert_tools = AsyncMock()
    return vector_repo


# ═══════════════════════════════════════════════════════════════
# PackageRepository Tests
# ═══════════════════════════════════════════════════════════════


class TestPackageRepository:
    """Tests for PackageRepository (in-memory mode)."""

    @pytest.mark.asyncio
    async def test_create_package(self):
        """Test creating a package."""
        repo = PackageRepository(db_pool=None)

        package = await repo.create_package(
            {
                "name": "test-package",
                "display_name": "Test Package",
                "description": "A test package",
            }
        )

        assert package["name"] == "test-package"
        assert package["display_name"] == "Test Package"
        assert "id" in package
        assert "created_at" in package

    @pytest.mark.asyncio
    async def test_get_package_by_name(self):
        """Test getting a package by name."""
        repo = PackageRepository(db_pool=None)

        # Create package
        created = await repo.create_package(
            {
                "name": "test-package",
                "description": "Test",
            }
        )

        # Retrieve by name
        found = await repo.get_package_by_name("test-package")

        assert found is not None
        assert found["id"] == created["id"]
        assert found["name"] == "test-package"

    @pytest.mark.asyncio
    async def test_get_package_not_found(self):
        """Test getting a non-existent package."""
        repo = PackageRepository(db_pool=None)

        found = await repo.get_package_by_name("nonexistent")

        assert found is None

    @pytest.mark.asyncio
    async def test_create_version(self):
        """Test creating a version."""
        repo = PackageRepository(db_pool=None)

        # Create package first
        package = await repo.create_package({"name": "test-pkg"})

        # Create version
        version = await repo.create_version(
            {
                "package_id": package["id"],
                "version": "1.0.0",
                "version_major": 1,
                "version_minor": 0,
                "version_patch": 0,
                "mcp_config": {"transport": "stdio"},
            }
        )

        assert version["version"] == "1.0.0"
        assert version["package_id"] == package["id"]

    @pytest.mark.asyncio
    async def test_create_installation(self):
        """Test creating an installation."""
        repo = PackageRepository(db_pool=None)

        installation = await repo.create_installation(
            package_id="pkg-001",
            version_id="ver-001",
            server_id="srv-001",
            user_id="user-001",
            org_id=None,
            install_config={"key": "value"},
        )

        assert installation["package_id"] == "pkg-001"
        assert installation["status"] == InstallStatus.INSTALLED.value
        assert "id" in installation


# ═══════════════════════════════════════════════════════════════
# PackageResolver Tests
# ═══════════════════════════════════════════════════════════════


class TestPackageResolver:
    """Tests for PackageResolver."""

    @pytest.mark.asyncio
    async def test_resolve_latest_version(self, mock_package, mock_version):
        """Test resolving latest version."""
        repo = PackageRepository(db_pool=None)
        fetcher = MagicMock(spec=RegistryFetcher)
        fetcher.fetch_package = AsyncMock(return_value=None)

        resolver = PackageResolver(repository=repo, fetcher=fetcher)

        # Setup: create package and version
        await repo.create_package(mock_package)
        mock_version["package_id"] = mock_package["id"]
        await repo.create_version(mock_version)

        # Resolve
        spec = PackageSpec(name=mock_package["name"])
        result = await resolver.resolve(spec)

        assert result is not None
        package, version = result
        assert package["name"] == mock_package["name"]
        assert version["version"] == "1.2.0"

    @pytest.mark.asyncio
    async def test_resolve_specific_version(self, mock_package):
        """Test resolving a specific version."""
        repo = PackageRepository(db_pool=None)
        fetcher = MagicMock(spec=RegistryFetcher)
        fetcher.fetch_package = AsyncMock(return_value=None)

        resolver = PackageResolver(repository=repo, fetcher=fetcher)

        # Setup: create package with multiple versions
        await repo.create_package(mock_package)
        await repo.create_version(
            {
                "package_id": mock_package["id"],
                "version": "1.0.0",
                "version_major": 1,
                "version_minor": 0,
                "version_patch": 0,
            }
        )
        await repo.create_version(
            {
                "package_id": mock_package["id"],
                "version": "1.1.0",
                "version_major": 1,
                "version_minor": 1,
                "version_patch": 0,
            }
        )

        # Resolve specific version
        spec = PackageSpec(name=mock_package["name"], version="1.0.0")
        result = await resolver.resolve(spec)

        assert result is not None
        _, version = result
        assert version["version"] == "1.0.0"

    def test_parse_semver(self):
        """Test semver parsing."""
        repo = MagicMock()
        fetcher = MagicMock()
        resolver = PackageResolver(repository=repo, fetcher=fetcher)

        # Standard version
        major, minor, patch, pre = resolver._parse_semver("1.2.3")
        assert (major, minor, patch) == (1, 2, 3)
        assert pre is None

        # With prerelease
        major, minor, patch, pre = resolver._parse_semver("2.0.0-beta.1")
        assert (major, minor, patch) == (2, 0, 0)
        assert pre == "beta.1"

        # Invalid format
        major, minor, patch, pre = resolver._parse_semver("invalid")
        assert major == 0

    def test_semver_range_caret(self):
        """Test caret range matching (^1.2.0)."""
        repo = MagicMock()
        fetcher = MagicMock()
        resolver = PackageResolver(repository=repo, fetcher=fetcher)

        versions = [
            {"version": "1.0.0", "version_major": 1, "version_minor": 0, "version_patch": 0},
            {"version": "1.2.0", "version_major": 1, "version_minor": 2, "version_patch": 0},
            {"version": "1.3.0", "version_major": 1, "version_minor": 3, "version_patch": 0},
            {"version": "2.0.0", "version_major": 2, "version_minor": 0, "version_patch": 0},
        ]

        # ^1.2.0 should match 1.2.0 and 1.3.0, return highest
        result = resolver._match_semver_range(versions, "^1.2.0")
        assert result["version"] == "1.3.0"


# ═══════════════════════════════════════════════════════════════
# InstallManager Tests
# ═══════════════════════════════════════════════════════════════


class TestInstallManager:
    """Tests for InstallManager."""

    @pytest.mark.asyncio
    async def test_install_success(
        self,
        mock_package,
        mock_version,
        mock_repository,
        mock_aggregator,
        mock_skill_service,
        mock_tool_repository,
        mock_vector_repository,
    ):
        """Test successful package installation."""
        # Setup mocks
        mock_repository.create_installation = AsyncMock(
            return_value={
                "id": "inst-001",
                "package_id": mock_package["id"],
                "version_id": mock_version["id"],
            }
        )
        mock_repository.create_tool_mappings = AsyncMock()

        manager = InstallManager(
            repository=mock_repository,
            aggregator=mock_aggregator,
            skill_service=mock_skill_service,
            tool_repository=mock_tool_repository,
            vector_repository=mock_vector_repository,
        )

        # Install
        result = await manager.install(
            package=mock_package,
            version=mock_version,
            user_config={"ALLOWED_PATHS": "/home/user"},
            user_id="user-001",
        )

        assert result.success is True
        assert result.package_name == mock_package["name"]
        assert result.version == mock_version["version"]
        assert result.server_id == "srv-001"
        assert result.tools_discovered == 2

    @pytest.mark.asyncio
    async def test_install_without_aggregator(
        self,
        mock_package,
        mock_version,
        mock_repository,
    ):
        """Test installation without aggregator service."""
        mock_repository.create_installation = AsyncMock(
            return_value={
                "id": "inst-001",
                "package_id": mock_package["id"],
                "version_id": mock_version["id"],
            }
        )

        manager = InstallManager(
            repository=mock_repository,
            aggregator=None,
            skill_service=None,
        )

        result = await manager.install(
            package=mock_package,
            version=mock_version,
            user_config={},
        )

        assert result.success is True
        assert result.server_id is None
        assert result.tools_discovered == 0

    @pytest.mark.asyncio
    async def test_prepare_config_placeholder_resolution(self):
        """Test configuration placeholder resolution."""
        manager = InstallManager(
            repository=MagicMock(),
            aggregator=None,
        )

        mcp_config = {
            "transport": "stdio",
            "command": "npx",
            "env": {
                "API_KEY": "{{API_KEY}}",
                "PATH": "/usr/bin",
                "WORKSPACE": "{{WORKSPACE}}",
            },
        }

        user_config = {
            "API_KEY": "secret-key-123",
            "WORKSPACE": "/home/user",
        }

        result = await manager.prepare_config(mcp_config, user_config)

        assert result["env"]["API_KEY"] == "secret-key-123"
        assert result["env"]["PATH"] == "/usr/bin"
        assert result["env"]["WORKSPACE"] == "/home/user"

    def test_get_server_name(self):
        """Test server name generation."""
        manager = InstallManager(
            repository=MagicMock(),
            aggregator=None,
        )

        assert manager._get_server_name("@anthropic/mcp-server") == "anthropic-mcp-server"
        assert manager._get_server_name("simple-package") == "simple-package"
        assert manager._get_server_name("@scope/pkg_name") == "scope-pkg-name"

    @pytest.mark.asyncio
    async def test_uninstall(
        self,
        mock_installation,
        mock_repository,
        mock_aggregator,
        mock_tool_repository,
    ):
        """Test package uninstallation."""
        mock_repository.update_installation_status = AsyncMock()
        mock_repository.delete_tool_mappings = AsyncMock()
        mock_repository.delete_installation = AsyncMock()

        manager = InstallManager(
            repository=mock_repository,
            aggregator=mock_aggregator,
            tool_repository=mock_tool_repository,
        )

        result = await manager.uninstall(mock_installation)

        assert result is True
        mock_aggregator.remove_server.assert_called_once_with("srv-001")
        mock_tool_repository.delete_tools_by_server.assert_called_once()
        mock_repository.delete_installation.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# UpdateManager Tests
# ═══════════════════════════════════════════════════════════════


class TestUpdateManager:
    """Tests for UpdateManager."""

    def test_is_newer_version(self):
        """Test version comparison."""
        repo = MagicMock()
        resolver = MagicMock()
        installer = MagicMock()

        manager = UpdateManager(
            repository=repo,
            resolver=resolver,
            installer=installer,
        )

        assert manager._is_newer_version("1.1.0", "1.0.0") is True
        assert manager._is_newer_version("2.0.0", "1.9.9") is True
        assert manager._is_newer_version("1.0.1", "1.0.0") is True
        assert manager._is_newer_version("1.0.0", "1.0.0") is False
        assert manager._is_newer_version("1.0.0", "1.1.0") is False

    def test_parse_version(self):
        """Test version parsing."""
        repo = MagicMock()
        resolver = MagicMock()
        installer = MagicMock()

        manager = UpdateManager(
            repository=repo,
            resolver=resolver,
            installer=installer,
        )

        assert manager._parse_version("1.2.3") == (1, 2, 3)
        assert manager._parse_version("0.0.1") == (0, 0, 1)
        assert manager._parse_version("10.20.30") == (10, 20, 30)
        assert manager._parse_version("1.2.3-beta") == (1, 2, 3)


# ═══════════════════════════════════════════════════════════════
# RegistryFetcher Tests
# ═══════════════════════════════════════════════════════════════


class TestRegistryFetcher:
    """Tests for RegistryFetcher."""

    def test_normalize_npm_package(self):
        """Test npm package normalization."""
        repo = MagicMock()
        fetcher = RegistryFetcher(repository=repo)

        npm_package = {
            "name": "@anthropic/mcp-server-test",
            "description": "Test MCP server",
            "version": "1.0.0",
            "keywords": ["mcp-server", "test"],
            "author": {"name": "Anthropic"},
            "license": "MIT",
        }

        result = fetcher._normalize_npm_package(npm_package)

        assert result is not None
        assert result["name"] == "@anthropic/mcp-server-test"
        assert result["author"] == "Anthropic"
        assert result["registry_source"] == RegistrySource.NPM.value
        assert "test" in result["tags"]
        assert "mcp-server" not in result["tags"]  # MCP keywords filtered out

    def test_normalize_npm_package_no_mcp_keyword(self):
        """Test that non-MCP packages are filtered out."""
        repo = MagicMock()
        fetcher = RegistryFetcher(repository=repo)

        npm_package = {
            "name": "some-random-package",
            "keywords": ["utility", "helper"],
        }

        result = fetcher._normalize_npm_package(npm_package)

        assert result is None

    def test_extract_mcp_config_explicit(self):
        """Test MCP config extraction from explicit field."""
        repo = MagicMock()
        fetcher = RegistryFetcher(repository=repo)

        pkg_data = {
            "name": "test-pkg",
            "mcp": {
                "transport": "sse",
                "url": "http://localhost:3000",
            },
        }

        result = fetcher._extract_mcp_config(pkg_data)

        assert result["transport"] == "sse"
        assert result["url"] == "http://localhost:3000"

    def test_extract_mcp_config_default(self):
        """Test MCP config extraction with defaults."""
        repo = MagicMock()
        fetcher = RegistryFetcher(repository=repo)

        pkg_data = {
            "name": "@test/mcp-server",
        }

        result = fetcher._extract_mcp_config(pkg_data)

        assert result["transport"] == "stdio"
        assert result["command"] == "npx"
        assert result["args"] == ["-y", "@test/mcp-server"]

    def test_name_to_display(self):
        """Test display name generation."""
        repo = MagicMock()
        fetcher = RegistryFetcher(repository=repo)

        assert fetcher._name_to_display("@anthropic/mcp-server") == "Anthropic Mcp Server"
        assert fetcher._name_to_display("simple-package") == "Simple Package"
        assert fetcher._name_to_display("pkg_with_underscores") == "Pkg With Underscores"


# ═══════════════════════════════════════════════════════════════
# Integration Tests (In-Memory)
# ═══════════════════════════════════════════════════════════════


class TestMarketplaceIntegration:
    """Integration tests using in-memory repositories."""

    @pytest.mark.asyncio
    async def test_full_install_workflow(self):
        """Test complete installation workflow."""
        # Create real in-memory repository
        repo = PackageRepository(db_pool=None)

        # Create package
        package = await repo.create_package(
            {
                "name": "@test/mcp-server",
                "display_name": "Test MCP Server",
                "description": "A test server",
                "latest_version": "1.0.0",
            }
        )

        # Create version
        version = await repo.create_version(
            {
                "package_id": package["id"],
                "version": "1.0.0",
                "version_major": 1,
                "version_minor": 0,
                "version_patch": 0,
                "mcp_config": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@test/mcp-server"],
                },
            }
        )

        # Create install manager without external deps
        manager = InstallManager(
            repository=repo,
            aggregator=None,
            skill_service=None,
        )

        # Install
        result = await manager.install(
            package=package,
            version=version,
            user_config={},
            user_id="test-user",
        )

        assert result.success is True
        assert result.package_name == "@test/mcp-server"

        # Verify installation record
        installation = await repo.get_installation(
            package_id=package["id"],
            user_id="test-user",
        )
        assert installation is not None
        assert installation["status"] == InstallStatus.INSTALLED.value

    @pytest.mark.asyncio
    async def test_search_packages(self):
        """Test package search."""
        repo = PackageRepository(db_pool=None)

        # Create multiple packages
        await repo.create_package(
            {
                "name": "@anthropic/filesystem",
                "description": "Filesystem access",
                "tags": ["filesystem", "io"],
            }
        )
        await repo.create_package(
            {
                "name": "@anthropic/database",
                "description": "Database access",
                "tags": ["database", "sql"],
            }
        )
        await repo.create_package(
            {
                "name": "@other/tool",
                "description": "Other tool",
                "tags": ["utility"],
            }
        )

        # Search - returns dict with 'packages' key
        results = await repo.search_packages(query="anthropic")

        assert results["total"] == 2
        packages = results["packages"]
        assert len(packages) == 2
        names = [r["name"] for r in packages]
        assert "@anthropic/filesystem" in names
        assert "@anthropic/database" in names
