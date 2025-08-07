"""
DuckDB Service Monitoring and Metrics
提供全面的DuckDB服务监控、指标收集和性能分析

Features:
- 实时性能指标收集
- 查询执行监控
- 连接池监控
- 健康检查系统
- 异常报警
- 性能分析报告
"""

import asyncio
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Deque
from statistics import mean, median

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available, system metrics will be limited")


logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 累计计数器
    GAUGE = "gauge"          # 瞬时值
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """告警信息"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: float
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[float] = None


class Metric:
    """基础指标类"""
    
    def __init__(self, name: str, metric_type: MetricType, 
                 description: str = "", max_points: int = 1000):
        self.name = name
        self.type = metric_type
        self.description = description
        self.max_points = max_points
        
        # 数据存储
        self.points: Deque[MetricPoint] = deque(maxlen=max_points)
        self.current_value: Optional[float] = None
        self.lock = threading.RLock()
        
        # 统计信息
        self.total_count = 0
        self.last_updated = 0.0
    
    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None, 
                  timestamp: Optional[float] = None):
        """添加数据点"""
        with self.lock:
            ts = timestamp or time.time()
            point = MetricPoint(ts, value, labels or {})
            
            self.points.append(point)
            self.current_value = value
            self.last_updated = ts
            self.total_count += 1
    
    def get_current_value(self) -> Optional[float]:
        """获取当前值"""
        with self.lock:
            return self.current_value
    
    def get_recent_values(self, duration: float = 300.0) -> List[float]:
        """获取最近一段时间的值"""
        with self.lock:
            cutoff_time = time.time() - duration
            return [p.value for p in self.points if p.timestamp >= cutoff_time]
    
    def get_statistics(self, duration: float = 300.0) -> Dict[str, Any]:
        """获取统计信息"""
        recent_values = self.get_recent_values(duration)
        
        if not recent_values:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None
            }
        
        return {
            "count": len(recent_values),
            "min": min(recent_values),
            "max": max(recent_values),
            "mean": mean(recent_values),
            "median": median(recent_values)
        }


class Timer:
    """计时器上下文管理器"""
    
    def __init__(self, metric: Metric, labels: Optional[Dict[str, str]] = None):
        self.metric = metric
        self.labels = labels or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metric.add_point(duration, self.labels)


class QueryMonitor:
    """查询监控器"""
    
    def __init__(self, max_slow_queries: int = 100):
        self.max_slow_queries = max_slow_queries
        
        # 慢查询记录
        self.slow_queries: Deque[Dict[str, Any]] = deque(maxlen=max_slow_queries)
        self.slow_query_threshold = 1.0  # 1秒
        
        # 查询统计
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'errors': 0
        })
        
        self.lock = threading.RLock()
    
    def record_query(self, sql: str, duration: float, success: bool = True, 
                    error: Optional[str] = None):
        """记录查询执行情况"""
        with self.lock:
            # 查询哈希（简化版）
            query_hash = hash(sql[:200])  # 使用前200字符的hash作为标识
            
            # 更新统计
            stats = self.query_stats[query_hash]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['max_time'] = max(stats['max_time'], duration)
            
            if not success:
                stats['errors'] += 1
            
            # 记录慢查询
            if duration > self.slow_query_threshold:
                slow_query = {
                    'sql': sql[:500],  # 限制长度
                    'duration': duration,
                    'timestamp': time.time(),
                    'success': success,
                    'error': error
                }
                self.slow_queries.append(slow_query)
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        with self.lock:
            return list(self.slow_queries)[-limit:]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        with self.lock:
            total_queries = sum(stats['count'] for stats in self.query_stats.values())
            total_errors = sum(stats['errors'] for stats in self.query_stats.values())
            
            if total_queries == 0:
                return {
                    'total_queries': 0,
                    'total_errors': 0,
                    'error_rate': 0.0,
                    'avg_query_time': 0.0,
                    'slow_queries_count': 0
                }
            
            total_time = sum(stats['total_time'] for stats in self.query_stats.values())
            
            return {
                'total_queries': total_queries,
                'total_errors': total_errors,
                'error_rate': total_errors / total_queries,
                'avg_query_time': total_time / total_queries,
                'slow_queries_count': len(self.slow_queries)
            }


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, service):
        self.service = service
        self.last_check_time = 0.0
        self.is_healthy = True
        self.health_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        check_time = time.time()
        health_result = {
            'timestamp': check_time,
            'overall_healthy': True,
            'checks': {}
        }
        
        try:
            # 检查数据库连接
            db_health = await self._check_database_connectivity()
            health_result['checks']['database'] = db_health
            
            # 检查连接池状态
            pool_health = await self._check_connection_pool()
            health_result['checks']['connection_pool'] = pool_health
            
            # 检查系统资源
            if PSUTIL_AVAILABLE:
                system_health = await self._check_system_resources()
                health_result['checks']['system'] = system_health
            
            # 计算总体健康状态
            health_result['overall_healthy'] = all(
                check.get('healthy', True) for check in health_result['checks'].values()
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_result['overall_healthy'] = False
            health_result['error'] = str(e)
        
        # 更新状态
        self.is_healthy = health_result['overall_healthy']
        self.last_check_time = check_time
        
        # 保存历史
        self.health_history.append(health_result)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
        
        return health_result
    
    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """检查数据库连接性"""
        try:
            start_time = time.time()
            self.service.execute_query("SELECT 1", access_level=self.service.AccessLevel.READ_ONLY)
            response_time = time.time() - start_time
            
            return {
                'healthy': True,
                'response_time': response_time,
                'message': 'Database connection OK'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'message': 'Database connection failed'
            }
    
    async def _check_connection_pool(self) -> Dict[str, Any]:
        """检查连接池状态"""
        try:
            stats = self.service.pool.get_stats()
            
            # 检查连接池利用率
            utilization = stats.get('pool_utilization', 0)
            is_healthy = utilization < 0.9  # 90%以下认为健康
            
            return {
                'healthy': is_healthy,
                'utilization': utilization,
                'active_connections': stats.get('active_connections', 0),
                'pool_size': stats.get('pool_size', 0),
                'message': f"Pool utilization: {utilization:.1%}"
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'message': 'Connection pool check failed'
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率（如果使用文件数据库）
            disk_percent = 0
            if self.service.connection_config.database_path != ":memory:":
                disk_usage = psutil.disk_usage('/')
                disk_percent = disk_usage.percent
            
            # 健康判断
            is_healthy = (
                cpu_percent < 80 and 
                memory_percent < 85 and 
                disk_percent < 90
            )
            
            return {
                'healthy': is_healthy,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'message': f"CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%"
            }
        except Exception as e:
            return {
                'healthy': True,  # 系统检查失败不影响服务健康状态
                'error': str(e),
                'message': 'System resource check failed'
            }


class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.alerts: Deque[Alert] = deque(maxlen=max_alerts)
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.lock = threading.RLock()
        
        # 告警规则
        self.rules = {}
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def create_alert(self, level: AlertLevel, title: str, message: str,
                    metric_name: Optional[str] = None, metric_value: Optional[float] = None) -> Alert:
        """创建告警"""
        alert = Alert(
            id=f"{int(time.time())}-{hash(title + message) & 0xFFFF}",
            level=level,
            title=title,
            message=message,
            timestamp=time.time(),
            metric_name=metric_name,
            metric_value=metric_value
        )
        
        with self.lock:
            self.alerts.append(alert)
            
            # 调用告警处理器
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler failed: {e}")
        
        logger.warning(f"Alert created: [{level.value.upper()}] {title}: {message}")
        return alert
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        with self.lock:
            for alert in self.alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = time.time()
                    logger.info(f"Alert resolved: {alert.title}")
                    break
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取活跃告警"""
        with self.lock:
            alerts = [alert for alert in self.alerts if not alert.resolved]
            if level:
                alerts = [alert for alert in alerts if alert.level == level]
            return alerts
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        with self.lock:
            active_alerts = [alert for alert in self.alerts if not alert.resolved]
            
            # 按级别统计
            level_counts = defaultdict(int)
            for alert in active_alerts:
                level_counts[alert.level.value] += 1
            
            return {
                'total_alerts': len(self.alerts),
                'active_alerts': len(active_alerts),
                'by_level': dict(level_counts),
                'resolved_alerts': len(self.alerts) - len(active_alerts)
            }


