"""
Package Resolver - Resolves package versions and dependencies.

Handles:
- Version resolution (semver, ranges, latest)
- Package lookup across registries
- Dependency resolution
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import re

from .domain import PackageSpec, RegistrySource

logger = logging.getLogger(__name__)


class PackageResolver:
    """
    Resolves package specifications to concrete packages and versions.
    """

    def __init__(self, repository, fetcher):
        """
        Initialize PackageResolver.

        Args:
            repository: PackageRepository for database lookups
            fetcher: RegistryFetcher for remote lookups
        """
        self._repo = repository
        self._fetcher = fetcher

    async def resolve(
        self,
        spec: PackageSpec,
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Resolve a package specification to package and version.

        Args:
            spec: Package specification with name and optional version

        Returns:
            Tuple of (package, version) or None if not found
        """
        logger.debug(f"Resolving package: {spec.name}@{spec.version or 'latest'}")

        # Step 1: Find the package
        package = await self._find_package(spec.name, spec.registry)
        if not package:
            logger.warning(f"Package not found: {spec.name}")
            return None

        # Step 2: Resolve version
        version = await self._resolve_version(package, spec.version)
        if not version:
            logger.warning(f"Version not found for {spec.name}: {spec.version}")
            return None

        logger.debug(f"Resolved {spec.name} to version {version['version']}")
        return package, version

    async def _find_package(
        self,
        name: str,
        registry: Optional[RegistrySource] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find package by name, searching local cache and registries."""
        # Check local cache first
        package = await self._repo.get_package_by_name(name)
        if package:
            return package

        # Try to fetch from registries
        package = await self._fetcher.fetch_package(name)
        if package:
            # Store in cache
            await self._repo.upsert_package(package)

            # Also store versions if available
            if "versions" in package:
                for version_data in package["versions"]:
                    version_data["package_id"] = package.get("id") or (
                        await self._repo.get_package_by_name(name)
                    ).get("id")
                    await self._repo.create_version(version_data)

            return await self._repo.get_package_by_name(name)

        return None

    async def _resolve_version(
        self,
        package: Dict[str, Any],
        version_spec: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve version specification to concrete version.

        Supports:
        - None or "latest" -> latest stable version
        - Exact version: "1.2.3"
        - Semver range: "^1.2.0", "~1.2.0", ">=1.0.0"
        """
        package_id = package["id"]

        # Get all available versions
        versions = await self._repo.get_package_versions(package_id)

        if not versions:
            # Try to fetch from registry
            full_package = await self._fetcher.fetch_package(package["name"])
            if full_package and "versions" in full_package:
                for v in full_package["versions"]:
                    v["package_id"] = package_id
                    await self._repo.create_version(v)
                versions = await self._repo.get_package_versions(package_id)

        if not versions:
            # Create a default version from latest_version
            if package.get("latest_version"):
                major, minor, patch, prerelease = self._parse_semver(package["latest_version"])
                version = await self._repo.create_version(
                    {
                        "package_id": package_id,
                        "version": package["latest_version"],
                        "version_major": major,
                        "version_minor": minor,
                        "version_patch": patch,
                        "prerelease": prerelease,
                        "mcp_config": package.get(
                            "mcp_config",
                            {
                                "transport": "stdio",
                                "command": "npx",
                                "args": ["-y", package["name"]],
                            },
                        ),
                        "published_at": package.get("created_at"),
                    }
                )
                return version
            return None

        # Resolve version spec
        if not version_spec or version_spec == "latest":
            # Return latest stable version
            stable = [v for v in versions if not v.get("prerelease")]
            return stable[0] if stable else versions[0]

        # Exact version match
        exact = [v for v in versions if v["version"] == version_spec]
        if exact:
            return exact[0]

        # Semver range matching
        return self._match_semver_range(versions, version_spec)

    def _match_semver_range(
        self,
        versions: List[Dict[str, Any]],
        range_spec: str,
    ) -> Optional[Dict[str, Any]]:
        """Match versions against semver range specification."""
        # Parse range spec
        if range_spec.startswith("^"):
            # Caret: Compatible with version (major must match)
            target = range_spec[1:]
            major, minor, patch, _ = self._parse_semver(target)

            matching = [
                v
                for v in versions
                if v["version_major"] == major
                and (v["version_minor"], v["version_patch"]) >= (minor, patch)
                and not v.get("prerelease")
            ]

        elif range_spec.startswith("~"):
            # Tilde: Approximately equivalent (major.minor must match)
            target = range_spec[1:]
            major, minor, patch, _ = self._parse_semver(target)

            matching = [
                v
                for v in versions
                if v["version_major"] == major
                and v["version_minor"] == minor
                and v["version_patch"] >= patch
                and not v.get("prerelease")
            ]

        elif range_spec.startswith(">="):
            # Greater than or equal
            target = range_spec[2:]
            major, minor, patch, _ = self._parse_semver(target)

            matching = [
                v
                for v in versions
                if (v["version_major"], v["version_minor"], v["version_patch"])
                >= (major, minor, patch)
                and not v.get("prerelease")
            ]

        elif range_spec.startswith(">"):
            # Greater than
            target = range_spec[1:]
            major, minor, patch, _ = self._parse_semver(target)

            matching = [
                v
                for v in versions
                if (v["version_major"], v["version_minor"], v["version_patch"])
                > (major, minor, patch)
                and not v.get("prerelease")
            ]

        else:
            # No special prefix, try exact match
            matching = [v for v in versions if v["version"] == range_spec]

        if matching:
            # Return highest matching version
            matching.sort(
                key=lambda v: (v["version_major"], v["version_minor"], v["version_patch"]),
                reverse=True,
            )
            return matching[0]

        return None

    def _parse_semver(self, version: str) -> Tuple[int, int, int, Optional[str]]:
        """Parse semver string into components."""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version)
        if not match:
            parts = version.split(".")
            major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch_str = parts[2].split("-")[0] if len(parts) > 2 else "0"
            patch = int(patch_str) if patch_str.isdigit() else 0
            return major, minor, patch, None

        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            match.group(4),
        )

    async def check_compatibility(
        self,
        package: Dict[str, Any],
        version: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check version compatibility and requirements.

        Returns:
            Compatibility info with missing requirements
        """
        result = {
            "compatible": True,
            "missing_env_vars": [],
            "missing_dependencies": [],
            "warnings": [],
        }

        # Check required env vars
        required_env_vars = version.get("required_env_vars", [])
        if required_env_vars:
            result["missing_env_vars"] = required_env_vars
            result["warnings"].append(
                f"This package requires environment variables: {', '.join(required_env_vars)}"
            )

        # Check MCP version compatibility
        min_mcp = version.get("min_mcp_version")
        if min_mcp:
            result["warnings"].append(f"This package requires MCP version >= {min_mcp}")

        return result
