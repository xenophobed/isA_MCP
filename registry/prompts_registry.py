import yaml
from pathlib import Path
from registry.base import BaseRegistry, ComponentType
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptRegistry(BaseRegistry):
    def __init__(self, auto_discover: bool = True, prompt_dirs: List[Path] = None):
        super().__init__()
        self._prompt_templates: Dict[str, Any] = {}
        
        if auto_discover:
            self._auto_discover(prompt_dirs or [Path.cwd() / "templates" / "prompts"])
    
    def _get_component_type(self) -> ComponentType:
        return ComponentType.PROMPT
    
    def register_prompt(self, name: str, template: str, arguments: List[Dict] = None,
                       description: str = ""):
        """Register a prompt template"""
        prompt_data = {
            'name': name,
            'template': template,
            'arguments': arguments or [],
            'description': description
        }
        
        metadata = {
            'description': description,
            'arguments': arguments or [],
            'template': template
        }
        
        self.register(name, prompt_data, metadata=metadata)
        self._prompt_templates[name] = prompt_data
    
    def get_prompt_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt template"""
        return self._prompt_templates.get(name)
    
    def render_prompt(self, name: str, **kwargs) -> str:
        """Render a prompt with arguments"""
        template_data = self.get_prompt_template(name)
        if not template_data:
            raise ValueError(f"Prompt template '{name}' not found")
        
        template = template_data['template']
        
        # Simple template rendering (can be enhanced with Jinja2)
        for key, value in kwargs.items():
            template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    def get_mcp_prompt_definitions(self) -> List[Dict[str, Any]]:
        """Get prompt definitions in MCP format"""
        prompts = []
        for info in self.list_all():
            prompts.append({
                'name': info.name,
                'description': info.metadata.get('description', ''),
                'arguments': info.metadata.get('arguments', [])
            })
        return prompts
    
    def _extract_dependencies(self, component: Any) -> List[str]:
        return []  # Prompts typically don't have dependencies
    
    def _auto_discover(self, prompt_dirs: List[Path]):
        """Auto-discover prompts from YAML files"""
        for prompt_dir in prompt_dirs:
            if not prompt_dir.exists():
                continue
            
            for yaml_file in prompt_dir.rglob("*.yaml"):
                self._load_prompts_from_yaml(yaml_file)
            
            for yml_file in prompt_dir.rglob("*.yml"):
                self._load_prompts_from_yaml(yml_file)
    
    def _load_prompts_from_yaml(self, yaml_path: Path):
        """Load prompts from a YAML file"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if isinstance(data, dict):
                for prompt_name, prompt_data in data.items():
                    if isinstance(prompt_data, dict):
                        template = prompt_data.get('template', '')
                        arguments = prompt_data.get('arguments', [])
                        description = prompt_data.get('description', '')
                    else:
                        template = str(prompt_data)
                        arguments = []
                        description = f"Prompt from {yaml_path.name}"
                    
                    self.register_prompt(prompt_name, template, arguments, description)
        
        except Exception as e:
            logger.error(f"Failed to load prompts from {yaml_path}: {e}")