#!/usr/bin/env python3
"""
Configuration Management System - isA MCP Core

PROJECT DESCRIPTION:
    Comprehensive configuration management system for the isA MCP (Model Context Protocol) infrastructure.
    Provides environment-aware configuration loading, type-safe settings management, and hierarchical 
    configuration structure supporting development, staging, and production environments.

INPUTS:
    - Environment variables from system and .env files
    - Configuration files specific to each environment
    - Runtime configuration overrides
    - External service API keys and endpoints
    - Database connection parameters

OUTPUTS:
    - Typed configuration objects with validation
    - Environment-specific settings instances
    - Service configuration parameters
    - Security and authentication settings
    - Database and external service configurations

FUNCTIONALITY:
    - Multi-Environment Configuration:
      * Development, staging, and production environment support
      * Environment-specific .env file loading
      * Hierarchical configuration inheritance
      * Runtime configuration validation
    
    - Service Configuration Categories:
      * Security settings (authentication, authorization, rate limiting)
      * Database configuration (Supabase local/cloud, connection pooling)
      * Logging and monitoring settings
      * Graph analytics and AI service parameters
      * External API configurations (OpenAI, Shopify, etc.)
    
    - Type Safety and Validation:
      * Dataclass-based configuration structures
      * Type hints for all configuration parameters
      * Default value management
      * Configuration validation and error reporting
    
    - Dynamic Configuration Management:
      * Runtime configuration reloading
      * Environment variable override support
      * Configuration change detection
      * Settings caching and optimization

DEPENDENCIES:
    - python-dotenv: Environment variable file loading
    - dataclasses: Type-safe configuration structures
    - pathlib: Cross-platform path handling
    - typing: Type hints and validation support
    - os: System environment variable access

OPTIMIZATION POINTS:
    - Add configuration schema validation with pydantic
    - Implement configuration caching for performance
    - Add configuration change notifications
    - Optimize environment file loading and parsing
    - Add configuration hot reloading capabilities
    - Implement configuration backup and versioning
    - Add configuration encryption for sensitive values
    - Optimize database connection configuration
    - Add configuration audit logging
    - Implement configuration drift detection

CONFIGURATION CATEGORIES:
    - SecuritySettings: Authentication, authorization, rate limiting
    - DatabaseSettings: Connection management and optimization
    - LoggingSettings: Structured logging and audit trails
    - MonitoringSettings: Metrics collection and alerting
    - GraphAnalyticsSettings: AI/ML service configurations
    - MCPSettings: Main server and service configurations

USAGE:
    from core.config import get_settings, reload_settings
    
    # Get current configuration
    settings = get_settings()
    
    # Access specific configurations
    db_config = settings.database
    security_config = settings.security
    
    # Reload configuration at runtime
    new_settings = reload_settings()
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables based on ENV
env = os.getenv("ENV", "development")

# Determine environment file path
if env == "development":
    env_file = "deployment/dev/.env"
else:
    env_file = f"deployment/{env}/.env.{env}"

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
    log_file: Optional[str] = "logs/mcp_server.log"
    enable_console: bool = True
    enable_structured: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    # Centralized Logging (Loki)
    loki_url: str = "http://localhost:3100"
    loki_enabled: bool = False
    service_name: str = "mcp"
    environment: str = "development"

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
    require_mcp_auth: bool = False
    api_keys: Dict[str, str] = field(default_factory=dict)
    mcp_api_keys: Dict[str, str] = field(default_factory=dict)
    
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
    
    # ISA Model Service APIs
    isa_service_url: Optional[str] = None
    isa_api_key: Optional[str] = None
    require_isa_auth: bool = False
    
    # Auth Service URLs
    auth_service_url: Optional[str] = None
    authz_service_url: Optional[str] = None
    
    # Storage Service Configuration
    storage_consul_host: Optional[str] = None
    storage_consul_port: int = 8500
    storage_fallback_host: Optional[str] = None
    storage_fallback_port: int = 8208
    
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
    
    def load_from_consul(self) -> 'MCPSettings':
        """Load all settings from Consul service discovery and KV store"""
        # Only need Consul connection info from env
        consul_host = os.getenv("CONSUL_HOST", "localhost")
        consul_port = int(os.getenv("CONSUL_PORT", "8500"))
        
        try:
            from core.consul_discovery import get_consul_discovery
            import consul
            
            # Initialize Consul clients
            discovery = get_consul_discovery()
            consul_client = consul.Consul(host=consul_host, port=consul_port)
            
            if not discovery.is_available():
                logger.error("Consul is required but not available!")
                # Use minimal defaults for critical settings
                self._set_minimal_defaults()
                return self
            
            logger.info(f"Loading all configuration from Consul at {consul_host}:{consul_port}")
            
            # 1. Load service URLs from Consul discovery
            self._load_service_urls_from_consul(discovery)
            
            # 2. Load configuration from Consul KV store
            self._load_config_from_consul_kv(consul_client)
            
            logger.info("Successfully loaded configuration from Consul")
            
        except ImportError as e:
            logger.error(f"Consul modules not available: {e}")
            self._set_minimal_defaults()
        except Exception as e:
            logger.error(f"Failed to load configuration from Consul: {e}")
            self._set_minimal_defaults()
        
        return self
    
    def _load_service_urls_from_consul(self, discovery):
        """Load all service URLs from Consul service discovery"""
        # Service discovery mappings
        service_mappings = {
            'model': 'isa_service_url',
            'agent': 'agent_service_url', 
            'auth': 'auth_service_url',
            'authz': 'authz_service_url',
            'user': 'user_service_url',
            'storage': None,  # Special handling
        }
        
        for service_name, attr_name in service_mappings.items():
            try:
                url = discovery.get_service_url(service_name)
                if url:
                    if service_name == 'storage':
                        # Special handling for storage service
                        import re
                        match = re.match(r'http://([^:]+):(\d+)', url)
                        if match:
                            self.storage_fallback_host = match.group(1)
                            self.storage_fallback_port = int(match.group(2))
                            logger.info(f"Discovered storage service: {url}")
                    elif attr_name:
                        setattr(self, attr_name, url)
                        logger.info(f"Discovered {service_name} service: {url}")
            except Exception as e:
                logger.warning(f"Failed to discover {service_name}: {e}")
    
    def _load_config_from_consul_kv(self, consul_client):
        """Load configuration from Consul KV store"""
        try:
            # Load MCP server config
            _, data = consul_client.kv.get('config/mcp/server')
            if data and data.get('Value'):
                import json
                server_config = json.loads(data['Value'].decode('utf-8'))
                self.host = server_config.get('host', '0.0.0.0')
                self.port = server_config.get('port', 8081)
                self.server_name = server_config.get('name', 'MCP Server')
                logger.info("Loaded server config from Consul KV")
        except Exception as e:
            logger.debug(f"No server config in Consul KV, using defaults: {e}")
        
        try:
            # Load security config
            _, data = consul_client.kv.get('config/mcp/security')
            if data and data.get('Value'):
                import json
                sec_config = json.loads(data['Value'].decode('utf-8'))
                self.require_auth = sec_config.get('require_auth', False)
                self.security.require_authorization = sec_config.get('require_authorization', True)
                self.security.auto_approve_low_security = sec_config.get('auto_approve_low', True)
                logger.info("Loaded security config from Consul KV")
        except Exception as e:
            logger.debug(f"No security config in Consul KV, using defaults: {e}")
        
        try:
            # Load API keys and credentials
            _, data = consul_client.kv.get('config/mcp/credentials')
            if data and data.get('Value'):
                import json
                creds = json.loads(data['Value'].decode('utf-8'))
                self.openai_api_key = creds.get('openai_api_key')
                self.brave_api_key = creds.get('brave_api_key')
                self.supabase_url = creds.get('supabase_url')
                self.supabase_anon_key = creds.get('supabase_anon_key')
                self.supabase_service_role_key = creds.get('supabase_service_role_key')
                logger.info("Loaded credentials from Consul KV")
        except Exception as e:
            logger.debug(f"No credentials in Consul KV: {e}")
        
        try:
            # Load logging config
            _, data = consul_client.kv.get('config/mcp/logging')
            if data and data.get('Value'):
                import json
                log_config = json.loads(data['Value'].decode('utf-8'))
                self.logging.log_level = log_config.get('level', 'INFO')
                self.logging.log_file = log_config.get('file', 'logs/mcp_server.log')
                self.logging.loki_enabled = log_config.get('loki_enabled', False)
                self.logging.loki_url = log_config.get('loki_url', 'http://localhost:3100')
                logger.info("Loaded logging config from Consul KV")
        except Exception as e:
            logger.debug(f"No logging config in Consul KV, using defaults: {e}")
    
    def _set_minimal_defaults(self):
        """Set minimal default values when Consul is unavailable"""
        logger.warning("Using minimal default configuration (Consul unavailable)")
        self.host = "0.0.0.0"
        self.port = 8081
        self.server_name = "MCP Server (No Consul)"
        self.require_auth = False
        self.logging.log_level = "INFO"
        self.logging.log_file = "logs/mcp_server.log"
    
    def load_from_env(self) -> 'MCPSettings':
        """Deprecated - redirects to load_from_consul"""
        logger.info("load_from_env called - redirecting to load_from_consul")
        return self.load_from_consul()

def create_settings() -> MCPSettings:
    """Create and configure settings instance from Consul"""
    settings = MCPSettings()
    return settings.load_from_consul()

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
