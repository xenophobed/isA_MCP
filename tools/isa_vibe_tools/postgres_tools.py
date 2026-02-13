#!/usr/bin/env python3
"""
PostgreSQL Tools for MCP Server

Provides database access for agents via native AsyncPostgresClient (asyncpg).
This allows agents to query database schema, validate data models, and generate design docs.

Migrated from isA_Vibe/src/agents/mcp_servers/postgres_mcp.py

Environment:
    POSTGRES_HOST: PostgreSQL host (default: localhost)
    POSTGRES_PORT: PostgreSQL port (default: 5432)
"""

import os
from typing import Optional, List

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

# Optional isa_common import
try:
    from isa_common import AsyncPostgresClient

    POSTGRES_CLIENT_AVAILABLE = True
except ImportError:
    POSTGRES_CLIENT_AVAILABLE = False
    AsyncPostgresClient = None

logger = get_logger(__name__)
tools = BaseTool()

# Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


async def get_client() -> "AsyncPostgresClient":
    """Get connected PostgreSQL client."""
    if not POSTGRES_CLIENT_AVAILABLE:
        raise ImportError("isa_common not installed. Install with: pip install isa_common")
    client = AsyncPostgresClient(host=POSTGRES_HOST, port=POSTGRES_PORT, user_id="mcp_agent")
    await client.__aenter__()
    return client


def register_postgres_tools(mcp: FastMCP):
    """Register PostgreSQL tools with the MCP server."""

    @mcp.tool()
    async def postgres_query(
        sql: str, params: Optional[List[str]] = None, schema: str = "public"
    ) -> dict:
        """Execute a read-only SQL query against PostgreSQL

        Args:
            sql: SQL query to execute (SELECT only for safety)
            params: Query parameters ($1, $2, etc.)
            schema: Database schema (default: public)

        Returns:
            Dict with query results
        """
        client = None
        try:
            # Safety check: only allow SELECT queries
            sql_upper = sql.strip().upper()
            if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
                return tools.create_response(
                    status="error",
                    action="postgres_query",
                    data={"sql": sql[:100]},
                    error_message="Only SELECT queries are allowed for safety. Use SELECT, WITH, or information_schema queries.",
                )

            client = await get_client()
            params = params or []
            result = await client.query(sql, params, schema=schema)

            if result is None:
                return tools.create_response(
                    status="error",
                    action="postgres_query",
                    data={"sql": sql[:100]},
                    error_message="Query returned no results or failed",
                )

            return tools.create_response(
                status="success",
                action="postgres_query",
                data={
                    "results": result,
                    "row_count": len(result) if isinstance(result, list) else 1,
                },
            )

        except Exception as e:
            logger.error(f"Error in postgres_query: {e}")
            return tools.create_response(
                status="error",
                action="postgres_query",
                data={"sql": sql[:100]},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def postgres_get_schema(table_name: str, schema: str = "public") -> dict:
        """Get table schema (columns, types, constraints) for a specific table

        Args:
            table_name: Name of the table to get schema for
            schema: Database schema (default: public)

        Returns:
            Dict with table columns and their properties
        """
        client = None
        try:
            client = await get_client()

            sql = """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
            """
            result = await client.query(sql, [schema, table_name])

            if not result:
                return tools.create_response(
                    status="error",
                    action="postgres_get_schema",
                    data={"table_name": table_name, "schema": schema},
                    error_message=f"Table '{table_name}' not found in schema '{schema}'",
                )

            return tools.create_response(
                status="success",
                action="postgres_get_schema",
                data={"table": table_name, "schema": schema, "columns": result},
            )

        except Exception as e:
            logger.error(f"Error in postgres_get_schema: {e}")
            return tools.create_response(
                status="error",
                action="postgres_get_schema",
                data={"table_name": table_name, "schema": schema},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def postgres_list_tables(schema: str = "public") -> dict:
        """List all tables in a database schema

        Args:
            schema: Database schema to list tables from (default: public)

        Returns:
            Dict with list of tables and their types
        """
        client = None
        try:
            client = await get_client()

            sql = """
                SELECT
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = $1
                ORDER BY table_name
            """
            result = await client.query(sql, [schema])

            return tools.create_response(
                status="success",
                action="postgres_list_tables",
                data={
                    "schema": schema,
                    "tables": result or [],
                    "count": len(result) if result else 0,
                },
            )

        except Exception as e:
            logger.error(f"Error in postgres_list_tables: {e}")
            return tools.create_response(
                status="error",
                action="postgres_list_tables",
                data={"schema": schema},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def postgres_get_indexes(table_name: str, schema: str = "public") -> dict:
        """Get indexes for a specific table

        Args:
            table_name: Name of the table to get indexes for
            schema: Database schema (default: public)

        Returns:
            Dict with list of indexes and their definitions
        """
        client = None
        try:
            client = await get_client()

            sql = """
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = $1 AND tablename = $2
            """
            result = await client.query(sql, [schema, table_name])

            return tools.create_response(
                status="success",
                action="postgres_get_indexes",
                data={
                    "table": table_name,
                    "schema": schema,
                    "indexes": result or [],
                    "count": len(result) if result else 0,
                },
            )

        except Exception as e:
            logger.error(f"Error in postgres_get_indexes: {e}")
            return tools.create_response(
                status="error",
                action="postgres_get_indexes",
                data={"table_name": table_name, "schema": schema},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def postgres_get_foreign_keys(table_name: str, schema: str = "public") -> dict:
        """Get foreign key relationships for a table

        Args:
            table_name: Name of the table to get foreign keys for
            schema: Database schema (default: public)

        Returns:
            Dict with list of foreign key relationships
        """
        client = None
        try:
            client = await get_client()

            sql = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = $1
                    AND tc.table_name = $2
            """
            result = await client.query(sql, [schema, table_name])

            return tools.create_response(
                status="success",
                action="postgres_get_foreign_keys",
                data={
                    "table": table_name,
                    "schema": schema,
                    "foreign_keys": result or [],
                    "count": len(result) if result else 0,
                },
            )

        except Exception as e:
            logger.error(f"Error in postgres_get_foreign_keys: {e}")
            return tools.create_response(
                status="error",
                action="postgres_get_foreign_keys",
                data={"table_name": table_name, "schema": schema},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def postgres_health_check() -> dict:
        """Check PostgreSQL service health

        Returns:
            Dict with health status information
        """
        client = None
        try:
            client = await get_client()
            health = await client.health_check()

            return tools.create_response(
                status="success",
                action="postgres_health_check",
                data=health or {"error": "Health check failed"},
            )

        except Exception as e:
            logger.error(f"Error in postgres_health_check: {e}")
            return tools.create_response(
                status="error", action="postgres_health_check", data={}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    logger.debug("Registered 6 PostgreSQL tools")
