"""
isA_Vibe Tools for MCP Server

Migrated from isA_Vibe/src/agents/mcp_servers/
These tools provide access to project infrastructure services:
- Notion: Workspace documentation, PRDs, backlog management
- Redis: Cache access, session debugging, observability metrics
- Postgres: Database schema inspection, read-only queries
- Consul: Service discovery, health checks, KV store access
- NATS: Event streams, consumers, message peeking
- NotebookLM: Browser automation for Google NotebookLM
- Graph RAG: File metadata graph, relationships, and codebase indexing

Auto-Discovery Pattern:
    This module follows the standard tool auto-discovery pattern.
    The register function is named: register_isa_vibe_tools(mcp)
"""

from mcp.server.fastmcp import FastMCP

from .notion_tools import register_notion_tools
from .redis_tools import register_redis_tools
from .postgres_tools import register_postgres_tools
from .consul_tools import register_consul_tools
from .nats_tools import register_nats_tools
from .notebooklm_tools import register_notebooklm_tools
from .graph_rag_tools import register_graph_rag_tools


def register_isa_vibe_tools(mcp: FastMCP):
    """Register all isA_Vibe tools with the MCP server"""
    register_notion_tools(mcp)
    register_redis_tools(mcp)
    register_postgres_tools(mcp)
    register_consul_tools(mcp)
    register_nats_tools(mcp)
    register_notebooklm_tools(mcp)
    register_graph_rag_tools(mcp)
