import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

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
