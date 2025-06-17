from registry.tool import ToolRegistry
from registry.resource import ResourceRegistry
from registry.prompt import PromptRegistry

import logging

logger = logging.getLogger(__name__)


class RegistryManager:
    """Central manager for all registries"""
    
    def __init__(self, auto_discover: bool = True):
        self.tool_registry = ToolRegistry(auto_discover=auto_discover)
        self.resource_registry = ResourceRegistry(auto_discover=auto_discover)
        self.prompt_registry = PromptRegistry(auto_discover=auto_discover)
        
        self._initialized = False
    
    def initialize(self):
        """Initialize all registries"""
        if self._initialized:
            return
        
        logger.info("Initializing registry manager...")
        
        # Initialize in dependency order
        registries = [
            self.resource_registry,
            self.prompt_registry,
            self.tool_registry
        ]
        
        for registry in registries:
            component_count = len(registry.list_all())
            logger.info(f"Initialized {registry._get_component_type().value} registry with {component_count} components")
        
        self._initialized = True
        logger.info("Registry manager initialization complete")
    
    def get_all_mcp_definitions(self) -> Dict[str, List[Dict]]:
        """Get all component definitions for MCP"""
        return {
            'tools': self.tool_registry.get_mcp_tool_definitions(),
            'resources': self.resource_registry.get_mcp_resource_definitions(),
            'prompts': self.prompt_registry.get_mcp_prompt_definitions()
        }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about all registries"""
        return {
            'tools': {
                'total': len(self.tool_registry._components),
                'enabled': len(self.tool_registry.list_all()),
                'by_security_level': {
                    'LOW': len(self.tool_registry.list_by_security_level('LOW')),
                    'MEDIUM': len(self.tool_registry.list_by_security_level('MEDIUM')),
                    'HIGH': len(self.tool_registry.list_by_security_level('HIGH')),
                    'CRITICAL': len(self.tool_registry.list_by_security_level('CRITICAL'))
                }
            },
            'resources': {
                'total': len(self.resource_registry._components),
                'enabled': len(self.resource_registry.list_all())
            },
            'prompts': {
                'total': len(self.prompt_registry._components),
                'enabled': len(self.prompt_registry.list_all())
            }
        }