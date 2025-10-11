"""
Consul Service Registry Module for MCP

Provides service registration and health check functionality for MCP service
Based on the optimized implementation from User project
"""

import consul
import logging
import asyncio
import socket
import json
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ConsulRegistry:
    """Handles service registration with Consul for MCP"""
    
    def __init__(
        self,
        service_name: str = "mcp_service",
        service_port: int = 8081,
        consul_host: Optional[str] = None,
        consul_port: Optional[int] = None,
        service_host: Optional[str] = None,
        tags: Optional[List[str]] = None,
        health_check_type: str = "ttl"
    ):
        """
        Initialize Consul registry for MCP
        
        Args:
            service_name: Name of the service to register
            service_port: Port the service is running on
            consul_host: Consul server host (defaults to env CONSUL_HOST or localhost)
            consul_port: Consul server port (defaults to env CONSUL_PORT or 8500)
            service_host: Service host (defaults to env SERVICE_HOST or hostname)
            tags: Service tags for discovery
            health_check_type: Type of health check (ttl or http)
        """
        # Read from environment variables with proper precedence
        consul_host = consul_host or os.getenv('CONSUL_HOST', 'localhost')
        consul_port = consul_port or int(os.getenv('CONSUL_PORT', '8500'))
        service_host = service_host or os.getenv('SERVICE_HOST', socket.gethostname())
        service_port = service_port or int(os.getenv('SERVICE_PORT', '8081'))
        
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.service_name = service_name
        self.service_port = service_port
        # Handle 0.0.0.0 which is invalid for Consul service registration
        if service_host and service_host != "0.0.0.0":
            self.service_host = service_host
        else:
            self.service_host = socket.gethostname()
        self.service_id = f"{service_name}-{self.service_host}-{service_port}"
        self.tags = tags or ["platform", "ai", "api"]
        self.check_interval = "15s"
        self.deregister_after = "90s"
        self._health_check_task = None
        self.health_check_type = health_check_type
        self.ttl_interval = 30  # 标准30秒TTL间隔
        
    def register(self) -> bool:
        """Register MCP service with Consul"""
        try:
            # Choose health check type
            if self.health_check_type == "ttl":
                check = consul.Check.ttl(f"{self.ttl_interval}s")
            else:
                check = consul.Check.http(
                    f"http://{self.service_host}:{self.service_port}/health",
                    interval=self.check_interval,
                    timeout="5s",
                    deregister=self.deregister_after
                )
            
            # Register service with selected health check
            self.consul.agent.service.register(
                name=self.service_name,
                service_id=self.service_id,
                address=self.service_host,
                port=self.service_port,
                tags=self.tags,
                check=check
            )
            
            # If TTL, immediately pass the health check
            if self.health_check_type == "ttl":
                self.consul.agent.check.ttl_pass(f"service:{self.service_id}")
            
            logger.info(
                f"✅ MCP service registered with Consul: {self.service_name} "
                f"({self.service_id}) at {self.service_host}:{self.service_port} "
                f"with {self.health_check_type} health check, tags: {self.tags}"
            )
            self._log_service_metrics("register", True)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register MCP service with Consul: {e}")
            self._log_service_metrics("register", False)
            return False
    
    def deregister(self) -> bool:
        """Deregister MCP service from Consul"""
        try:
            self.consul.agent.service.deregister(self.service_id)
            logger.info(f"✅ MCP service deregistered from Consul: {self.service_id}")
            self._log_service_metrics("deregister", True)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to deregister MCP service from Consul: {e}")
            self._log_service_metrics("deregister", False)
            return False
    
    async def maintain_registration(self):
        """Maintain service registration with enhanced error handling"""
        retry_count = 0
        max_retries = 3
        
        while True:
            try:
                # Check if service is still registered
                services = self.consul.agent.services()
                if self.service_id not in services:
                    logger.warning(f"MCP service {self.service_id} not found in Consul, re-registering...")
                    if self.register():
                        retry_count = 0
                        logger.info(f"✅ Successfully re-registered MCP {self.service_id}")
                    else:
                        retry_count += 1
                        logger.error(f"❌ Failed to re-register MCP {self.service_id}, retry {retry_count}/{max_retries}")
                
                # If using TTL checks, update the health status
                if self.health_check_type == "ttl":
                    try:
                        self.consul.agent.check.ttl_pass(
                            f"service:{self.service_id}",
                            f"MCP service is healthy - {self.service_name}@{self.service_host}:{self.service_port}"
                        )
                        logger.debug(f"✅ TTL health check passed for MCP {self.service_id}")
                        retry_count = 0  # TTL成功则重置重试计数
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Failed to update MCP TTL health check: {e}, retry {retry_count}/{max_retries}")
                        
                        # 如果TTL连续失败，尝试重新注册
                        if retry_count >= max_retries:
                            logger.error(f"MCP TTL failed {max_retries} times, attempting re-registration")
                            self.register()
                            retry_count = 0
                
                # 动态调整睡眠时间，错误时更频繁检查
                if retry_count > 0:
                    sleep_time = 5  # 有错误时5秒检查一次
                else:
                    sleep_time = self.ttl_interval / 2 if self.health_check_type == "ttl" else 30
                    
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Error maintaining MCP registration: {e}, retry {retry_count}/{max_retries}")
                # 指数退避
                sleep_time = min(10 * (2 ** (retry_count - 1)), 60)
                await asyncio.sleep(sleep_time)
    
    def start_maintenance(self):
        """Start the background maintenance task"""
        if not self._health_check_task:
            loop = asyncio.get_event_loop()
            self._health_check_task = loop.create_task(self.maintain_registration())
    
    def stop_maintenance(self):
        """Stop the background maintenance task"""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    def _log_service_metrics(self, operation: str, success: bool, service_name: str = None):
        """记录服务操作指标"""
        service = service_name or self.service_name
        status = "SUCCESS" if success else "FAILED"
        
        # 使用项目统一的logger记录指标
        logger.info(
            f"🔍 CONSUL_METRICS | operation={operation} | service={service} | "
            f"status={status} | service_id={self.service_id}"
        )

    # Service Discovery Methods
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover healthy instances of a service"""
        try:
            # Get health checks for the service
            index, services = self.consul.health.service(service_name, passing=True)
            
            instances = []
            for service in services:
                instance = {
                    'id': service['Service']['ID'],
                    'address': service['Service']['Address'],
                    'port': service['Service']['Port'],
                    'tags': service['Service'].get('Tags', []),
                    'meta': service['Service'].get('Meta', {})
                }
                instances.append(instance)
            
            return instances
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return []
    
    def get_service_endpoint(self, service_name: str, strategy: str = 'random') -> Optional[str]:
        """Get a single service endpoint using load balancing strategy"""
        instances = self.discover_service(service_name)
        if not instances:
            return None

        # 只有一个实例时直接返回
        if len(instances) == 1:
            instance = instances[0]
            return f"http://{instance['address']}:{instance['port']}"

        # 负载均衡策略
        if strategy == 'random':
            import random
            instance = random.choice(instances)
        else:
            # 默认随机选择
            import random
            instance = random.choice(instances)

        return f"http://{instance['address']}:{instance['port']}"

    def get_service_address(self, service_name: str, fallback_url: Optional[str] = None, max_retries: int = 3) -> str:
        """
        Get service address from Consul discovery with automatic fallback and retry
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                endpoint = self.get_service_endpoint(service_name)
                if endpoint:
                    logger.debug(f"Discovered {service_name} at {endpoint} (attempt {attempt + 1})")
                    return endpoint
                    
                # 如果没找到服务但没有异常，记录并继续
                last_error = f"Service {service_name} not found in Consul registry"
                
            except Exception as e:
                last_error = e
                logger.warning(f"Consul discovery attempt {attempt + 1} failed for {service_name}: {e}")
                
                # 短暂等待后重试（除了最后一次）
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))  # 递增延迟

        # 所有重试都失败，使用fallback
        if fallback_url:
            logger.warning(f"All {max_retries} discovery attempts failed for {service_name}: {last_error}, using fallback: {fallback_url}")
            return fallback_url

        raise ValueError(f"Service {service_name} not found after {max_retries} attempts and no fallback provided. Last error: {last_error}")


