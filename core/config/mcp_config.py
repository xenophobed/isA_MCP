#!/usr/bin/env python3
"""MCP Server main configuration"""
import os
from dataclasses import dataclass, field
from typing import Optional
from .logging_config import LoggingConfig
from .infra_config import InfraConfig

def _bool(val: str) -> bool:
    return val.lower() == "true"

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default

@dataclass
class MCPConfig:
    """Main MCP server configuration with all sub-configs"""
    # Server
    host: str = "0.0.0.0"
    port: int = 8081
    server_name: str = "MCP Server"
    debug: bool = False

    # Authentication
    require_auth: bool = False
    require_mcp_auth: bool = False
    mcp_api_key: Optional[str] = None
    auth_service_url: Optional[str] = None
    authz_service_url: Optional[str] = None

    # External APIs
    openai_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    composio_api_key: Optional[str] = None
    composio_cache_dir: str = "/app/cache"

    # ISA Model Service
    isa_service_url: str = "http://localhost:8082"
    isa_api_key: Optional[str] = None
    require_isa_auth: bool = False

    # Supabase Database
    supabase_local_url: str = "http://localhost:54321"
    supabase_local_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    db_schema: str = "dev"

    # Performance Optimization
    lazy_load_ai_selectors: bool = True
    lazy_load_external_services: bool = True

    # Sub-configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    infrastructure: InfraConfig = field(default_factory=InfraConfig)

    @classmethod
    def from_env(cls) -> 'MCPConfig':
        """Load complete configuration from environment"""
        return cls(
            # Server
            host=os.getenv("HOST", "0.0.0.0"),
            port=_int(os.getenv("MCP_PORT", "8081"), 8081),
            server_name=os.getenv("SERVER_NAME", "MCP Server"),
            debug=_bool(os.getenv("DEBUG", "false")),
            # Auth
            require_auth=_bool(os.getenv("REQUIRE_AUTH", "false")),
            require_mcp_auth=_bool(os.getenv("REQUIRE_MCP_AUTH", "false")),
            mcp_api_key=os.getenv("MCP_API_KEY"),
            auth_service_url=os.getenv("AUTH_SERVICE_URL"),
            authz_service_url=os.getenv("AUTHZ_SERVICE_URL"),
            # External APIs
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            brave_api_key=os.getenv("BRAVE_TOKEN") or os.getenv("BRAVE_API_KEY"),
            composio_api_key=os.getenv("COMPOSIO_API_KEY"),
            composio_cache_dir=os.getenv("COMPOSIO_CACHE_DIR", "/app/cache"),
            # ISA Service
            isa_service_url=os.getenv("ISA_SERVICE_URL", "http://localhost:8082"),
            isa_api_key=os.getenv("ISA_API_KEY"),
            require_isa_auth=_bool(os.getenv("REQUIRE_ISA_AUTH", "false")),
            # Supabase
            supabase_local_url=os.getenv("SUPABASE_LOCAL_URL", "http://localhost:54321"),
            supabase_local_anon_key=os.getenv("SUPABASE_LOCAL_ANON_KEY"),
            supabase_service_role_key=os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY"),
            db_schema=os.getenv("DB_SCHEMA", "dev"),
            # Optimization
            lazy_load_ai_selectors=_bool(os.getenv("LAZY_LOAD_AI_SELECTORS", "true")),
            lazy_load_external_services=_bool(os.getenv("LAZY_LOAD_EXTERNAL_SERVICES", "true")),
            # Load sub-configs
            logging=LoggingConfig.from_env(),
            infrastructure=InfraConfig.from_env()
        )
