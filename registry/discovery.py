import ast
import os
from typing import Dict, List, Tuple, Any
from pathlib import Path
from registry.base import ComponentType
import logging
import importlib

logger = logging.getLogger(__name__)


class ComponentDiscovery:
    """Auto-discovery system for MCP components"""
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path.cwd()
        self._discovery_patterns = {
            ComponentType.TOOL: {
                'decorators': ['@mcp_tool', '@tool', '@mcp.tool'],
                'base_classes': ['BaseTool'],
                'file_patterns': ['*_tool.py', 'tool_*.py'],
                'directories': ['tools']
            },
            ComponentType.RESOURCE: {
                'decorators': ['@mcp_resource', '@resource', '@mcp.resource'],
                'base_classes': ['BaseResource'],
                'file_patterns': ['*_resource.py', 'resource_*.py'],
                'directories': ['resources']
            },
            ComponentType.PROMPT: {
                'decorators': ['@mcp_prompt', '@prompt', '@mcp.prompt'],
                'base_classes': ['BasePrompt'],
                'file_patterns': ['*_prompt.py', 'prompt_*.py', '*.yaml', '*.yml'],
                'directories': ['templates/prompts', 'prompts']
            }
        }
    
    def discover_all(self) -> Dict[ComponentType, List[Tuple[str, Any]]]:
        """Discover all components"""
        discovered = {}
        for component_type in ComponentType:
            discovered[component_type] = self.discover_components(component_type)
        return discovered
    
    def discover_components(self, component_type: ComponentType) -> List[Tuple[str, Any]]:
        """Discover components of a specific type"""
        patterns = self._discovery_patterns[component_type]
        discovered = []
        
        # Search in specific directories
        for directory in patterns['directories']:
            search_path = self.base_path / directory
            if search_path.exists():
                discovered.extend(self._scan_directory(search_path, component_type, patterns))
        
        return discovered
    
    def _scan_directory(self, directory: Path, component_type: ComponentType, 
                       patterns: Dict) -> List[Tuple[str, Any]]:
        """Scan a directory for components"""
        discovered = []
        
        for file_path in directory.rglob("*.py"):
            if file_path.name.startswith('__'):
                continue
                
            try:
                # Parse the Python file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Find decorated functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if self._has_mcp_decorators(node, patterns['decorators']):
                            component_name = self._extract_component_name(node, file_path)
                            discovered.append((component_name, self._load_component(file_path, node.name)))
                    
                    elif isinstance(node, ast.ClassDef):
                        if self._inherits_from_base(node, patterns['base_classes']):
                            component_name = self._extract_component_name(node, file_path)
                            discovered.append((component_name, self._load_component(file_path, node.name)))
            
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
        
        # Handle YAML/YML files for prompts
        if component_type == ComponentType.PROMPT:
            for file_path in directory.rglob("*.yaml"):
                discovered.extend(self._load_yaml_prompts(file_path))
            for file_path in directory.rglob("*.yml"):
                discovered.extend(self._load_yaml_prompts(file_path))
        
        return discovered
    
    def _has_mcp_decorators(self, node: ast.FunctionDef, decorators: List[str]) -> bool:
        """Check if function has MCP decorators"""
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if any(pattern.replace('@', '') in decorator_name for pattern in decorators):
                return True
        return False
    
    def _inherits_from_base(self, node: ast.ClassDef, base_classes: List[str]) -> bool:
        """Check if class inherits from base classes"""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in base_classes:
                return True
        return False
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if isinstance(decorator.value, ast.Name) else decorator.attr
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""
    
    def _extract_component_name(self, node, file_path: Path) -> str:
        """Extract component name from node and file path"""
        # Use function/class name, or derive from file name
        if hasattr(node, 'name'):
            return node.name
        return file_path.stem
    
    def _load_component(self, file_path: Path, component_name: str) -> Any:
        """Dynamically load component from file"""
        try:
            # Convert file path to module path
            relative_path = file_path.relative_to(self.base_path)
            module_path = str(relative_path.with_suffix('')).replace(os.sep, '.')
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the component
            return getattr(module, component_name)
        
        except Exception as e:
            logger.error(f"Failed to load component {component_name} from {file_path}: {e}")
            return None
    
    def _load_yaml_prompts(self, file_path: Path) -> List[Tuple[str, Any]]:
        """Load prompts from YAML files"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            prompts = []
            if isinstance(data, dict):
                for name, content in data.items():
                    prompts.append((name, content))
            
            return prompts
        
        except Exception as e:
            logger.error(f"Failed to load YAML prompts from {file_path}: {e}")
            return []