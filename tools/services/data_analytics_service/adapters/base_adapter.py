#!/usr/bin/env python3
"""
Base Adapter for Data Analytics Service

Provides common functionality for all adapters.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from ...models.interfaces import IAdapter
from ...models.data_models import DataSource, DataTarget

logger = logging.getLogger(__name__)

class BaseAdapter(IAdapter, ABC):
    """
    Base adapter class providing common functionality
    
    All adapters should inherit from this class and implement
    the abstract methods for their specific data source/target type.
    """
    
    def __init__(self, name: str, adapter_type: str):
        self.name = name
        self.adapter_type = adapter_type
        self.config: Dict[str, Any] = {}
        self.is_initialized = False
        self.last_health_check: Optional[datetime] = None
        self.health_status = "unknown"
        self.connection = None
        
        # Statistics tracking
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'last_operation_time': None,
            'average_response_time': 0.0
        }
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize adapter with configuration
        
        Args:
            config: Adapter configuration
            
        Returns:
            True if initialization successful
        """
        try:
            self.config = config
            self.logger.info(f"Initializing {self.name} adapter")
            
            # Validate configuration
            if not await self._validate_config(config):
                raise ValueError(f"Invalid configuration for {self.name} adapter")
            
            # Perform adapter-specific initialization
            await self._initialize_adapter()
            
            self.is_initialized = True
            self.logger.info(f"{self.name} adapter initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name} adapter: {e}")
            self.is_initialized = False
            return False
    
    async def health_check(self) -> bool:
        """
        Check if adapter is healthy
        
        Returns:
            True if adapter is healthy
        """
        try:
            if not self.is_initialized:
                self.health_status = "not_initialized"
                return False
            
            # Perform adapter-specific health check
            is_healthy = await self._perform_health_check()
            
            self.health_status = "healthy" if is_healthy else "unhealthy"
            self.last_health_check = datetime.now()
            
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"Health check failed for {self.name} adapter: {e}")
            self.health_status = "error"
            self.last_health_check = datetime.now()
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get adapter capabilities
        
        Returns:
            Dictionary containing adapter capabilities
        """
        base_capabilities = {
            'name': self.name,
            'type': self.adapter_type,
            'initialized': self.is_initialized,
            'health_status': self.health_status,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'statistics': self.stats.copy()
        }
        
        # Add adapter-specific capabilities
        specific_capabilities = self._get_specific_capabilities()
        base_capabilities.update(specific_capabilities)
        
        return base_capabilities
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return self.stats.copy()
    
    def _update_stats(self, operation_time: float, success: bool):
        """Update adapter statistics"""
        self.stats['total_operations'] += 1
        self.stats['last_operation_time'] = datetime.now().isoformat()
        
        if success:
            self.stats['successful_operations'] += 1
        else:
            self.stats['failed_operations'] += 1
        
        # Update average response time
        if self.stats['successful_operations'] > 0:
            current_avg = self.stats['average_response_time']
            total_successful = self.stats['successful_operations']
            self.stats['average_response_time'] = (
                (current_avg * (total_successful - 1) + operation_time) / total_successful
            )
    
    async def _execute_with_stats(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute operation with statistics tracking"""
        import time
        start_time = time.time()
        
        try:
            self.logger.debug(f"Executing {operation_name} operation")
            result = await operation_func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            self._update_stats(execution_time, True)
            
            self.logger.debug(f"{operation_name} completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(execution_time, False)
            
            self.logger.error(f"{operation_name} failed after {execution_time:.2f}s: {e}")
            raise
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    async def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate adapter configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        pass
    
    @abstractmethod
    async def _initialize_adapter(self) -> None:
        """
        Perform adapter-specific initialization
        
        This method should establish connections, validate credentials,
        and perform any other setup required for the adapter.
        """
        pass
    
    @abstractmethod
    async def _perform_health_check(self) -> bool:
        """
        Perform adapter-specific health check
        
        Returns:
            True if adapter is healthy
        """
        pass
    
    @abstractmethod
    def _get_specific_capabilities(self) -> Dict[str, Any]:
        """
        Get adapter-specific capabilities
        
        Returns:
            Dictionary containing adapter-specific capabilities
        """
        pass
    
    # Utility methods
    
    def _ensure_initialized(self):
        """Ensure adapter is initialized"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name} adapter is not initialized")
    
    async def _safe_close_connection(self):
        """Safely close connection if it exists"""
        if self.connection:
            try:
                if hasattr(self.connection, 'close'):
                    close_method = getattr(self.connection, 'close')
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                elif hasattr(self.connection, 'disconnect'):
                    disconnect_method = getattr(self.connection, 'disconnect')
                    if asyncio.iscoroutinefunction(disconnect_method):
                        await disconnect_method()
                    else:
                        disconnect_method()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
            finally:
                self.connection = None 