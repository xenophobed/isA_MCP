from .base import BaseRegistry, ComponentInfo, ComponentType
from .discovery import ComponentDiscovery
from typing import Dict, Any, List, Callable, Optional
import inspect
from pathlib import Path

class ToolRegistry(BaseRegistry):
    def __init__(self, auto_discover: bool = True, discovery_paths: List[Path] = None):
        super().__init__()
        self._tool_functions: Dict[str, Callable] = {}
        self._security_policies: Dict[str, str] = {}
        
        if auto_discover:
            self._auto_discover(discovery_paths or [Path.cwd() / "tools"])
    
    def _get_component_type(self) -> ComponentType:
        return ComponentType.TOOL
    
    def register_tool(self, name: str = None, security_level: str = "LOW", 
                     metadata: Dict[str, Any] = None):
        """Decorator to register a tool function"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            
            # Extract metadata from function
            sig = inspect.signature(func)
            extracted_metadata = {
                'description': func.__doc__ or f"Tool: {tool_name}",
                'parameters': self._extract_parameters(sig),
                'return_type': sig.return_annotation if sig.return_annotation != sig.empty else 'str'
            }
            
            if metadata:
                extracted_metadata.update(metadata)
            
            # Register the tool
            self.register(
                tool_name, 
                func, 
                metadata=extracted_metadata,
                security_level=security_level
            )
            
            self._tool_functions[tool_name] = func
            self._security_policies[tool_name] = security_level
            
            return func
        return decorator
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """Get the tool function"""
        return self._tool_functions.get(name)
    
    def get_security_level(self, tool_name: str) -> str:
        """Get security level for a tool"""
        return self._security_policies.get(tool_name, "LOW")
    
    def get_mcp_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions in MCP format"""
        tools = []
        for info in self.list_all():
            tools.append({
                'name': info.name,
                'description': info.metadata.get('description', ''),
                'inputSchema': {
                    'type': 'object',
                    'properties': info.metadata.get('parameters', {}),
                    'required': info.metadata.get('required_params', [])
                }
            })
        return tools
    
    def _extract_dependencies(self, component: Any) -> List[str]:
        """Extract dependencies from tool function"""
        if not callable(component):
            return []
        
        signature = inspect.signature(component)
        dependencies = []
        
        for param_name, param in signature.parameters.items():
            # Skip basic types and self/cls
            if param_name in ['self', 'cls']:
                continue
            
            if param.annotation != param.empty:
                annotation_str = str(param.annotation)
                # Extract custom class dependencies
                if not annotation_str.startswith('<class \'builtins.'):
                    dependencies.append(param_name)
        
        return dependencies
    
    def _extract_parameters(self, signature: inspect.Signature) -> Dict[str, Any]:
        """Extract parameter schema from function signature"""
        parameters = {}
        
        for param_name, param in signature.parameters.items():
            if param_name in ['self', 'cls']:
                continue
            
            param_schema = {'type': 'string'}  # default
            
            # Handle type annotations
            if param.annotation != param.empty:
                annotation = param.annotation
                if annotation == str:
                    param_schema['type'] = 'string'
                elif annotation == int:
                    param_schema['type'] = 'integer'
                elif annotation == float:
                    param_schema['type'] = 'number'
                elif annotation == bool:
                    param_schema['type'] = 'boolean'
                elif annotation == dict:
                    param_schema['type'] = 'object'
                elif annotation == list:
                    param_schema['type'] = 'array'
            
            # Handle default values
            if param.default != param.empty:
                param_schema['default'] = param.default
            
            parameters[param_name] = param_schema
        
        return parameters
    
    def _auto_discover(self, discovery_paths: List[Path]):
        """Auto-discover tools in specified paths"""
        for path in discovery_paths:
            if path.exists():
                discovery = ComponentDiscovery(path.parent)
                discovered = discovery.discover_components(ComponentType.TOOL)
                
                for tool_name, tool_component in discovered:
                    if tool_component and callable(tool_component):
                        self.register(
                            tool_name,
                            tool_component,
                            auto_discovered=True,
                            security_level="MEDIUM"  # Default for auto-discovered
                        )
