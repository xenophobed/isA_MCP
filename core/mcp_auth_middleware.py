#!/usr/bin/env python3
"""
MCP Service Authentication Middleware
Optional API key authentication for MCP endpoints
"""

import os
import logging
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """
    Optional authentication middleware for MCP service endpoints
    
    Features:
    - Environment-driven authentication (REQUIRE_MCP_AUTH=false by default)
    - API key validation for MCP endpoints
    - Bypass authentication for health checks and static files
    - Support for multiple API key formats
    - Integration with existing security manager
    """
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        
        # Get authentication settings from environment or config
        self.require_auth = self._get_auth_setting()
        self.api_keys = self._load_api_keys()
        
        # Paths that bypass authentication
        self.bypass_paths = {
            "/health",
            "/static",
            "/portal",
            "/",
            "/admin"  # Portal access (separate auth)
        }
        
        # MCP paths that require authentication when enabled
        self.mcp_paths = {
            "/mcp/",
            "/discover",
            "/stats", 
            "/capabilities"
        }
        
        if self.require_auth:
            logger.info("MCP authentication enabled - API keys required")
            logger.info(f"Loaded {len(self.api_keys)} API keys for authentication")
        else:
            logger.info("MCP authentication disabled - open access mode")
            logger.info(f"Environment REQUIRE_MCP_AUTH: {repr(os.getenv('REQUIRE_MCP_AUTH', 'not set'))}")
            logger.info(f"Environment MCP_API_KEY: {repr(os.getenv('MCP_API_KEY', 'not set')[:20])}")
    
    def _get_auth_setting(self) -> bool:
        """Get authentication requirement from environment or config"""
        # Check environment variable first (config system loads .env into environment)
        env_auth = os.getenv('REQUIRE_MCP_AUTH', 'false').lower()
        if env_auth in ['true', '1', 'yes', 'on']:
            return True
        
        # Check config setting as fallback
        try:
            from core.config import get_settings
            settings = get_settings()
            config_auth = getattr(settings, 'require_mcp_auth', False)
            if config_auth:
                return True
        except Exception as e:
            logger.debug(f"Could not load config settings: {e}")
            
        return False
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment or config"""
        api_keys = {}
        
        # Load from environment variables (config system loads .env into environment)
        mcp_api_key = os.getenv('MCP_API_KEY')
        if mcp_api_key:
            api_keys[mcp_api_key] = "Environment API Key"
        
        # Load additional keys from environment (comma-separated)
        mcp_api_keys = os.getenv('MCP_API_KEYS', '')
        if mcp_api_keys:
            for key in mcp_api_keys.split(','):
                key = key.strip()
                if key:
                    api_keys[key] = "Environment API Key (Multi)"
        
        # Load from config as additional source
        try:
            from core.config import get_settings
            settings = get_settings()
            config_keys = getattr(settings, 'mcp_api_keys', {})
            if isinstance(config_keys, dict):
                api_keys.update(config_keys)
            
            # Also check legacy api_keys field
            legacy_keys = getattr(settings, 'api_keys', {})
            if isinstance(legacy_keys, dict):
                api_keys.update(legacy_keys)
                
        except Exception as e:
            logger.debug(f"Could not load config API keys: {e}")
        
        # Load from security manager if available
        try:
            from core.auth import SecurityManager
            security_manager = SecurityManager()
            if hasattr(security_manager, 'api_keys'):
                api_keys.update(security_manager.api_keys)
        except Exception as e:
            logger.debug(f"Could not load security manager API keys: {e}")
        
        logger.info(f"Loaded {len(api_keys)} API keys for MCP authentication")
        return api_keys
    
    def _should_bypass_auth(self, path: str) -> bool:
        """Check if path should bypass authentication"""
        # Bypass paths
        for bypass_path in self.bypass_paths:
            if path.startswith(bypass_path):
                return True
        
        # Static files
        if "/static/" in path:
            return True
            
        return False
    
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication"""
        if not self.require_auth:
            return False
            
        if self._should_bypass_auth(path):
            return False
        
        # Check if it's an MCP path
        for mcp_path in self.mcp_paths:
            if path.startswith(mcp_path):
                return True
        
        # Default: require auth for unknown paths when auth is enabled
        return True
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header:
            return api_key_header.strip()
        
        # Check X-MCP-API-Key header (MCP-specific)
        mcp_key_header = request.headers.get("X-MCP-API-Key", "")
        if mcp_key_header:
            return mcp_key_header.strip()
        
        # Check query parameter (less secure, but convenient for testing)
        api_key_param = request.query_params.get("api_key", "")
        if api_key_param:
            return api_key_param.strip()
        
        return None
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key against stored keys"""
        if not api_key or not self.api_keys:
            return False
        
        # Direct key match
        if api_key in self.api_keys:
            return True
        
        # Check if it starts with mcp_ prefix (our format)
        if api_key.startswith("mcp_") and api_key in self.api_keys:
            return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        path = request.url.path
        
        # Check if authentication is required for this path
        if not self._requires_auth(path):
            # No authentication required, proceed normally
            return await call_next(request)
        
        # Authentication required - extract and validate API key
        api_key = self._extract_api_key(request)
        
        if not api_key:
            logger.warning(f"Authentication required but no API key provided for {path}")
            return JSONResponse(
                {
                    "error": "Authentication required",
                    "message": "API key required for MCP access. Include in Authorization header or X-API-Key header.",
                    "status": "unauthorized"
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Auth-Methods": "Bearer token, X-API-Key header, X-MCP-API-Key header"
                }
            )
        
        if not self._validate_api_key(api_key):
            logger.warning(f"Invalid API key provided for {path}: {api_key[:8]}...")
            return JSONResponse(
                {
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid for MCP access.",
                    "status": "forbidden"
                },
                status_code=403
            )
        
        # Authentication successful
        logger.debug(f"Authenticated request to {path} with API key {api_key[:8]}...")
        
        # Add user context to request state for downstream use
        request.state.authenticated = True
        request.state.api_key = api_key
        request.state.user_info = self.api_keys.get(api_key, "Unknown User")
        
        # Proceed with the request
        return await call_next(request)


def add_mcp_auth_middleware(app, config: Optional[Dict[str, Any]] = None):
    """
    Add MCP authentication middleware to the application
    
    Args:
        app: Starlette/FastAPI application
        config: Optional configuration dictionary
    """
    # Create middleware instance for logging info
    temp_middleware = MCPAuthMiddleware(app, config)
    
    # Add middleware to app with proper parameters
    app.add_middleware(MCPAuthMiddleware, config=config)
    
    # Log middleware setup
    if temp_middleware.require_auth:
        logger.info(f"MCP Authentication middleware added - {len(temp_middleware.api_keys)} API keys configured")
    else:
        logger.info("MCP Authentication middleware added - authentication disabled")
    
    return temp_middleware


def generate_mcp_api_key(description: str = "Generated MCP API Key") -> str:
    """
    Generate a new MCP API key
    
    Args:
        description: Description for the API key
        
    Returns:
        Generated API key string
    """
    import secrets
    api_key = f"mcp_{secrets.token_urlsafe(32)}"
    
    logger.info(f"Generated new MCP API key: {api_key[:8]}... ({description})")
    return api_key


def validate_mcp_api_key(api_key: str) -> bool:
    """
    Validate an MCP API key format
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if format is valid
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    # Check length (should be reasonable)
    if len(api_key) < 16:
        return False
    
    # Check prefix if it's our format
    if api_key.startswith("mcp_"):
        # Our format: mcp_ + base64 encoded string (typically 43 chars) = ~47 total
        return len(api_key) >= 36 and len(api_key) <= 50
    
    # Accept other formats too (for compatibility)
    return len(api_key) >= 16 and len(api_key) <= 128


# Helper function for environment setup
def setup_mcp_auth_env(api_key: Optional[str] = None, require_auth: bool = False):
    """
    Setup environment variables for MCP authentication
    
    Args:
        api_key: API key to set (generates one if None)
        require_auth: Whether to require authentication
    """
    if api_key is None:
        api_key = generate_mcp_api_key("Environment Setup")
    
    os.environ['MCP_API_KEY'] = api_key
    os.environ['REQUIRE_MCP_AUTH'] = 'true' if require_auth else 'false'
    
    logger.info(f"MCP authentication environment configured - Auth required: {require_auth}")
    if require_auth:
        logger.info(f"MCP API Key: {api_key[:8]}...")
    
    return api_key