"""
DuckDB Service Configuration Management
提供灵活的配置管理系统，支持多环境、动态配置和配置验证

Features:
- 多环境配置支持 (dev/test/prod)
- 环境变量和配置文件支持
- 配置验证和类型检查
- 动态配置更新
- 配置继承和覆盖
- 敏感信息加密存储
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urlparse

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available, YAML config files not supported")

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("cryptography not available, config encryption not supported")


logger = logging.getLogger(__name__)


class Environment(Enum):
    """部署环境"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    # 基础连接配置
    database_path: str = ":memory:"
    read_only: bool = False
    access_mode: str = "automatic"
    
    # 性能配置
    threads: int = 4
    memory_limit: str = "1GB"
    enable_object_cache: bool = True
    enable_checkpoint_on_shutdown: bool = True
    
    # 存储配置
    temp_directory: Optional[str] = None
    wal_mode: bool = True
    synchronous: str = "NORMAL"  # OFF, NORMAL, FULL
    
    # 扩展配置
    custom_extensions: List[str] = field(default_factory=list)
    auto_load_extensions: bool = True
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证内存限制格式
        if not self._validate_memory_limit(self.memory_limit):
            errors.append(f"Invalid memory_limit format: {self.memory_limit}")
        
        # 验证线程数
        if self.threads < 1 or self.threads > 64:
            errors.append(f"threads must be between 1 and 64, got {self.threads}")
        
        # 验证数据库路径
        if self.database_path != ":memory:":
            path = Path(self.database_path)
            if not path.parent.exists():
                errors.append(f"Database directory does not exist: {path.parent}")
        
        # 验证临时目录
        if self.temp_directory:
            temp_path = Path(self.temp_directory)
            if not temp_path.exists():
                errors.append(f"Temp directory does not exist: {temp_path}")
        
        return errors
    
    def _validate_memory_limit(self, limit: str) -> bool:
        """验证内存限制格式"""
        import re
        pattern = r'^\d+(\.\d+)?(GB|MB|KB|B)$'
        return bool(re.match(pattern, limit.upper()))


@dataclass
class PoolConfig:
    """连接池配置"""
    # 连接数配置
    min_connections: int = 2
    max_connections: int = 10
    
    # 超时配置
    idle_timeout: float = 300.0  # 5分钟
    max_lifetime: float = 3600.0  # 1小时
    connection_timeout: float = 30.0  # 30秒
    
    # 健康检查配置
    health_check_interval: float = 30.0  # 30秒
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # 性能配置
    enable_connection_warming: bool = True
    warmup_connections: int = 2
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.min_connections < 1:
            errors.append("min_connections must be at least 1")
        
        if self.max_connections < self.min_connections:
            errors.append("max_connections must be >= min_connections")
        
        if self.idle_timeout <= 0:
            errors.append("idle_timeout must be positive")
        
        if self.max_lifetime <= 0:
            errors.append("max_lifetime must be positive")
        
        if self.warmup_connections > self.max_connections:
            errors.append("warmup_connections cannot exceed max_connections")
        
        return errors


@dataclass
class SecurityConfig:
    """安全配置"""
    # 访问控制
    enable_access_control: bool = True
    allowed_functions: Optional[List[str]] = None
    blocked_functions: List[str] = field(default_factory=lambda: [
        'system', 'shell', 'read_csv_auto', 'copy'
    ])
    
    # 查询限制
    max_query_timeout: float = 300.0  # 5分钟
    max_query_complexity: int = 1000000  # 查询复杂度限制
    max_result_rows: int = 100000  # 结果行数限制
    
    # 审计日志
    enable_audit_log: bool = True
    audit_log_path: Optional[str] = None
    audit_log_level: LogLevel = LogLevel.INFO
    
    # IP访问控制
    allowed_ips: List[str] = field(default_factory=list)
    blocked_ips: List[str] = field(default_factory=list)
    
    # SSL/TLS配置
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.max_query_timeout <= 0:
            errors.append("max_query_timeout must be positive")
        
        if self.max_query_complexity <= 0:
            errors.append("max_query_complexity must be positive")
        
        if self.max_result_rows <= 0:
            errors.append("max_result_rows must be positive")
        
        # 验证SSL配置
        if self.enable_ssl:
            if not self.ssl_cert_path:
                errors.append("ssl_cert_path required when SSL is enabled")
            elif not Path(self.ssl_cert_path).exists():
                errors.append(f"SSL cert file not found: {self.ssl_cert_path}")
            
            if not self.ssl_key_path:
                errors.append("ssl_key_path required when SSL is enabled")
            elif not Path(self.ssl_key_path).exists():
                errors.append(f"SSL key file not found: {self.ssl_key_path}")
        
        # 验证IP地址格式
        for ip in self.allowed_ips + self.blocked_ips:
            if not self._validate_ip(ip):
                errors.append(f"Invalid IP address format: {ip}")
        
        return errors
    
    def _validate_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            try:
                ipaddress.ip_network(ip, strict=False)
                return True
            except ValueError:
                return False


