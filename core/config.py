import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables based on ENV
env = os.getenv("ENV", "development")

# Determine environment file path
if env == "development":
    env_file = "deployment/dev/.env"
else:
    env_file = f"deployment/.env.{env}"

# Load the appropriate environment file (override existing env vars)
load_dotenv(env_file, override=True)

@dataclass
class SecuritySettings:
    """Security-related configuration"""
    # Authorization settings
    require_authorization: bool = True
    auto_approve_low_security: bool = True
    auto_approve_medium_security: bool = False
    authorization_timeout_minutes: int = 30
    approval_cache_hours: int = 1
    
    # Rate limiting
    default_rate_limit_calls: int = 100
    default_rate_limit_window: int = 3600  # seconds
    
    # Security patterns
    forbidden_patterns: List[str] = field(default_factory=lambda: [
        r"password", r"secret", r"api_key", r"private_key", r"token",
        r"delete.*database", r"drop.*table"
    ])

@dataclass
class DatabaseSettings:
    """Database configuration"""
    connection_timeout: int = 30
    max_connections: int = 10

@dataclass
class LoggingSettings:
    """Logging configuration"""
    log_level: str = "INFO"
    log_file: Optional[str] = "mcp_server.log"
    enable_console: bool = True
    enable_structured: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class MonitoringSettings:
    """Monitoring and metrics configuration"""
    enable_metrics: bool = True
    metrics_history_limit: int = 1000
    enable_audit_log: bool = True

@dataclass
class GraphAnalyticsSettings:
    """Graph Analytics configuration"""
    # LLM Configuration for Graph Analytics
    max_tokens: int = 4000
    temperature: float = 0.1
    default_confidence: float = 0.8
    
    # Text Processing Configuration
    long_text_threshold: int = 50000
    chunk_size: int = 100000
    chunk_overlap: int = 5000
    
    # Processing Configuration
    max_concurrent: int = 5
    batch_size: int = 10
    
    # Similarity and Search Configuration
    similarity_threshold: float = 0.7
    embedding_dimension: int = 1536
    
    # Performance and Logging
    debug: bool = False
    perf_log: bool = True
    slow_threshold: float = 5.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_fallback: bool = True
    
    # Neo4j Configuration
    neo4j_uri: Optional[str] = None
    neo4j_username: Optional[str] = None
    neo4j_password: Optional[str] = None
    neo4j_database: Optional[str] = None
    
    # Pattern Matching Configuration
    pattern_confidence: float = 0.9
    min_entity_length: int = 2
    max_entity_length: int = 200
    
    # Entity Type Mapping
    entity_type_mappings: Dict[str, List[str]] = field(default_factory=lambda: {
        'PERSON': ['PERSON', 'PEOPLE', 'INDIVIDUAL', 'AUTHOR', 'RESEARCHER'],
        'ORG': ['ORG', 'ORGANIZATION', 'COMPANY', 'INSTITUTION', 'UNIVERSITY'],
        'LOC': ['LOC', 'LOCATION', 'PLACE', 'COUNTRY', 'CITY', 'ADDRESS'],
        'EVENT': ['EVENT', 'MEETING', 'CONFERENCE', 'OCCURRENCE'],
        'PRODUCT': ['PRODUCT', 'TOOL', 'SOFTWARE', 'TECHNOLOGY'],
        'CONCEPT': ['CONCEPT', 'METHOD', 'ALGORITHM', 'THEORY', 'IDEA'],
        'DATE': ['DATE', 'TIME', 'TEMPORAL', 'WHEN'],
        'MONEY': ['MONEY', 'CURRENCY', 'FINANCIAL', 'AMOUNT'],
        'CUSTOM': ['CUSTOM', 'ENTITY', 'MISC', 'OTHER', 'UNKNOWN']
    })
    
    # Relation Type Mapping
    relation_type_mappings: Dict[str, List[str]] = field(default_factory=lambda: {
        'IS_A': ['IS_A', 'TYPE_OF', 'KIND_OF'],
        'PART_OF': ['PART_OF', 'COMPONENT_OF', 'BELONGS_TO'],
        'LOCATED_IN': ['LOCATED_IN', 'IN', 'AT', 'BASED_IN'],
        'WORKS_FOR': ['WORKS_FOR', 'EMPLOYED_BY', 'AFFILIATED_WITH'],
        'OWNS': ['OWNS', 'HAS', 'POSSESSES'],
        'CREATED_BY': ['CREATED_BY', 'AUTHORED_BY', 'DEVELOPED_BY'],
        'HAPPENED_AT': ['HAPPENED_AT', 'OCCURRED_AT', 'TOOK_PLACE'],
        'CAUSED_BY': ['CAUSED_BY', 'RESULTED_FROM', 'DUE_TO'],
        'SIMILAR_TO': ['SIMILAR_TO', 'LIKE', 'COMPARABLE_TO'],
        'RELATES_TO': ['RELATES_TO', 'CONNECTED_TO', 'ASSOCIATED_WITH'],
        'DEPENDS_ON': ['DEPENDS_ON', 'REQUIRES', 'NEEDS'],
        'CUSTOM': ['CUSTOM', 'RELATION', 'CONNECTS_TO']
    })

