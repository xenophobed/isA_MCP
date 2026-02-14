"""
Aggregator Service Domain Types.

Canonical enums and types for the aggregator service.
These are the production source of truth — test contracts re-export from here.
"""

from enum import Enum


class ServerTransportType(str, Enum):
    """Transport types for external MCP servers."""

    STDIO = "STDIO"
    SSE = "SSE"
    HTTP = "HTTP"
    STREAMABLE_HTTP = "STREAMABLE_HTTP"


class ServerStatus(str, Enum):
    """Connection status of external MCP server."""

    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    CONNECTING = "CONNECTING"
    DEGRADED = "DEGRADED"


class RoutingStrategy(str, Enum):
    """How routing decision was made."""

    NAMESPACE_RESOLVED = "namespace_resolved"
    EXPLICIT_SERVER = "explicit_server"
    FALLBACK = "fallback"
