"""
Update Manager - Manages package updates and version upgrades.

Handles:
- Update availability checking
- Version upgrades
- Rollback on failure
"""

from typing import Any, Dict, List, Optional
import logging

from .domain import InstallStatus, UpdateChannel, InstallResult, UpdateInfo, PackageSpec

logger = logging.getLogger(__name__)


class UpdateManager:
    """
    Manages package update workflow.

    Coordinates:
    - Update availability checking
    - Version resolution for updates
    - Safe update with rollback capability
    """

    def __init__(
        self,
        repository,
        resolver,
        installer,
    ):
        """
        Initialize UpdateManager.

        Args:
            repository: PackageRepository for database operations
            resolver: PackageResolver for version resolution
            installer: InstallManager for installation operations
        """
        self._repo = repository
        self._resolver = resolver
        self._installer = installer

    async def check_updates(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check for available updates for installed packages.

        Args:
            user_id: User ID
            org_id: Organization ID

        Returns:
            List of packages with available updates
        """
        updates = []

        # Get all installations
        installations = await self._repo.list_installations(
            user_id=user_id,
            org_id=org_id,
        )

        for inst in installations:
            # Skip if pinned or not installed
            if inst.get("pinned_version") or inst.get("status") != InstallStatus.INSTALLED.value:
                continue

            # Get package info
            package = await self._repo.get_package(inst["package_id"])
            if not package:
                continue

            # Get current version
            current_version = inst.get("version")
            latest_version = package.get("latest_version")

            # Check if update available
            if latest_version and latest_version != current_version:
                # Parse versions to compare
                if self._is_newer_version(latest_version, current_version):
                    updates.append(
                        {
                            "package_id": package["id"],
                            "package_name": package["name"],
                            "display_name": package.get("display_name", package["name"]),
                            "current_version": current_version,
                            "latest_version": latest_version,
                            "update_channel": inst.get(
                                "update_channel", UpdateChannel.STABLE.value
                            ),
                            "installation_id": inst["id"],
                        }
                    )

        logger.info(f"Found {len(updates)} packages with updates available")
        return updates

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
        logger.info(f"Updating package: {package_name} to {target_version or 'latest'}")

        # Get package
        package = await self._repo.get_package_by_name(package_name)
        if not package:
            return InstallResult(
                success=False,
                package_id="",
                package_name=package_name,
                version="",
                error=f"Package not found: {package_name}",
            )

        # Get current installation
        installation = await self._repo.get_installation(
            package_id=package["id"],
            user_id=user_id,
            org_id=org_id,
        )
        if not installation:
            return InstallResult(
                success=False,
                package_id=package["id"],
                package_name=package_name,
                version="",
                error=f"Package not installed: {package_name}",
            )

        # Store current state for rollback
        previous_version_id = installation["version_id"]
        previous_status = installation["status"]

        try:
            # Update status
            await self._repo.update_installation_status(
                installation["id"],
                InstallStatus.UPDATING,
            )

            # Resolve target version
            spec = PackageSpec(name=package_name, version=target_version)
            resolved = await self._resolver.resolve(spec)
            if not resolved:
                raise ValueError(f"Could not resolve version: {target_version or 'latest'}")

            _, new_version = resolved

            # Check if already at target version
            if new_version["id"] == previous_version_id:
                await self._repo.update_installation_status(
                    installation["id"],
                    InstallStatus.INSTALLED,
                )
                return InstallResult(
                    success=True,
                    package_id=package["id"],
                    package_name=package_name,
                    version=new_version["version"],
                    error="Already at target version",
                )

            # Prepare new config
            user_config = installation.get("install_config", {})
            await self._installer.prepare_config(
                new_version.get("mcp_config", {}),
                user_config,
            )

            # Update the server configuration if aggregator available
            if installation.get("server_id") and self._installer._aggregator:
                try:
                    # Disconnect old version
                    await self._installer._aggregator.disconnect_server(installation["server_id"])

                    # The aggregator should reconnect with new config
                    # For now, we just reconnect
                    await self._installer._aggregator.connect_server(installation["server_id"])

                except Exception as e:
                    logger.warning(f"Server update failed, may need manual reconnect: {e}")

            # Update installation record
            if self._repo._db_pool:
                async with self._repo._db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE mcp.installed_packages
                        SET version_id = $1, status = $2, updated_at = NOW()
                        WHERE id = $3
                        """,
                        new_version["id"],
                        InstallStatus.INSTALLED.value,
                        installation["id"],
                    )
            else:
                self._repo._installations[installation["id"]]["version_id"] = new_version["id"]
                self._repo._installations[installation["id"]][
                    "status"
                ] = InstallStatus.INSTALLED.value

            # Refresh tool discovery
            tools_discovered = await self._installer.refresh_tools(
                {
                    **installation,
                    "package_name": package_name,
                }
            )

            logger.info(f"Updated {package_name} to {new_version['version']}")

            return InstallResult(
                success=True,
                package_id=package["id"],
                package_name=package_name,
                version=new_version["version"],
                server_id=installation.get("server_id"),
                tools_discovered=tools_discovered,
            )

        except Exception as e:
            logger.error(f"Update failed: {e}")

            # Attempt rollback
            try:
                await self._repo.update_installation_status(
                    installation["id"],
                    InstallStatus(previous_status) if previous_status else InstallStatus.ERROR,
                    error_message=f"Update failed: {e}",
                )
            except Exception:
                pass

            return InstallResult(
                success=False,
                package_id=package["id"],
                package_name=package_name,
                version="",
                error=str(e),
            )

    async def update_all(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[InstallResult]:
        """
        Update all packages with available updates.

        Args:
            user_id: User ID
            org_id: Organization ID

        Returns:
            List of update results
        """
        updates = await self.check_updates(user_id=user_id, org_id=org_id)

        results = []
        for update in updates:
            result = await self.update_package(
                package_name=update["package_name"],
                target_version=update["latest_version"],
                user_id=user_id,
                org_id=org_id,
            )
            results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Updated {successful}/{len(results)} packages")

        return results

    def _is_newer_version(self, new: str, old: str) -> bool:
        """
        Check if new version is newer than old.

        Simple semver comparison.
        """
        try:
            new_parts = self._parse_version(new)
            old_parts = self._parse_version(old)
            return new_parts > old_parts
        except Exception:
            return new != old

    def _parse_version(self, version: str) -> tuple:
        """Parse version string to comparable tuple."""

        # Remove prerelease suffix for comparison
        base = version.split("-")[0]
        parts = base.split(".")

        result = []
        for part in parts[:3]:
            try:
                result.append(int(part))
            except ValueError:
                result.append(0)

        while len(result) < 3:
            result.append(0)

        return tuple(result)

    async def get_update_info(
        self,
        package_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Optional[UpdateInfo]:
        """
        Get detailed update information for a package.

        Args:
            package_name: Package name
            user_id: User ID
            org_id: Organization ID

        Returns:
            Update info or None if no update available
        """
        package = await self._repo.get_package_by_name(package_name)
        if not package:
            return None

        installation = await self._repo.get_installation(
            package_id=package["id"],
            user_id=user_id,
            org_id=org_id,
        )
        if not installation:
            return None

        current_version = installation.get("version")
        latest_version = package.get("latest_version")

        if not latest_version or latest_version == current_version:
            return None

        if not self._is_newer_version(latest_version, current_version):
            return None

        # Get changelog for latest version
        latest_version_record = await self._repo.get_version(
            package["id"],
            latest_version,
        )

        # Check for breaking changes (major version bump)
        current_major = self._parse_version(current_version)[0]
        latest_major = self._parse_version(latest_version)[0]
        breaking_changes = latest_major > current_major

        return UpdateInfo(
            package_id=package["id"],
            package_name=package["name"],
            current_version=current_version,
            latest_version=latest_version,
            update_channel=UpdateChannel(
                installation.get("update_channel", UpdateChannel.STABLE.value)
            ),
            changelog=latest_version_record.get("changelog") if latest_version_record else None,
            breaking_changes=breaking_changes,
        )