@dataclass
class MonitoringConfig:
    """监控配置"""
    # 基础监控配置
    enable_monitoring: bool = True
    update_interval: float = 10.0  # 10秒
    
    # 指标配置
    enable_metrics: bool = True
    metrics_retention_days: int = 7
    max_metric_points: int = 1000
    
    # 健康检查配置
    enable_health_checks: bool = True
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    
    # 告警配置
    enable_alerts: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ['log'])
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'cpu_usage': 80.0,
        'memory_usage': 85.0,
        'pool_utilization': 90.0,
        'query_error_rate': 0.1
    })
    
    # 性能分析配置
    enable_query_profiling: bool = True
    slow_query_threshold: float = 1.0  # 1秒
    max_slow_queries: int = 100
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.update_interval <= 0:
            errors.append("update_interval must be positive")
        
        if self.metrics_retention_days <= 0:
            errors.append("metrics_retention_days must be positive")
        
        if self.health_check_interval <= 0:
            errors.append("health_check_interval must be positive")
        
        if self.slow_query_threshold <= 0:
            errors.append("slow_query_threshold must be positive")
        
        # 验证告警阈值
        for metric, threshold in self.alert_thresholds.items():
            if threshold <= 0:
                errors.append(f"Alert threshold for {metric} must be positive")
        
        return errors


@dataclass
class LoggingConfig:
    """日志配置"""
    # 基础日志配置
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 文件日志配置
    enable_file_logging: bool = True
    log_file_path: Optional[str] = None
    max_file_size: str = "10MB"
    backup_count: int = 5
    
    # 控制台日志配置
    enable_console_logging: bool = True
    console_level: LogLevel = LogLevel.INFO
    
    # 结构化日志配置
    enable_structured_logging: bool = False
    structured_format: str = "json"  # json, logfmt
    
    # 外部日志系统
    enable_syslog: bool = False
    syslog_address: Optional[str] = None
    syslog_facility: str = "local0"
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证文件大小格式
        if not self._validate_file_size(self.max_file_size):
            errors.append(f"Invalid max_file_size format: {self.max_file_size}")
        
        if self.backup_count < 0:
            errors.append("backup_count must be non-negative")
        
        # 验证syslog地址
        if self.enable_syslog and self.syslog_address:
            if not self._validate_syslog_address(self.syslog_address):
                errors.append(f"Invalid syslog_address: {self.syslog_address}")
        
        return errors
    
    def _validate_file_size(self, size: str) -> bool:
        """验证文件大小格式"""
        import re
        pattern = r'^\d+(\.\d+)?(KB|MB|GB)$'
        return bool(re.match(pattern, size.upper()))
    
    def _validate_syslog_address(self, address: str) -> bool:
        """验证syslog地址格式"""
        try:
            if address.startswith('/'):
                # Unix socket
                return Path(address).exists()
            else:
                # Network address
                host, port = address.split(':')
                return 1 <= int(port) <= 65535
        except (ValueError, OSError):
            return False


