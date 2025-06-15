from typing import Optional, Dict, Any, List
import pandas as pd
from contextlib import contextmanager
from app.services.db.duckdb.duck_pool import DuckDBConnectionPool
import logging
from filelock import FileLock
import os

logger = logging.getLogger(__name__)

class DuckDBService:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not config:
            from app.config.config_manager import config_manager
            config = config_manager.get_config('duckdb')
            
        # 获取配置
        conn_params = config.get_connection_params()
        pool_settings = config.get_pool_settings() if hasattr(config, 'get_pool_settings') else {}
        
        # 确保目录存在
        os.makedirs(os.path.dirname(conn_params['database']), exist_ok=True)
        
        # 从 config 中提取连接池需要的参数
        pool_params = {
            'database': conn_params['database'],
            'threads': conn_params.get('config', {}).get('threads', 4),
            'memory_limit': conn_params.get('config', {}).get('memory_limit', '4GB'),
            'temp_directory': conn_params.get('config', {}).get('temp_directory'),
            'min_connections': pool_settings.get('min_connections', 1),
            'max_connections': pool_settings.get('max_connections', 10),
            'max_idle_time': pool_settings.get('max_idle_time', 300)
        }
        
        # 创建连接池
        self.pool = DuckDBConnectionPool(**pool_params)
        
        # 文件锁
        self.lock_path = f"{conn_params['database']}.lock"
        self.file_lock = FileLock(self.lock_path, timeout=30)
    
    def query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """
        执行查询并返回DataFrame
        
        Args:
            query: SQL查询语句
            params: 查询参数列表
            
        Returns:
            pd.DataFrame: 查询结果DataFrame
        """
        with self.pool.get_connection() as conn:
            try:
                if params:
                    result = conn.execute(query, params).fetchdf()
                else:
                    result = conn.execute(query).fetchdf()
                return result
            except Exception as e:
                logger.error(f"Query failed: {str(e)}")
                raise
    
    def execute(self, sql: str, params: Optional[List[Any]] = None):
        """执行SQL语句"""
        with self.pool.get_connection() as conn:
            try:
                if params:
                    return conn.execute(sql, params)
                return conn.execute(sql)
            except Exception as e:
                logger.error(f"SQL execution failed: {str(e)}")
                raise
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = None
        try:
            with self.pool.get_connection() as conn:
                with self.file_lock:  # 文件锁放在外层
                    try:
                        conn.execute("BEGIN TRANSACTION")
                        yield conn
                        conn.execute("COMMIT")
                    except Exception as e:
                        conn.execute("ROLLBACK")
                        raise e
        finally:
            # 连接会通过 pool.get_connection 的上下文管理器自动返回到连接池
            pass
    
    def cleanup(self):
        """清理资源"""
        self.pool.close_all()