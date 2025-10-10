#!/usr/bin/env python3
"""
Extended Auto Discovery System with External Services Support

Extends the existing AutoDiscoverySystem to include external service integration.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from .auto_discovery import AutoDiscoverySystem
from tools.external_services import ExternalServiceRegistry
from tools.external_services.mindsdb_service import MindsDBService
# Composio service moved to internal services - no longer external

logger = logging.getLogger(__name__)

class ExtendedAutoDiscoverySystem(AutoDiscoverySystem):
    """
    Extended discovery system that includes external service integration
    while maintaining full backward compatibility with existing functionality.
    """
    
    def __init__(self, base_dir: str = "."):
        # Initialize parent class
        super().__init__(base_dir)
        
        # Initialize external service registry
        self.external_registry = ExternalServiceRegistry(
            config_dir=self.base_dir / "config" / "external_services"
        )
        
        # Register known service types
        self._register_service_types()
        
        # Track external service registration status
        self.external_services_enabled = self._check_external_services_enabled()
        self.external_service_status = {}
    
    def _register_service_types(self):
        """Register known external service types"""
        self.external_registry.register_service_type("mindsdb", MindsDBService)
        # Note: Composio service moved to internal services (tools/services/composio_service)
        logger.info("Registered external service types: mindsdb")
    
    def _check_external_services_enabled(self) -> bool:
        """Check if external services are globally enabled"""
        try:
            config_file = self.base_dir / "config" / "external_services" / "external_services.yaml"
            if config_file.exists():
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('global_settings', {}).get('enabled', True)
        except Exception as e:
            logger.warning(f"Could not check external services config: {e}")
        
        # Default to enabled if config not found or error occurred
        return True
    
    async def auto_register_with_mcp(self, mcp: FastMCP):
        """
        Extended auto-registration that includes both local and external capabilities.
        Maintains full backward compatibility with existing functionality.
        """
        logger.info("🚀 Starting extended auto-discovery with external services support...")

        # 1. Register all local capabilities (existing functionality)
        logger.info("📦 Registering local capabilities...")
        await super().auto_register_with_mcp(mcp)
        logger.info("✅ Local capabilities registered")

        # 2. Register external services if enabled
        # Option: Load external services in background (LAZY_LOAD_EXTERNAL_SERVICES=true)
        lazy_load_external = os.getenv('LAZY_LOAD_EXTERNAL_SERVICES', 'false').lower() == 'true'

        if self.external_services_enabled:
            if lazy_load_external:
                logger.info("🌐 External services will load in background (LAZY_LOAD_EXTERNAL_SERVICES=true)...")
                # Start background task - doesn't block startup
                import asyncio
                asyncio.create_task(self._register_external_services_background(mcp))
            else:
                # Synchronous load (default, slower)
                logger.info("🌐 Registering external services...")
                await self._register_external_services(mcp)
        else:
            logger.info("⏭️  External services disabled, skipping external registration")

        logger.info("🎉 Extended auto-discovery completed!")

    async def _register_external_services_background(self, mcp: FastMCP):
        """Register external services in background without blocking startup"""
        try:
            import asyncio
            await asyncio.sleep(8)  # Wait for server to be fully ready
            logger.info("🌐 Starting background external services registration...")
            print("🌐 Starting background external services registration...")
            await self._register_external_services(mcp)
            logger.info("✅ External services ready (background registration complete)")
            print("✅ External services ready (background registration complete)")
        except Exception as e:
            error_msg = f"❌ Background external services registration failed: {e}"
            logger.error(error_msg)
            print(error_msg)
            import traceback
            logger.error(traceback.format_exc())
    
    async def _register_external_services(self, mcp: FastMCP):
        """Register external services with MCP server"""
        try:
            # Set MCP server in registry for capability registration
            self.external_registry.set_mcp_server(mcp)
            
            # Initialize all external services
            logger.info("🔧 Initializing external services...")
            initialization_results = await self.external_registry.initialize_services()
            
            # Log results
            successful_services = []
            failed_services = []
            
            for service_name, success in initialization_results.items():
                if success:
                    successful_services.append(service_name)
                    logger.info(f"  ✅ {service_name} - Successfully initialized")
                else:
                    failed_services.append(service_name)
                    logger.warning(f"  ❌ {service_name} - Failed to initialize")
            
            # Store status for monitoring
            self.external_service_status = initialization_results
            
            # Summary
            if successful_services:
                logger.info(f"🎯 Successfully initialized {len(successful_services)} external services: {', '.join(successful_services)}")
            
            if failed_services:
                logger.warning(f"⚠️  Failed to initialize {len(failed_services)} external services: {', '.join(failed_services)}")
            
            # Add external service management tools to MCP
            await self._register_external_management_tools(mcp)
            
        except Exception as e:
            logger.error(f"Error during external service registration: {e}")
            # Don't fail the entire registration process if external services fail
    
    async def _register_external_management_tools(self, mcp: FastMCP):
        """Register management tools for external services"""
        
        @mcp.tool("external_service_status")
        async def get_external_service_status() -> Dict[str, Any]:
            """Get status of all external services"""
            return {
                "enabled": self.external_services_enabled,
                "services": self.external_registry.get_service_status(),
                "initialization_status": self.external_service_status
            }
        
        @mcp.tool("external_service_health_check")
        async def external_service_health_check(service_name: Optional[str] = None) -> Dict[str, Any]:
            """Perform health check on external services"""
            if service_name:
                service = await self.external_registry.get_service(service_name)
                if service:
                    is_healthy = await service.health_check()
                    return {
                        "service": service_name,
                        "healthy": is_healthy,
                        "timestamp": str(datetime.utcnow())
                    }
                else:
                    return {
                        "error": f"Service '{service_name}' not found",
                        "timestamp": str(datetime.utcnow())
                    }
            else:
                health_results = await self.external_registry.health_check_all()
                return {
                    "all_services": health_results,
                    "timestamp": str(datetime.utcnow())
                }
        
        @mcp.tool("external_service_reconnect")
        async def reconnect_external_service(service_name: str) -> Dict[str, Any]:
            """Attempt to reconnect an external service"""
            success = await self.external_registry.reconnect_service(service_name)
            return {
                "service": service_name,
                "reconnected": success,
                "timestamp": str(datetime.utcnow())
            }
        
        @mcp.tool("list_external_service_tools")
        async def list_external_service_tools() -> Dict[str, List[str]]:
            """List all available tools from external services"""
            return self.external_registry.list_available_tools()
        
        logger.info("🛠️  Registered external service management tools")
    
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get comprehensive discovery summary including external services"""
        base_summary = {
            "local_discovery": {
                "tools": len(self.discovered_tools),
                "prompts": len(self.discovered_prompts),
                "resources": len(self.discovered_resources)
            }
        }
        
        # Add external service summary if enabled
        if self.external_services_enabled:
            external_summary = {
                "external_services": {
                    "enabled": True,
                    "total_services": len(self.external_service_status),
                    "successful_services": sum(1 for success in self.external_service_status.values() if success),
                    "failed_services": sum(1 for success in self.external_service_status.values() if not success),
                    "services": self.external_service_status,
                    "available_tools": self.external_registry.list_available_tools() if hasattr(self.external_registry, 'list_available_tools') else {}
                }
            }
        else:
            external_summary = {
                "external_services": {
                    "enabled": False,
                    "reason": "Disabled in configuration"
                }
            }
        
        return {**base_summary, **external_summary}
    
    async def cleanup(self):
        """Cleanup resources including external services"""
        if hasattr(self.external_registry, 'disconnect_all'):
            await self.external_registry.disconnect_all()
            logger.info("🧹 External services cleaned up")