class DuckDBMonitor:
    """DuckDB服务综合监控器"""
    
    def __init__(self, service, update_interval: float = 10.0):
        self.service = service
        self.update_interval = update_interval
        
        # 组件初始化
        self.query_monitor = QueryMonitor()
        self.health_checker = HealthChecker(service)
        self.alert_manager = AlertManager()
        
        # 指标收集
        self.metrics: Dict[str, Metric] = {}
        self._init_metrics()
        
        # 监控状态
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # 添加默认告警处理器
        self.alert_manager.add_alert_handler(self._default_alert_handler)
        
        logger.info("DuckDB Monitor initialized")
    
    def _init_metrics(self):
        """初始化指标"""
        # 连接池指标
        self.metrics['pool_active_connections'] = Metric(
            'pool_active_connections', MetricType.GAUGE,
            'Number of active connections in the pool'
        )
        self.metrics['pool_utilization'] = Metric(
            'pool_utilization', MetricType.GAUGE,
            'Connection pool utilization percentage'
        )
        
        # 查询指标
        self.metrics['query_duration'] = Metric(
            'query_duration', MetricType.TIMER,
            'Query execution duration in seconds'
        )
        self.metrics['query_count'] = Metric(
            'query_count', MetricType.COUNTER,
            'Total number of queries executed'
        )
        self.metrics['query_errors'] = Metric(
            'query_errors', MetricType.COUNTER,
            'Total number of query errors'
        )
        
        # 系统指标
        if PSUTIL_AVAILABLE:
            self.metrics['cpu_usage'] = Metric(
                'cpu_usage', MetricType.GAUGE,
                'CPU usage percentage'
            )
            self.metrics['memory_usage'] = Metric(
                'memory_usage', MetricType.GAUGE,
                'Memory usage percentage'
            )
    
    async def start_monitoring(self):
        """开始监控"""
        if self._monitoring_task:
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("DuckDB monitoring started")
    
    async def stop_monitoring(self):
        """停止监控"""
        if not self._monitoring_task:
            return
        
        self._shutdown_event.set()
        try:
            await asyncio.wait_for(self._monitoring_task, timeout=5.0)
        except asyncio.TimeoutError:
            self._monitoring_task.cancel()
        
        self._monitoring_task = None
        logger.info("DuckDB monitoring stopped")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while not self._shutdown_event.is_set():
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _collect_metrics(self):
        """收集指标"""
        try:
            # 连接池指标
            pool_stats = self.service.pool.get_stats()
            self.metrics['pool_active_connections'].add_point(
                pool_stats.get('active_connections', 0)
            )
            self.metrics['pool_utilization'].add_point(
                pool_stats.get('pool_utilization', 0) * 100
            )
            
            # 查询指标
            query_stats = self.query_monitor.get_query_statistics()
            self.metrics['query_count'].add_point(query_stats.get('total_queries', 0))
            self.metrics['query_errors'].add_point(query_stats.get('total_errors', 0))
            
            # 系统指标
            if PSUTIL_AVAILABLE:
                self.metrics['cpu_usage'].add_point(psutil.cpu_percent())
                self.metrics['memory_usage'].add_point(psutil.virtual_memory().percent)
                
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    async def _check_alerts(self):
        """检查告警条件"""
        try:
            # 检查连接池利用率
            pool_util = self.metrics['pool_utilization'].get_current_value()
            if pool_util and pool_util > 90:
                self.alert_manager.create_alert(
                    AlertLevel.WARNING,
                    "High Connection Pool Utilization",
                    f"Connection pool utilization is {pool_util:.1f}%",
                    "pool_utilization",
                    pool_util
                )
            
            # 检查查询错误率
            query_stats = self.query_monitor.get_query_statistics()
            error_rate = query_stats.get('error_rate', 0)
            if error_rate > 0.1:  # 10%错误率
                self.alert_manager.create_alert(
                    AlertLevel.ERROR,
                    "High Query Error Rate",
                    f"Query error rate is {error_rate:.1%}",
                    "query_error_rate",
                    error_rate
                )
            
            # 检查系统资源
            if PSUTIL_AVAILABLE:
                cpu_usage = self.metrics['cpu_usage'].get_current_value()
                memory_usage = self.metrics['memory_usage'].get_current_value()
                
                if cpu_usage and cpu_usage > 80:
                    self.alert_manager.create_alert(
                        AlertLevel.WARNING,
                        "High CPU Usage",
                        f"CPU usage is {cpu_usage:.1f}%",
                        "cpu_usage",
                        cpu_usage
                    )
                
                if memory_usage and memory_usage > 85:
                    self.alert_manager.create_alert(
                        AlertLevel.WARNING,
                        "High Memory Usage",
                        f"Memory usage is {memory_usage:.1f}%",
                        "memory_usage",
                        memory_usage
                    )
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
    
    def _default_alert_handler(self, alert: Alert):
        """默认告警处理器"""
        # 记录到日志
        level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }
        
        logger.log(
            level_map.get(alert.level, logging.INFO),
            f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}"
        )
    
    def record_query_execution(self, sql: str, duration: float, success: bool = True, 
                             error: Optional[str] = None):
        """记录查询执行"""
        self.query_monitor.record_query(sql, duration, success, error)
        
        # 更新指标
        self.metrics['query_duration'].add_point(duration)
        if not success:
            self.metrics['query_errors'].add_point(1)
    
    def get_query_timer(self, sql: str) -> Timer:
        """获取查询计时器"""
        return Timer(self.metrics['query_duration'], {'query_type': 'sql'})
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """获取监控报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'service_status': 'healthy' if self.health_checker.is_healthy else 'unhealthy',
            'metrics': {},
            'query_statistics': self.query_monitor.get_query_statistics(),
            'slow_queries': self.query_monitor.get_slow_queries(10),
            'alerts': self.alert_manager.get_alert_statistics(),
            'active_alerts': [
                {
                    'id': alert.id,
                    'level': alert.level.value,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp
                }
                for alert in self.alert_manager.get_active_alerts()
            ]
        }
        
        # 添加指标统计
        for name, metric in self.metrics.items():
            stats = metric.get_statistics()
            report['metrics'][name] = {
                'current_value': metric.get_current_value(),
                'statistics': stats,
                'type': metric.type.value
            }
        
        return report
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        return await self.health_checker.perform_health_check()


# 全局监控器实例
_monitor_instance: Optional[DuckDBMonitor] = None
_monitor_lock = threading.Lock()


def get_duckdb_monitor(service, update_interval: float = 10.0) -> DuckDBMonitor:
    """获取DuckDB监控器实例"""
    global _monitor_instance
    
    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = DuckDBMonitor(service, update_interval)
        return _monitor_instance