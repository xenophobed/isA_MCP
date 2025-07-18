#!/usr/bin/env python3
"""
Test file for BaseAdapter
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from .base_adapter import BaseAdapter
from ..models.interfaces import IAdapter


class MockAdapter(BaseAdapter):
    """Mock implementation of BaseAdapter for testing"""
    
    def __init__(self):
        super().__init__("test_adapter", "mock")
        
    async def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Mock config validation"""
        return config.get("valid", True)
    
    async def _initialize_adapter(self) -> None:
        """Mock adapter initialization"""
        if self.config.get("fail_init", False):
            raise Exception("Initialization failed")
    
    async def _perform_health_check(self) -> bool:
        """Mock health check"""
        return self.config.get("healthy", True)
    
    def _get_specific_capabilities(self) -> Dict[str, Any]:
        """Mock specific capabilities"""
        return {
            "mock_capability": True,
            "test_feature": "enabled"
        }


class TestBaseAdapter:
    """Test cases for BaseAdapter"""
    
    @pytest.fixture
    def adapter(self):
        """Create a mock adapter for testing"""
        return MockAdapter()
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, adapter):
        """Test successful adapter initialization"""
        config = {"valid": True, "test_param": "value"}
        
        result = await adapter.initialize(config)
        
        assert result is True
        assert adapter.is_initialized is True
        assert adapter.config == config
    
    @pytest.mark.asyncio
    async def test_initialization_invalid_config(self, adapter):
        """Test adapter initialization with invalid config"""
        config = {"valid": False}
        
        result = await adapter.initialize(config)
        
        assert result is False
        assert adapter.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialization_adapter_failure(self, adapter):
        """Test adapter initialization when adapter-specific init fails"""
        config = {"valid": True, "fail_init": True}
        
        result = await adapter.initialize(config)
        
        assert result is False
        assert adapter.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter):
        """Test health check when adapter is healthy"""
        await adapter.initialize({"healthy": True})
        
        result = await adapter.health_check()
        
        assert result is True
        assert adapter.health_status == "healthy"
        assert adapter.last_health_check is not None
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, adapter):
        """Test health check when adapter is unhealthy"""
        await adapter.initialize({"healthy": False})
        
        result = await adapter.health_check()
        
        assert result is False
        assert adapter.health_status == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, adapter):
        """Test health check when adapter is not initialized"""
        result = await adapter.health_check()
        
        assert result is False
        assert adapter.health_status == "not_initialized"
    
    def test_get_capabilities(self, adapter):
        """Test getting adapter capabilities"""
        capabilities = adapter.get_capabilities()
        
        assert capabilities["name"] == "test_adapter"
        assert capabilities["type"] == "mock"
        assert capabilities["initialized"] is False
        assert capabilities["health_status"] == "unknown"
        assert capabilities["mock_capability"] is True
        assert capabilities["test_feature"] == "enabled"
    
    def test_get_stats(self, adapter):
        """Test getting adapter statistics"""
        stats = adapter.get_stats()
        
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["last_operation_time"] is None
        assert stats["average_response_time"] == 0.0
    
    def test_update_stats_success(self, adapter):
        """Test updating statistics for successful operation"""
        adapter._update_stats(1.5, True)
        
        stats = adapter.get_stats()
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 1
        assert stats["failed_operations"] == 0
        assert stats["average_response_time"] == 1.5
    
    def test_update_stats_failure(self, adapter):
        """Test updating statistics for failed operation"""
        adapter._update_stats(2.0, False)
        
        stats = adapter.get_stats()
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 1
        assert stats["average_response_time"] == 0.0
    
    @pytest.mark.asyncio
    async def test_execute_with_stats_success(self, adapter):
        """Test executing operation with stats tracking - success"""
        
        async def mock_operation():
            return "success_result"
        
        result = await adapter._execute_with_stats("test_op", mock_operation)
        
        assert result == "success_result"
        stats = adapter.get_stats()
        assert stats["total_operations"] == 1
        assert stats["successful_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_stats_failure(self, adapter):
        """Test executing operation with stats tracking - failure"""
        
        async def mock_operation():
            raise Exception("Operation failed")
        
        with pytest.raises(Exception, match="Operation failed"):
            await adapter._execute_with_stats("test_op", mock_operation)
        
        stats = adapter.get_stats()
        assert stats["total_operations"] == 1
        assert stats["failed_operations"] == 1
    
    def test_ensure_initialized_success(self, adapter):
        """Test ensure initialized when adapter is initialized"""
        adapter.is_initialized = True
        
        # Should not raise exception
        adapter._ensure_initialized()
    
    def test_ensure_initialized_failure(self, adapter):
        """Test ensure initialized when adapter is not initialized"""
        adapter.is_initialized = False
        
        with pytest.raises(RuntimeError, match="test_adapter adapter is not initialized"):
            adapter._ensure_initialized()
    
    @pytest.mark.asyncio
    async def test_safe_close_connection_with_close_method(self, adapter):
        """Test safe close connection with close method"""
        mock_connection = Mock()
        mock_connection.close = AsyncMock()
        adapter.connection = mock_connection
        
        await adapter._safe_close_connection()
        
        mock_connection.close.assert_called_once()
        assert adapter.connection is None
    
    @pytest.mark.asyncio
    async def test_safe_close_connection_with_disconnect_method(self, adapter):
        """Test safe close connection with disconnect method"""
        mock_connection = Mock()
        mock_connection.disconnect = Mock()
        adapter.connection = mock_connection
        
        await adapter._safe_close_connection()
        
        mock_connection.disconnect.assert_called_once()
        assert adapter.connection is None
    
    @pytest.mark.asyncio
    async def test_safe_close_connection_no_connection(self, adapter):
        """Test safe close connection when no connection exists"""
        adapter.connection = None
        
        # Should not raise exception
        await adapter._safe_close_connection()
    
    @pytest.mark.asyncio
    async def test_safe_close_connection_exception(self, adapter):
        """Test safe close connection when close method raises exception"""
        mock_connection = Mock()
        mock_connection.close = Mock(side_effect=Exception("Close failed"))
        adapter.connection = mock_connection
        
        # Should not raise exception, but should log warning
        await adapter._safe_close_connection()
        
        assert adapter.connection is None


if __name__ == "__main__":
    pytest.main([__file__])