#!/usr/bin/env python3
"""
Smart MCP Server with FAST Hot Reload
Following MCP best practices for uvicorn --reload compatibility

🎯 Now with incremental sync optimization - only syncs changed tools!
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# Setup paths
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Core imports
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_mcp_logging
from core.auto_discovery import AutoDiscoverySystem
from routes_registry import get_routes_for_consul, SERVICE_METADATA

# Initialize settings and logging at module level (required for hot reload)
settings = get_settings()
setup_mcp_logging(settings)
logger = logging.getLogger(__name__)

# Global state
smart_server = None
mcp = None

# ==============================================================================
# SMART HOT RELOAD ARCHITECTURE
# ==============================================================================
# Key Design:
# 1. MCP instance created at MODULE LEVEL (for uvicorn reload)
# 2. Tools registered BEFORE creating app (via auto-discovery)
# 3. Embeddings computed INCREMENTALLY (only new/updated)
# 4. Lifespan handler for async initialization
# ==============================================================================

class SmartMCPServer:
    """MCP Server with smart hot reload support"""

    def __init__(self):
        self.startup_time = datetime.now()
        self.reload_count = int(os.getenv('SERVER_RELOAD_COUNT', '0'))
        self.mcp = None

        # Services
        self.sync_service = None
        self.search_service = None
        self.consul_registry = None

    async def initialize(self):
        """Initialize MCP with tools/prompts/resources"""
        logger.info("🚀 Initializing Smart MCP Server...")

        # Create FastMCP instance with stateless_http=True
        # Note: We use ProgressManager for progress tracking, so Context is not needed
        # This allows simple HTTP calls without session management
        self.mcp = FastMCP("Smart MCP Server", stateless_http=True)

        # Auto-discover and register ALL capabilities
        # This runs BEFORE creating the app (MCP best practice!)
        auto_discovery = AutoDiscoverySystem()
        await auto_discovery.auto_register_with_mcp(self.mcp)

        # Get counts
        tools = await self.mcp.list_tools()
        prompts = await self.mcp.list_prompts()
        resources = await self.mcp.list_resources()

        logger.info(f"✅ Registered {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources")

        # Consul service registration
        if settings.consul.enabled:
            try:
                from isa_common.consul_client import ConsulRegistry

                # Get route metadata
                route_meta = get_routes_for_consul()

                # Merge service metadata
                consul_meta = {
                    'version': SERVICE_METADATA['version'],
                    'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                    **route_meta
                }

                self.consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA['service_name'],
                    service_port=settings.port,
                    consul_host=settings.consul.host,
                    consul_port=settings.consul.port,
                    tags=SERVICE_METADATA['tags'],
                    meta=consul_meta,
                    health_check_type='http'
                )
                self.consul_registry.register()
                logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count', 0)} routes")
            except Exception as e:
                logger.warning(f"Failed to register with Consul: {e}")
                self.consul_registry = None

        # Initialize services (Qdrant-based semantic search)
        logger.info("🔄 Initializing sync and search services...")
        from services.sync_service.sync_service import SyncService
        from services.search_service.search_service import SearchService

        self.sync_service = SyncService(mcp_server=self.mcp)
        self.search_service = SearchService()

        await self.sync_service.initialize()
        await self.search_service.initialize()

        # Run initial sync (增量同步，只同步变化的)
        logger.info("🔄 Running initial sync from MCP Server to PostgreSQL + Qdrant...")
        sync_result = await self.sync_service.sync_all()
        logger.info(f"✅ Sync completed: {sync_result['total_synced']} synced, {sync_result['total_failed']} failed")

        logger.info("✅ Smart MCP Server initialized")
        return self.mcp

    async def get_server_info(self):
        """Get server information"""
        tools = await self.mcp.list_tools()
        prompts = await self.mcp.list_prompts()
        resources = await self.mcp.list_resources()

        return {
            "server_name": "Smart MCP Server",
            "startup_time": self.startup_time.isoformat(),
            "reload_count": self.reload_count,
            "capabilities_count": {
                "tools": len(tools),
                "prompts": len(prompts),
                "resources": len(resources)
            }
        }

@asynccontextmanager
async def lifespan(app):
    """Lifespan handler for async initialization"""
    global smart_server, mcp

    logger.info("🔥 Starting MCP Server with HOT RELOAD enabled...")

    # Initialize server (tools, prompts, resources, embeddings)
    smart_server = SmartMCPServer()
    mcp = await smart_server.initialize()

    # Store in app state
    app.state.smart_server = smart_server
    app.state.mcp = mcp

    # CRITICAL FIX: Update temp_mcp's internal tool/prompt/resource lists
    # This makes the existing /mcp endpoint work with the real tools
    temp_mcp._tool_manager = mcp._tool_manager
    temp_mcp._prompt_manager = mcp._prompt_manager
    temp_mcp._resource_manager = mcp._resource_manager
    logger.info("✅ Updated MCP endpoint with real tools/prompts/resources")

    port = int(os.getenv("SERVICE_PORT", "8081"))
    logger.info(f"✅ MCP Server ready at http://0.0.0.0:{port}/mcp/")
    logger.info("🔥 HOT RELOAD: Edit tools/prompts/resources and save - auto-reloads!")

    # CRITICAL: Start MCP session manager (required for streamable HTTP!)
    # This is the official way according to MCP docs
    async with temp_mcp.session_manager.run():
        try:
            yield  # Server runs here
        finally:
            # Cleanup
            logger.info("🛑 Shutting down...")

            # Consul deregistration
            if smart_server and smart_server.consul_registry:
                try:
                    smart_server.consul_registry.deregister()
                    logger.info("✅ Service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            logger.info("✅ Shutdown complete")

# ==============================================================================
# CREATE MCP APP AT MODULE LEVEL (Required for uvicorn --reload!)
# ==============================================================================
# CRITICAL: This must execute at module import time, not in a function!
# ==============================================================================

# Step 1: Create empty MCP instance
# The real MCP with tools will be created in lifespan()
# But we need SOMETHING here for uvicorn to import
# Using stateless_http=True for simple HTTP calls without session management
temp_mcp = FastMCP("Smart MCP Server", stateless_http=True)

# Step 2: Create Starlette app from MCP
app = temp_mcp.streamable_http_app()

# Step 3: Attach lifespan handler
# This is the magic that makes hot reload work!
app.router.lifespan_context = lifespan

# Step 4: Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Step 5: Add auth middleware
from core.auth.middleware import add_mcp_unified_auth_middleware
auth_config = {
    "auth_service_url": settings.auth_service_url or "http://localhost:8000",
    "authz_service_url": settings.authz_service_url or "http://localhost:8203",
    "require_auth": settings.require_auth
}
add_mcp_unified_auth_middleware(app, auth_config)

# Step 6: Add custom endpoints (health, discover, etc.)
# Import from main.py's endpoint functions
from starlette.responses import JSONResponse
from starlette.routing import Route
import json

async def health_check(request):
    """Health check endpoint"""
    if not smart_server:
        return JSONResponse({"status": "initializing"})

    uptime = (datetime.now() - smart_server.startup_time).total_seconds()
    uptime_str = f"{int(uptime // 60)}m {int(uptime % 60)}s"

    server_info = await smart_server.get_server_info()

    return JSONResponse({
        "status": "healthy ✅ HOT RELOAD IS WORKING PERFECTLY!",
        "service": "Smart MCP Server",
        "uptime": uptime_str,
        "reload_count": smart_server.reload_count,
        "capabilities": server_info["capabilities_count"]
    })

async def search_endpoint(request):
    """New Qdrant-based semantic search endpoint"""
    if request.method == "OPTIONS":
        return JSONResponse({})

    try:
        logger.info(f"🌐 [/search] Endpoint called")
        body = await request.body()
        data = json.loads(body) if body else {}
        query = data.get("query", "")
        item_type = data.get("type")  # Optional: 'tool', 'prompt', 'resource'
        limit = data.get("limit", 10)

        logger.info(f"🌐 [/search] Request: query='{query}', type={item_type}, limit={limit}")

        if not query or not smart_server:
            logger.error(f"❌ [/search] Invalid request: query={query}, smart_server={smart_server is not None}")
            return JSONResponse({"status": "error", "message": "Invalid request"})

        # Use search service
        if smart_server.search_service:
            logger.info(f"🌐 [/search] Calling SearchService...")
            results = await smart_server.search_service.search(
                query=query,
                item_type=item_type,
                limit=limit,
                score_threshold=data.get("score_threshold", 0.3)
            )
            logger.info(f"🌐 [/search] SearchService returned {len(results)} results")

            # Convert protobuf Struct to dict for JSON serialization
            from google.protobuf.json_format import MessageToDict

            def safe_serialize(obj):
                """Convert protobuf Struct to dict, handle None"""
                if obj is None:
                    return None
                if hasattr(obj, 'DESCRIPTOR'):  # It's a protobuf message
                    return MessageToDict(obj, preserving_proto_field_name=True)
                return obj

            return JSONResponse({
                "status": "success",
                "query": query,
                "count": len(results),
                "results": [
                    {
                        "id": r.id,
                        "type": r.type,
                        "name": r.name,
                        "description": r.description,
                        "score": r.score,
                        "db_id": r.db_id,
                        # Include schema fields for tool calling (converted to dict)
                        "inputSchema": safe_serialize(r.inputSchema),
                        "outputSchema": safe_serialize(r.outputSchema),
                        "annotations": safe_serialize(r.annotations)
                    }
                    for r in results
                ]
            })

        return JSONResponse({"status": "error", "message": "Search service not ready"})

    except Exception as e:
        logger.error(f"Search error: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


async def sync_endpoint(request):
    """Manual sync trigger endpoint"""
    if request.method == "OPTIONS":
        return JSONResponse({})

    try:
        if not smart_server or not smart_server.sync_service:
            return JSONResponse({"status": "error", "message": "Sync service not ready"})

        # Run sync
        logger.info("Manual sync triggered")
        sync_result = await smart_server.sync_service.sync_all()

        return JSONResponse({
            "status": "success",
            "result": sync_result
        })

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


async def progress_stream_endpoint(request):
    """SSE streaming endpoint for real-time progress updates"""
    from starlette.responses import StreamingResponse
    import asyncio

    operation_id = request.path_params.get('operation_id')

    if not operation_id:
        return JSONResponse({"status": "error", "message": "operation_id required"})

    # Import ProgressManager
    from services.progress_service.progress_manager import ProgressManager
    progress_manager = ProgressManager()

    async def event_generator():
        """Generate SSE events for progress updates"""
        try:
            logger.info(f"📡 Starting SSE stream for operation: {operation_id}")

            while True:
                # Get current progress
                progress = await progress_manager.get_progress(operation_id)

                if not progress:
                    # Operation not found
                    yield f"event: error\ndata: {{\"error\": \"Operation not found\"}}\n\n"
                    break

                # Convert to JSON
                data = json.dumps(progress.to_dict())

                # Send SSE event
                yield f"event: progress\ndata: {data}\n\n"

                # Check if completed/failed/cancelled
                if progress.status in ["completed", "failed", "cancelled"]:
                    logger.info(f"📡 SSE stream ending: {operation_id} status={progress.status}")

                    # Send completion event
                    yield f"event: done\ndata: {{\"status\": \"{progress.status}\"}}\n\n"
                    break

                # Wait 1 second before next update
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"SSE stream error for {operation_id}: {e}")
            yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Register routes
app.router.routes.append(Route("/health", health_check))
# /discover endpoint removed - use /search instead
app.router.routes.append(Route("/search", search_endpoint, methods=["POST", "OPTIONS"]))  # NEW!
app.router.routes.append(Route("/sync", sync_endpoint, methods=["POST", "OPTIONS"]))  # NEW!
app.router.routes.append(Route("/progress/{operation_id}/stream", progress_stream_endpoint, methods=["GET"]))  # SSE Progress Stream

# ==============================================================================
# DIRECT EXECUTION (for testing)
# ==============================================================================

def main():
    """Run server directly (for testing without supervisor)"""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=8081)
    args = parser.parse_args()

    # Run with uvicorn and --reload
    uvicorn.run(
        "main_hotreload_proposal:app",
        host="0.0.0.0",
        port=args.port,
        reload=True,  # Enable hot reload
        log_level="info"
    )

if __name__ == "__main__":
    main()

# ==============================================================================
# HOW IT WORKS:
# ==============================================================================
# 1. uvicorn imports this module and gets the 'app' variable (line 170)
# 2. When starting, uvicorn calls the lifespan() context manager (line 107)
# 3. lifespan() initializes SmartMCPServer which:
#    a. Creates FastMCP and registers tools via auto-discovery
#    b. Initializes search service with INCREMENTAL embedding
#       (only embeds NEW/UPDATED tools/prompts/resources!)
# 4. App is ready and serves requests
# 5. When you edit a tool file and SAVE:
#    - uvicorn detects the file change
#    - uvicorn REL OADS the module (re-imports main.py)
#    - Steps 1-4 repeat automatically!
#    - Embeddings are INCREMENTAL (fast!)
# ==============================================================================
