"""
Server Registry - Data access layer for external MCP server registrations.

Manages server records in PostgreSQL with full CRUD operations.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from tests.contracts.aggregator.data_contract import (
    ServerTransportType,
    ServerStatus,
    ServerRecordContract,
)

logger = logging.getLogger(__name__)


class ServerRegistry:
    """
    Manages registration and lifecycle of external MCP servers.

    Provides data access operations for the mcp.external_servers table.
    """

    def __init__(self, db_pool=None, event_emitter=None):
        """
        Initialize ServerRegistry.

        Args:
            db_pool: Database connection pool (asyncpg pool or mock)
            event_emitter: Optional event emitter for status change notifications
        """
        self._db_pool = db_pool
        self._event_emitter = event_emitter
        # In-memory cache for fast lookups (used when db_pool is None)
        self._servers: Dict[str, Dict[str, Any]] = {}

    async def add(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new server to the registry.

        Args:
            config: Server configuration with name, transport_type, connection_config

        Returns:
            Created server record

        Raises:
            ValueError: If server name already exists
        """
        name = config["name"]

        # Check for duplicate name (scoped: global or within same org)
        existing = await self.get_by_name(name)
        if existing:
            # Allow same name in different orgs
            existing_org = existing.get("org_id")
            new_org = config.get("org_id")
            if existing_org == new_org or existing.get("is_global", True):
                raise ValueError(f"Server already exists: {name}")

        server_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Normalize transport_type to enum if string
        transport_type = config["transport_type"]
        if isinstance(transport_type, str):
            transport_type = ServerTransportType(transport_type)

        server = {
            "id": server_id,
            "name": name,
            "description": config.get("description"),
            "transport_type": transport_type,
            "connection_config": config["connection_config"],
            "health_check_url": config.get("health_check_url"),
            "status": ServerStatus.DISCONNECTED,
            "tool_count": 0,
            "error_message": None,
            "registered_at": now,
            "connected_at": None,
            "last_health_check": None,
            # Multi-tenant fields
            "org_id": config.get("org_id"),
            "is_global": config.get("is_global", True),
        }

        if self._db_pool:
            # Use database
            await self._insert_server_db(server)
        else:
            # Use in-memory storage
            self._servers[server_id] = server

        logger.info(f"Registered server: {name} ({server_id})")

        # Emit event
        if self._event_emitter:
            await self._event_emitter.emit("server.registered", server)

        return server

    async def _insert_server_db(self, server: Dict[str, Any]) -> None:
        """Insert server record into database."""
        # Convert enum to string for DB storage
        transport_type = server["transport_type"]
        if isinstance(transport_type, ServerTransportType):
            transport_type = transport_type.value

        status = server["status"]
        if isinstance(status, ServerStatus):
            status = status.value

        import json
        connection_config_json = json.dumps(server["connection_config"])

        async with self._db_pool.acquire() as conn:
            # Check if tenant columns exist (migration may not have run yet)
            has_tenant = await conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'mcp' AND table_name = 'external_servers' AND column_name = 'is_global'"
            ) > 0

            if has_tenant:
                await conn.execute(
                    """
                    INSERT INTO mcp.external_servers (
                        id, name, description, transport_type, connection_config,
                        health_check_url, status, tool_count, error_message,
                        registered_at, connected_at, last_health_check,
                        org_id, is_global
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """,
                    server["id"],
                    server["name"],
                    server.get("description"),
                    transport_type,
                    connection_config_json,
                    server.get("health_check_url"),
                    status,
                    server.get("tool_count", 0),
                    server.get("error_message"),
                    server["registered_at"],
                    server.get("connected_at"),
                    server.get("last_health_check"),
                    server.get("org_id"),
                    server.get("is_global", True),
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO mcp.external_servers (
                        id, name, description, transport_type, connection_config,
                        health_check_url, status, tool_count, error_message,
                        registered_at, connected_at, last_health_check
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    server["id"],
                    server["name"],
                    server.get("description"),
                    transport_type,
                    connection_config_json,
                    server.get("health_check_url"),
                    status,
                    server.get("tool_count", 0),
                    server.get("error_message"),
                    server["registered_at"],
                    server.get("connected_at"),
                    server.get("last_health_check"),
                )

    async def get(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a server by ID.

        Args:
            server_id: Server UUID

        Returns:
            Server record or None if not found
        """
        if self._db_pool:
            return await self._get_server_db(server_id)
        return self._servers.get(server_id)

    async def _get_server_db(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server from database."""
        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mcp.external_servers WHERE id = $1",
                server_id
            )
            if row:
                return self._row_to_server(row)
        return None

    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a server by name.

        Args:
            name: Server name

        Returns:
            Server record or None if not found
        """
        if self._db_pool:
            return await self._get_server_by_name_db(name)

        for server in self._servers.values():
            if server["name"] == name:
                return server
        return None

    async def _get_server_by_name_db(self, name: str) -> Optional[Dict[str, Any]]:
        """Get server by name from database."""
        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mcp.external_servers WHERE name = $1",
                name
            )
            if row:
                return self._row_to_server(row)
        return None

    async def update(self, server_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update a server's attributes.

        Args:
            server_id: Server UUID
            **updates: Fields to update

        Returns:
            Updated server record or None if not found
        """
        if self._db_pool:
            return await self._update_server_db(server_id, updates)

        if server_id not in self._servers:
            return None

        server = self._servers[server_id]
        for key, value in updates.items():
            if key in server and key not in ("id", "registered_at"):
                server[key] = value

        return server

    async def _update_server_db(self, server_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update server in database."""
        if not updates:
            return await self.get(server_id)

        # Build UPDATE query dynamically
        set_clauses = []
        values = []
        param_idx = 1

        for key, value in updates.items():
            if key in ("id", "registered_at"):
                continue

            # Handle enum conversion
            if key == "status" and isinstance(value, ServerStatus):
                value = value.value
            elif key == "transport_type" and isinstance(value, ServerTransportType):
                value = value.value
            elif key == "connection_config" and isinstance(value, dict):
                import json
                value = json.dumps(value)

            set_clauses.append(f"{key} = ${param_idx}")
            values.append(value)
            param_idx += 1

        if not set_clauses:
            return await self.get(server_id)

        values.append(server_id)
        query = f"""
            UPDATE mcp.external_servers
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx}
            RETURNING *
        """

        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            if row:
                return self._row_to_server(row)
        return None

    async def remove(self, server_id: str) -> bool:
        """
        Remove a server from the registry.

        Args:
            server_id: Server UUID

        Returns:
            True if removed, False if not found
        """
        if self._db_pool:
            return await self._remove_server_db(server_id)

        if server_id not in self._servers:
            return False

        del self._servers[server_id]
        logger.info(f"Removed server: {server_id}")
        return True

    async def _remove_server_db(self, server_id: str) -> bool:
        """Remove server from database."""
        async with self._db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM mcp.external_servers WHERE id = $1",
                server_id
            )
            return "DELETE 1" in result

    async def list(self, status: ServerStatus = None, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all servers with optional status and org filter.

        Args:
            status: Optional status filter
            org_id: Optional organization ID for tenant filtering

        Returns:
            List of server records
        """
        if self._db_pool:
            return await self._list_servers_db(status, org_id=org_id)

        results = []
        for server in self._servers.values():
            if status is not None and server["status"] != status:
                continue
            # In-memory tenant filter
            if org_id:
                if not (server.get("is_global", True) or server.get("org_id") == org_id):
                    continue
            else:
                if not server.get("is_global", True):
                    continue
            results.append(server)
        return results

    async def _list_servers_db(self, status: Optional[ServerStatus], org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List servers from database with tenant filtering."""
        async with self._db_pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1

            # Tenant filter: only applied when org_id is provided (pre-migration safe)
            if org_id:
                conditions.append(f"(is_global = TRUE OR org_id = ${param_idx})")
                params.append(org_id)
                param_idx += 1

            if status:
                status_value = status.value if isinstance(status, ServerStatus) else status
                conditions.append(f"status = ${param_idx}")
                params.append(status_value)
                param_idx += 1

            where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM mcp.external_servers {where_sql} ORDER BY name"

            rows = await conn.fetch(query, *params)
            return [self._row_to_server(row) for row in rows]

    async def update_status(
        self,
        server_id: str,
        status: ServerStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update server connection status.

        Args:
            server_id: Server UUID
            status: New status
            error_message: Optional error message

        Returns:
            True if updated, False if not found
        """
        updates = {"status": status, "error_message": error_message}

        if status == ServerStatus.CONNECTED:
            updates["connected_at"] = datetime.now(timezone.utc)

        result = await self.update(server_id, **updates)

        if result and self._event_emitter:
            await self._event_emitter.emit("server.status_changed", {
                "server_id": server_id,
                "status": status.value if isinstance(status, ServerStatus) else status
            })

        return result is not None

    async def update_tool_count(self, server_id: str, count: int) -> bool:
        """
        Update server tool count.

        Args:
            server_id: Server UUID
            count: New tool count

        Returns:
            True if updated, False if not found
        """
        result = await self.update(server_id, tool_count=count)
        return result is not None

    async def update_last_health_check(self, server_id: str) -> bool:
        """
        Update last health check timestamp.

        Args:
            server_id: Server UUID

        Returns:
            True if updated, False if not found
        """
        result = await self.update(
            server_id,
            last_health_check=datetime.now(timezone.utc)
        )
        return result is not None

    def _row_to_server(self, row) -> Dict[str, Any]:
        """Convert database row to server dict."""
        import json

        connection_config = row["connection_config"]
        if isinstance(connection_config, str):
            connection_config = json.loads(connection_config)

        transport_type = row["transport_type"]
        if isinstance(transport_type, str):
            transport_type = ServerTransportType(transport_type)

        status = row["status"]
        if isinstance(status, str):
            status = ServerStatus(status)

        return {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row.get("description"),
            "transport_type": transport_type,
            "connection_config": connection_config,
            "health_check_url": row.get("health_check_url"),
            "status": status,
            "tool_count": row.get("tool_count", 0),
            "error_message": row.get("error_message"),
            "registered_at": row["registered_at"],
            "connected_at": row.get("connected_at"),
            "last_health_check": row.get("last_health_check"),
            "org_id": str(row["org_id"]) if row.get("org_id") else None,
            "is_global": row.get("is_global") if row.get("is_global") is not None else True,
        }
