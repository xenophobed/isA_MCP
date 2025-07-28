"""
User Service Configuration

用户服务的配置管理
支持环境变量和配置文件
"""

import os
from typing import List, Optional
from functools import lru_cache
from dotenv import load_dotenv
from pathlib import Path


class UserServiceConfig:
    """用户服务配置类"""
    
    def __init__(self):
        # Load environment-specific configuration
        self._load_environment_config()
    
    def _load_environment_config(self):
        """加载环境特定的配置"""
        # 加载环境配置文件
        env_file = os.getenv("ENV_FILE", ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
        
        # 加载开发环境配置
        dev_env_file = "deployment/dev/.env"
        if os.path.exists(dev_env_file):
            load_dotenv(dev_env_file)
        
        # 加载用户服务特定的环境配置
        user_service_env = "deployment/dev/.env.user_service"
        if os.path.exists(user_service_env):
            load_dotenv(user_service_env)
        
        # 应用基础配置
        self.app_name = os.getenv("APP_NAME", "User Management Service")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # 服务器配置
        self.host = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "8000"))
        self.reload = os.getenv("RELOAD", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "info")
        
        # CORS 配置
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,https://www.iapro.ai")
        self.cors_origins = [x.strip() for x in cors_origins_str.split(",")]
        self.cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
        self.cors_allow_methods = ["*"]
        self.cors_allow_headers = ["*"]
        
        # Auth0 配置
        self.auth0_domain = os.getenv("AUTH0_DOMAIN", "dev-47zcqarlxizdkads.us.auth0.com")
        self.auth0_audience = os.getenv("AUTH0_AUDIENCE", "https://dev-47zcqarlxizdkads.us.auth0.com/api/v2/")
        self.auth0_client_id = os.getenv("AUTH0_CLIENT_ID", "Vsm0s23JTKzDrq9bq0foKyYieOCyeoQJ")
        self.auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET", "kk6n0zkaavCzd5FuqpoTeWudnQBNQvhXneb-LI3TPWunhUkJNim9FEZeWXKRJd7m")
        
        # Supabase 认证配置
        self.supabase_url = os.getenv("SUPABASE_LOCAL_URL", "http://127.0.0.1:54321")
        self.supabase_anon_key = os.getenv("SUPABASE_LOCAL_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMAs_-IsVo")
        self.supabase_service_role_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU")
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "your-super-secret-jwt-token-with-at-least-32-characters-long")
        
        # 认证模式配置 (auth0 | supabase | both)
        self.auth_provider = os.getenv("AUTH_PROVIDER", "both")
        
        # Stripe 配置
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.stripe_pro_price_id = os.getenv("STRIPE_PRO_PRICE_ID", "price_1RbchvL7y127fTKemRuw8Elz")
        self.stripe_enterprise_price_id = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "price_1RbciEL7y127fTKexyDAX9JA")
        
        # 数据库配置
        self.database_url = os.getenv("DATABASE_URL")
        self.database_echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.database_pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.database_max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        
        # Redis 配置
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        
        # 缓存配置
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))  # 1小时
        self.auth_cache_ttl = int(os.getenv("AUTH_CACHE_TTL", "300"))  # 5分钟
        
        # 安全配置
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # 速率限制配置
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # 秒
        
        # 监控配置
        self.metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        
        # 文件上传配置
        self.upload_max_size = int(os.getenv("UPLOAD_MAX_SIZE", str(50 * 1024 * 1024)))  # 50MB
        upload_types_str = os.getenv("UPLOAD_ALLOWED_TYPES", "image/jpeg,image/png,image/gif,image/webp,application/pdf,text/plain,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/json")
        self.upload_allowed_types = [x.strip() for x in upload_types_str.split(",")]
        
        # MinIO存储配置 (与S3兼容)
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.minio_bucket_name = os.getenv("MINIO_BUCKET_NAME", "user-files")
        
        # 邮件配置
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # 第三方服务配置
        self.webhook_timeout = int(os.getenv("WEBHOOK_TIMEOUT", "30"))
        self.external_api_timeout = int(os.getenv("EXTERNAL_API_TIMEOUT", "10"))


@lru_cache()
def get_config() -> UserServiceConfig:
    """
    获取配置实例（单例模式）
    
    Returns:
        UserServiceConfig: 配置实例
    """
    return UserServiceConfig()


# 配置验证函数
def validate_config(config: UserServiceConfig) -> bool:
    """
    验证配置是否正确
    
    Args:
        config: 配置实例
        
    Returns:
        bool: 配置是否有效
        
    Raises:
        ValueError: 配置无效时抛出
    """
    errors = []
    
    # 验证必要的配置
    if not config.auth0_domain:
        errors.append("AUTH0_DOMAIN is required")
    
    if not config.auth0_client_id:
        errors.append("AUTH0_CLIENT_ID is required")
    
    if not config.auth0_client_secret:
        errors.append("AUTH0_CLIENT_SECRET is required")
    
    if not config.stripe_secret_key:
        errors.append("STRIPE_SECRET_KEY is required")
    
    if not config.stripe_webhook_secret:
        errors.append("STRIPE_WEBHOOK_SECRET is required")
    
    # 验证端口范围
    if not (1 <= config.port <= 65535):
        errors.append("PORT must be between 1 and 65535")
    
    # 验证日志级别
    valid_log_levels = ["debug", "info", "warning", "error", "critical"]
    if config.log_level.lower() not in valid_log_levels:
        errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")
    
    # 验证环境
    valid_environments = ["development", "staging", "production"]
    if config.environment.lower() not in valid_environments:
        errors.append(f"ENVIRONMENT must be one of: {', '.join(valid_environments)}")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return True


# 获取环境特定的配置
def get_environment_config() -> dict:
    """
    根据环境获取特定配置
    
    Returns:
        dict: 环境特定的配置
    """
    config = get_config()
    
    base_config = {
        "app_name": config.app_name,
        "version": config.app_version,
        "environment": config.environment
    }
    
    if config.environment == "development":
        return {
            **base_config,
            "debug": True,
            "reload": True,
            "log_level": "debug"
        }
    elif config.environment == "staging":
        return {
            **base_config,
            "debug": False,
            "reload": False,
            "log_level": "info"
        }
    elif config.environment == "production":
        return {
            **base_config,
            "debug": False,
            "reload": False,
            "log_level": "warning"
        }
    
    return base_config


# 导出主要配置实例
config = get_config() 