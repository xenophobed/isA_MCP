#!/usr/bin/env python3
"""
NATS Tools for MCP Server

Provides event bus access for agents via native AsyncNATSClient (nats-py).
This allows agents to inspect event streams, verify subscriptions, and debug event flows.

Migrated from isA_Vibe/src/agents/mcp_servers/nats_mcp.py

Environment:
    NATS_HOST: NATS host (default: localhost)
    NATS_PORT: NATS port (default: 4222)
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

# Optional isa_common import
try:
    from isa_common import AsyncNATSClient
    NATS_CLIENT_AVAILABLE = True
except ImportError:
    NATS_CLIENT_AVAILABLE = False
    AsyncNATSClient = None

logger = get_logger(__name__)
tools = BaseTool()

# Configuration
NATS_HOST = os.getenv("NATS_HOST", "localhost")
NATS_PORT = int(os.getenv("NATS_PORT", "4222"))

# Known isA Platform streams for fallback
KNOWN_STREAMS = [
    "billing-stream", "session-stream", "order-stream", "wallet-stream",
    "user-stream", "device-stream", "payment-stream", "organization-stream",
    "notification-stream", "storage-stream", "album-stream", "task-stream",
    "memory-stream", "product-stream", "vault-stream", "event-stream",
    "media-stream", "calendar-stream", "location-stream", "telemetry-stream",
    "weather-stream", "invitation-stream", "authorization-stream",
    "compliance-stream", "ota-stream"
]


async def get_client() -> "AsyncNATSClient":
    """Get connected NATS client."""
    if not NATS_CLIENT_AVAILABLE:
        raise ImportError("isa_common not installed. Install with: pip install isa_common")
    client = AsyncNATSClient(
        host=NATS_HOST,
        port=NATS_PORT,
        user_id="mcp_agent",
        organization_id="isa-platform"
    )
    await client.__aenter__()
    return client


def register_nats_tools(mcp: FastMCP):
    """Register NATS tools with the MCP server."""

    @mcp.tool()
    async def nats_health_check() -> dict:
        """Check NATS service health and JetStream status

        Returns:
            Dict with health status information
        """
        client = None
        try:
            client = await get_client()
            health = await client.health_check()

            return tools.create_response(
                status="success",
                action="nats_health_check",
                data=health or {"error": "Health check failed"}
            )

        except Exception as e:
            logger.error(f"Error in nats_health_check: {e}")
            return tools.create_response(
                status="error",
                action="nats_health_check",
                data={},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_list_streams() -> dict:
        """List all JetStream streams

        Returns:
            Dict with list of streams and count
        """
        client = None
        try:
            client = await get_client()

            try:
                result = await client.list_streams()
                return tools.create_response(
                    status="success",
                    action="nats_list_streams",
                    data={
                        "streams": result or [],
                        "count": len(result) if result else 0
                    }
                )
            except AttributeError:
                # Fallback: return known stream names
                return tools.create_response(
                    status="success",
                    action="nats_list_streams",
                    data={
                        "streams": KNOWN_STREAMS,
                        "count": len(KNOWN_STREAMS),
                        "note": "List based on known isA Platform streams (client.list_streams not available)"
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_list_streams: {e}")
            return tools.create_response(
                status="error",
                action="nats_list_streams",
                data={},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_get_stream_info(stream_name: str) -> dict:
        """Get detailed information about a JetStream stream

        Args:
            stream_name: Name of the stream (e.g., 'billing-stream', 'session-stream')

        Returns:
            Dict with stream configuration and state
        """
        client = None
        try:
            client = await get_client()

            try:
                result = await client.get_stream_info(stream_name)
                return tools.create_response(
                    status="success",
                    action="nats_get_stream_info",
                    data=result or {"error": "Stream not found"}
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="nats_get_stream_info",
                    data={
                        "stream_name": stream_name,
                        "note": "get_stream_info not available in client",
                        "hint": "Use NATS CLI: nats stream info " + stream_name
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_get_stream_info: {e}")
            return tools.create_response(
                status="error",
                action="nats_get_stream_info",
                data={"stream_name": stream_name},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_list_consumers(stream_name: str) -> dict:
        """List all consumers for a JetStream stream

        Args:
            stream_name: Name of the stream

        Returns:
            Dict with list of consumers
        """
        client = None
        try:
            client = await get_client()

            try:
                result = await client.list_consumers(stream_name)
                return tools.create_response(
                    status="success",
                    action="nats_list_consumers",
                    data={
                        "stream": stream_name,
                        "consumers": result or [],
                        "count": len(result) if result else 0
                    }
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="nats_list_consumers",
                    data={
                        "stream": stream_name,
                        "note": "list_consumers not available in client",
                        "hint": "Use NATS CLI: nats consumer ls " + stream_name
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_list_consumers: {e}")
            return tools.create_response(
                status="error",
                action="nats_list_consumers",
                data={"stream_name": stream_name},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_get_consumer_info(stream_name: str, consumer_name: str) -> dict:
        """Get detailed information about a consumer

        Args:
            stream_name: Name of the stream
            consumer_name: Name of the consumer

        Returns:
            Dict with consumer configuration and state
        """
        client = None
        try:
            client = await get_client()

            try:
                result = await client.get_consumer_info(stream_name, consumer_name)
                return tools.create_response(
                    status="success",
                    action="nats_get_consumer_info",
                    data=result or {"error": "Consumer not found"}
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="nats_get_consumer_info",
                    data={
                        "stream": stream_name,
                        "consumer": consumer_name,
                        "note": "get_consumer_info not available in client",
                        "hint": f"Use NATS CLI: nats consumer info {stream_name} {consumer_name}"
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_get_consumer_info: {e}")
            return tools.create_response(
                status="error",
                action="nats_get_consumer_info",
                data={"stream_name": stream_name, "consumer_name": consumer_name},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_peek_messages(
        stream_name: str,
        count: int = 5,
        start_sequence: Optional[int] = None
    ) -> dict:
        """Peek at recent messages in a stream (read-only, does not consume)

        Args:
            stream_name: Name of the stream
            count: Number of messages to peek (default: 5, max: 20)
            start_sequence: Starting sequence number (optional, defaults to latest)

        Returns:
            Dict with list of messages
        """
        client = None
        try:
            client = await get_client()
            count = min(count, 20)  # Cap at 20

            try:
                result = await client.peek_messages(stream_name, count, start_sequence)
                messages = []
                if result:
                    for msg in result:
                        try:
                            data = msg.get("data", b"")
                            if isinstance(data, bytes):
                                data = json.loads(data.decode())
                            messages.append({
                                "sequence": msg.get("sequence"),
                                "subject": msg.get("subject"),
                                "data": data,
                                "timestamp": msg.get("timestamp")
                            })
                        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                            messages.append(msg)

                return tools.create_response(
                    status="success",
                    action="nats_peek_messages",
                    data={
                        "stream": stream_name,
                        "messages": messages,
                        "count": len(messages)
                    }
                )
            except AttributeError:
                return tools.create_response(
                    status="success",
                    action="nats_peek_messages",
                    data={
                        "stream": stream_name,
                        "note": "peek_messages not available in client",
                        "hint": f"Use NATS CLI: nats stream get {stream_name} --last={count}"
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_peek_messages: {e}")
            return tools.create_response(
                status="error",
                action="nats_peek_messages",
                data={"stream_name": stream_name},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_get_subjects(stream_name: str) -> dict:
        """List all subjects in a stream

        Args:
            stream_name: Name of the stream

        Returns:
            Dict with list of subjects or subject pattern
        """
        client = None
        try:
            client = await get_client()

            try:
                result = await client.get_stream_subjects(stream_name)
                return tools.create_response(
                    status="success",
                    action="nats_get_subjects",
                    data={
                        "stream": stream_name,
                        "subjects": result or [],
                        "count": len(result) if result else 0
                    }
                )
            except AttributeError:
                # Return known subjects based on stream name
                prefix = stream_name.replace("-stream", "")
                return tools.create_response(
                    status="success",
                    action="nats_get_subjects",
                    data={
                        "stream": stream_name,
                        "subjects_pattern": f"{prefix}.>",
                        "note": "get_stream_subjects not available, showing pattern"
                    }
                )

        except Exception as e:
            logger.error(f"Error in nats_get_subjects: {e}")
            return tools.create_response(
                status="error",
                action="nats_get_subjects",
                data={"stream_name": stream_name},
                error_message=str(e)
            )
        finally:
            if client:
                await client.__aexit__(None, None, None)

    @mcp.tool()
    async def nats_check_subscription(event_pattern: str) -> dict:
        """Check if a service has active subscriptions for an event type

        Args:
            event_pattern: Event pattern to check (e.g., 'billing.usage.recorded')

        Returns:
            Dict with stream info and hints for checking subscriptions
        """
        try:
            prefix = event_pattern.split('.')[0]
            stream_name = f"{prefix}-stream"

            return tools.create_response(
                status="success",
                action="nats_check_subscription",
                data={
                    "event_pattern": event_pattern,
                    "stream": stream_name,
                    "note": "To verify active subscriptions, check the consumer list",
                    "hint": f"Use: nats_list_consumers('{stream_name}')"
                }
            )

        except Exception as e:
            logger.error(f"Error in nats_check_subscription: {e}")
            return tools.create_response(
                status="error",
                action="nats_check_subscription",
                data={"event_pattern": event_pattern},
                error_message=str(e)
            )

    logger.debug("Registered 8 NATS tools")