# Global instance for singleton pattern
_consul_registry_instance = None


def get_consul_registry() -> Optional[ConsulRegistry]:
    """Get global Consul registry instance (singleton)"""
    global _consul_registry_instance
    if _consul_registry_instance is None:
        try:
            _consul_registry_instance = ConsulRegistry()
        except Exception as e:
            logger.error(f"Failed to create Consul registry: {e}")
            return None
    return _consul_registry_instance


def initialize_consul_registry(service_name: str = "mcp_service", service_port: int = 8081) -> Optional[ConsulRegistry]:
    """Initialize and register MCP service with Consul"""
    global _consul_registry_instance
    
    try:
        _consul_registry_instance = ConsulRegistry(
            service_name=service_name,
            service_port=service_port
            # consul_host and consul_port will be read from environment variables
        )
        
        if _consul_registry_instance.register():
            _consul_registry_instance.start_maintenance()
            logger.info("✅ MCP Consul registry initialized and registered successfully")
            return _consul_registry_instance
        else:
            logger.warning("⚠️ Failed to register MCP with Consul, continuing without service discovery")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ MCP Consul registration failed: {e}, continuing without service discovery")
        return None


def cleanup_consul_registry():
    """Cleanup Consul registry on shutdown"""
    global _consul_registry_instance
    if _consul_registry_instance:
        try:
            _consul_registry_instance.stop_maintenance()
            _consul_registry_instance.deregister()
            logger.info("✅ MCP Consul registry cleaned up successfully")
        except Exception as e:
            logger.error(f"❌ Error during MCP Consul cleanup: {e}")
        finally:
            _consul_registry_instance = None