@dataclass
class MCPSettings:
    """Main configuration settings for MCP services"""
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    server_name: str = "Enhanced Secure MCP Server"
    
    # Authentication (disabled by default for initial setup)
    require_auth: bool = False
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # External service configurations
    openweather_api_key: Optional[str] = None
    
    # AI/ML Service APIs
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    replicate_api_token: Optional[str] = None
    hf_token: Optional[str] = None
    runpod_api_key: Optional[str] = None
    
    # Search APIs
    brave_api_key: Optional[str] = None
    
    # Development/Package APIs
    pypi_api_token: Optional[str] = None
    
    # E-commerce APIs
    shopify_store_domain: Optional[str] = None
    shopify_storefront_access_token: Optional[str] = None
    shopify_admin_api_key: Optional[str] = None
    
    # Database/Storage APIs
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_pwd: Optional[str] = None
    db_schema: Optional[str] = None
    
    # Local and Cloud Supabase URLs
    supabase_local_url: Optional[str] = None
    supabase_local_anon_key: Optional[str] = None
    supabase_local_service_role_key: Optional[str] = None
    supabase_cloud_url: Optional[str] = None
    supabase_cloud_anon_key: Optional[str] = None
    supabase_cloud_service_role_key: Optional[str] = None
    
    # Sub-configurations
    security: SecuritySettings = field(default_factory=SecuritySettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)
    graph_analytics: GraphAnalyticsSettings = field(default_factory=GraphAnalyticsSettings)
    
    # Tool-specific settings
    tool_policies: Dict[str, str] = field(default_factory=lambda: {
        "remember": "MEDIUM",
        "forget": "HIGH", 
        "search_memories": "LOW",
        "get_weather": "LOW",
        "calculate": "MEDIUM",
        "get_current_time": "LOW",
        "analyze_sentiment": "LOW",
    })
    
    # Cache settings
    weather_cache_hours: int = 1
        
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get log file path as Path object"""
        if self.logging.log_file:
            return Path(self.logging.log_file)
        return None
    
    def load_from_env(self) -> 'MCPSettings':
        """Load settings from environment variables"""
        # Server settings
        self.host = os.getenv("MCP_HOST", self.host)
        self.port = int(os.getenv("MCP_PORT", str(self.port)))
        self.server_name = os.getenv("MCP_SERVER_NAME", self.server_name)
        
        # Authentication
        self.require_auth = os.getenv("MCP_REQUIRE_AUTH", "false").lower() == "true"
        
        # Security settings
        self.security.require_authorization = os.getenv("MCP_SECURITY_REQUIRE_AUTHORIZATION", "true").lower() == "true"
        self.security.auto_approve_low_security = os.getenv("MCP_SECURITY_AUTO_APPROVE_LOW", "true").lower() == "true"
        
        
        # Logging settings
        self.logging.log_level = os.getenv("MCP_LOG_LOG_LEVEL", self.logging.log_level)
        self.logging.log_file = os.getenv("MCP_LOG_LOG_FILE", self.logging.log_file)
        
        # External service API keys
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY", self.openweather_api_key)
        
        # AI/ML Service APIs
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_api_base = os.getenv("OPENAI_API_BASE", self.openai_api_base)
        self.replicate_api_token = os.getenv("REPLICATE_API_TOKEN", self.replicate_api_token)
        self.hf_token = os.getenv("HF_TOKEN", self.hf_token)
        self.runpod_api_key = os.getenv("RUNPOD_API_KEY", self.runpod_api_key)
        
        # Search APIs (note: using BRAVE_TOKEN from .env)
        self.brave_api_key = os.getenv("BRAVE_TOKEN", self.brave_api_key)
        
        # Development/Package APIs
        self.pypi_api_token = os.getenv("PYPI_API_TOKEN", self.pypi_api_token)
        
        # E-commerce APIs
        self.shopify_store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", self.shopify_store_domain)
        self.shopify_storefront_access_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN", self.shopify_storefront_access_token)
        self.shopify_admin_api_key = os.getenv("SHOPIFY_ADMIN_API_KEY", self.shopify_admin_api_key)
        
        # Database/Storage APIs - Load both local and cloud configurations
        self.supabase_local_url = os.getenv("SUPABASE_LOCAL_URL", self.supabase_local_url)
        self.supabase_local_anon_key = os.getenv("SUPABASE_LOCAL_ANON_KEY", self.supabase_local_anon_key)
        self.supabase_local_service_role_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY", self.supabase_local_service_role_key)
        self.supabase_cloud_url = os.getenv("SUPABASE_CLOUD_URL", self.supabase_cloud_url)
        self.supabase_cloud_anon_key = os.getenv("SUPABASE_CLOUD_ANON_KEY", self.supabase_cloud_anon_key)
        self.supabase_cloud_service_role_key = os.getenv("SUPABASE_CLOUD_SERVICE_ROLE_KEY", self.supabase_cloud_service_role_key)
        
        # Determine which Supabase instance to use based on environment
        current_env = os.getenv("ENV", "development")
        if current_env in ["development", "test"]:
            # Use local Supabase for dev and test
            self.supabase_url = self.supabase_local_url
            self.supabase_anon_key = self.supabase_local_anon_key
            self.supabase_service_role_key = self.supabase_local_service_role_key
        else:
            # Use cloud Supabase for staging and production
            self.supabase_url = self.supabase_cloud_url
            self.supabase_anon_key = self.supabase_cloud_anon_key
            self.supabase_service_role_key = self.supabase_cloud_service_role_key
        
        self.supabase_pwd = os.getenv("SUPABASE_PWD", self.supabase_pwd)
        self.db_schema = os.getenv("DB_SCHEMA", self.db_schema)
        
        # Graph Analytics settings
        self.graph_analytics.max_tokens = int(os.getenv("GRAPH_MAX_TOKENS", str(self.graph_analytics.max_tokens)))
        self.graph_analytics.temperature = float(os.getenv("GRAPH_TEMPERATURE", str(self.graph_analytics.temperature)))
        self.graph_analytics.default_confidence = float(os.getenv("GRAPH_DEFAULT_CONFIDENCE", str(self.graph_analytics.default_confidence)))
        self.graph_analytics.long_text_threshold = int(os.getenv("GRAPH_LONG_TEXT_THRESHOLD", str(self.graph_analytics.long_text_threshold)))
        self.graph_analytics.chunk_size = int(os.getenv("GRAPH_CHUNK_SIZE", str(self.graph_analytics.chunk_size)))
        self.graph_analytics.chunk_overlap = int(os.getenv("GRAPH_CHUNK_OVERLAP", str(self.graph_analytics.chunk_overlap)))
        self.graph_analytics.max_concurrent = int(os.getenv("GRAPH_MAX_CONCURRENT", str(self.graph_analytics.max_concurrent)))
        self.graph_analytics.batch_size = int(os.getenv("GRAPH_BATCH_SIZE", str(self.graph_analytics.batch_size)))
        self.graph_analytics.similarity_threshold = float(os.getenv("GRAPH_SIMILARITY_THRESHOLD", str(self.graph_analytics.similarity_threshold)))
        self.graph_analytics.embedding_dimension = int(os.getenv("GRAPH_EMBEDDING_DIMENSION", str(self.graph_analytics.embedding_dimension)))
        self.graph_analytics.debug = os.getenv("GRAPH_DEBUG", "false").lower() == "true"
        self.graph_analytics.perf_log = os.getenv("GRAPH_PERF_LOG", "true").lower() == "true"
        self.graph_analytics.slow_threshold = float(os.getenv("GRAPH_SLOW_THRESHOLD", str(self.graph_analytics.slow_threshold)))
        self.graph_analytics.max_retries = int(os.getenv("GRAPH_MAX_RETRIES", str(self.graph_analytics.max_retries)))
        self.graph_analytics.retry_delay = float(os.getenv("GRAPH_RETRY_DELAY", str(self.graph_analytics.retry_delay)))
        self.graph_analytics.enable_fallback = os.getenv("GRAPH_ENABLE_FALLBACK", "true").lower() == "true"
        
        # Neo4j configuration
        self.graph_analytics.neo4j_uri = os.getenv("NEO4J_URI", self.graph_analytics.neo4j_uri)
        self.graph_analytics.neo4j_username = os.getenv("NEO4J_USERNAME", self.graph_analytics.neo4j_username)
        self.graph_analytics.neo4j_password = os.getenv("NEO4J_PASSWORD", self.graph_analytics.neo4j_password)
        self.graph_analytics.neo4j_database = os.getenv("NEO4J_DATABASE", self.graph_analytics.neo4j_database)
        
        return self

def create_settings() -> MCPSettings:
    """Create and configure settings instance"""
    settings = MCPSettings()
    return settings.load_from_env()

# Global settings instance
settings = create_settings()

def get_settings() -> MCPSettings:
    """Get global settings instance"""
    return settings

def reload_settings() -> MCPSettings:
    """Reload settings from environment/config files"""
    global settings
    settings = create_settings()
    return settings
