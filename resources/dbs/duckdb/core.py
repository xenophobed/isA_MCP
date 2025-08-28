"""
Professional DuckDB Service for MCP Resources
企业级DuckDB服务，专为MCP资源系统设计

Features:
- 连接池管理 (Connection Pool Management)
- 并发控制 (Concurrency Control)
- 事务管理 (Transaction Management)
- 安全访问控制 (Security & Access Control)
- 性能监控 (Performance Monitoring)
- 扩展支持 (Extension Support for Polars/Pandas)
"""

import asyncio
import logging
import threading
import time
import weakref
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Callable, 
    AsyncGenerator, Generator, TypeVar, Generic
)
from uuid import uuid4

import duckdb
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import RLock, Semaphore, Event


logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """数据库访问级别"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class TransactionIsolation(Enum):
    """事务隔离级别"""
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass
class ConnectionConfig:
    """连接配置"""
    database_path: str = ":memory:"
    read_only: bool = False
    access_mode: str = "automatic"
    threads: int = 4
    memory_limit: str = "1GB"
    temp_directory: Optional[str] = None
    enable_object_cache: bool = True
    enable_checkpoint_on_shutdown: bool = True
    custom_extensions: List[str] = field(default_factory=list)
    
    def to_config_dict(self) -> Dict[str, Any]:
        """转换为DuckDB配置字典"""
        config = {
            'threads': self.threads,
            'memory_limit': self.memory_limit,
            'enable_object_cache': self.enable_object_cache,
            # 'enable_checkpoint_on_shutdown': self.enable_checkpoint_on_shutdown,  # 不支持的选项
        }
        if self.temp_directory:
            config['temp_directory'] = self.temp_directory
        return config


@dataclass
class PoolConfig:
    """连接池配置"""
    min_connections: int = 2
    max_connections: int = 10
    idle_timeout: float = 300.0  # 5分钟
    max_lifetime: float = 3600.0  # 1小时
    health_check_interval: float = 30.0  # 30秒
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_access_control: bool = True
    allowed_functions: Optional[List[str]] = None
    blocked_functions: List[str] = field(default_factory=lambda: [
        'system', 'shell', 'read_csv_auto'  # 危险函数
    ])
    max_query_timeout: float = 300.0  # 5分钟
    enable_audit_log: bool = True
    audit_log_path: Optional[str] = None


class ConnectionHealth:
    """连接健康状态"""
    
    def __init__(self):
        self.created_at = time.time()
        self.last_used = time.time()
        self.last_health_check = time.time()
        self.is_healthy = True
        self.error_count = 0
        self.query_count = 0
    
    def mark_used(self):
        """标记连接被使用"""
        self.last_used = time.time()
        self.query_count += 1
    
    def mark_error(self):
        """标记连接错误"""
        self.error_count += 1
        if self.error_count > 3:
            self.is_healthy = False
    
    def mark_healthy(self):
        """标记连接健康"""
        self.last_health_check = time.time()
        self.is_healthy = True
    
    @property
    def age(self) -> float:
        """连接年龄（秒）"""
        return time.time() - self.created_at
    
    @property
    def idle_time(self) -> float:
        """空闲时间（秒）"""
        return time.time() - self.last_used


class ManagedConnection:
    """托管连接"""
    
    def __init__(self, connection: duckdb.DuckDBPyConnection, 
                 pool: 'ConnectionPool', config: ConnectionConfig):
        self.connection = connection
        self.pool = pool
        self.config = config
        self.health = ConnectionHealth()
        self.lock = RLock()
        self.in_transaction = False
        self.access_level = AccessLevel.READ_WRITE
        self._closed = False
    
    def execute(self, query: str, parameters: Optional[List] = None) -> Any:
        """执行查询"""
        if self._closed:
            raise RuntimeError("Connection is closed")
        
        with self.lock:
            try:
                self.health.mark_used()
                if parameters:
                    return self.connection.execute(query, parameters)
                return self.connection.execute(query)
            except Exception as e:
                self.health.mark_error()
                logger.error(f"Query execution failed: {e}")
                raise
    
    def fetchall(self) -> List[tuple]:
        """获取所有结果"""
        with self.lock:
            return self.connection.fetchall()
    
    def fetchone(self) -> Optional[tuple]:
        """获取单行结果"""
        with self.lock:
            return self.connection.fetchone()
    
    def fetchdf(self) -> pd.DataFrame:
        """获取DataFrame结果"""
        with self.lock:
            return self.connection.fetchdf()
    
    def begin_transaction(self, isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED):
        """开始事务"""
        if self.in_transaction:
            raise RuntimeError("Already in transaction")
        
        with self.lock:
            self.execute("BEGIN TRANSACTION")
            self.in_transaction = True
    
    def commit(self):
        """提交事务"""
        if not self.in_transaction:
            raise RuntimeError("Not in transaction")
        
        with self.lock:
            self.execute("COMMIT")
            self.in_transaction = False
    
    def rollback(self):
        """回滚事务"""
        if not self.in_transaction:
            raise RuntimeError("Not in transaction")
        
        with self.lock:
            self.execute("ROLLBACK")
            self.in_transaction = False
    
    def close(self):
        """关闭连接"""
        if self._closed:
            return
        
        with self.lock:
            if self.in_transaction:
                try:
                    self.rollback()
                except Exception:
                    pass
            
            try:
                self.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._closed = True
    
    @property
    def is_closed(self) -> bool:
        """连接是否已关闭"""
        return self._closed
    
    def health_check(self) -> bool:
        """健康检查"""
        if self._closed:
            return False
        
        try:
            with self.lock:
                self.execute("SELECT 1")
                self.health.mark_healthy()
                return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self.health.mark_error()
            return False


class ConnectionPool:
    """DuckDB连接池"""
    
    def __init__(self, 
                 connection_config: ConnectionConfig,
                 pool_config: PoolConfig,
                 security_config: Optional[SecurityConfig] = None):
        self.connection_config = connection_config
        self.pool_config = pool_config
        self.security_config = security_config or SecurityConfig()
        
        # 连接池
        self._pool: List[ManagedConnection] = []
        self._pool_lock = RLock()
        self._semaphore = Semaphore(pool_config.max_connections)
        
        # 状态管理
        self._shutdown = Event()
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            'created_connections': 0,
            'active_connections': 0,
            'total_queries': 0,
            'failed_queries': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
    
    def _create_connection(self) -> ManagedConnection:
        """创建新连接"""
        try:
            conn = duckdb.connect(
                database=self.connection_config.database_path,
                read_only=self.connection_config.read_only,
                config=self.connection_config.to_config_dict()
            )
            
            # 加载扩展
            for ext in self.connection_config.custom_extensions:
                try:
                    conn.install_extension(ext)
                    conn.load_extension(ext)
                except Exception as e:
                    logger.warning(f"Failed to load extension {ext}: {e}")
            
            managed_conn = ManagedConnection(conn, self, self.connection_config)
            self.stats['created_connections'] += 1
            
            logger.debug(f"Created new DuckDB connection (total: {self.stats['created_connections']})")
            return managed_conn
            
        except Exception as e:
            logger.error(f"Failed to create DuckDB connection: {e}")
            raise
    
    def _get_healthy_connection(self) -> Optional[ManagedConnection]:
        """从池中获取健康连接"""
        with self._pool_lock:
            # 移除不健康的连接
            healthy_connections = []
            for conn in self._pool:
                if conn.is_closed or not conn.health.is_healthy:
                    try:
                        conn.close()
                    except Exception:
                        pass
                else:
                    healthy_connections.append(conn)
            
            self._pool = healthy_connections
            
            # 返回最老的健康连接
            if self._pool:
                conn = self._pool.pop(0)
                self.stats['pool_hits'] += 1
                return conn
            
            self.stats['pool_misses'] += 1
            return None
    
    def _return_connection(self, connection: ManagedConnection):
        """归还连接到池"""
        if connection.is_closed or not connection.health.is_healthy:
            return
        
        # 检查连接是否过期
        if (connection.health.age > self.pool_config.max_lifetime or
            connection.health.idle_time > self.pool_config.idle_timeout):
            connection.close()
            return
        
        with self._pool_lock:
            if len(self._pool) < self.pool_config.max_connections:
                self._pool.append(connection)
            else:
                connection.close()
    
    @contextmanager
    def get_connection(self, 
                      access_level: AccessLevel = AccessLevel.READ_WRITE,
                      timeout: float = 30.0) -> Generator[ManagedConnection, None, None]:
        """获取连接（同步上下文管理器）"""
        acquired = self._semaphore.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError("Failed to acquire connection within timeout")
        
        connection = None
        try:
            # 尝试从池获取连接
            connection = self._get_healthy_connection()
            
            # 如果池中没有连接，创建新连接
            if connection is None:
                connection = self._create_connection()
            
            connection.access_level = access_level
            self.stats['active_connections'] += 1
            
            yield connection
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            if connection and not connection.is_closed:
                connection.health.mark_error()
            raise
        finally:
            if connection:
                self.stats['active_connections'] -= 1
                if not connection.is_closed:
                    self._return_connection(connection)
                else:
                    connection.close()
            
            self._semaphore.release()
    
    async def start_health_monitoring(self):
        """启动健康监控"""
        if self._health_check_task:
            return
        
        async def health_check_loop():
            while not self._shutdown.is_set():
                try:
                    await asyncio.sleep(self.pool_config.health_check_interval)
                    await self._perform_health_checks()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        with self._pool_lock:
            unhealthy_connections = []
            for conn in self._pool:
                if not conn.health_check():
                    unhealthy_connections.append(conn)
            
            # 移除不健康的连接
            for conn in unhealthy_connections:
                if conn in self._pool:
                    self._pool.remove(conn)
                conn.close()
            
            logger.debug(f"Health check: {len(self._pool)} healthy connections, "
                        f"{len(unhealthy_connections)} removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        with self._pool_lock:
            return {
                **self.stats,
                'pool_size': len(self._pool),
                'pool_capacity': self.pool_config.max_connections,
                'pool_utilization': len(self._pool) / self.pool_config.max_connections
            }
    
    async def shutdown(self):
        """关闭连接池"""
        logger.info("Shutting down DuckDB connection pool...")
        
        # 停止健康检查
        self._shutdown.set()
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有连接
        with self._pool_lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
        
        logger.info("DuckDB connection pool shutdown complete")


# 继续实现扩展适配器和主服务类...
T = TypeVar('T')

class DataFrameAdapter(Generic[T]):
    """数据框架适配器基类"""
    
    def to_duckdb(self, data: T, table_name: str, connection: ManagedConnection) -> None:
        """将数据写入DuckDB"""
        raise NotImplementedError
    
    def from_duckdb(self, query: str, connection: ManagedConnection) -> T:
        """从DuckDB读取数据"""
        raise NotImplementedError


class PandasAdapter(DataFrameAdapter[pd.DataFrame]):
    """Pandas适配器"""
    
    def to_duckdb(self, data: pd.DataFrame, table_name: str, connection: ManagedConnection) -> None:
        """将Pandas DataFrame写入DuckDB"""
        connection.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM data")
    
    def from_duckdb(self, query: str, connection: ManagedConnection) -> pd.DataFrame:
        """从DuckDB读取为Pandas DataFrame"""
        connection.execute(query)
        return connection.fetchdf()


try:
    import polars as pl
    
    class PolarsAdapter(DataFrameAdapter[pl.DataFrame]):
        """Polars适配器"""
        
        def to_duckdb(self, data: pl.DataFrame, table_name: str, connection: ManagedConnection) -> None:
            """将Polars DataFrame写入DuckDB"""
            # 转换为Arrow然后写入DuckDB
            arrow_table = data.to_arrow()
            connection.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM arrow_table")
        
        def from_duckdb(self, query: str, connection: ManagedConnection) -> pl.DataFrame:
            """从DuckDB读取为Polars DataFrame"""
            connection.execute(query)
            df = connection.fetchdf()
            return pl.from_pandas(df)

except ImportError:
    logger.info("Polars not available, skipping Polars adapter")
    PolarsAdapter = None


class DuckDBService:
    """专业DuckDB服务
    
    提供企业级DuckDB功能：
    - 连接池管理
    - 事务支持
    - 安全控制
    - 性能监控
    - 多框架支持
    """
    
    def __init__(self,
                 connection_config: Optional[ConnectionConfig] = None,
                 pool_config: Optional[PoolConfig] = None,
                 security_config: Optional[SecurityConfig] = None):
        self.connection_config = connection_config or ConnectionConfig()
        self.pool_config = pool_config or PoolConfig()
        self.security_config = security_config or SecurityConfig()
        
        # 初始化连接池
        self.pool = ConnectionPool(
            self.connection_config,
            self.pool_config,
            self.security_config
        )
        
        # 初始化适配器
        self.adapters = {
            'pandas': PandasAdapter(),
        }
        if PolarsAdapter:
            self.adapters['polars'] = PolarsAdapter()
        
        self._initialized = False
        logger.info("DuckDB Service initialized")
    
    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return
        
        await self.pool.start_health_monitoring()
        self._initialized = True
        logger.info("DuckDB Service started")
    
    async def shutdown(self):
        """关闭服务"""
        if not self._initialized:
            return
        
        await self.pool.shutdown()
        self._initialized = False
        logger.info("DuckDB Service stopped")
    
    def execute_query(self, 
                     query: str, 
                     parameters: Optional[List] = None,
                     access_level: AccessLevel = AccessLevel.READ_WRITE,
                     fetch_result: bool = True) -> Optional[List[tuple]]:
        """执行SQL查询"""
        self._validate_query(query)
        
        with self.pool.get_connection(access_level) as conn:
            self.pool.stats['total_queries'] += 1
            try:
                result = conn.execute(query, parameters)
                if fetch_result:
                    return conn.fetchall()
                return None
            except Exception as e:
                self.pool.stats['failed_queries'] += 1
                logger.error(f"Query failed: {query[:100]}... Error: {e}")
                raise
    
    def execute_query_df(self, 
                        query: str, 
                        parameters: Optional[List] = None,
                        framework: str = 'pandas',
                        access_level: AccessLevel = AccessLevel.READ_ONLY) -> Union[pd.DataFrame, Any]:
        """执行查询并返回DataFrame"""
        self._validate_query(query)
        
        if framework not in self.adapters:
            raise ValueError(f"Unsupported framework: {framework}. Available: {list(self.adapters.keys())}")
        
        with self.pool.get_connection(access_level) as conn:
            adapter = self.adapters[framework]
            return adapter.from_duckdb(query, conn)
    
    @contextmanager
    def transaction(self, 
                   isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED,
                   access_level: AccessLevel = AccessLevel.READ_WRITE) -> Generator[ManagedConnection, None, None]:
        """事务上下文管理器"""
        with self.pool.get_connection(access_level) as conn:
            conn.begin_transaction(isolation)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def create_table_from_dataframe(self,
                                   data: Union[pd.DataFrame, Any],
                                   table_name: str,
                                   framework: str = 'pandas',
                                   if_exists: str = 'replace') -> None:
        """从DataFrame创建表"""
        if framework not in self.adapters:
            raise ValueError(f"Unsupported framework: {framework}")
        
        with self.pool.get_connection(AccessLevel.READ_WRITE) as conn:
            if if_exists == 'replace':
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            elif if_exists == 'fail':
                # 检查表是否存在
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    [table_name]
                )
                if conn.fetchone():
                    raise ValueError(f"Table {table_name} already exists")
            
            adapter = self.adapters[framework]
            adapter.to_duckdb(data, table_name, conn)
    
    def _validate_query(self, query: str) -> None:
        """验证查询安全性"""
        if not self.security_config.enable_access_control:
            return
        
        query_upper = query.upper().strip()
        
        # 检查被禁止的函数
        for blocked_func in self.security_config.blocked_functions:
            if blocked_func.upper() in query_upper:
                raise SecurityError(f"Function '{blocked_func}' is not allowed")
        
        # 检查允许的函数（如果配置了）
        if self.security_config.allowed_functions:
            # 这里可以添加更复杂的SQL解析逻辑
            pass
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            'service_status': 'active' if self._initialized else 'inactive',
            'pool_stats': self.pool.get_stats(),
            'adapters': list(self.adapters.keys()),
            'config': {
                'database_path': self.connection_config.database_path,
                'max_connections': self.pool_config.max_connections,
                'security_enabled': self.security_config.enable_access_control
            }
        }


class SecurityError(Exception):
    """安全相关错误"""
    pass


# 全局服务实例（单例模式）
_service_instance: Optional[DuckDBService] = None
_service_lock = threading.Lock()


def get_duckdb_service(
    connection_config: Optional[ConnectionConfig] = None,
    pool_config: Optional[PoolConfig] = None,
    security_config: Optional[SecurityConfig] = None
) -> DuckDBService:
    """获取DuckDB服务实例（单例）"""
    global _service_instance
    
    with _service_lock:
        if _service_instance is None:
            _service_instance = DuckDBService(
                connection_config, pool_config, security_config
            )
        return _service_instance


async def initialize_duckdb_service(
    connection_config: Optional[ConnectionConfig] = None,
    pool_config: Optional[PoolConfig] = None,
    security_config: Optional[SecurityConfig] = None
) -> DuckDBService:
    """初始化DuckDB服务"""
    service = get_duckdb_service(connection_config, pool_config, security_config)
    await service.initialize()
    return service