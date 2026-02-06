#!/usr/bin/env python3
"""MCP Server main configuration"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
from .logging_config import LoggingConfig
from .infra_config import InfraConfig
from .consul_config import ConsulConfig
from .model_config import ModelConfig
from .service_config import ServiceConfig

def _bool(val: str) -> bool:
    return val.lower() == "true"

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default


# ===========================================
# MCP-Specific Resource Configuration
# ===========================================

@dataclass
class MCPQdrantConfig:
    """Qdrant collection names for MCP"""
    unified_collection: str = "mcp_unified_search"
    tool_collection: str = "mcp_tool_embeddings"
    prompt_collection: str = "mcp_prompt_embeddings"
    resource_collection: str = "mcp_resource_embeddings"
    skill_collection: str = "mcp_skills"
    document_collection: str = "mcp_document_embeddings"
    code_collection: str = "mcp_code_embeddings"

    @property
    def all_collections(self) -> List[str]:
        return [
            self.unified_collection,
            self.tool_collection,
            self.prompt_collection,
            self.resource_collection,
            self.skill_collection,
            self.document_collection,
            self.code_collection,
        ]

    @classmethod
    def from_env(cls) -> 'MCPQdrantConfig':
        prefix = os.getenv("MCP_QDRANT_PREFIX", "mcp")
        return cls(
            unified_collection=os.getenv("MCP_QDRANT_UNIFIED", f"{prefix}_unified_search"),
            tool_collection=os.getenv("MCP_QDRANT_TOOLS", f"{prefix}_tool_embeddings"),
            prompt_collection=os.getenv("MCP_QDRANT_PROMPTS", f"{prefix}_prompt_embeddings"),
            resource_collection=os.getenv("MCP_QDRANT_RESOURCES", f"{prefix}_resource_embeddings"),
            skill_collection=os.getenv("MCP_QDRANT_SKILLS", f"{prefix}_skills"),
            document_collection=os.getenv("MCP_QDRANT_DOCUMENTS", f"{prefix}_document_embeddings"),
            code_collection=os.getenv("MCP_QDRANT_CODE", f"{prefix}_code_embeddings"),
        )


@dataclass
class MCPMinIOConfig:
    """MinIO bucket names for MCP"""
    resources_bucket: str = "mcp-resources"
    cache_bucket: str = "mcp-cache"
    exports_bucket: str = "mcp-exports"

    @property
    def all_buckets(self) -> List[str]:
        return [self.resources_bucket, self.cache_bucket, self.exports_bucket]

    @classmethod
    def from_env(cls) -> 'MCPMinIOConfig':
        prefix = os.getenv("MCP_MINIO_PREFIX", "mcp")
        return cls(
            resources_bucket=os.getenv("MCP_MINIO_RESOURCES", f"{prefix}-resources"),
            cache_bucket=os.getenv("MCP_MINIO_CACHE", f"{prefix}-cache"),
            exports_bucket=os.getenv("MCP_MINIO_EXPORTS", f"{prefix}-exports"),
        )


@dataclass
class MCPRedisConfig:
    """Redis key prefixes for MCP"""
    tool_prefix: str = "mcp:tool:"
    prompt_prefix: str = "mcp:prompt:"
    resource_prefix: str = "mcp:resource:"
    embedding_prefix: str = "mcp:embedding:"
    session_prefix: str = "mcp:session:"
    rate_prefix: str = "mcp:rate:"
    cache_prefix: str = "mcp:cache:"

    @classmethod
    def from_env(cls) -> 'MCPRedisConfig':
        prefix = os.getenv("MCP_REDIS_PREFIX", "mcp")
        return cls(
            tool_prefix=f"{prefix}:tool:",
            prompt_prefix=f"{prefix}:prompt:",
            resource_prefix=f"{prefix}:resource:",
            embedding_prefix=f"{prefix}:embedding:",
            session_prefix=f"{prefix}:session:",
            rate_prefix=f"{prefix}:rate:",
            cache_prefix=f"{prefix}:cache:",
        )


@dataclass
class MCPPostgresConfig:
    """PostgreSQL schema and table names for MCP"""
    schema: str = "mcp"
    tools_table: str = "tools"
    prompts_table: str = "prompts"
    resources_table: str = "resources"
    skills_table: str = "skills"
    executions_table: str = "tool_executions"
    templates_table: str = "prompt_templates"
    cache_table: str = "resource_cache"
    servers_table: str = "aggregated_servers"

    @classmethod
    def from_env(cls) -> 'MCPPostgresConfig':
        return cls(
            schema=os.getenv("MCP_POSTGRES_SCHEMA", "mcp"),
            tools_table=os.getenv("MCP_POSTGRES_TOOLS", "tools"),
            prompts_table=os.getenv("MCP_POSTGRES_PROMPTS", "prompts"),
            resources_table=os.getenv("MCP_POSTGRES_RESOURCES", "resources"),
            skills_table=os.getenv("MCP_POSTGRES_SKILLS", "skills"),
            executions_table=os.getenv("MCP_POSTGRES_EXECUTIONS", "tool_executions"),
            templates_table=os.getenv("MCP_POSTGRES_TEMPLATES", "prompt_templates"),
            cache_table=os.getenv("MCP_POSTGRES_CACHE", "resource_cache"),
            servers_table=os.getenv("MCP_POSTGRES_SERVERS", "aggregated_servers"),
        )


@dataclass
class MCPResourceConfig:
    """Combined MCP resource configuration"""
    qdrant: MCPQdrantConfig = field(default_factory=MCPQdrantConfig)
    minio: MCPMinIOConfig = field(default_factory=MCPMinIOConfig)
    redis: MCPRedisConfig = field(default_factory=MCPRedisConfig)
    postgres: MCPPostgresConfig = field(default_factory=MCPPostgresConfig)

    @classmethod
    def from_env(cls) -> 'MCPResourceConfig':
        return cls(
            qdrant=MCPQdrantConfig.from_env(),
            minio=MCPMinIOConfig.from_env(),
            redis=MCPRedisConfig.from_env(),
            postgres=MCPPostgresConfig.from_env(),
        )


# ===========================================
# Main MCP Configuration
# ===========================================

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
    authorization_service_url: Optional[str] = None

    # External APIs
    openai_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    composio_api_key: Optional[str] = None
    composio_cache_dir: str = "/app/cache"

    # ISA Model Service
    isa_service_url: str = "http://localhost:8082"
    isa_api_key: Optional[str] = None
    require_isa_auth: bool = False

    # Database
    db_schema: str = "dev"

    # Performance Optimization
    lazy_load_ai_selectors: bool = True
    lazy_load_external_services: bool = True

    # Meta-tools only mode
    # When True, only expose 4 meta-tools (discover, get_tool_schema, execute, list_skills)
    # The 89+ underlying tools are hidden but accessible via the execute meta-tool
    meta_tools_only: bool = False

    # Sub-configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    infrastructure: InfraConfig = field(default_factory=InfraConfig)
    consul: ConsulConfig = field(default_factory=ConsulConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    services: ServiceConfig = field(default_factory=ServiceConfig)
    resources: MCPResourceConfig = field(default_factory=MCPResourceConfig)

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
            authorization_service_url=os.getenv("AUTHORIZATION_SERVICE_URL"),
            # External APIs
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            brave_api_key=os.getenv("BRAVE_TOKEN") or os.getenv("BRAVE_API_KEY"),
            composio_api_key=os.getenv("COMPOSIO_API_KEY"),
            composio_cache_dir=os.getenv("COMPOSIO_CACHE_DIR", "/app/cache"),
            # ISA Service
            isa_service_url=os.getenv("ISA_SERVICE_URL", "http://localhost:8082"),
            isa_api_key=os.getenv("ISA_API_KEY"),
            require_isa_auth=_bool(os.getenv("REQUIRE_ISA_AUTH", "false")),
            # Database
            db_schema=os.getenv("DB_SCHEMA", "dev"),
            # Optimization
            lazy_load_ai_selectors=_bool(os.getenv("LAZY_LOAD_AI_SELECTORS", "true")),
            lazy_load_external_services=_bool(os.getenv("LAZY_LOAD_EXTERNAL_SERVICES", "true")),
            # Meta-tools only mode
            meta_tools_only=_bool(os.getenv("META_TOOLS_ONLY", "false")),
            # Load sub-configs
            logging=LoggingConfig.from_env(),
            infrastructure=InfraConfig.from_env(),
            consul=ConsulConfig.from_env(),
            model=ModelConfig.from_env(),
            services=ServiceConfig.from_env(),
            resources=MCPResourceConfig.from_env(),
        )
