"""
Live integration tests for MarketplaceService.

Tests actual registry fetching from npm and GitHub.
Run with: python -m pytest tests/integration/test_marketplace_live.py -v -s

Note: These tests require network access and may be slow.
"""
import pytest
import asyncio
import logging

from services.marketplace_service.package_repository import PackageRepository
from services.marketplace_service.registry_fetcher import RegistryFetcher
from services.marketplace_service.package_resolver import PackageResolver
from services.marketplace_service.install_manager import InstallManager
from services.marketplace_service.marketplace_service import MarketplaceService
from tests.contracts.marketplace import PackageSpec, RegistrySource

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestNpmRegistryFetcher:
    """Test real npm registry fetching."""

    @pytest.mark.asyncio
    async def test_search_mcp_packages(self):
        """Search npm for real MCP packages."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)

        try:
            packages = await fetcher.search_npm("mcp server", limit=10)

            logger.info(f"Found {len(packages)} MCP packages on npm")
            for pkg in packages[:5]:
                logger.info(f"  - {pkg['name']}: {pkg.get('description', 'N/A')[:50]}")

            # Should find at least some MCP packages
            assert len(packages) > 0, "Should find MCP packages on npm"

            # All should have mcp-related data
            for pkg in packages:
                assert pkg["registry_source"] == RegistrySource.NPM.value
                assert pkg["name"]

        finally:
            await fetcher.close()

    @pytest.mark.asyncio
    async def test_fetch_specific_package(self):
        """Fetch a specific MCP package from npm."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)

        try:
            # Try to fetch a known MCP package (using actual npm package)
            package = await fetcher.fetch_package("mcp-filesystem-server")

            if package:
                logger.info(f"Fetched package: {package['name']}")
                logger.info(f"  Description: {package.get('description', 'N/A')}")
                logger.info(f"  Latest version: {package.get('latest_version', 'N/A')}")
                logger.info(f"  Versions: {len(package.get('versions', []))}")

                assert package["name"] == "mcp-filesystem-server"
                assert package.get("versions"), "Should have versions"

                # Check MCP config extraction
                if package.get("mcp_config"):
                    logger.info(f"  MCP Config: {package['mcp_config']}")
            else:
                logger.warning("Package not found - may not exist on npm")

        finally:
            await fetcher.close()

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_package(self):
        """Test fetching a package that doesn't exist."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)

        try:
            package = await fetcher.fetch_package("nonexistent-mcp-package-12345")
            assert package is None, "Should return None for non-existent package"

        finally:
            await fetcher.close()


class TestGitHubRegistryFetcher:
    """Test real GitHub registry fetching."""

    @pytest.mark.asyncio
    async def test_search_github_mcp_repos(self):
        """Search GitHub for MCP repositories."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)

        try:
            packages = await fetcher.search_github("mcp server", limit=10)

            logger.info(f"Found {len(packages)} MCP repos on GitHub")
            for pkg in packages[:5]:
                logger.info(f"  - {pkg['name']}: ⭐{pkg.get('star_count', 0)}")

            # May or may not find packages depending on GitHub rate limits
            if packages:
                for pkg in packages:
                    assert pkg["registry_source"] == RegistrySource.GITHUB.value
                    assert pkg["name"]

        finally:
            await fetcher.close()


