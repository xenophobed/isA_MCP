from registry.base import BaseRegistry, ComponentType
from typing import List, Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ResourceRegistry(BaseRegistry):
    def __init__(self, auto_discover: bool = True):
        super().__init__()
        self._resource_handlers: Dict[str, Callable] = {}
        
        if auto_discover:
            self._auto_discover()
    
    def _get_component_type(self) -> ComponentType:
        return ComponentType.RESOURCE
    
    def register_resource(self, uri: str, name: str = None, description: str = "", 
                         mime_type: str = "text/plain"):
        """Decorator to register a resource handler"""
        def decorator(func: Callable):
            resource_name = name or func.__name__
            
            metadata = {
                'uri': uri,
                'name': resource_name,
                'description': description or func.__doc__ or f"Resource: {resource_name}",
                'mimeType': mime_type
            }
            
            self.register(resource_name, func, metadata=metadata)
            self._resource_handlers[uri] = func
            
            return func
        return decorator
    
    def get_resource_handler(self, uri: str) -> Optional[Callable]:
        """Get resource handler by URI"""
        return self._resource_handlers.get(uri)
    
    def get_mcp_resource_definitions(self) -> List[Dict[str, Any]]:
        """Get resource definitions in MCP format"""
        resources = []
        for info in self.list_all():
            resources.append({
                'uri': info.metadata.get('uri', ''),
                'name': info.metadata.get('name', info.name),
                'description': info.metadata.get('description', ''),
                'mimeType': info.metadata.get('mimeType', 'text/plain')
            })
        return resources
    
    def _extract_dependencies(self, component: Any) -> List[str]:
        return []  # Resources typically don't have dependencies
    
    def _auto_discover(self):
        """Auto-discover resources"""
        discovery = ComponentDiscovery()
        discovered = discovery.discover_components(ComponentType.RESOURCE)
        
        for resource_name, resource_component in discovered:
            if resource_component:
                self.register(
                    resource_name,
                    resource_component,
                    auto_discovered=True
                )