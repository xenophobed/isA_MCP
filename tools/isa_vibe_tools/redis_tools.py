#!/usr/bin/env python3
"""
Redis Tools for MCP Server

Provides cache access for agents via native AsyncRedisClient (redis-py async).
This allows agents to inspect cache state, verify sessions, and debug caching issues.

Migrated from isA_Vibe/src/agents/mcp_servers/redis_mcp.py

Environment:
    REDIS_HOST: Redis host (default: localhost)
    REDIS_PORT: Redis port (default: 6379)
"""

import json
import os
from datetime import datetime
from typing import Optional, List

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

# Optional isa_common import
try:
    from isa_common import AsyncRedisClient

    REDIS_CLIENT_AVAILABLE = True
except ImportError:
    REDIS_CLIENT_AVAILABLE = False
    AsyncRedisClient = None

logger = get_logger(__name__)
tools = BaseTool()

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


async def get_client() -> "AsyncRedisClient":
    """Get connected Redis client."""
    if not REDIS_CLIENT_AVAILABLE:
        raise ImportError("isa_common not installed. Install with: pip install isa_common")
    client = AsyncRedisClient(
        host=REDIS_HOST, port=REDIS_PORT, user_id="mcp_agent", organization_id="isa-platform"
    )
    await client.__aenter__()
    return client


