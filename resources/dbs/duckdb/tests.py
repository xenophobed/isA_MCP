"""
DuckDB Service Unit Tests
全面的单元测试套件，确保服务的可靠性和正确性

Test Coverage:
- 核心服务功能测试
- 连接池管理测试
- 并发和事务测试
- 安全性测试
- 监控系统测试
- 配置管理测试
- MCP资源接口测试
"""

import asyncio
import json
import pytest
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

import pandas as pd

# 导入被测试的模块
from .core import (
    DuckDBService, ConnectionConfig, PoolConfig, SecurityConfig,
    AccessLevel, TransactionIsolation, ManagedConnection, ConnectionPool,
    get_duckdb_service, initialize_duckdb_service
)
from .mcp_resource import DuckDBResourceProvider, get_duckdb_resource_provider
from .monitoring import (
    DuckDBMonitor, QueryMonitor, HealthChecker, AlertManager,
    MetricType, AlertLevel, get_duckdb_monitor
)
from .config import (
    DuckDBServiceConfig, DatabaseConfig, ConfigManager,
    Environment, LogLevel, load_config
)


class TestDatabaseConfig:
    """数据库配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = DatabaseConfig()
        assert config.database_path == ":memory:"
        assert config.read_only is False
        assert config.threads == 4
        assert config.memory_limit == "1GB"
    
    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        config = DatabaseConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # 无效线程数
        config.threads = 0
        errors = config.validate()
        assert any("threads must be between" in error for error in errors)
        
        # 无效内存限制
        config.threads = 4
        config.memory_limit = "invalid"
        errors = config.validate()
        assert any("Invalid memory_limit format" in error for error in errors)
    
    def test_config_dict_conversion(self):
        """测试配置字典转换"""
        config = DatabaseConfig(threads=8, memory_limit="2GB")
        config_dict = config.to_config_dict()
        
        assert config_dict['threads'] == 8
        assert config_dict['memory_limit'] == "2GB"
        assert 'enable_object_cache' in config_dict


class TestPoolConfig:
    """连接池配置测试"""
    
    def test_default_pool_config(self):
        """测试默认池配置"""
        config = PoolConfig()
        assert config.min_connections == 2
        assert config.max_connections == 10
        assert config.idle_timeout == 300.0
    
    def test_pool_config_validation(self):
        """测试池配置验证"""
        # 有效配置
        config = PoolConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # 无效连接数配置
        config.max_connections = 1
        config.min_connections = 5
        errors = config.validate()
        assert any("max_connections must be >= min_connections" in error for error in errors)


class TestDuckDBService:
    """DuckDB服务核心功能测试"""
    
    @pytest.fixture
    def service(self):
        """测试服务实例"""
        config = ConnectionConfig(database_path=":memory:")
        pool_config = PoolConfig(min_connections=1, max_connections=3)
        service = DuckDBService(config, pool_config)
        return service
    
    @pytest.fixture
    async def initialized_service(self, service):
        """初始化的服务实例"""
        await service.initialize()
        yield service
        await service.shutdown()
    
    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.connection_config.database_path == ":memory:"
        assert service.pool_config.max_connections == 3
        assert service._initialized is False
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, service):
        """测试服务生命周期"""
        # 初始化
        await service.initialize()
        assert service._initialized is True
        
        # 关闭
        await service.shutdown()
        assert service._initialized is False
    
    def test_basic_query_execution(self, service):
        """测试基本查询执行"""
        result = service.execute_query("SELECT 1 as test_column")
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == 1
    
    def test_query_with_parameters(self, service):
        """测试参数化查询"""
        result = service.execute_query("SELECT ? as value", [42])
        assert result is not None
        assert result[0][0] == 42
    
    def test_dataframe_query(self, service):
        """测试DataFrame查询"""
        # 创建测试表
        service.execute_query("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
        service.execute_query("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
        
        # 查询DataFrame
        df = service.execute_query_df("SELECT * FROM test_table ORDER BY id")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]['id'] == 1
        assert df.iloc[0]['name'] == 'Alice'
    
    def test_table_creation_from_dataframe(self, service):
        """测试从DataFrame创建表"""
        # 创建测试DataFrame
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10.5, 20.5, 30.5]
        })
        
        # 创建表
        service.create_table_from_dataframe(df, 'df_test_table')
        
        # 验证表内容
        result = service.execute_query("SELECT COUNT(*) FROM df_test_table")
        assert result[0][0] == 3
    
    def test_transaction_management(self, service):
        """测试事务管理"""
        # 创建测试表
        service.execute_query("CREATE TABLE transaction_test (id INTEGER)")
        
        # 测试成功事务
        with service.transaction() as conn:
            conn.execute("INSERT INTO transaction_test VALUES (1)")
            conn.execute("INSERT INTO transaction_test VALUES (2)")
        
        result = service.execute_query("SELECT COUNT(*) FROM transaction_test")
        assert result[0][0] == 2
        
        # 测试回滚事务
        try:
            with service.transaction() as conn:
                conn.execute("INSERT INTO transaction_test VALUES (3)")
                raise Exception("Test exception")
        except Exception:
            pass
        
        result = service.execute_query("SELECT COUNT(*) FROM transaction_test")
        assert result[0][0] == 2  # 第三条记录应该被回滚
    
    def test_concurrent_queries(self, service):
        """测试并发查询"""
        def execute_query(query_id):
            result = service.execute_query(f"SELECT {query_id} as id")
            return result[0][0]
        
        # 并发执行查询
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_query, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        assert len(results) == 10
        assert set(results) == set(range(10))
    
    def test_security_validation(self):
        """测试安全验证"""
        security_config = SecurityConfig(
            enable_access_control=True,
            blocked_functions=['system']
        )
        service = DuckDBService(security_config=security_config)
        
        with pytest.raises(Exception):  # 应该抛出安全错误
            service.execute_query("SELECT system('ls')")


class TestConnectionPool:
    """连接池测试"""
    
    @pytest.fixture
    def pool(self):
        """测试连接池"""
        config = ConnectionConfig(database_path=":memory:")
        pool_config = PoolConfig(min_connections=1, max_connections=3)
        return ConnectionPool(config, pool_config)
    
    def test_connection_acquisition(self, pool):
        """测试连接获取"""
        with pool.get_connection() as conn:
            assert isinstance(conn, ManagedConnection)
            assert not conn.is_closed
            
            # 执行简单查询
            result = conn.execute("SELECT 1")
            assert conn.fetchone()[0] == 1
    
    def test_connection_pooling(self, pool):
        """测试连接池复用"""
        initial_stats = pool.get_stats()
        
        # 获取并释放连接
        with pool.get_connection() as conn1:
            conn1_id = id(conn1.connection)
        
        with pool.get_connection() as conn2:
            conn2_id = id(conn2.connection)
        
        # 应该复用相同的连接
        assert conn1_id == conn2_id
        
        final_stats = pool.get_stats()
        assert final_stats['pool_hits'] >= initial_stats['pool_hits']
    
    def test_connection_timeout(self, pool):
        """测试连接超时"""
        # 占用所有连接
        connections = []
        for _ in range(pool.pool_config.max_connections):
            conn = pool.get_connection(timeout=1.0).__enter__()
            connections.append(conn)
        
        # 尝试获取额外连接应该超时
        with pytest.raises(TimeoutError):
            with pool.get_connection(timeout=0.1):
                pass
        
        # 清理连接
        for conn in connections:
            pool.get_connection(timeout=1.0).__exit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, pool):
        """测试健康监控"""
        await pool.start_health_monitoring()
        
        # 等待一次健康检查
        await asyncio.sleep(0.1)
        
        await pool.shutdown()


class TestMCPResourceProvider:
    """MCP资源提供器测试"""
    
    @pytest.fixture
    def service(self):
        """测试服务"""
        return DuckDBService(ConnectionConfig(database_path=":memory:"))
    
    @pytest.fixture
    def provider(self, service):
        """测试资源提供器"""
        return DuckDBResourceProvider(service)
    
    @pytest.fixture
    def mock_session(self):
        """模拟MCP会话"""
        return Mock()
    
    def test_provider_initialization(self, provider):
        """测试提供器初始化"""
        assert provider.service is not None
        assert len(provider.uri_patterns) > 0
        assert "duckdb://query/" in provider.uri_patterns
    
    @pytest.mark.asyncio
    async def test_list_resources(self, provider, mock_session):
        """测试资源列表"""
        # 创建测试表
        provider.service.execute_query("CREATE TABLE test_table (id INTEGER)")
        
        resources = await provider.list_resources(mock_session)
        assert len(resources) > 0
        
        # 检查是否包含基础查询资源
        query_resources = [r for r in resources if r.uri.startswith("duckdb://query/")]
        assert len(query_resources) > 0
        
        # 检查是否包含表资源
        table_resources = [r for r in resources if r.uri.startswith("duckdb://table/")]
        assert any("test_table" in r.uri for r in table_resources)
    
    @pytest.mark.asyncio
    async def test_query_resource(self, provider, mock_session):
        """测试查询资源"""
        uri = "duckdb://query/?sql=SELECT 1 as test"
        result = await provider.read_resource(mock_session, uri)
        
        assert result.mimeType == "application/json"
        
        data = json.loads(result.text)
        assert "query" in data
        assert "data" in data
        assert data["data"][0][0] == 1
    
    @pytest.mark.asyncio
    async def test_table_resource(self, provider, mock_session):
        """测试表资源"""
        # 创建测试表
        provider.service.execute_query("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
        provider.service.execute_query("INSERT INTO test_table VALUES (1, 'Test')")
        
        uri = "duckdb://table/test_table"
        result = await provider.read_resource(mock_session, uri)
        
        assert result.mimeType == "application/json"
        
        data = json.loads(result.text)
        assert data["table_name"] == "test_table"
        assert data["total_rows"] == 1
        assert len(data["data"]) == 1
    
    @pytest.mark.asyncio
    async def test_export_resource(self, provider, mock_session):
        """测试导出资源"""
        # 创建测试数据
        provider.service.execute_query("CREATE TABLE export_test (id INTEGER, value REAL)")
        provider.service.execute_query("INSERT INTO export_test VALUES (1, 10.5), (2, 20.5)")
        
        # 测试CSV导出
        uri = "duckdb://export/export_test?format=csv"
        result = await provider.read_resource(mock_session, uri)
        
        assert result.mimeType == "text/csv"
        assert "id,value" in result.text
        assert "1,10.5" in result.text
    
    @pytest.mark.asyncio
    async def test_stats_resource(self, provider, mock_session):
        """测试统计资源"""
        uri = "duckdb://stats/service"
        result = await provider.read_resource(mock_session, uri)
        
        assert result.mimeType == "application/json"
        
        data = json.loads(result.text)
        assert "service_stats" in data
        assert "cache_stats" in data
    
    @pytest.mark.asyncio
    async def test_error_handling(self, provider, mock_session):
        """测试错误处理"""
        # 无效SQL查询
        uri = "duckdb://query/?sql=INVALID SQL"
        result = await provider.read_resource(mock_session, uri)
        
        data = json.loads(result.text)
        assert "error" in data
    
    def test_cache_functionality(self, provider):
        """测试缓存功能"""
        # 执行相同查询两次
        query = "SELECT 1 as test"
        cache_key = f"query:{hash(query)}:json"
        
        # 第一次查询
        provider._add_to_cache(cache_key, "test_content")
        
        # 检查缓存
        assert cache_key in provider._query_cache
        assert provider._query_cache[cache_key]['content'] == "test_content"
        
        # 清空缓存
        provider.clear_cache()
        assert len(provider._query_cache) == 0


class TestMonitoring:
    """监控系统测试"""
    
    @pytest.fixture
    def service(self):
        """测试服务"""
        return DuckDBService(ConnectionConfig(database_path=":memory:"))
    
    @pytest.fixture
    def monitor(self, service):
        """测试监控器"""
        return DuckDBMonitor(service, update_interval=0.1)
    
    def test_query_monitor(self):
        """测试查询监控"""
        monitor = QueryMonitor()
        
        # 记录查询
        monitor.record_query("SELECT 1", 0.5, success=True)
        monitor.record_query("SELECT 2", 1.5, success=True)  # 慢查询
        monitor.record_query("INVALID", 0.1, success=False, error="Syntax error")
        
        # 检查统计
        stats = monitor.get_query_statistics()
        assert stats['total_queries'] == 3
        assert stats['total_errors'] == 1
        assert stats['error_rate'] == 1/3
        
        # 检查慢查询
        slow_queries = monitor.get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0]['duration'] == 1.5
    
    def test_alert_manager(self):
        """测试告警管理"""
        alert_manager = AlertManager()
        
        # 创建告警
        alert = alert_manager.create_alert(
            AlertLevel.WARNING,
            "Test Alert",
            "This is a test alert"
        )
        
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "Test Alert"
        assert not alert.resolved
        
        # 获取活跃告警
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        
        # 解决告警
        alert_manager.resolve_alert(alert.id)
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_lifecycle(self, monitor):
        """测试监控器生命周期"""
        # 启动监控
        await monitor.start_monitoring()
        assert monitor._monitoring_task is not None
        
        # 等待一些监控周期
        await asyncio.sleep(0.3)
        
        # 停止监控
        await monitor.stop_monitoring()
        assert monitor._monitoring_task is None
    
    def test_query_timing(self, monitor):
        """测试查询计时"""
        sql = "SELECT 1"
        
        with monitor.get_query_timer(sql) as timer:
            time.sleep(0.1)  # 模拟查询执行时间
        
        # 检查是否记录了时间
        duration_metric = monitor.metrics['query_duration']
        assert duration_metric.get_current_value() >= 0.1
    
    @pytest.mark.asyncio
    async def test_health_checker(self, service):
        """测试健康检查器"""
        health_checker = HealthChecker(service)
        
        # 执行健康检查
        health_result = await health_checker.perform_health_check()
        
        assert 'overall_healthy' in health_result
        assert 'checks' in health_result
        assert 'database' in health_result['checks']
        
        # 数据库应该是健康的
        assert health_result['checks']['database']['healthy'] is True


class TestConfigManager:
    """配置管理测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """配置管理器"""
        return ConfigManager(temp_config_dir)
    
    def test_config_manager_initialization(self, config_manager, temp_config_dir):
        """测试配置管理器初始化"""
        assert config_manager.config_dir == Path(temp_config_dir)
        assert config_manager.config_dir.exists()
    
    def test_default_config_loading(self, config_manager):
        """测试默认配置加载"""
        config = config_manager.load_config(Environment.DEVELOPMENT)
        
        assert isinstance(config, DuckDBServiceConfig)
        assert config.environment == Environment.DEVELOPMENT
        assert config.database.database_path == ":memory:"
    
    def test_config_saving_and_loading(self, config_manager):
        """测试配置保存和加载"""
        # 创建自定义配置
        config = DuckDBServiceConfig(
            environment=Environment.TESTING,
            database=DatabaseConfig(
                database_path="/tmp/test.db",
                threads=8
            )
        )
        
        # 保存配置
        config_manager.save_config(config, "test.yml")
        
        # 加载配置
        loaded_config = config_manager.load_config(
            Environment.TESTING,
            config_file=config_manager.config_dir / "test.yml"
        )
        
        assert loaded_config.environment == Environment.TESTING
        assert loaded_config.database.database_path == "/tmp/test.db"
        assert loaded_config.database.threads == 8
    
    @patch.dict(os.environ, {'DUCKDB_THREADS': '16', 'DUCKDB_LOG_LEVEL': 'DEBUG'})
    def test_environment_variable_override(self, config_manager):
        """测试环境变量覆盖"""
        config = config_manager.load_config(Environment.DEVELOPMENT)
        
        assert config.database.threads == 16
        assert config.logging.level == LogLevel.DEBUG
    
    def test_config_validation(self, config_manager):
        """测试配置验证"""
        # 创建无效配置
        invalid_config = DuckDBServiceConfig(
            database=DatabaseConfig(threads=0),  # 无效线程数
            pool=PoolConfig(max_connections=1, min_connections=5)  # 无效连接数
        )
        
        errors = invalid_config.validate()
        assert len(errors) > 0
        assert any("threads must be between" in error for error in errors)
        assert any("max_connections must be >=" in error for error in errors)
    
    def test_sample_config_creation(self, config_manager):
        """测试示例配置创建"""
        config_manager.create_sample_configs()
        
        # 检查文件是否创建
        dev_config_file = config_manager.config_dir / "development.yml"
        prod_config_file = config_manager.config_dir / "production.yml"
        
        assert dev_config_file.exists()
        assert prod_config_file.exists()


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_service_integration(self):
        """测试完整服务集成"""
        # 创建配置
        config = DuckDBServiceConfig(
            database=DatabaseConfig(database_path=":memory:"),
            pool=PoolConfig(min_connections=1, max_connections=3),
            monitoring=MonitoringConfig(update_interval=0.1)
        )
        
        # 初始化服务
        service = await initialize_duckdb_service(
            config.database, config.pool, config.security
        )
        
        try:
            # 初始化监控
            monitor = get_duckdb_monitor(service, config.monitoring.update_interval)
            await monitor.start_monitoring()
            
            # 初始化资源提供器
            provider = get_duckdb_resource_provider(service)
            
            # 执行一些操作
            service.execute_query("CREATE TABLE integration_test (id INTEGER, name VARCHAR)")
            service.execute_query("INSERT INTO integration_test VALUES (1, 'Test')")
            
            # 测试MCP资源
            mock_session = Mock()
            resources = await provider.list_resources(mock_session)
            assert len(resources) > 0
            
            # 测试查询资源
            query_uri = "duckdb://query/?sql=SELECT COUNT(*) FROM integration_test"
            result = await provider.read_resource(mock_session, query_uri)
            
            data = json.loads(result.text)
            assert data["data"][0][0] == 1
            
            # 检查监控报告
            report = monitor.get_monitoring_report()
            assert "service_status" in report
            assert "metrics" in report
            
            # 停止监控
            await monitor.stop_monitoring()
            
        finally:
            # 清理
            await service.shutdown()
    
    def test_concurrent_service_access(self):
        """测试并发服务访问"""
        service = DuckDBService(ConnectionConfig(database_path=":memory:"))
        
        # 创建测试表
        service.execute_query("CREATE TABLE concurrent_test (id INTEGER, thread_id INTEGER)")
        
        def worker_function(thread_id, iterations=10):
            """工作线程函数"""
            results = []
            for i in range(iterations):
                try:
                    service.execute_query(
                        "INSERT INTO concurrent_test VALUES (?, ?)",
                        [i, thread_id]
                    )
                    results.append((i, thread_id))
                except Exception as e:
                    results.append(('error', str(e)))
            return results
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(worker_function, thread_id, 20)
                for thread_id in range(5)
            ]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # 验证结果
        final_count = service.execute_query("SELECT COUNT(*) FROM concurrent_test")
        assert final_count[0][0] == 100  # 5 threads * 20 iterations each
        
        # 检查数据完整性
        thread_counts = service.execute_query(
            "SELECT thread_id, COUNT(*) FROM concurrent_test GROUP BY thread_id ORDER BY thread_id"
        )
        assert len(thread_counts) == 5
        for thread_id, count in thread_counts:
            assert count == 20


# 测试运行配置
@pytest.fixture(scope="session")
def event_loop():
    """为异步测试提供事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])