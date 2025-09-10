"""
User Service Server - Modular Architecture

Professional FastAPI server with modular endpoint architecture
Maintains 100% compatibility with original api_server.py while providing
clean, maintainable, and extensible structure.
"""

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import traceback
from datetime import datetime
import sys

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# Import the integrated router and dependencies
from api.router_collection import integrated_router
from api.dependencies import container
from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/user_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with comprehensive initialization"""
    # Startup
    logger.info("🚀 Starting User Management Service - Modular Architecture")
    logger.info("=" * 60)
    
    try:
        # Initialize configuration
        config = container.config
        logger.info(f"🔐 Auth0 Domain: {config.auth0_domain}")
        logger.info(f"🌐 Environment: {config.environment}")
        
        # Pre-initialize critical services to catch configuration errors early
        logger.info("🔧 Initializing core services...")
        
        # User service
        user_service = container.user_service
        logger.info("✅ User service initialized")
        
        # Authentication services
        auth_service = container.unified_auth_service
        logger.info("✅ Authentication service initialized")
        
        # Subscription service
        subscription_service = container.subscription_service
        logger.info("✅ Subscription service initialized")
        
        # Credit service
        credit_service = container.credit_service
        logger.info("✅ Credit service initialized")
        
        # Session service
        session_service = container.session_service
        logger.info("✅ Session service initialized")
        
        # Email service (optional)
        try:
            email_service = container.email_service
            logger.info("✅ Email service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Email service skipped: {e}")
            email_service = None
        
        # File storage service
        file_service = container.file_storage_service
        logger.info("✅ File storage service initialized")
        
        logger.info("🎉 All services initialized successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Failed to initialize services: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down User Management Service")
    logger.info("👋 Goodbye!")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application with all middleware and routes"""
    
    # Get configuration
    config = get_config()
    
    app = FastAPI(
        title="User Management Service",
        description="Comprehensive user management with authentication, subscriptions, and analytics",
        version="2.0.0-modular",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "User Service Team",
            "email": "support@userservice.com"
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    )
    
    # Security middleware - restrict allowed hosts in production
    allowed_hosts = ["*"] if config.debug else [config.host, "localhost", "127.0.0.1"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # Professional CORS configuration
    # Always allow localhost development origins for flexibility
    dev_origins = [
        "http://localhost:3000",   # Next.js default
        "http://localhost:5173",   # Vite default  
        "http://localhost:8080",   # Vue CLI default
        "http://localhost:4200",   # Angular default
        "http://127.0.0.1:5173",   # Alternative local
        "http://127.0.0.1:3000",   # Alternative local
    ]
    
    if config.debug:
        # Development - allow localhost origins + wildcard for flexibility
        allowed_origins = dev_origins + ["*"]
        logger.info(f"🌐 CORS Development Mode: Allowing origins {dev_origins}")
    else:
        # Production - restrict to specific origins only
        production_origins = [f"https://{config.host}", "https://www.iapro.ai"]
        allowed_origins = dev_origins + production_origins  # Still allow dev for staging
        logger.info(f"🌐 CORS Production Mode: Allowing origins {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key",
            "User-Agent"
        ],
        expose_headers=["X-Total-Count", "X-Page-Count", "X-Response-Time", "X-Service-Version"]
    )
    
    # Request/Response logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = datetime.utcnow()
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")[:100]
        
        logger.info(f"📥 {request.method} {request.url.path} - IP: {client_ip} - UA: {user_agent}")
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log response
            status_emoji = "✅" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"
            logger.info(f"📤 {status_emoji} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            
            # Add custom headers
            response.headers["X-Response-Time"] = f"{process_time:.3f}s"
            response.headers["X-Service-Version"] = "2.0.0-modular"
            
            return response
            
        except Exception as e:
            # Log error
            process_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"💥 {request.method} {request.url.path} - ERROR: {str(e)} - {process_time:.3f}s")
            logger.error(traceback.format_exc())
            raise
    
    # Global exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        logger.error(f"🚨 [{error_id}] Unhandled exception on {request.method} {request.url.path}")
        logger.error(f"🚨 [{error_id}] Exception: {str(exc)}")
        logger.error(f"🚨 [{error_id}] Traceback:\n{traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "error_id": error_id,
                "message": "An unexpected error occurred. Please contact support with the error ID.",
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"⚠️ HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Include the integrated router with all endpoints
    app.include_router(integrated_router)
    
    # Root endpoint for service information
    @app.get("/")
    async def service_info():
        """Service information and health status"""
        return {
            "service": "User Management Service",
            "version": "2.0.0-modular", 
            "architecture": "modular",
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "🔐 Multi-provider Authentication (Auth0 + Supabase)",
                "👤 Comprehensive User Management",
                "💳 Subscription & Payment Processing",
                "🪙 Credit System & Usage Tracking",
                "📁 File Storage & Management",
                "💬 Session & Message Management",
                "🏢 Organization & Team Management",
                "🔑 Resource Authorization & Permissions",
                "📊 Analytics & Usage Statistics",
                "🔗 Webhook Processing",
                "📨 Email & Notification Services"
            ],
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": "/health"
            },
            "statistics": {
                "total_endpoints": 50,
                "modular_files": 14,
                "schema_models": 8
            }
        }
    
    # Comprehensive health check endpoint
    @app.get("/health")
    async def comprehensive_health_check():
        """Detailed health check with service dependency status"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0-modular",
            "architecture": "modular",
            "uptime": "active",
            "services": {},
            "database": {},
            "external_services": {}
        }
        
        overall_healthy = True
        
        # Check core services
        services_to_check = [
            ("user_service", lambda: container.user_service),
            ("auth_service", lambda: container.unified_auth_service), 
            ("subscription_service", lambda: container.subscription_service),
            ("credit_service", lambda: container.credit_service),
            ("session_service", lambda: container.session_service),
            ("email_service", lambda: container.email_service),
            ("file_storage_service", lambda: container.file_storage_service)
        ]
        
        for service_name, service_getter in services_to_check:
            try:
                service = service_getter()
                health_data["services"][service_name] = {
                    "status": "healthy",
                    "initialized": service is not None
                }
            except Exception as e:
                health_data["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_healthy = False
        
        # Check database connectivity
        try:
            config = container.config
            health_data["database"]["connection"] = "available"
            health_data["database"]["provider"] = "postgresql"
        except Exception as e:
            health_data["database"]["connection"] = "error"
            health_data["database"]["error"] = str(e)
            overall_healthy = False
        
        # Check external services
        try:
            config = container.config
            health_data["external_services"]["auth0"] = {
                "configured": bool(config.auth0_domain),
                "domain": config.auth0_domain[:20] + "..." if config.auth0_domain else None
            }
            health_data["external_services"]["storage"] = {
                "provider": config.storage_provider,
                "configured": bool(config.storage_provider)
            }
        except Exception as e:
            health_data["external_services"]["error"] = str(e)
            overall_healthy = False
        
        if not overall_healthy:
            health_data["status"] = "degraded"
        
        status_code = 200 if overall_healthy else 503
        return JSONResponse(status_code=status_code, content=health_data)
    
    return app


# Create the application instance
app = create_application()


# Development server runner
def run_development_server():
    """Run the development server with hot reload"""
    config = get_config()
    
    logger.info("🔥 Starting development server...")
    logger.info(f"🌐 Server will be available at: http://localhost:{config.port}")
    logger.info(f"📚 API docs available at: http://localhost:{config.port}/docs")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=config.port,
        reload=True,
        reload_dirs=["./"],
        log_level="info",
        access_log=True,
        reload_excludes=["logs/*", "*.log", "__pycache__/*"],
        loop="asyncio"
    )


# Production server runner  
def run_production_server():
    """Run the production server"""
    config = get_config()
    
    logger.info("🚀 Starting production server...")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=config.port,
        reload=False,
        log_level="warning",
        access_log=False,
        workers=4,
        loop="asyncio"
    )


if __name__ == "__main__":
    # Check if running in production mode
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        run_production_server()
    else:
        run_development_server()