def register_redis_tools(mcp: FastMCP):
    """Register Redis tools with the MCP server."""

    @mcp.tool()
    async def redis_health_check(deep_check: bool = False) -> dict:
        """Check Redis service health

        Args:
            deep_check: Perform deep health check (default: False)

        Returns:
            Dict with health status information
        """
        client = None
        try:
            client = await get_client()
            health = await client.health_check(deep_check=deep_check)
            return tools.create_response(
                status="success",
                action="redis_health_check",
                data=health or {"error": "Health check failed"},
            )
        except Exception as e:
            logger.error(f"Error in redis_health_check: {e}")
            return tools.create_response(
                status="error", action="redis_health_check", data={}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_get(key: str) -> dict:
        """Get value by key from Redis

        Args:
            key: Redis key to get

        Returns:
            Dict with key, value, and type info
        """
        client = None
        try:
            client = await get_client()
            value = await client.get(key)

            if value is None:
                return tools.create_response(
                    status="success",
                    action="redis_get",
                    data={"key": key, "value": None, "exists": False},
                )

            # Try to parse as JSON
            try:
                parsed = json.loads(value)
                return tools.create_response(
                    status="success",
                    action="redis_get",
                    data={"key": key, "value": parsed, "type": "json"},
                )
            except (json.JSONDecodeError, TypeError):
                return tools.create_response(
                    status="success",
                    action="redis_get",
                    data={"key": key, "value": value, "type": "string"},
                )

        except Exception as e:
            logger.error(f"Error in redis_get: {e}")
            return tools.create_response(
                status="error", action="redis_get", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_keys(pattern: str, limit: int = 100) -> dict:
        """Find keys matching a pattern (use sparingly in production)

        Args:
            pattern: Key pattern (e.g., 'session:*', 'cache:user:*')
            limit: Maximum number of keys to return (default: 100)

        Returns:
            Dict with matching keys, count, and truncation status
        """
        client = None
        try:
            client = await get_client()

            try:
                keys = await client.keys(pattern)
                truncated = False
                if keys and len(keys) > limit:
                    keys = keys[:limit]
                    truncated = True

                return tools.create_response(
                    status="success",
                    action="redis_keys",
                    data={
                        "pattern": pattern,
                        "keys": keys or [],
                        "count": len(keys) if keys else 0,
                        "truncated": truncated,
                    },
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_keys",
                    data={
                        "pattern": pattern,
                        "note": "keys() not available in client",
                        "hint": "Use redis-cli: KEYS " + pattern,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_keys: {e}")
            return tools.create_response(
                status="error", action="redis_keys", data={"pattern": pattern}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_ttl(key: str) -> dict:
        """Get time-to-live for a key

        Args:
            key: Redis key to check TTL for

        Returns:
            Dict with TTL in seconds and description
        """
        client = None
        try:
            client = await get_client()

            try:
                ttl = await client.ttl(key)
                ttl_desc = (
                    "no expiry"
                    if ttl == -1
                    else ("key not found" if ttl == -2 else f"{ttl} seconds")
                )
                return tools.create_response(
                    status="success",
                    action="redis_ttl",
                    data={"key": key, "ttl_seconds": ttl, "ttl_description": ttl_desc},
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_ttl",
                    data={
                        "key": key,
                        "note": "ttl() not available in client",
                        "hint": "Use redis-cli: TTL " + key,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_ttl: {e}")
            return tools.create_response(
                status="error", action="redis_ttl", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_type(key: str) -> dict:
        """Get the type of a key

        Args:
            key: Redis key to check type for

        Returns:
            Dict with key type (string, list, set, hash, zset, etc.)
        """
        client = None
        try:
            client = await get_client()

            try:
                key_type = await client.type(key)
                return tools.create_response(
                    status="success", action="redis_type", data={"key": key, "type": key_type}
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_type",
                    data={
                        "key": key,
                        "note": "type() not available in client",
                        "hint": "Use redis-cli: TYPE " + key,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_type: {e}")
            return tools.create_response(
                status="error", action="redis_type", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_exists(keys: List[str]) -> dict:
        """Check if key(s) exist

        Args:
            keys: List of keys to check

        Returns:
            Dict with existing count and all_exist flag
        """
        client = None
        try:
            client = await get_client()

            try:
                count = await client.exists(*keys)
                return tools.create_response(
                    status="success",
                    action="redis_exists",
                    data={"keys": keys, "existing_count": count, "all_exist": count == len(keys)},
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_exists",
                    data={
                        "keys": keys,
                        "note": "exists() not available in client",
                        "hint": "Use redis-cli: EXISTS " + " ".join(keys),
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_exists: {e}")
            return tools.create_response(
                status="error", action="redis_exists", data={"keys": keys}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_hgetall(key: str) -> dict:
        """Get all fields and values in a hash

        Args:
            key: Hash key

        Returns:
            Dict with hash data and field count
        """
        client = None
        try:
            client = await get_client()

            try:
                data = await client.hgetall(key)
                return tools.create_response(
                    status="success",
                    action="redis_hgetall",
                    data={"key": key, "data": data or {}, "field_count": len(data) if data else 0},
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_hgetall",
                    data={
                        "key": key,
                        "note": "hgetall() not available in client",
                        "hint": "Use redis-cli: HGETALL " + key,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_hgetall: {e}")
            return tools.create_response(
                status="error", action="redis_hgetall", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_lrange(key: str, start: int = 0, stop: int = -1) -> dict:
        """Get a range of elements from a list

        Args:
            key: List key
            start: Start index (0-based, default: 0)
            stop: Stop index (-1 for all, default: -1)

        Returns:
            Dict with list items and count
        """
        client = None
        try:
            client = await get_client()

            try:
                items = await client.lrange(key, start, stop)
                return tools.create_response(
                    status="success",
                    action="redis_lrange",
                    data={"key": key, "items": items or [], "count": len(items) if items else 0},
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_lrange",
                    data={
                        "key": key,
                        "note": "lrange() not available in client",
                        "hint": f"Use redis-cli: LRANGE {key} {start} {stop}",
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_lrange: {e}")
            return tools.create_response(
                status="error", action="redis_lrange", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_smembers(key: str) -> dict:
        """Get all members of a set

        Args:
            key: Set key

        Returns:
            Dict with set members and count
        """
        client = None
        try:
            client = await get_client()

            try:
                members = await client.smembers(key)
                return tools.create_response(
                    status="success",
                    action="redis_smembers",
                    data={
                        "key": key,
                        "members": list(members) if members else [],
                        "count": len(members) if members else 0,
                    },
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_smembers",
                    data={
                        "key": key,
                        "note": "smembers() not available in client",
                        "hint": "Use redis-cli: SMEMBERS " + key,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_smembers: {e}")
            return tools.create_response(
                status="error", action="redis_smembers", data={"key": key}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_info(section: str = "default") -> dict:
        """Get Redis server information

        Args:
            section: Info section (server, clients, memory, stats, etc., default: default)

        Returns:
            Dict with server information
        """
        client = None
        try:
            client = await get_client()

            try:
                info = await client.info(section if section != "default" else None)
                return tools.create_response(
                    status="success", action="redis_info", data={"section": section, "info": info}
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_info",
                    data={
                        "section": section,
                        "note": "info() not available in client",
                        "hint": "Use redis-cli: INFO " + section,
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_info: {e}")
            return tools.create_response(
                status="error", action="redis_info", data={"section": section}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_dbsize() -> dict:
        """Get the number of keys in the database

        Returns:
            Dict with key count
        """
        client = None
        try:
            client = await get_client()

            try:
                size = await client.dbsize()
                return tools.create_response(
                    status="success", action="redis_dbsize", data={"key_count": size}
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="redis_dbsize",
                    data={
                        "note": "dbsize() not available in client",
                        "hint": "Use redis-cli: DBSIZE",
                    },
                )

        except Exception as e:
            logger.error(f"Error in redis_dbsize: {e}")
            return tools.create_response(
                status="error", action="redis_dbsize", data={}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    # ==================== Observability Tools ====================

    @mcp.tool()
    async def redis_obs_traces(session_id: str, limit: int = 50) -> dict:
        """Get tool call traces for an agent session (observability)

        Args:
            session_id: Agent session ID
            limit: Maximum traces to return (default: 50)

        Returns:
            Dict with session traces and count
        """
        client = None
        try:
            client = await get_client()
            trace_key = f"obs:{session_id}:trace"
            entries = await client.lrange(trace_key, -limit, -1)
            traces = []
            for entry in entries or []:
                try:
                    traces.append(json.loads(entry))
                except (json.JSONDecodeError, TypeError):
                    traces.append({"raw": entry})

            return tools.create_response(
                status="success",
                action="redis_obs_traces",
                data={"session_id": session_id, "traces": traces, "count": len(traces)},
            )

        except Exception as e:
            logger.error(f"Error in redis_obs_traces: {e}")
            return tools.create_response(
                status="error",
                action="redis_obs_traces",
                data={"session_id": session_id},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_obs_metrics(session_id: str) -> dict:
        """Get session metrics - tool calls, duration, errors (observability)

        Args:
            session_id: Agent session ID

        Returns:
            Dict with session metrics
        """
        client = None
        try:
            client = await get_client()
            metrics_key = f"obs:{session_id}:metrics"
            data = await client.hgetall(metrics_key)

            if data:
                metrics = {
                    "session_id": session_id,
                    "tool_calls": int(data.get("tool_calls", 0)),
                    "total_duration_ms": int(data.get("total_duration_ms", 0)),
                    "errors": int(data.get("errors", 0)),
                    "started_at": data.get("started_at", ""),
                    "last_activity": data.get("last_activity", ""),
                }
                if metrics["tool_calls"] > 0:
                    metrics["avg_duration_ms"] = (
                        metrics["total_duration_ms"] // metrics["tool_calls"]
                    )
            else:
                metrics = {"session_id": session_id, "found": False}

            return tools.create_response(status="success", action="redis_obs_metrics", data=metrics)

        except Exception as e:
            logger.error(f"Error in redis_obs_metrics: {e}")
            return tools.create_response(
                status="error",
                action="redis_obs_metrics",
                data={"session_id": session_id},
                error_message=str(e),
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_obs_activity(limit: int = 20) -> dict:
        """Get recent agent activity across all sessions (observability)

        Args:
            limit: Maximum entries to return (default: 20)

        Returns:
            Dict with recent activity list
        """
        client = None
        try:
            client = await get_client()
            activity_key = "obs:agents:activity"
            entries = await client.zrevrange(activity_key, 0, limit - 1, withscores=True)

            activity = []
            if entries:
                for session_id, score in entries:
                    activity.append(
                        {
                            "session_id": session_id,
                            "timestamp": datetime.fromtimestamp(score).isoformat(),
                        }
                    )

            return tools.create_response(
                status="success",
                action="redis_obs_activity",
                data={"recent_activity": activity, "count": len(activity)},
            )

        except Exception as e:
            logger.error(f"Error in redis_obs_activity: {e}")
            return tools.create_response(
                status="error", action="redis_obs_activity", data={}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def redis_obs_tool_stats() -> dict:
        """Get global tool usage statistics (observability)

        Returns:
            Dict with tool usage stats sorted by count
        """
        client = None
        try:
            client = await get_client()
            stats_key = "obs:tools:usage"
            data = await client.hgetall(stats_key)
            stats = {k: int(v) for k, v in (data or {}).items()}
            sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))

            return tools.create_response(
                status="success",
                action="redis_obs_tool_stats",
                data={
                    "tool_usage": sorted_stats,
                    "total_tools": len(sorted_stats),
                    "total_calls": sum(sorted_stats.values()),
                },
            )

        except Exception as e:
            logger.error(f"Error in redis_obs_tool_stats: {e}")
            return tools.create_response(
                status="error", action="redis_obs_tool_stats", data={}, error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    logger.debug("Registered 15 Redis tools")
