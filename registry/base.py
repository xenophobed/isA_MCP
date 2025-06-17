from abc import ABC, abstractmethod
from typing import Dict, List, Any, Type, Optional, Callable
from dataclasses import dataclass, field
import inspect
import importlib
import pkgutil
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ComponentType(Enum):
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"

@dataclass
class ComponentInfo:
    name: str
    component: Any
    component_type: ComponentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    security_level: str = "LOW"
    enabled: bool = True
    auto_discovered: bool = False

class BaseRegistry(ABC):
    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._initialized = False
        self._dependency_graph: Dict[str, List[str]] = {}
    
    def register(self, name: str, component: Any, **kwargs):
        """Register a component"""
        component_info = ComponentInfo(
            name=name,
            component=component,
            component_type=self._get_component_type(),
            metadata=kwargs.get('metadata', {}),
            dependencies=self._extract_dependencies(component),
            security_level=kwargs.get('security_level', 'LOW'),
            enabled=kwargs.get('enabled', True),
            auto_discovered=kwargs.get('auto_discovered', False)
        )
        
        self._components[name] = component_info
        self._update_dependency_graph(name, component_info.dependencies)
        logger.info(f"Registered {self._get_component_type().value}: {name}")
    
    def get(self, name: str) -> Optional[ComponentInfo]:
        """Get a registered component"""
        return self._components.get(name)
    
    def get_component(self, name: str) -> Optional[Any]:
        """Get the actual component object"""
        info = self.get(name)
        return info.component if info else None
    
    def list_all(self) -> List[ComponentInfo]:
        """List all registered components"""
        return [info for info in self._components.values() if info.enabled]
    
    def list_by_security_level(self, security_level: str) -> List[ComponentInfo]:
        """List components by security level"""
        return [info for info in self._components.values() 
                if info.security_level == security_level and info.enabled]
    
    def disable(self, name: str):
        """Disable a component"""
        if name in self._components:
            self._components[name].enabled = False
    
    def enable(self, name: str):
        """Enable a component"""
        if name in self._components:
            self._components[name].enabled = True
    
    @abstractmethod
    def _get_component_type(self) -> ComponentType:
        """Get the component type for this registry"""
        pass
    
    @abstractmethod
    def _extract_dependencies(self, component: Any) -> List[str]:
        """Extract dependencies from component"""
        pass
    
    def _update_dependency_graph(self, name: str, dependencies: List[str]):
        """Update the dependency graph"""
        self._dependency_graph[name] = dependencies
    
    def get_dependency_order(self) -> List[str]:
        """Get components in dependency order (topological sort)"""
        # Simple topological sort implementation
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node not in visited:
                temp_visited.add(node)
                for dep in self._dependency_graph.get(node, []):
                    if dep in self._components:  # Only visit if dependency is registered
                        visit(dep)
                temp_visited.remove(node)
                visited.add(node)
                result.append(node)
        
        for component_name in self._components.keys():
            if component_name not in visited:
                visit(component_name)
        
        return result