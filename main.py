#!/usr/bin/env python3
"""
Smart MCP Server with FAST Hot Reload
Following MCP best practices for uvicorn --reload compatibility
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
        self.reload_count = int(os.getenv("SERVER_RELOAD_COUNT", "0"))
        self.mcp = None
        self.internal_mcp = None  # Internal MCP with all tools (for meta_tools_only mode)

        # Services
        self.sync_service = None
        self.search_service = None
        self.consul_registry = None
        self.aggregator_service = None

    async def initialize(self, skip_sync: bool = False, meta_tools_only: bool = False):
        """Initialize MCP with tools/prompts/resources

        Args:
            skip_sync: If True, skip sync services and Consul registration.
                      Use for stdio mode where only tool execution is needed,
                      not search functionality. Makes startup ~3x faster.
            meta_tools_only: If True, only expose 8 meta-tools (discover, get_tool_schema,
                            execute, list_skills). The 89+ underlying tools are hidden
                            but accessible via the execute meta-tool.
        """
        import time as _time

        _startup_start = _time.monotonic()

        mode_label = "stdio fast" if skip_sync else "HTTP full"
        if meta_tools_only:
            mode_label += " + meta-tools-only"
        logger.info(f"isA MCP Server starting ({mode_label} mode)...")

        if meta_tools_only:
            # ===================================================================
            # META-TOOLS ONLY MODE
            # ===================================================================
            # Create two MCP instances:
            # 1. internal_mcp: Has all 89 tools (hidden from Claude, used by execute)
            # 2. mcp: Only has 8 meta-tools (visible to Claude)
            # ===================================================================

            # Step 1: Create internal MCP with all tools
            logger.debug("Creating internal MCP with all tools...")
            self.internal_mcp = FastMCP("Internal MCP", stateless_http=True)
            auto_discovery = AutoDiscoverySystem()
            await auto_discovery.auto_register_with_mcp(self.internal_mcp)

            internal_tools = await self.internal_mcp.list_tools()
            logger.debug(f"  Internal MCP: {len(internal_tools)} tools registered")

            # Step 2: Create external MCP with only meta-tools
            logger.debug("Creating external MCP with meta-tools only...")
            self.mcp = FastMCP("Smart MCP Server", stateless_http=True)

            # Register only the meta-tools, passing internal_mcp for tool execution
            from tools.meta_tools.discovery_tools import register_discovery_tools

            register_discovery_tools(self.mcp, internal_mcp=self.internal_mcp)

            # Register aggregator tools for external MCP server management
            logger.debug("Initializing Aggregator Service for external MCP servers...")
            try:
                from services.aggregator_service import create_aggregator_service
                from tools.meta_tools.aggregator_tools import register_aggregator_tools

                self.aggregator_service = await create_aggregator_service(
                    enable_classification=True
                )
                register_aggregator_tools(self.mcp, self.aggregator_service)
                logger.debug("  Aggregator tools registered")
            except Exception as e:
                logger.debug(f"  Aggregator service not available: {e}")
                self.aggregator_service = None

            external_tools = await self.mcp.list_tools()
            logger.info(
                f"  Meta-tools: {len(external_tools)} visible, {len(internal_tools)} hidden"
            )

        else:
            # ===================================================================
            # NORMAL MODE - All tools visible
            # ===================================================================
            # Create FastMCP instance with stateless_http=True
            # Note: We use ProgressManager for progress tracking, so Context is not needed
            # This allows simple HTTP calls without session management
            self.mcp = FastMCP("Smart MCP Server", stateless_http=True)

            # Auto-discover and register ALL capabilities
            # This runs BEFORE creating the app (MCP best practice!)
            auto_discovery = AutoDiscoverySystem()
            await auto_discovery.auto_register_with_mcp(self.mcp)

            # Initialize aggregator service for external MCP server management
            logger.debug("Initializing Aggregator Service for external MCP servers...")
            try:
                from services.aggregator_service import create_aggregator_service

                self.aggregator_service = await create_aggregator_service(
                    enable_classification=True
                )
                logger.debug("  Aggregator service initialized")
            except Exception as e:
                logger.debug(f"  Aggregator service not available: {e}")
                self.aggregator_service = None

        # Get counts
        tools = await self.mcp.list_tools()
        prompts = await self.mcp.list_prompts()
        resources = await self.mcp.list_resources()

        logger.info(
            f"  Registered: {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources"
        )

        # Skip Consul and sync for stdio mode (not needed, saves ~3 seconds)
        if skip_sync:
            _elapsed = _time.monotonic() - _startup_start
            logger.info(f"Server ready ({_elapsed:.1f}s) | stdio mode")
            return self.mcp

        # Consul service registration (HTTP mode only)
        if settings.consul.enabled:
            try:
                from isa_common.consul_client import ConsulRegistry

                # Get route metadata
                route_meta = get_routes_for_consul()

                # Merge service metadata
                consul_meta = {
                    "version": SERVICE_METADATA["version"],
                    "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                    **route_meta,
                }

                self.consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA["service_name"],
                    service_port=settings.port,
                    consul_host=settings.consul.host,
                    consul_port=settings.consul.port,
                    tags=SERVICE_METADATA["tags"],
                    meta=consul_meta,
                    health_check_type="ttl",  # Use TTL for reliable health checks in K8s
                )
                self.consul_registry.register()
                self.consul_registry.start_maintenance()  # Start background TTL heartbeat
                logger.info(f"  Consul: {route_meta.get('route_count', 0)} routes registered")
            except Exception as e:
                logger.warning(f"Failed to register with Consul: {e}")
                self.consul_registry = None

        # Initialize services (Qdrant-based semantic search) - HTTP mode only
        logger.debug("Initializing sync and search services...")
        from services.sync_service.sync_service import SyncService
        from services.search_service.hierarchical_search_service import HierarchicalSearchService

        # IMPORTANT: In meta_tools_only mode, sync from internal_mcp (all tools)
        # not from self.mcp (which only has 8 meta-tools)
        sync_mcp = self.internal_mcp if self.internal_mcp else self.mcp
        self.sync_service = SyncService(mcp_server=sync_mcp)
        self.search_service = HierarchicalSearchService()  # Uses lazy initialization

        await self.sync_service.initialize()
        # Note: HierarchicalSearchService uses lazy initialization, no initialize() needed

        # Run initial sync
        logger.debug("Running initial sync from MCP Server to PostgreSQL + Qdrant...")
        sync_result = await self.sync_service.sync_all()
        logger.info(
            f"  Sync: {sync_result.get('total_synced', 0)} updated, {sync_result.get('total_skipped', 0)} skipped, {sync_result.get('total_failed', 0)} failed"
        )

        _elapsed = _time.monotonic() - _startup_start
        host = "0.0.0.0"
        port = settings.port if hasattr(settings, "port") else 8081
        reload_info = "hot reload enabled" if not skip_sync else ""
        logger.info(
            f"Server ready ({_elapsed:.1f}s) | http://{host}:{port} | {reload_info}".rstrip(" | ")
        )
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
                "resources": len(resources),
            },
        }


@asynccontextmanager
async def lifespan(app):
    """Lifespan handler for async initialization"""
    global smart_server, mcp

    logger.debug("Starting MCP Server lifespan...")

    # Initialize server (tools, prompts, resources, embeddings)
    # Use meta_tools_only from config if enabled
    smart_server = SmartMCPServer()
    mcp = await smart_server.initialize(meta_tools_only=settings.meta_tools_only)

    # Store in app state
    app.state.smart_server = smart_server
    app.state.mcp = mcp

    # CRITICAL FIX: Update temp_mcp's internal tool/prompt/resource lists
    # This makes the existing /mcp endpoint work with the real tools
    temp_mcp._tool_manager = mcp._tool_manager
    temp_mcp._prompt_manager = mcp._prompt_manager
    temp_mcp._resource_manager = mcp._resource_manager
    logger.debug("Updated MCP endpoint with real tools/prompts/resources")

    # CRITICAL: Start MCP session manager (required for streamable HTTP!)
    # This is the official way according to MCP docs
    async with temp_mcp.session_manager.run():
        try:
            yield  # Server runs here
        finally:
            # Cleanup
            logger.info("Shutting down...")

            # Consul deregistration
            if smart_server and smart_server.consul_registry:
                try:
                    smart_server.consul_registry.deregister()
                    logger.debug("Service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            logger.info("Shutdown complete")


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
    "authorization_service_url": settings.authorization_service_url or "http://localhost:8203",
    "require_auth": settings.require_auth,
}
add_mcp_unified_auth_middleware(app, auth_config)

# Step 6: Add custom endpoints (health, discover, etc.)
# Import from main.py's endpoint functions
from starlette.responses import JSONResponse
from starlette.routing import Route
import json
from core.auth.org_context import get_org_id


async def health_check(request):
    """Health check endpoint"""
    if not smart_server:
        return JSONResponse({"status": "initializing"})

    uptime = (datetime.now() - smart_server.startup_time).total_seconds()
    uptime_str = f"{int(uptime // 60)}m {int(uptime % 60)}s"

    server_info = await smart_server.get_server_info()

    return JSONResponse(
        {
            "status": "healthy",
            "service": "Smart MCP Server",
            "uptime": uptime_str,
            "reload_count": smart_server.reload_count,
            "capabilities": server_info["capabilities_count"],
        }
    )


async def search_endpoint(request):
    """Hierarchical semantic search endpoint - Skill-based two-stage search"""
    if request.method == "OPTIONS":
        return JSONResponse({})

    try:
        logger.info(f"[/search] Endpoint called")
        body = await request.body()
        data = json.loads(body) if body else {}
        query = data.get("query", "")
        item_type = data.get("type")  # Optional: 'tool', 'prompt', 'resource'
        limit = data.get("limit", 10)

        # Hierarchical search parameters
        skill_limit = data.get("skill_limit", 3)
        skill_threshold = data.get("skill_threshold", 0.4)
        tool_threshold = data.get("score_threshold", 0.3)  # Backward compatible param name
        include_schemas = data.get("include_schemas", True)
        strategy = data.get("strategy", "hierarchical")  # hierarchical/direct/hybrid

        logger.info(
            f"[/search] Request: query='{query}', type={item_type}, limit={limit}, strategy={strategy}"
        )

        if not query or not smart_server:
            logger.error(
                f"[/search] Invalid request: query={query}, smart_server={smart_server is not None}"
            )
            return JSONResponse({"status": "error", "message": "Invalid request"})

        # Use hierarchical search service
        if smart_server.search_service:
            logger.info(f"[/search] Calling HierarchicalSearchService...")
            result = await smart_server.search_service.search(
                query=query,
                item_type=item_type,
                limit=limit,
                skill_limit=skill_limit,
                skill_threshold=skill_threshold,
                tool_threshold=tool_threshold,
                include_schemas=include_schemas,
                strategy=strategy,
            )
            logger.info(
                f"[/search] HierarchicalSearchService returned {len(result.tools)} tools via {len(result.matched_skills)} skills"
            )

            # Use the service's to_dict method for consistent serialization
            response_data = smart_server.search_service.to_dict(result)
            response_data["status"] = "success"

            # Add backward-compatible fields
            response_data["count"] = len(result.tools)
            response_data["results"] = [
                {
                    "id": t.id,
                    "type": t.type,
                    "name": t.name,
                    "description": t.description,
                    "score": t.score,
                    "db_id": t.db_id,
                    "inputSchema": t.input_schema,
                    "outputSchema": t.output_schema,
                    "annotations": t.annotations,
                    "skill_ids": t.skill_ids,
                    "primary_skill_id": t.primary_skill_id,
                }
                for t in result.tools
            ]

            return JSONResponse(response_data)

        return JSONResponse({"status": "error", "message": "Search service not ready"})

    except ValueError as e:
        logger.warning(f"Search validation error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
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

        return JSONResponse({"status": "success", "result": sync_result})

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


async def progress_stream_endpoint(request):
    """SSE streaming endpoint for real-time progress updates"""
    from starlette.responses import StreamingResponse
    import asyncio

    operation_id = request.path_params.get("operation_id")

    if not operation_id:
        return JSONResponse({"status": "error", "message": "operation_id required"})

    # Import ProgressManager
    from services.progress_service.progress_manager import ProgressManager

    progress_manager = ProgressManager()

    async def event_generator():
        """Generate SSE events for progress updates"""
        try:
            logger.info(f"Starting SSE stream for operation: {operation_id}")

            while True:
                # Get current progress
                progress = await progress_manager.get_progress(operation_id)

                if not progress:
                    # Operation not found
                    yield f'event: error\ndata: {{"error": "Operation not found"}}\n\n'
                    break

                # Convert to JSON
                data = json.dumps(progress.to_dict())

                # Send SSE event
                yield f"event: progress\ndata: {data}\n\n"

                # Check if completed/failed/cancelled
                if progress.status in ["completed", "failed", "cancelled"]:
                    logger.info(f"SSE stream ending: {operation_id} status={progress.status}")

                    # Send completion event
                    yield f'event: done\ndata: {{"status": "{progress.status}"}}\n\n'
                    break

                # Wait 1 second before next update
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"SSE stream error for {operation_id}: {e}")
            yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ==============================================================================
# SKILL API ENDPOINTS (/api/v1/skills/*)
# ==============================================================================


async def skills_list_endpoint(request):
    """GET /api/v1/skills - List all skill categories"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        # Parse query parameters
        is_active = request.query_params.get("is_active", "true").lower() == "true"
        parent_domain = request.query_params.get("parent_domain")
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        skills = await service.list_skills(
            is_active=is_active, parent_domain=parent_domain, limit=limit, offset=offset
        )

        return JSONResponse([_serialize_record(s) for s in skills])

    except Exception as e:
        logger.error(f"List skills error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_create_endpoint(request):
    """POST /api/v1/skills - Create a skill category"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        body = await request.body()
        data = json.loads(body) if body else {}

        # Validate required fields
        if not data.get("id") or not data.get("name") or not data.get("description"):
            return JSONResponse(
                {"detail": "id, name, and description are required"}, status_code=422
            )

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        result = await service.create_skill_category(data)

        if result is None:
            return JSONResponse({"detail": "Skill already exists"}, status_code=409)

        return JSONResponse(_serialize_record(result), status_code=201)

    except Exception as e:
        logger.error(f"Create skill error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_get_endpoint(request):
    """GET /api/v1/skills/{skill_id} - Get skill by ID"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        skill_id = request.path_params.get("skill_id")

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        skill = await service.get_skill(skill_id)

        if skill is None:
            return JSONResponse({"detail": "Skill not found"}, status_code=404)

        return JSONResponse(_serialize_record(skill))

    except Exception as e:
        logger.error(f"Get skill error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_delete_endpoint(request):
    """DELETE /api/v1/skills/{skill_id} - Delete skill"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        skill_id = request.path_params.get("skill_id")

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        success = await service.delete_skill_category(skill_id)

        if not success:
            return JSONResponse({"detail": "Skill not found"}, status_code=404)

        return JSONResponse({"status": "deleted"})

    except Exception as e:
        logger.error(f"Delete skill error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_tools_endpoint(request):
    """GET /api/v1/skills/{skill_id}/tools - Get tools in skill"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        skill_id = request.path_params.get("skill_id")

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        # First verify skill exists
        skill = await service.get_skill(skill_id)
        if skill is None:
            return JSONResponse({"detail": "Skill not found"}, status_code=404)

        tools = await service.get_tools_by_skill(skill_id)
        return JSONResponse([_serialize_record(t) for t in tools])

    except Exception as e:
        logger.error(f"Get tools in skill error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_classify_endpoint(request):
    """POST /api/v1/skills/classify - Classify a tool into skills"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        body = await request.body()
        data = json.loads(body) if body else {}

        # Validate required fields
        if not data.get("tool_id") or not data.get("tool_name") or not data.get("tool_description"):
            return JSONResponse(
                {"detail": "tool_id, tool_name, and tool_description are required"}, status_code=422
            )

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        result = await service.classify_tool(
            tool_id=data["tool_id"],
            tool_name=data["tool_name"],
            tool_description=data["tool_description"],
            force_reclassify=data.get("force_reclassify", False),
        )

        # Convert datetime to ISO string for JSON serialization
        if result.get("classification_timestamp"):
            result["classification_timestamp"] = result["classification_timestamp"].isoformat()

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Classify tool error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def skills_suggestions_endpoint(request):
    """GET /api/v1/skills/suggestions - List pending skill suggestions"""
    try:
        from services.skill_service import SkillService
        from services.skill_service.skill_repository import SkillRepository

        repo = SkillRepository(
            host=settings.infrastructure.postgres_grpc_host,
            port=settings.infrastructure.postgres_grpc_port,
        )
        service = SkillService(repository=repo)

        suggestions = await service.list_pending_suggestions()
        return JSONResponse([_serialize_record(s) for s in suggestions])

    except Exception as e:
        logger.error(f"List suggestions error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


# ==============================================================================
# SEARCH API ENDPOINTS (/api/v1/search/*)
# ==============================================================================


async def api_search_endpoint(request):
    """POST /api/v1/search - Hierarchical search"""
    if request.method == "OPTIONS":
        return JSONResponse({})

    try:
        body = await request.body()
        data = json.loads(body) if body else {}

        query = data.get("query", "")
        if not query or not query.strip():
            return JSONResponse({"detail": "query is required"}, status_code=422)
        if len(query) > 1000:
            return JSONResponse({"detail": "query cannot exceed 1000 characters"}, status_code=422)

        # Validate parameters
        limit = data.get("limit", 10)
        if limit > 50:
            return JSONResponse({"detail": "limit cannot exceed 50"}, status_code=422)

        skill_threshold = data.get("skill_threshold", 0.4)
        tool_threshold = data.get("tool_threshold", 0.3)
        if skill_threshold < 0 or skill_threshold > 1:
            return JSONResponse(
                {"detail": "skill_threshold must be between 0 and 1"}, status_code=422
            )
        if tool_threshold < 0 or tool_threshold > 1:
            return JSONResponse(
                {"detail": "tool_threshold must be between 0 and 1"}, status_code=422
            )

        strategy = data.get("strategy", "hierarchical")
        if strategy not in ["hierarchical", "direct", "hybrid"]:
            return JSONResponse(
                {"detail": "strategy must be hierarchical, direct, or hybrid"}, status_code=422
            )

        item_type = data.get("item_type")
        if item_type and item_type not in ["tool", "prompt", "resource"]:
            return JSONResponse(
                {"detail": "item_type must be tool, prompt, or resource"}, status_code=422
            )

        if not smart_server or not smart_server.search_service:
            return JSONResponse({"detail": "Search service not ready"}, status_code=503)

        org_id = get_org_id(request)
        result = await smart_server.search_service.search(
            query=query,
            item_type=item_type,
            limit=limit,
            skill_limit=data.get("skill_limit", 3),
            skill_threshold=skill_threshold,
            tool_threshold=tool_threshold,
            include_schemas=data.get("include_schemas", True),
            strategy=strategy,
            org_id=org_id,
        )

        return JSONResponse(smart_server.search_service.to_dict(result))

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        logger.error(f"API search error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def search_skills_endpoint(request):
    """GET /api/v1/search/skills - Search skills only"""
    try:
        query = request.query_params.get("query", "")
        if not query:
            return JSONResponse({"detail": "query is required"}, status_code=422)

        limit = int(request.query_params.get("limit", 5))
        threshold = float(request.query_params.get("threshold", 0.4))

        if not smart_server or not smart_server.search_service:
            return JSONResponse({"detail": "Search service not ready"}, status_code=503)

        skills = await smart_server.search_service.search_skills_only(
            query=query, limit=limit, threshold=threshold
        )

        return JSONResponse(
            [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "score": s.score,
                    "tool_count": s.tool_count,
                }
                for s in skills
            ]
        )

    except Exception as e:
        logger.error(f"Search skills error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def search_tools_endpoint(request):
    """GET /api/v1/search/tools - Search tools only"""
    try:
        query = request.query_params.get("query", "")
        if not query:
            return JSONResponse({"detail": "query is required"}, status_code=422)

        limit = int(request.query_params.get("limit", 10))
        threshold = float(request.query_params.get("threshold", 0.3))
        item_type = request.query_params.get("item_type")
        skill_ids_param = request.query_params.get("skill_ids")
        skill_ids = skill_ids_param.split(",") if skill_ids_param else None

        if not smart_server or not smart_server.search_service:
            return JSONResponse({"detail": "Search service not ready"}, status_code=503)

        tools = await smart_server.search_service.search_tools_only(
            query=query, skill_ids=skill_ids, item_type=item_type, limit=limit, threshold=threshold
        )

        return JSONResponse(
            [
                {
                    "id": t.id,
                    "db_id": t.db_id,
                    "type": t.type,
                    "name": t.name,
                    "description": t.description,
                    "score": t.score,
                    "skill_ids": t.skill_ids,
                    "primary_skill_id": t.primary_skill_id,
                }
                for t in tools
            ]
        )

    except Exception as e:
        logger.error(f"Search tools error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


def _serialize_record(record: dict) -> dict:
    """Serialize a database record for JSON response, converting datetime/Decimal fields."""
    from datetime import datetime, date
    from decimal import Decimal

    result = {}
    for key, value in record.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif hasattr(value, "value"):  # Enum
            result[key] = value.value
        else:
            result[key] = value
    return result


def _serialize_tool(tool: dict) -> dict:
    """Serialize tool dict for JSON response."""
    return _serialize_record(tool)


async def get_default_tools_endpoint(request):
    """GET /api/v1/tools/defaults - Get default tools (meta-tools)

    Returns tools marked with is_default=True in the database.
    These are the gateway tools always available in agent context:
    - discover, get_tool_schema, execute
    - list_skills, list_prompts, get_prompt, list_resources, read_resource
    """
    try:
        if not smart_server or not smart_server.sync_service:
            return JSONResponse({"detail": "Tool service not ready"}, status_code=503)

        tool_service = smart_server.sync_service.tool_service
        default_tools = await tool_service.get_default_tools()

        # Serialize datetime fields for JSON response
        serialized_tools = [_serialize_tool(t) for t in default_tools]

        return JSONResponse({"tools": serialized_tools, "count": len(serialized_tools)})

    except Exception as e:
        logger.error(f"Get default tools error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


# ==============================================================================
# AGGREGATOR API ENDPOINTS (/api/v1/aggregator/*)
# ==============================================================================


def _serialize_server(server: dict) -> dict:
    """Serialize server dict for JSON response."""
    return _serialize_record(server)


async def aggregator_list_servers_endpoint(request):
    """GET /api/v1/aggregator/servers - List registered MCP servers"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        status_filter = request.query_params.get("status")
        if status_filter:
            from tests.contracts.aggregator.data_contract import ServerStatus

            status_filter = ServerStatus(status_filter)

        org_id = get_org_id(request)
        servers = await smart_server.aggregator_service.list_servers(
            status=status_filter, org_id=org_id
        )
        return JSONResponse([_serialize_server(s) for s in servers])

    except Exception as e:
        logger.error(f"List servers error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_register_server_endpoint(request):
    """POST /api/v1/aggregator/servers - Register a new MCP server"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        body = await request.body()
        data = json.loads(body) if body else {}

        if not data.get("name") or not data.get("transport_type"):
            return JSONResponse({"detail": "name and transport_type are required"}, status_code=422)

        # Inject org_id from auth context into server config
        org_id = get_org_id(request)
        if org_id:
            data["org_id"] = org_id
            data["is_global"] = False  # Org-scoped server
        else:
            data.setdefault("is_global", True)

        server = await smart_server.aggregator_service.register_server(data)
        return JSONResponse(_serialize_server(server), status_code=201)

    except Exception as e:
        logger.error(f"Register server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_get_server_endpoint(request):
    """GET /api/v1/aggregator/servers/{server_id} - Get server details"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        server_id = request.path_params.get("server_id")
        server = await smart_server.aggregator_service.get_server(server_id)

        if server is None:
            return JSONResponse({"detail": "Server not found"}, status_code=404)

        return JSONResponse(_serialize_server(server))

    except Exception as e:
        logger.error(f"Get server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_remove_server_endpoint(request):
    """DELETE /api/v1/aggregator/servers/{server_id} - Remove a server"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        server_id = request.path_params.get("server_id")
        await smart_server.aggregator_service.remove_server(server_id)
        return JSONResponse({"status": "removed"})

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Remove server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_connect_server_endpoint(request):
    """POST /api/v1/aggregator/servers/{server_id}/connect - Connect to a server"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        server_id = request.path_params.get("server_id")
        success = await smart_server.aggregator_service.connect_server(server_id)
        return JSONResponse({"status": "connected" if success else "failed", "success": success})

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Connect server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_disconnect_server_endpoint(request):
    """POST /api/v1/aggregator/servers/{server_id}/disconnect - Disconnect from a server"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        server_id = request.path_params.get("server_id")
        success = await smart_server.aggregator_service.disconnect_server(server_id)
        return JSONResponse({"status": "disconnected" if success else "failed", "success": success})

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Disconnect server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_refresh_server_endpoint(request):
    """POST /api/v1/aggregator/servers/{server_id}/refresh - Re-discover tools"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        server_id = request.path_params.get("server_id")
        tools = await smart_server.aggregator_service.discover_tools(server_id)
        return JSONResponse({"tools_discovered": len(tools)})

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Refresh server error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


async def aggregator_health_endpoint(request):
    """GET /api/v1/aggregator/health - Aggregator state overview"""
    try:
        if not smart_server or not smart_server.aggregator_service:
            return JSONResponse({"detail": "Aggregator service not available"}, status_code=503)

        state = await smart_server.aggregator_service.get_state()
        return JSONResponse(state)

    except Exception as e:
        logger.error(f"Aggregator health error: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)


# ==============================================================================
# ROUTE REGISTRATION
# ==============================================================================

# Register routes
app.router.routes.append(Route("/health", health_check))
# /discover endpoint removed - use /search instead
app.router.routes.append(Route("/search", search_endpoint, methods=["POST", "OPTIONS"]))  # Legacy
app.router.routes.append(Route("/sync", sync_endpoint, methods=["POST", "OPTIONS"]))
app.router.routes.append(
    Route("/progress/{operation_id}/stream", progress_stream_endpoint, methods=["GET"])
)

# Skill API endpoints
app.router.routes.append(Route("/api/v1/skills", skills_list_endpoint, methods=["GET"]))
app.router.routes.append(Route("/api/v1/skills", skills_create_endpoint, methods=["POST"]))
app.router.routes.append(
    Route("/api/v1/skills/classify", skills_classify_endpoint, methods=["POST"])
)
app.router.routes.append(
    Route("/api/v1/skills/suggestions", skills_suggestions_endpoint, methods=["GET"])
)
app.router.routes.append(Route("/api/v1/skills/{skill_id}", skills_get_endpoint, methods=["GET"]))
app.router.routes.append(
    Route("/api/v1/skills/{skill_id}", skills_delete_endpoint, methods=["DELETE"])
)
app.router.routes.append(
    Route("/api/v1/skills/{skill_id}/tools", skills_tools_endpoint, methods=["GET"])
)

# Search API endpoints
app.router.routes.append(Route("/api/v1/search", api_search_endpoint, methods=["POST", "OPTIONS"]))
app.router.routes.append(Route("/api/v1/search/skills", search_skills_endpoint, methods=["GET"]))
app.router.routes.append(Route("/api/v1/search/tools", search_tools_endpoint, methods=["GET"]))

# Tools API endpoints
app.router.routes.append(
    Route("/api/v1/tools/defaults", get_default_tools_endpoint, methods=["GET"])
)

# Aggregator API endpoints
app.router.routes.append(
    Route("/api/v1/aggregator/servers", aggregator_list_servers_endpoint, methods=["GET"])
)
app.router.routes.append(
    Route("/api/v1/aggregator/servers", aggregator_register_server_endpoint, methods=["POST"])
)
app.router.routes.append(
    Route("/api/v1/aggregator/health", aggregator_health_endpoint, methods=["GET"])
)
app.router.routes.append(
    Route("/api/v1/aggregator/servers/{server_id}", aggregator_get_server_endpoint, methods=["GET"])
)
app.router.routes.append(
    Route(
        "/api/v1/aggregator/servers/{server_id}",
        aggregator_remove_server_endpoint,
        methods=["DELETE"],
    )
)
app.router.routes.append(
    Route(
        "/api/v1/aggregator/servers/{server_id}/connect",
        aggregator_connect_server_endpoint,
        methods=["POST"],
    )
)
app.router.routes.append(
    Route(
        "/api/v1/aggregator/servers/{server_id}/disconnect",
        aggregator_disconnect_server_endpoint,
        methods=["POST"],
    )
)
app.router.routes.append(
    Route(
        "/api/v1/aggregator/servers/{server_id}/refresh",
        aggregator_refresh_server_endpoint,
        methods=["POST"],
    )
)

# ==============================================================================
# DIRECT EXECUTION (for testing)
# ==============================================================================


async def run_stdio(meta_tools_only: bool = False):
    """Run as stdio MCP server (for Claude Code / isA_Vibe integration)

    This mode allows isA_MCP to be used directly by Claude Code SDK
    without needing an HTTP wrapper.

    OPTIMIZATION: Uses skip_sync=True to skip PostgreSQL/Qdrant sync,
    reducing startup time from ~5s to ~2s. Claude SDK doesn't need
    our search functionality - it has its own tool selection.

    Args:
        meta_tools_only: If True, only expose 8 meta-tools. Claude must use
                        discover() -> get_tool_schema() -> execute() workflow.

    Usage:
        python main.py --stdio                    # All tools visible
        python main.py --stdio --meta-tools-only  # Only meta-tools visible

    In isA_Vibe MCP config:
        "isa_mcp": {
            "command": "python",
            "args": ["/path/to/isA_MCP/main.py", "--stdio", "--meta-tools-only"],
        }
    """
    global smart_server, mcp

    mode_desc = "meta-tools-only" if meta_tools_only else "all-tools"
    logger.info(f"Starting isA_MCP in stdio mode ({mode_desc})...")

    # Initialize with skip_sync=True for fast startup (~2s instead of ~5s)
    # Sync services not needed for stdio - Claude SDK has its own tool selection
    smart_server = SmartMCPServer()
    mcp = await smart_server.initialize(skip_sync=True, meta_tools_only=meta_tools_only)

    tools = await mcp.list_tools()
    prompts = await mcp.list_prompts()
    resources = await mcp.list_resources()

    if meta_tools_only and smart_server.internal_mcp:
        internal_tools = await smart_server.internal_mcp.list_tools()
        logger.info(
            f"isA_MCP stdio ready: {len(tools)} meta-tools visible, {len(internal_tools)} hidden"
        )
    else:
        logger.info(
            f"isA_MCP stdio ready: {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources"
        )

    # Run stdio server - this blocks until stdin closes
    # FastMCP provides run_stdio_async() for stdio transport
    await mcp.run_stdio_async()

    # Cleanup on exit
    if smart_server and smart_server.consul_registry:
        try:
            smart_server.consul_registry.deregister()
            logger.debug("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister from Consul: {e}")

    logger.info("stdio server shutdown complete")


def main():
    """Run server directly (for testing without supervisor)

    Modes:
        --stdio                   Run as stdio MCP server (for Claude Code / SDK integration)
        --meta-tools-only         Only expose 8 meta-tools (discover, execute, etc.)
        (default)                 Run as HTTP server with hot reload

    Examples:
        python main.py                              # HTTP mode, all tools
        python main.py --stdio                      # stdio mode, all tools
        python main.py --stdio --meta-tools-only   # stdio mode, only meta-tools
        META_TOOLS_ONLY=true python main.py        # HTTP mode, only meta-tools
    """
    import uvicorn
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="isA_MCP Server")
    parser.add_argument("--port", "-p", type=int, default=8081, help="HTTP server port")
    parser.add_argument(
        "--stdio", action="store_true", help="Run as stdio MCP server (for Claude Code integration)"
    )
    parser.add_argument(
        "--meta-tools-only",
        action="store_true",
        help="Only expose 8 meta-tools (discover, get_tool_schema, execute, list_skills)",
    )
    args = parser.parse_args()

    if args.stdio:
        # stdio mode for Claude Code / isA_Vibe SDK integration
        # Use CLI flag or fall back to config setting
        meta_tools_only = args.meta_tools_only or settings.meta_tools_only
        asyncio.run(run_stdio(meta_tools_only=meta_tools_only))
    else:
        # HTTP mode with hot reload (existing behavior)
        # meta_tools_only is controlled by META_TOOLS_ONLY env var (in settings)
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=args.port,
            reload=True,  # Enable hot reload
            log_level="info",
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