class TestPackageResolverLive:
    """Test package resolution with real data."""

    @pytest.mark.asyncio
    async def test_resolve_from_npm(self):
        """Resolve a package from npm."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)
        resolver = PackageResolver(repository=repo, fetcher=fetcher)

        try:
            spec = PackageSpec(name="mcp-filesystem-server")
            result = await resolver.resolve(spec)

            if result:
                package, version = result
                logger.info(f"Resolved: {package['name']}@{version['version']}")
                logger.info(f"  MCP config: {version.get('mcp_config', {})}")

                assert package["name"] == spec.name
                assert version["version"]
            else:
                logger.warning("Could not resolve package")

        finally:
            await fetcher.close()


class TestMarketplaceServiceLive:
    """Test MarketplaceService with real registries."""

    @pytest.mark.asyncio
    async def test_search_marketplace(self):
        """Search marketplace for packages."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)
        resolver = PackageResolver(repository=repo, fetcher=fetcher)
        installer = InstallManager(repository=repo, aggregator=None)

        from services.marketplace_service.update_manager import UpdateManager
        updater = UpdateManager(repository=repo, resolver=resolver, installer=installer)

        service = MarketplaceService(
            package_repository=repo,
            registry_fetcher=fetcher,
            package_resolver=resolver,
            install_manager=installer,
            update_manager=updater,
        )

        try:
            results = await service.search("filesystem")

            logger.info(f"Search results: {results.get('total', 0)} packages")
            for pkg in results.get("packages", [])[:5]:
                logger.info(f"  - {pkg['name']}")

        finally:
            await fetcher.close()

    @pytest.mark.asyncio
    async def test_sync_registries(self):
        """Test registry synchronization."""
        repo = PackageRepository(db_pool=None)
        fetcher = RegistryFetcher(repository=repo)

        try:
            results = await fetcher.sync_registries(
                registries=[RegistrySource.NPM],
                force_full=False,
            )

            logger.info(f"Sync results:")
            logger.info(f"  Discovered: {results['packages_discovered']}")
            logger.info(f"  Updated: {results['packages_updated']}")
            logger.info(f"  Errors: {len(results['errors'])}")
            logger.info(f"  Duration: {results['duration_ms']}ms")

            # Should sync some packages
            total = results["packages_discovered"] + results["packages_updated"]
            assert total > 0 or len(results["errors"]) > 0, "Should have synced or errored"

        finally:
            await fetcher.close()


# ═══════════════════════════════════════════════════════════════
# Manual Test Runner
# ═══════════════════════════════════════════════════════════════

async def run_manual_tests():
    """Run tests manually for debugging."""
    print("\n" + "="*60)
    print("MARKETPLACE SERVICE LIVE TESTS")
    print("="*60 + "\n")

    # Test 1: Search npm
    print("1. Searching npm for MCP packages...")
    repo = PackageRepository(db_pool=None)
    fetcher = RegistryFetcher(repository=repo)

    try:
        packages = await fetcher.search_npm("mcp server", limit=10)
        print(f"   Found {len(packages)} packages")
        for pkg in packages[:3]:
            print(f"   - {pkg['name']}")
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        await fetcher.close()

    # Test 2: Fetch specific package
    print("\n2. Fetching mcp-filesystem-server...")
    fetcher = RegistryFetcher(repository=repo)

    try:
        package = await fetcher.fetch_package("mcp-filesystem-server")
        if package:
            print(f"   Name: {package['name']}")
            print(f"   Description: {package.get('description', 'N/A')[:60]}...")
            print(f"   Latest: {package.get('latest_version')}")
            print(f"   Versions: {len(package.get('versions', []))}")
        else:
            print("   Package not found")
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        await fetcher.close()

    # Test 3: Resolve package
    print("\n3. Resolving package version...")
    fetcher = RegistryFetcher(repository=repo)
    resolver = PackageResolver(repository=repo, fetcher=fetcher)

    try:
        spec = PackageSpec(name="mcp-filesystem-server")
        result = await resolver.resolve(spec)
        if result:
            pkg, ver = result
            print(f"   Resolved: {pkg['name']}@{ver['version']}")
            print(f"   MCP Config: {ver.get('mcp_config', {})}")
        else:
            print("   Could not resolve")
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        await fetcher.close()

    # Test 4: In-memory installation
    print("\n4. Testing in-memory installation flow...")
    fetcher = RegistryFetcher(repository=repo)
    resolver = PackageResolver(repository=repo, fetcher=fetcher)
    installer = InstallManager(repository=repo, aggregator=None)

    try:
        spec = PackageSpec(name="mcp-filesystem-server")
        result = await resolver.resolve(spec)
        if result:
            pkg, ver = result
            install_result = await installer.install(
                package=pkg,
                version=ver,
                user_config={},
                user_id="test-user",
            )
            print(f"   Success: {install_result.success}")
            print(f"   Package: {install_result.package_name}")
            print(f"   Version: {install_result.version}")
            print(f"   Server ID: {install_result.server_id or 'None (no aggregator)'}")
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        await fetcher.close()

    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_manual_tests())