@dataclass
class DuckDBServiceConfig:
    """完整的DuckDB服务配置"""
    # 环境配置
    environment: Environment = Environment.DEVELOPMENT
    service_name: str = "duckdb-service"
    version: str = "1.0.0"
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    pool: PoolConfig = field(default_factory=PoolConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 扩展配置
    extensions: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """验证所有配置"""
        errors = []
        errors.extend(self.database.validate())
        errors.extend(self.pool.validate())
        errors.extend(self.security.validate())
        errors.extend(self.monitoring.validate())
        errors.extend(self.logging.validate())
        return errors
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DuckDBServiceConfig':
        """从字典创建配置"""
        # 处理环境枚举
        if 'environment' in data and isinstance(data['environment'], str):
            data['environment'] = Environment(data['environment'])
        
        # 处理日志级别枚举
        if 'logging' in data and 'level' in data['logging']:
            if isinstance(data['logging']['level'], str):
                data['logging']['level'] = LogLevel(data['logging']['level'])
        
        if 'logging' in data and 'console_level' in data['logging']:
            if isinstance(data['logging']['console_level'], str):
                data['logging']['console_level'] = LogLevel(data['logging']['console_level'])
        
        if 'security' in data and 'audit_log_level' in data['security']:
            if isinstance(data['security']['audit_log_level'], str):
                data['security']['audit_log_level'] = LogLevel(data['security']['audit_log_level'])
        
        # 创建子配置对象
        config = cls()
        
        if 'environment' in data:
            config.environment = data['environment']
        if 'service_name' in data:
            config.service_name = data['service_name']
        if 'version' in data:
            config.version = data['version']
        
        if 'database' in data:
            config.database = DatabaseConfig(**data['database'])
        if 'pool' in data:
            config.pool = PoolConfig(**data['pool'])
        if 'security' in data:
            config.security = SecurityConfig(**data['security'])
        if 'monitoring' in data:
            config.monitoring = MonitoringConfig(**data['monitoring'])
        if 'logging' in data:
            config.logging = LoggingConfig(**data['logging'])
        if 'extensions' in data:
            config.extensions = data['extensions']
        
        return config


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # 加密密钥
        self._encryption_key: Optional[bytes] = None
        if CRYPTO_AVAILABLE:
            self._init_encryption()
        
        logger.info(f"Config manager initialized with directory: {self.config_dir}")
    
    def _init_encryption(self):
        """初始化加密"""
        key_file = self.config_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                self._encryption_key = f.read()
        else:
            self._encryption_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self._encryption_key)
            # 设置文件权限为仅所有者可读写
            key_file.chmod(0o600)
    
    def load_config(self, environment: Environment = Environment.DEVELOPMENT,
                   config_file: Optional[str] = None) -> DuckDBServiceConfig:
        """加载配置"""
        # 默认配置
        config = DuckDBServiceConfig(environment=environment)
        
        # 加载基础配置文件
        base_config_file = self.config_dir / "base.yml"
        if base_config_file.exists():
            base_config = self._load_config_file(base_config_file)
            config = self._merge_config(config, base_config)
        
        # 加载环境特定配置
        env_config_file = self.config_dir / f"{environment.value}.yml"
        if env_config_file.exists():
            env_config = self._load_config_file(env_config_file)
            config = self._merge_config(config, env_config)
        
        # 加载指定配置文件
        if config_file:
            file_path = Path(config_file)
            if file_path.exists():
                file_config = self._load_config_file(file_path)
                config = self._merge_config(config, file_config)
        
        # 从环境变量覆盖配置
        config = self._apply_env_overrides(config)
        
        # 验证配置
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        logger.info(f"Configuration loaded for environment: {environment.value}")
        return config
    
    def save_config(self, config: DuckDBServiceConfig, 
                   filename: Optional[str] = None, encrypt_sensitive: bool = True):
        """保存配置"""
        if filename is None:
            filename = f"{config.environment.value}.yml"
        
        config_file = self.config_dir / filename
        config_data = config.to_dict()
        
        # 加密敏感信息
        if encrypt_sensitive and CRYPTO_AVAILABLE and self._encryption_key:
            config_data = self._encrypt_sensitive_data(config_data)
        
        if YAML_AVAILABLE:
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
        else:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        
        logger.info(f"Configuration saved to: {config_file}")
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml'] and YAML_AVAILABLE:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # 解密敏感信息
            if CRYPTO_AVAILABLE and self._encryption_key:
                data = self._decrypt_sensitive_data(data)
            
            return data or {}
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
            return {}
    
    def _merge_config(self, base_config: DuckDBServiceConfig, 
                     override_data: Dict[str, Any]) -> DuckDBServiceConfig:
        """合并配置"""
        base_dict = base_config.to_dict()
        merged_dict = self._deep_merge(base_dict, override_data)
        return DuckDBServiceConfig.from_dict(merged_dict)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: DuckDBServiceConfig) -> DuckDBServiceConfig:
        """应用环境变量覆盖"""
        # 环境变量映射
        env_mappings = {
            'DUCKDB_DATABASE_PATH': ('database', 'database_path'),
            'DUCKDB_MEMORY_LIMIT': ('database', 'memory_limit'),
            'DUCKDB_THREADS': ('database', 'threads'),
            'DUCKDB_MAX_CONNECTIONS': ('pool', 'max_connections'),
            'DUCKDB_MIN_CONNECTIONS': ('pool', 'min_connections'),
            'DUCKDB_ENABLE_MONITORING': ('monitoring', 'enable_monitoring'),
            'DUCKDB_LOG_LEVEL': ('logging', 'level'),
        }
        
        config_dict = config.to_dict()
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # 类型转换
                if key == 'threads' or key.endswith('_connections'):
                    value = int(value)
                elif key.startswith('enable_'):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif key == 'level':
                    value = LogLevel(value.upper())
                
                if section not in config_dict:
                    config_dict[section] = {}
                config_dict[section][key] = value
        
        return DuckDBServiceConfig.from_dict(config_dict)
    
    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """加密敏感数据"""
        if not self._encryption_key:
            return data
        
        fernet = Fernet(self._encryption_key)
        sensitive_keys = [
            'ssl_key_path', 'ssl_cert_path', 'database_path'
        ]
        
        def encrypt_recursive(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if k in sensitive_keys and isinstance(v, str):
                        result[k] = fernet.encrypt(v.encode()).decode()
                        result[f"{k}_encrypted"] = True
                    else:
                        result[k] = encrypt_recursive(v)
                return result
            elif isinstance(obj, list):
                return [encrypt_recursive(item) for item in obj]
            else:
                return obj
        
        return encrypt_recursive(data)
    
    def _decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解密敏感数据"""
        if not self._encryption_key:
            return data
        
        fernet = Fernet(self._encryption_key)
        
        def decrypt_recursive(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if k.endswith('_encrypted'):
                        continue
                    elif f"{k}_encrypted" in obj and obj[f"{k}_encrypted"]:
                        try:
                            result[k] = fernet.decrypt(v.encode()).decode()
                        except Exception as e:
                            logger.warning(f"Failed to decrypt {k}: {e}")
                            result[k] = v
                    else:
                        result[k] = decrypt_recursive(v)
                return result
            elif isinstance(obj, list):
                return [decrypt_recursive(item) for item in obj]
            else:
                return obj
        
        return decrypt_recursive(data)
    
    def create_sample_configs(self):
        """创建示例配置文件"""
        # 开发环境配置
        dev_config = DuckDBServiceConfig(
            environment=Environment.DEVELOPMENT,
            database=DatabaseConfig(
                database_path=":memory:",
                threads=2,
                memory_limit="512MB"
            ),
            pool=PoolConfig(
                min_connections=1,
                max_connections=5
            ),
            security=SecurityConfig(
                enable_access_control=False,
                enable_audit_log=False
            ),
            monitoring=MonitoringConfig(
                enable_monitoring=True,
                update_interval=5.0
            ),
            logging=LoggingConfig(
                level=LogLevel.DEBUG,
                enable_file_logging=False
            )
        )
        
        # 生产环境配置
        prod_config = DuckDBServiceConfig(
            environment=Environment.PRODUCTION,
            database=DatabaseConfig(
                database_path="/data/duckdb/production.db",
                threads=8,
                memory_limit="4GB",
                wal_mode=True
            ),
            pool=PoolConfig(
                min_connections=5,
                max_connections=20,
                idle_timeout=600.0
            ),
            security=SecurityConfig(
                enable_access_control=True,
                enable_audit_log=True,
                audit_log_path="/var/log/duckdb/audit.log",
                max_query_timeout=60.0
            ),
            monitoring=MonitoringConfig(
                enable_monitoring=True,
                enable_alerts=True,
                update_interval=10.0
            ),
            logging=LoggingConfig(
                level=LogLevel.INFO,
                enable_file_logging=True,
                log_file_path="/var/log/duckdb/service.log"
            )
        )
        
        # 保存示例配置
        self.save_config(dev_config, "development.yml", encrypt_sensitive=False)
        self.save_config(prod_config, "production.yml", encrypt_sensitive=True)
        
        logger.info("Sample configuration files created")


# 全局配置管理器
_config_manager: Optional[ConfigManager] = None
_current_config: Optional[DuckDBServiceConfig] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager


def load_config(environment: Environment = Environment.DEVELOPMENT,
               config_file: Optional[str] = None,
               config_dir: Optional[str] = None) -> DuckDBServiceConfig:
    """加载配置"""
    global _current_config
    manager = get_config_manager(config_dir)
    _current_config = manager.load_config(environment, config_file)
    return _current_config


def get_current_config() -> Optional[DuckDBServiceConfig]:
    """获取当前配置"""
    return _current_config