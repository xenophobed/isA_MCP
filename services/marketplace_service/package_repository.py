"""
Package Repository - Data access layer for marketplace tables.

Manages CRUD operations for:
- marketplace_packages
- package_versions
- installed_packages
- package_tool_mappings
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from tests.contracts.marketplace import (
    RegistrySource,
    InstallStatus,
    UpdateChannel,
)

logger = logging.getLogger(__name__)


class PackageRepository:
    """
    Data access layer for marketplace tables.

    Provides CRUD operations with both PostgreSQL and in-memory fallback.
    """

    def __init__(self, db_pool=None):
        """
        Initialize PackageRepository.

        Args:
            db_pool: asyncpg connection pool (optional, uses in-memory if None)
        """
        self._db_pool = db_pool

        # In-memory fallback
        self._packages: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, Dict[str, Any]] = {}
        self._installations: Dict[str, Dict[str, Any]] = {}
        self._tool_mappings: Dict[str, List[Dict[str, Any]]] = {}

    # =========================================================================
    # Package Operations
    # =========================================================================

    async def create_package(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new package record."""
        package_id = data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        package = {
            "id": package_id,
            "name": data["name"],
            "display_name": data.get("display_name") or data["name"],
            "description": data.get("description"),
            "author": data.get("author"),
            "author_email": data.get("author_email"),
            "homepage_url": data.get("homepage_url"),
            "repository_url": data.get("repository_url"),
            "documentation_url": data.get("documentation_url"),
            "license": data.get("license"),
            "category": data.get("category"),
            "tags": data.get("tags", []),
            "registry_source": data.get("registry_source", RegistrySource.NPM.value),
            "registry_url": data.get("registry_url"),
            "download_count": data.get("download_count", 0),
            "weekly_downloads": data.get("weekly_downloads", 0),
            "star_count": data.get("star_count", 0),
            "verified": data.get("verified", False),
            "official": data.get("official", False),
            "security_score": data.get("security_score"),
            "latest_version": data.get("latest_version"),
            "latest_version_id": data.get("latest_version_id"),
            "deprecated": data.get("deprecated", False),
            "deprecation_message": data.get("deprecation_message"),
            "created_at": now,
            "updated_at": now,
            "last_synced_at": now,
        }

        if self._db_pool:
            await self._insert_package_db(package)
        else:
            self._packages[package_id] = package

        logger.debug(f"Created package: {package['name']} ({package_id})")
        return package

    async def _insert_package_db(self, package: Dict[str, Any]) -> None:
        """Insert package into database."""
        async with self._db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp.marketplace_packages (
                    id, name, display_name, description, author, author_email,
                    homepage_url, repository_url, documentation_url, license,
                    category, tags, registry_source, registry_url,
                    download_count, weekly_downloads, star_count,
                    verified, official, security_score,
                    latest_version, latest_version_id,
                    deprecated, deprecation_message,
                    created_at, updated_at, last_synced_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26, $27
                )
                """,
                package["id"],
                package["name"],
                package["display_name"],
                package["description"],
                package["author"],
                package["author_email"],
                package["homepage_url"],
                package["repository_url"],
                package["documentation_url"],
                package["license"],
                package["category"],
                package["tags"],
                package["registry_source"],
                package["registry_url"],
                package["download_count"],
                package["weekly_downloads"],
                package["star_count"],
                package["verified"],
                package["official"],
                package["security_score"],
                package["latest_version"],
                package["latest_version_id"],
                package["deprecated"],
                package["deprecation_message"],
                package["created_at"],
                package["updated_at"],
                package["last_synced_at"],
            )

    async def get_package(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Get package by ID."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM mcp.marketplace_packages WHERE id = $1",
                    package_id
                )
                return dict(row) if row else None
        return self._packages.get(package_id)

    async def get_package_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get package by name."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM mcp.marketplace_packages WHERE name = $1",
                    name
                )
                return dict(row) if row else None

        for pkg in self._packages.values():
            if pkg["name"] == name:
                return pkg
        return None

    async def update_package(
        self,
        package_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update package fields."""
        if self._db_pool:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_idx = 1

            allowed_fields = {
                "display_name", "description", "author", "author_email",
                "homepage_url", "repository_url", "documentation_url",
                "license", "category", "tags", "registry_url",
                "download_count", "weekly_downloads", "star_count",
                "verified", "official", "security_score",
                "latest_version", "latest_version_id",
                "deprecated", "deprecation_message", "last_synced_at"
            }

            for key, value in data.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ${param_idx}")
                    values.append(value)
                    param_idx += 1

            if not set_clauses:
                return await self.get_package(package_id)

            values.append(package_id)
            query = f"""
                UPDATE mcp.marketplace_packages
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE id = ${param_idx}
                RETURNING *
            """

            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(query, *values)
                return dict(row) if row else None
        else:
            if package_id not in self._packages:
                return None
            self._packages[package_id].update(data)
            self._packages[package_id]["updated_at"] = datetime.now(timezone.utc)
            return self._packages[package_id]

    async def upsert_package(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update package."""
        existing = await self.get_package_by_name(data["name"])
        if existing:
            return await self.update_package(existing["id"], data)
        return await self.create_package(data)

    async def search_packages(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        registry: Optional[str] = None,
        verified_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search packages with filters."""
        if self._db_pool:
            # Build query with full-text search
            conditions = ["deprecated = FALSE"]
            values = []
            param_idx = 1

            if query:
                conditions.append(f"""
                    to_tsvector('english', coalesce(name, '') || ' ' ||
                    coalesce(display_name, '') || ' ' ||
                    coalesce(description, '')) @@ plainto_tsquery('english', ${param_idx})
                """)
                values.append(query)
                param_idx += 1

            if category:
                conditions.append(f"category = ${param_idx}")
                values.append(category)
                param_idx += 1

            if tags:
                conditions.append(f"tags && ${param_idx}")
                values.append(tags)
                param_idx += 1

            if registry:
                conditions.append(f"registry_source = ${param_idx}")
                values.append(registry)
                param_idx += 1

            if verified_only:
                conditions.append("verified = TRUE")

            where_clause = " AND ".join(conditions)

            async with self._db_pool.acquire() as conn:
                # Get total count
                count_query = f"""
                    SELECT COUNT(*) FROM mcp.marketplace_packages
                    WHERE {where_clause}
                """
                total = await conn.fetchval(count_query, *values)

                # Get packages
                search_query = f"""
                    SELECT * FROM mcp.marketplace_packages
                    WHERE {where_clause}
                    ORDER BY download_count DESC, star_count DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """
                values.extend([limit, offset])
                rows = await conn.fetch(search_query, *values)

                return {
                    "total": total,
                    "packages": [dict(row) for row in rows],
                    "limit": limit,
                    "offset": offset,
                }
        else:
            # In-memory search
            results = []
            query_lower = query.lower()

            for pkg in self._packages.values():
                if pkg.get("deprecated"):
                    continue

                # Text match
                if query:
                    searchable = f"{pkg['name']} {pkg.get('display_name', '')} {pkg.get('description', '')}".lower()
                    if query_lower not in searchable:
                        continue

                # Category filter
                if category and pkg.get("category") != category:
                    continue

                # Tags filter
                if tags and not any(t in pkg.get("tags", []) for t in tags):
                    continue

                # Registry filter
                if registry and pkg.get("registry_source") != registry:
                    continue

                # Verified filter
                if verified_only and not pkg.get("verified"):
                    continue

                results.append(pkg)

            # Sort by popularity
            results.sort(key=lambda p: (p.get("download_count", 0), p.get("star_count", 0)), reverse=True)

            return {
                "total": len(results),
                "packages": results[offset:offset + limit],
                "limit": limit,
                "offset": offset,
            }

    async def increment_download_count(self, package_id: str) -> None:
        """Increment package download count."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE mcp.marketplace_packages
                    SET download_count = download_count + 1
                    WHERE id = $1
                    """,
                    package_id
                )
        elif package_id in self._packages:
            self._packages[package_id]["download_count"] += 1

    async def count_packages(self) -> int:
        """Count total packages."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM mcp.marketplace_packages WHERE deprecated = FALSE"
                )
        return len([p for p in self._packages.values() if not p.get("deprecated")])

    async def list_categories(self) -> List[Dict[str, Any]]:
        """List categories with package counts."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT category, COUNT(*) as count
                    FROM mcp.marketplace_packages
                    WHERE deprecated = FALSE AND category IS NOT NULL
                    GROUP BY category
                    ORDER BY count DESC
                    """
                )
                return [{"category": row["category"], "count": row["count"]} for row in rows]
        else:
            categories = {}
            for pkg in self._packages.values():
                if not pkg.get("deprecated") and pkg.get("category"):
                    categories[pkg["category"]] = categories.get(pkg["category"], 0) + 1
            return [{"category": k, "count": v} for k, v in sorted(categories.items(), key=lambda x: -x[1])]

    async def get_popular_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular packages."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM mcp.marketplace_packages
                    WHERE deprecated = FALSE
                    ORDER BY download_count DESC, star_count DESC
                    LIMIT $1
                    """,
                    limit
                )
                return [dict(row) for row in rows]
        else:
            packages = [p for p in self._packages.values() if not p.get("deprecated")]
            packages.sort(key=lambda p: (p.get("download_count", 0), p.get("star_count", 0)), reverse=True)
            return packages[:limit]

    async def get_curated_packages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get curated/featured packages."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT p.* FROM mcp.marketplace_packages p
                    JOIN mcp.featured_packages f ON p.id = f.package_id
                    WHERE f.is_active = TRUE
                      AND (f.featured_until IS NULL OR f.featured_until > NOW())
                    ORDER BY f.display_order
                    LIMIT $1
                    """,
                    limit
                )
                return [dict(row) for row in rows]
        return []

    # =========================================================================
    # Version Operations
    # =========================================================================

    async def create_version(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a package version."""
        version_id = data.get("id") or str(uuid.uuid4())

        version = {
            "id": version_id,
            "package_id": data["package_id"],
            "version": data["version"],
            "version_major": data.get("version_major", 0),
            "version_minor": data.get("version_minor", 0),
            "version_patch": data.get("version_patch", 0),
            "prerelease": data.get("prerelease"),
            "mcp_config": data.get("mcp_config", {}),
            "declared_tools": data.get("declared_tools", []),
            "tool_count": data.get("tool_count", 0),
            "min_mcp_version": data.get("min_mcp_version"),
            "required_env_vars": data.get("required_env_vars", []),
            "dependencies": data.get("dependencies", {}),
            "changelog": data.get("changelog"),
            "release_notes_url": data.get("release_notes_url"),
            "published_at": data.get("published_at") or datetime.now(timezone.utc),
            "published_by": data.get("published_by"),
            "deprecated": data.get("deprecated", False),
            "yanked": data.get("yanked", False),
            "created_at": datetime.now(timezone.utc),
        }

        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mcp.package_versions (
                        id, package_id, version,
                        version_major, version_minor, version_patch, prerelease,
                        mcp_config, declared_tools, tool_count,
                        min_mcp_version, required_env_vars, dependencies,
                        changelog, release_notes_url, published_at, published_by,
                        deprecated, yanked, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                    )
                    """,
                    version["id"],
                    version["package_id"],
                    version["version"],
                    version["version_major"],
                    version["version_minor"],
                    version["version_patch"],
                    version["prerelease"],
                    json.dumps(version["mcp_config"]),
                    json.dumps(version["declared_tools"]),
                    version["tool_count"],
                    version["min_mcp_version"],
                    version["required_env_vars"],
                    json.dumps(version["dependencies"]),
                    version["changelog"],
                    version["release_notes_url"],
                    version["published_at"],
                    version["published_by"],
                    version["deprecated"],
                    version["yanked"],
                    version["created_at"],
                )
        else:
            self._versions[version_id] = version

        return version

    async def get_package_versions(self, package_id: str) -> List[Dict[str, Any]]:
        """Get all versions for a package."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM mcp.package_versions
                    WHERE package_id = $1 AND yanked = FALSE
                    ORDER BY version_major DESC, version_minor DESC, version_patch DESC
                    """,
                    package_id
                )
                return [dict(row) for row in rows]
        return [v for v in self._versions.values() if v["package_id"] == package_id and not v.get("yanked")]

    async def get_latest_version(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Get latest stable version for a package."""
        versions = await self.get_package_versions(package_id)
        # Filter out prereleases for stable
        stable = [v for v in versions if not v.get("prerelease")]
        return stable[0] if stable else (versions[0] if versions else None)

    async def get_version(self, package_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Get specific version."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM mcp.package_versions
                    WHERE package_id = $1 AND version = $2
                    """,
                    package_id, version
                )
                return dict(row) if row else None
        for v in self._versions.values():
            if v["package_id"] == package_id and v["version"] == version:
                return v
        return None

    # =========================================================================
    # Installation Operations
    # =========================================================================

    async def create_installation(
        self,
        package_id: str,
        version_id: str,
        server_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        install_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create installation record."""
        installation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        installation = {
            "id": installation_id,
            "package_id": package_id,
            "version_id": version_id,
            "server_id": server_id,
            "user_id": user_id,
            "org_id": org_id,
            "team_id": None,
            "install_config": install_config or {},
            "env_overrides": {},
            "auto_update": True,
            "update_channel": UpdateChannel.STABLE.value,
            "pinned_version": False,
            "status": InstallStatus.INSTALLED.value,
            "error_message": None,
            "last_used_at": None,
            "use_count": 0,
            "installed_at": now,
            "updated_at": now,
            "last_sync_at": now,
        }

        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mcp.installed_packages (
                        id, package_id, version_id, server_id,
                        user_id, org_id, team_id,
                        install_config, env_overrides,
                        auto_update, update_channel, pinned_version,
                        status, error_message,
                        last_used_at, use_count,
                        installed_at, updated_at, last_sync_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9,
                        $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                    )
                    """,
                    installation["id"],
                    installation["package_id"],
                    installation["version_id"],
                    installation["server_id"],
                    installation["user_id"],
                    installation["org_id"],
                    installation["team_id"],
                    json.dumps(installation["install_config"]),
                    json.dumps(installation["env_overrides"]),
                    installation["auto_update"],
                    installation["update_channel"],
                    installation["pinned_version"],
                    installation["status"],
                    installation["error_message"],
                    installation["last_used_at"],
                    installation["use_count"],
                    installation["installed_at"],
                    installation["updated_at"],
                    installation["last_sync_at"],
                )
        else:
            self._installations[installation_id] = installation

        return installation

    async def get_installation(
        self,
        package_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get installation for package and user/org."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                if user_id:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM mcp.installed_packages
                        WHERE package_id = $1 AND user_id = $2
                        """,
                        package_id, user_id
                    )
                elif org_id:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM mcp.installed_packages
                        WHERE package_id = $1 AND org_id = $2 AND team_id IS NULL
                        """,
                        package_id, org_id
                    )
                else:
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM mcp.installed_packages
                        WHERE package_id = $1 AND user_id IS NULL AND org_id IS NULL
                        """,
                        package_id
                    )
                return dict(row) if row else None
        else:
            for inst in self._installations.values():
                if inst["package_id"] == package_id:
                    if user_id and inst.get("user_id") == user_id:
                        return inst
                    if org_id and inst.get("org_id") == org_id:
                        return inst
                    if not user_id and not org_id and not inst.get("user_id") and not inst.get("org_id"):
                        return inst
            return None

    async def get_installation_status(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Get simplified installation status."""
        inst = await self.get_installation(package_id)
        if inst:
            return {
                "installed": True,
                "status": inst["status"],
                "version": inst.get("version"),
            }
        return None

    async def list_installations(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List installations for user/org."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                if user_id:
                    rows = await conn.fetch(
                        """
                        SELECT i.*, p.name as package_name, p.display_name,
                               p.description, p.category, v.version
                        FROM mcp.installed_packages i
                        JOIN mcp.marketplace_packages p ON i.package_id = p.id
                        JOIN mcp.package_versions v ON i.version_id = v.id
                        WHERE i.user_id = $1
                        ORDER BY i.installed_at DESC
                        """,
                        user_id
                    )
                elif org_id:
                    rows = await conn.fetch(
                        """
                        SELECT i.*, p.name as package_name, p.display_name,
                               p.description, p.category, v.version
                        FROM mcp.installed_packages i
                        JOIN mcp.marketplace_packages p ON i.package_id = p.id
                        JOIN mcp.package_versions v ON i.version_id = v.id
                        WHERE i.org_id = $1
                        ORDER BY i.installed_at DESC
                        """,
                        org_id
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT i.*, p.name as package_name, p.display_name,
                               p.description, p.category, v.version
                        FROM mcp.installed_packages i
                        JOIN mcp.marketplace_packages p ON i.package_id = p.id
                        JOIN mcp.package_versions v ON i.version_id = v.id
                        ORDER BY i.installed_at DESC
                        """
                    )
                return [dict(row) for row in rows]
        return list(self._installations.values())

    async def update_installation_status(
        self,
        installation_id: str,
        status: InstallStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update installation status."""
        status_value = status.value if isinstance(status, InstallStatus) else status

        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE mcp.installed_packages
                    SET status = $1, error_message = $2, updated_at = NOW()
                    WHERE id = $3
                    """,
                    status_value, error_message, installation_id
                )
                return "UPDATE 1" in result
        elif installation_id in self._installations:
            self._installations[installation_id]["status"] = status_value
            self._installations[installation_id]["error_message"] = error_message
            return True
        return False

    async def delete_installation(self, installation_id: str) -> bool:
        """Delete installation record."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM mcp.installed_packages WHERE id = $1",
                    installation_id
                )
                return "DELETE 1" in result
        elif installation_id in self._installations:
            del self._installations[installation_id]
            return True
        return False

    async def count_installations(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> int:
        """Count installations."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                if user_id:
                    return await conn.fetchval(
                        "SELECT COUNT(*) FROM mcp.installed_packages WHERE user_id = $1",
                        user_id
                    )
                elif org_id:
                    return await conn.fetchval(
                        "SELECT COUNT(*) FROM mcp.installed_packages WHERE org_id = $1",
                        org_id
                    )
                return await conn.fetchval("SELECT COUNT(*) FROM mcp.installed_packages")
        return len(self._installations)

    # =========================================================================
    # Tool Mapping Operations
    # =========================================================================

    async def create_tool_mappings(
        self,
        installed_package_id: str,
        tools: List[Dict[str, Any]],
        package_name: str,
    ) -> None:
        """Create tool mappings for installed package."""
        for tool in tools:
            mapping = {
                "installed_package_id": installed_package_id,
                "tool_id": tool.get("id") or tool.get("tool_id"),
                "original_name": tool.get("name", ""),
                "namespaced_name": f"{package_name}:{tool.get('name', '')}",
                "skill_ids": tool.get("skill_ids", []),
                "primary_skill_id": tool.get("primary_skill_id"),
                "discovered_at": datetime.now(timezone.utc),
            }

            if self._db_pool:
                async with self._db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO mcp.package_tool_mappings (
                            installed_package_id, tool_id,
                            original_name, namespaced_name,
                            skill_ids, primary_skill_id, discovered_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (installed_package_id, tool_id) DO UPDATE
                        SET skill_ids = $5, primary_skill_id = $6
                        """,
                        mapping["installed_package_id"],
                        mapping["tool_id"],
                        mapping["original_name"],
                        mapping["namespaced_name"],
                        mapping["skill_ids"],
                        mapping["primary_skill_id"],
                        mapping["discovered_at"],
                    )
            else:
                if installed_package_id not in self._tool_mappings:
                    self._tool_mappings[installed_package_id] = []
                self._tool_mappings[installed_package_id].append(mapping)

    async def get_tool_mappings(self, installed_package_id: str) -> List[Dict[str, Any]]:
        """Get tool mappings for installed package."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM mcp.package_tool_mappings
                    WHERE installed_package_id = $1
                    """,
                    installed_package_id
                )
                return [dict(row) for row in rows]
        return self._tool_mappings.get(installed_package_id, [])

    async def delete_tool_mappings(self, installed_package_id: str) -> None:
        """Delete all tool mappings for installed package."""
        if self._db_pool:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM mcp.package_tool_mappings WHERE installed_package_id = $1",
                    installed_package_id
                )
        elif installed_package_id in self._tool_mappings:
            del self._tool_mappings[installed_package_id]
