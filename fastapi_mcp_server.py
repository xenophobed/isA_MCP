#!/usr/bin/env python
"""
FastAPI Wrapper for MCP Server
Provides scalable, configurable deployment with health checks and metrics
"""
import asyncio
import uvicorn
import os
import threading
import time
from typing import Dict, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import the MCP server components
from mcp_server import mcp, register_all_components, initialize_database
from core.logging import get_logger
from core.monitoring import monitor_manager

logger = get_logger(__name__)

# Configuration from environment variables
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "3000"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVICE_NAME = os.getenv("SERVICE_NAME", "mcp-server")
VERSION = os.getenv("VERSION", "1.0.0")

# Global variables for server management
mcp_server_thread: Optional[threading.Thread] = None
mcp_server_running = False
startup_time = datetime.now()

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    mcp_server_running: bool
    environment: str
    version: str
    service_name: str

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]
    timestamp: str
    mcp_server_status: str

def run_mcp_server():
    """Run MCP server in a separate thread"""
    global mcp_server_running
    
    try:
        logger.info(f"Starting MCP server on port {MCP_PORT}")
        mcp_server_running = True
        
        # Initialize database and components
        initialize_database()
        register_all_components()
        
        # Run MCP server with custom transport settings
        mcp.run(
            transport="streamable-http",
            host=MCP_HOST,
            port=MCP_PORT
        )
        
    except Exception as e:
        logger.error(f"MCP server failed to start: {e}")
        mcp_server_running = False
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage FastAPI application lifespan"""
    global mcp_server_thread, mcp_server_running
    
    logger.info("Starting FastAPI MCP Server wrapper...")
    
    # Start MCP server in background thread
    mcp_server_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_server_thread.start()
    
    # Wait a bit for MCP server to start
    await asyncio.sleep(2)
    
    if not mcp_server_running:
        logger.error("Failed to start MCP server")
        raise RuntimeError("MCP server failed to start")
    
    logger.info(f"MCP server started successfully on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"FastAPI wrapper starting on {FASTAPI_HOST}:{FASTAPI_PORT}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down MCP server...")
    mcp_server_running = False

# Create FastAPI app with lifespan management
app = FastAPI(
    title="MCP Server API Gateway",
    description="Scalable FastAPI wrapper for MCP (Model Context Protocol) Server",
    version=VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with service information"""
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "environment": ENVIRONMENT,
        "mcp_endpoint": f"http://{MCP_HOST}:{MCP_PORT}/mcp",
        "status": "running" if mcp_server_running else "stopped",
        "documentation": "/docs",
        "health_check": "/health",
        "metrics": "/metrics"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    uptime = (datetime.now() - startup_time).total_seconds()
    
    # Check if MCP server thread is alive
    thread_alive = mcp_server_thread.is_alive() if mcp_server_thread else False
    
    status = "healthy" if (mcp_server_running and thread_alive) else "unhealthy"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        mcp_server_running=mcp_server_running and thread_alive,
        environment=ENVIRONMENT,
        version=VERSION,
        service_name=SERVICE_NAME
    )

@app.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe"""
    if not mcp_server_running:
        raise HTTPException(status_code=503, detail="MCP server not running")
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe"""
    if not (mcp_server_running and mcp_server_thread and mcp_server_thread.is_alive()):
        raise HTTPException(status_code=503, detail="MCP server not ready")
    return {"status": "ready"}

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get application and MCP server metrics"""
    try:
        # Get metrics from monitor manager
        mcp_metrics = monitor_manager.get_metrics() if monitor_manager else {}
        
        # Add FastAPI wrapper metrics
        wrapper_metrics = {
            "fastapi_uptime_seconds": (datetime.now() - startup_time).total_seconds(),
            "mcp_port": MCP_PORT,
            "fastapi_port": FASTAPI_PORT,
            "environment": ENVIRONMENT,
            "version": VERSION,
            "mcp_server_thread_alive": mcp_server_thread.is_alive() if mcp_server_thread else False
        }
        
        combined_metrics = {
            "wrapper": wrapper_metrics,
            "mcp_server": mcp_metrics
        }
        
        return MetricsResponse(
            metrics=combined_metrics,
            timestamp=datetime.now().isoformat(),
            mcp_server_status="running" if mcp_server_running else "stopped"
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "mcp_server": {
            "host": MCP_HOST,
            "port": MCP_PORT,
            "endpoint": f"http://{MCP_HOST}:{MCP_PORT}/mcp"
        },
        "fastapi_wrapper": {
            "host": FASTAPI_HOST,
            "port": FASTAPI_PORT
        },
        "environment": ENVIRONMENT,
        "service_name": SERVICE_NAME,
        "version": VERSION,
        "startup_time": startup_time.isoformat()
    }

@app.post("/admin/restart")
async def restart_mcp_server():
    """Admin endpoint to restart MCP server (for debugging)"""
    global mcp_server_thread, mcp_server_running
    
    if ENVIRONMENT == "production":
        raise HTTPException(status_code=403, detail="Restart not allowed in production")
    
    try:
        # Stop current server
        mcp_server_running = False
        if mcp_server_thread and mcp_server_thread.is_alive():
            # Give it time to stop gracefully
            time.sleep(2)
        
        # Start new server
        mcp_server_thread = threading.Thread(target=run_mcp_server, daemon=True)
        mcp_server_thread.start()
        
        # Wait for startup
        await asyncio.sleep(2)
        
        return {"status": "restarted", "mcp_server_running": mcp_server_running}
        
    except Exception as e:
        logger.error(f"Failed to restart MCP server: {e}")
        raise HTTPException(status_code=500, detail=f"Restart failed: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if ENVIRONMENT != "production" else "An error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

def main():
    """Main entry point"""
    print(f"🚀 Starting FastAPI MCP Server Gateway")
    print(f"🔧 Environment: {ENVIRONMENT}")
    print(f"📡 MCP Server: {MCP_HOST}:{MCP_PORT}")
    print(f"🌐 FastAPI Gateway: {FASTAPI_HOST}:{FASTAPI_PORT}")
    print(f"📖 Documentation: http://{FASTAPI_HOST}:{FASTAPI_PORT}/docs")
    
    # Configure uvicorn based on environment
    if ENVIRONMENT == "development":
        uvicorn.run(
            "fastapi_mcp_server:app",
            host=FASTAPI_HOST,
            port=FASTAPI_PORT,
            reload=True,
            log_level="info"
        )
    else:
        uvicorn.run(
            app,
            host=FASTAPI_HOST,
            port=FASTAPI_PORT,
            workers=1,  # Single worker to avoid MCP port conflicts
            log_level="info",
            access_log=True
        )

if __name__ == "__main__":
    main()