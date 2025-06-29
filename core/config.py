import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    database_path: str = "memory.db"
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
    
    # Sub-configurations
    security: SecuritySettings = field(default_factory=SecuritySettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)
    
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
        
    def get_database_path(self) -> Path:
        """Get database path as Path object"""
        return Path(self.database.database_path)
    
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
        
        # Database settings
        self.database.database_path = os.getenv("MCP_DB_DATABASE_PATH", self.database.database_path)
        
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
        
        # Database/Storage APIs
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", self.supabase_url)
        self.supabase_anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", self.supabase_anon_key)
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key)
        self.supabase_pwd = os.getenv("SUPABASE_PWD", self.supabase_pwd)
        
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
