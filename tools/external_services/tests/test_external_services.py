#!/usr/bin/env python3
"""
Tests for External Services Integration

Basic tests to verify external service integration functionality.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tools.external_services.base_external_service import BaseExternalService, ExternalServiceConfig
from tools.external_services.service_registry import ExternalServiceRegistry

class MockExternalService(BaseExternalService):
    """Mock external service for testing"""
    
    async def connect(self) -> bool:
        self.is_connected = True
        return True
    
    async def disconnect(self) -> None:
        self.is_connected = False
    
    async def health_check(self) -> bool:
        return self.is_connected
    
    async def discover_capabilities(self) -> dict:
        return {
            "tools": ["mock_tool_1", "mock_tool_2"],
            "resources": ["mock_resource_1"],
            "prompts": ["mock_prompt_1"]
        }
    
    async def invoke_tool(self, tool_name: str, params: dict) -> dict:
        return {"success": True, "tool": tool_name, "params": params}
    
    async def _fetch_resource(self, resource, params: dict) -> dict:
        return {"resource_data": "mock_data"}

class TestExternalServiceConfig:
    """Test ExternalServiceConfig"""
    
    def test_config_creation(self):
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={"url": "http://test.com"},
            auth_config={"api_key": "test_key"}
        )
        
        assert config.name == "test_service"
        assert config.service_type == "custom"
        assert config.connection_params["url"] == "http://test.com"
        assert config.auth_config["api_key"] == "test_key"
        assert config.enabled is True
        assert config.timeout_seconds == 30

class TestBaseExternalService:
    """Test BaseExternalService abstract class"""
    
    def test_service_creation(self):
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom", 
            connection_params={}
        )
        
        service = MockExternalService(config)
        assert service.service_name == "test_service"
        assert service.is_connected is False
        assert service.is_healthy is False
    
    @pytest.mark.asyncio
    async def test_service_connection(self):
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={}
        )
        
        service = MockExternalService(config)
        
        # Test connection
        connected = await service.connect()
        assert connected is True
        assert service.is_connected is True
        assert service.is_healthy is True
        
        # Test health check
        healthy = await service.health_check()
        assert healthy is True
        
        # Test disconnect
        await service.disconnect()
        assert service.is_connected is False
    
    @pytest.mark.asyncio
    async def test_capability_discovery(self):
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={}
        )
        
        service = MockExternalService(config)
        await service.connect()
        
        capabilities = await service.discover_capabilities()
        assert "tools" in capabilities
        assert "resources" in capabilities
        assert "prompts" in capabilities
        assert "mock_tool_1" in capabilities["tools"]
    
    @pytest.mark.asyncio 
    async def test_tool_invocation(self):
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={}
        )
        
        service = MockExternalService(config)
        await service.connect()
        
        result = await service.invoke_tool("mock_tool_1", {"param1": "value1"})
        assert result["success"] is True
        assert result["tool"] == "mock_tool_1"
        assert result["params"]["param1"] == "value1"

class TestExternalServiceRegistry:
    """Test ExternalServiceRegistry"""
    
    @pytest.mark.asyncio
    async def test_registry_creation(self):
        registry = ExternalServiceRegistry()
        assert registry.services == {}
        assert registry.service_configs == {}
    
    @pytest.mark.asyncio
    async def test_service_registration(self):
        registry = ExternalServiceRegistry()
        
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={}
        )
        
        service = MockExternalService(config)
        
        # Register service
        success = await registry.register_service(service)
        assert success is True
        assert "test_service" in registry.services
        
        # Get service
        retrieved_service = await registry.get_service("test_service")
        assert retrieved_service == service
    
    @pytest.mark.asyncio
    async def test_service_type_registration(self):
        registry = ExternalServiceRegistry()
        
        # Register service type
        registry.register_service_type("mock", MockExternalService)
        assert "mock" in registry._service_type_registry
        assert registry._service_type_registry["mock"] == MockExternalService
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        registry = ExternalServiceRegistry()
        
        # Create and register a service
        config = ExternalServiceConfig(
            name="test_service",
            service_type="custom",
            connection_params={}
        )
        
        service = MockExternalService(config)
        await registry.register_service(service)
        
        # Perform health check
        health_results = await registry.health_check_all()
        assert "test_service" in health_results
        assert health_results["test_service"] is True

class TestExternalServicesIntegration:
    """Integration tests for external services"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_service_flow(self):
        """Test complete service lifecycle"""
        registry = ExternalServiceRegistry()
        registry.register_service_type("mock", MockExternalService)
        
        # Create config
        config = ExternalServiceConfig(
            name="integration_test_service",
            service_type="mock",
            connection_params={"test_param": "test_value"},
            enabled=True
        )
        
        # Create service instance
        service = await registry._create_service_instance(config)
        assert service is not None
        assert isinstance(service, MockExternalService)
        
        # Register service
        success = await registry.register_service(service)
        assert success is True
        
        # Verify service capabilities
        capabilities = await service.discover_capabilities()
        assert len(capabilities["tools"]) > 0
        
        # Test tool invocation
        result = await registry.invoke_service_tool(
            "integration_test_service", 
            "mock_tool_1", 
            {"test": "data"}
        )
        assert result["success"] is True
        
        # Health check
        health_results = await registry.health_check_all()
        assert health_results["integration_test_service"] is True
        
        # Cleanup
        await registry.disconnect_all()

# Test configuration loading (requires YAML)
@pytest.mark.skipif(not Path("config/external_services").exists(), 
                   reason="External services config directory not found")
class TestConfigurationLoading:
    """Test configuration loading functionality"""
    
    @pytest.mark.asyncio
    async def test_config_loading(self):
        registry = ExternalServiceRegistry()
        
        # Create a temporary config file
        config_dir = Path("config/external_services")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        test_config_file = config_dir / "test_config.yaml"
        test_config_content = """
external_services:
  test_yaml_service:
    type: "custom"
    enabled: true
    connection:
      url: "http://test.example.com"
    auth:
      method: "api_key"
      api_key: "${TEST_API_KEY}"
"""
        
        with open(test_config_file, 'w') as f:
            f.write(test_config_content)
        
        try:
            # Load configs
            configs = await registry.load_service_configs()
            
            if "test_yaml_service" in configs:
                config = configs["test_yaml_service"]
                assert config.name == "test_yaml_service"
                assert config.service_type == "custom"
                assert config.enabled is True
                assert config.connection_params["url"] == "http://test.example.com"
        finally:
            # Cleanup
            if test_config_file.exists():
                test_config_file.unlink()

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])