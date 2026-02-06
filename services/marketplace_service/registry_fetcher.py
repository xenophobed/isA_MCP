"""
Registry Fetcher - Fetches packages from multiple registry sources.

Supports:
- npm registry (MCP packages with mcp-server keyword)
- GitHub releases
- isA Cloud registry (future)
- Private enterprise registries
"""
import aiohttp
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
import re

from tests.contracts.marketplace import RegistrySource

logger = logging.getLogger(__name__)


class RegistryFetcher:
    """
    Fetches and normalizes package data from multiple registries.
    """

    # npm registry endpoints
    NPM_SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
    NPM_PACKAGE_URL = "https://registry.npmjs.org"

    # GitHub API
    GITHUB_API_URL = "https://api.github.com"

    # MCP-related keywords to filter npm packages
    MCP_KEYWORDS = {"mcp-server", "model-context-protocol", "anthropic-mcp", "mcp"}

    def __init__(
        self,
        repository,
        http_timeout: int = 30,
        cache_ttl: int = 3600,
    ):
        """
        Initialize RegistryFetcher.

        Args:
            repository: PackageRepository for storing results
            http_timeout: HTTP request timeout in seconds
            cache_ttl: Cache TTL in seconds
        """
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

        Filters by mcp-server keyword to find relevant packages.
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

                logger.debug(f"npm search for '{query}' returned {len(packages)} packages")
                return packages

        except Exception as e:
            logger.error(f"npm search error: {e}")
            return []

    async def fetch_package(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed package info from npm.

        Note: Direct fetches skip keyword filtering since user explicitly
        requested this package. Search results are still filtered.
        """
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
                # Skip keyword filter for direct fetches - user explicitly requested this package
                return self._normalize_npm_full_package(data, skip_keyword_filter=True)

        except Exception as e:
            logger.error(f"npm fetch error for {name}: {e}")
            return None

    def _normalize_npm_package(
        self,
        pkg: Dict[str, Any],
        skip_keyword_filter: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Normalize npm package to our format."""
        keywords = pkg.get("keywords", []) or []

        # Filter: must have MCP-related keywords (unless skipped for direct fetches)
        if not skip_keyword_filter:
            if not any(kw.lower() in self.MCP_KEYWORDS for kw in keywords):
                return None

        author = pkg.get("author")
        if isinstance(author, dict):
            author = author.get("name")

        return {
            "name": pkg["name"],
            "display_name": self._name_to_display(pkg["name"]),
            "description": pkg.get("description", ""),
            "author": author,
            "homepage_url": pkg.get("homepage"),
            "repository_url": self._extract_repo_url(pkg.get("repository")),
            "license": pkg.get("license"),
            "tags": [kw for kw in keywords if kw.lower() not in self.MCP_KEYWORDS],
            "registry_source": RegistrySource.NPM.value,
            "registry_url": f"https://www.npmjs.com/package/{pkg['name']}",
            "latest_version": pkg.get("version"),
        }

    def _normalize_npm_full_package(
        self,
        data: Dict[str, Any],
        skip_keyword_filter: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Normalize full npm package with versions."""
        latest_version = data.get("dist-tags", {}).get("latest")
        latest_data = data.get("versions", {}).get(latest_version, {})

        package = self._normalize_npm_package(latest_data, skip_keyword_filter=skip_keyword_filter)
        if not package:
            return None

        # Extract MCP config
        mcp_config = self._extract_mcp_config(latest_data)

        # Build versions list
        versions = []
        for version, version_data in data.get("versions", {}).items():
            major, minor, patch, prerelease = self._parse_semver(version)
            versions.append({
                "version": version,
                "version_major": major,
                "version_minor": minor,
                "version_patch": patch,
                "prerelease": prerelease,
                "mcp_config": self._extract_mcp_config(version_data),
                "published_at": data.get("time", {}).get(version),
            })

        package["versions"] = versions
        package["mcp_config"] = mcp_config

        return package

    def _extract_mcp_config(self, pkg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract MCP server configuration from npm package.

        Looks for:
        1. Explicit mcp field in package.json
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

                logger.debug(f"GitHub search for '{query}' returned {len(packages)} packages")
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
            "registry_source": RegistrySource.GITHUB.value,
            "registry_url": repo["html_url"],
            "star_count": repo["stargazers_count"],
        }

    # =========================================================================
    # Registry Sync
    # =========================================================================

    async def sync_registries(
        self,
        registries: Optional[List[RegistrySource]] = None,
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

        registry_values = registries or [RegistrySource.NPM, RegistrySource.GITHUB]

        # Sync npm
        if RegistrySource.NPM in registry_values:
            try:
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
        if RegistrySource.GITHUB in registry_values:
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

        logger.info(
            f"Registry sync complete: "
            f"{results['packages_discovered']} discovered, "
            f"{results['packages_updated']} updated, "
            f"{len(results['errors'])} errors"
        )

        return results

    async def search_registries(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search all registries and return combined results."""
        tasks = [
            self.search_npm(query),
            self.search_github(query),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        packages = []
        for result in results:
            if isinstance(result, list):
                packages.extend(result)

        return packages

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _name_to_display(self, name: str) -> str:
        """Convert package name to display name."""
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
            if url.startswith("git+"):
                url = url[4:]
            if url.endswith(".git"):
                url = url[:-4]
            return url
        return None

    def _parse_semver(self, version: str) -> tuple:
        """Parse semver string into components."""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version)
        if not match:
            parts = version.split('.')
            major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch_str = parts[2].split('-')[0] if len(parts) > 2 else "0"
            patch = int(patch_str) if patch_str.isdigit() else 0
            return major, minor, patch, None

        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            match.group(4),
        )
