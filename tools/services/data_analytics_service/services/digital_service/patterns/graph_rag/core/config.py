"""
Configuration system for Generic Knowledge Analytics

Provides domain-specific configuration management using YAML/JSON
for complete customization of knowledge extraction behavior.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json
from enum import Enum

from .types import EntityTypeRegistry, RelationTypeRegistry, AttributeTypeRegistry


class AIModelType(Enum):
    """Supported AI model types"""
    LLM = "llm"          # Large Language Models (GPT, Claude, etc.)
    VLM = "vlm"          # Vision-Language Models (GPT-4V, LLaVA, etc.)
    MULTIMODAL = "multimodal"  # Combined text+vision
    EMBEDDING = "embedding"     # Embedding models
    CUSTOM = "custom"    # Custom AI implementations


@dataclass
class AIStrategyConfig:
    """Configuration for AI-based extraction strategies"""
    model_type: AIModelType = AIModelType.LLM
    model_name: str = "claude-3-sonnet"
    model_version: str = "latest"
    
    # Model parameters
    temperature: float = 0.1
    max_tokens: int = 4000
    top_p: float = 0.9
    
    # Extraction settings
    confidence_threshold: float = 0.7
    retry_attempts: int = 3
    timeout_seconds: int = 30
    
    # Prompt configuration
    system_prompt: str = ""
    few_shot_examples: List[Dict[str, Any]] = field(default_factory=list)
    domain_context: str = ""
    
    # Vision-specific (for VLM)
    image_processing: Dict[str, Any] = field(default_factory=dict)
    multimodal_fusion: str = "late"  # early, late, joint
    
    # Custom model settings
    custom_endpoint: str = ""
    custom_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractionConfig:
    """Configuration for extraction methods and fallbacks"""
    
    # Primary extraction methods (ordered by preference)
    primary_methods: List[str] = field(default_factory=lambda: ["llm", "pattern"])
    
    # Fallback strategy
    enable_fallback: bool = True
    fallback_methods: List[str] = field(default_factory=lambda: ["pattern"])
    
    # Confidence-based routing
    confidence_routing: Dict[str, float] = field(default_factory=lambda: {
        "llm": 0.8,
        "pattern": 0.6,
        "hybrid": 0.9
    })
    
    # Text processing
    max_text_length: int = 50000
    chunk_size: int = 4000
    chunk_overlap: int = 200
    enable_preprocessing: bool = True
    
    # Parallel processing
    enable_parallel: bool = True
    max_workers: int = 4
    batch_size: int = 10
    
    # Quality control
    enable_validation: bool = True
    enable_deduplication: bool = True
    similarity_threshold: float = 0.85


@dataclass
class DomainConfig:
    """Complete domain configuration for knowledge analytics"""
    
    # Domain metadata
    domain_name: str = "generic"
    domain_description: str = ""
    version: str = "1.0.0"
    created_by: str = ""
    created_at: str = ""
    
    # Language and locale
    language: str = "en"
    locale: str = "en_US"
    
    # Type registries
    entity_registry: EntityTypeRegistry = field(default_factory=EntityTypeRegistry)
    relation_registry: RelationTypeRegistry = field(default_factory=RelationTypeRegistry)
    attribute_registry: AttributeTypeRegistry = field(default_factory=AttributeTypeRegistry)
    
    # AI strategy configurations
    ai_strategies: Dict[str, AIStrategyConfig] = field(default_factory=dict)
    
    # Extraction configuration
    extraction_config: ExtractionConfig = field(default_factory=ExtractionConfig)
    
    # Domain-specific prompts and templates
    prompts: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)
    
    # Custom rules and patterns
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> 'DomainConfig':
        """Load domain configuration from YAML file"""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Domain config file not found: {yaml_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls._from_dict(data)
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> 'DomainConfig':
        """Load domain configuration from JSON file"""
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Domain config file not found: {json_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'DomainConfig':
        """Create DomainConfig from dictionary"""
        config = cls(
            domain_name=data.get('domain_name', 'generic'),
            domain_description=data.get('domain_description', ''),
            version=data.get('version', '1.0.0'),
            language=data.get('language', 'en'),
            locale=data.get('locale', 'en_US')
        )
        
        # Load entity types
        for entity_type, entity_config in data.get('entity_types', {}).items():
            config.entity_registry.register_type(
                type_name=entity_type,
                schema=entity_config.get('schema', {}),
                description=entity_config.get('description', ''),
                extraction_patterns=entity_config.get('patterns', []),
                ai_prompts=entity_config.get('ai_prompts', {})
            )
        
        # Load relation types
        for relation_type, relation_config in data.get('relation_types', {}).items():
            config.relation_registry.register_type(
                relation_type=relation_type,
                schema=relation_config.get('schema', {}),
                predicate=relation_config.get('predicate', ''),
                patterns=relation_config.get('patterns', []),
                ai_prompts=relation_config.get('ai_prompts', {}),
                valid_entity_pairs=relation_config.get('valid_entity_pairs', [])
            )
        
        # Load attribute types
        for attr_type, attr_config in data.get('attribute_types', {}).items():
            config.attribute_registry.register_type(
                attribute_type=attr_type,
                schema=attr_config.get('schema', {}),
                validation_rules=attr_config.get('validation_rules', {}),
                normalization_rules=attr_config.get('normalization_rules', {}),
                ai_prompts=attr_config.get('ai_prompts', {})
            )
        
        # Load AI strategies
        for strategy_name, strategy_config in data.get('ai_strategies', {}).items():
            config.ai_strategies[strategy_name] = AIStrategyConfig(
                model_type=AIModelType(strategy_config.get('model_type', 'llm')),
                model_name=strategy_config.get('model_name', 'claude-3-sonnet'),
                temperature=strategy_config.get('temperature', 0.1),
                max_tokens=strategy_config.get('max_tokens', 4000),
                confidence_threshold=strategy_config.get('confidence_threshold', 0.7),
                system_prompt=strategy_config.get('system_prompt', ''),
                domain_context=strategy_config.get('domain_context', '')
            )
        
        # Load extraction config
        if 'extraction_config' in data:
            ext_config = data['extraction_config']
            config.extraction_config = ExtractionConfig(
                primary_methods=ext_config.get('primary_methods', ['llm']),
                enable_fallback=ext_config.get('enable_fallback', True),
                confidence_routing=ext_config.get('confidence_routing', {}),
                max_text_length=ext_config.get('max_text_length', 50000),
                enable_parallel=ext_config.get('enable_parallel', True)
            )
        
        # Load prompts and templates
        config.prompts = data.get('prompts', {})
        config.templates = data.get('templates', {})
        config.custom_rules = data.get('custom_rules', {})
        
        return config
    
    def to_yaml(self, yaml_path: Union[str, Path]):
        """Save domain configuration to YAML file"""
        data = self._to_dict()
        path = Path(yaml_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def to_json(self, json_path: Union[str, Path]):
        """Save domain configuration to JSON file"""
        data = self._to_dict()
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _to_dict(self) -> Dict[str, Any]:
        """Convert DomainConfig to dictionary"""
        return {
            'domain_name': self.domain_name,
            'domain_description': self.domain_description,
            'version': self.version,
            'language': self.language,
            'locale': self.locale,
            'entity_types': {
                type_name: {
                    'schema': self.entity_registry.get_schema(type_name),
                    'patterns': self.entity_registry.get_extraction_patterns(type_name),
                    'ai_prompts': self.entity_registry.get_ai_prompts(type_name)
                }
                for type_name in self.entity_registry.get_types()
            },
            'relation_types': {
                rel_type: {
                    'schema': self.relation_registry.get_schema(rel_type),
                    'predicate': self.relation_registry.get_predicate(rel_type),
                    'patterns': self.relation_registry.get_patterns(rel_type)
                }
                for rel_type in self.relation_registry.get_types()
            },
            'attribute_types': {
                attr_type: {
                    'schema': self.attribute_registry.get_schema(attr_type),
                    'validation_rules': self.attribute_registry.get_validation_rules(attr_type),
                    'normalization_rules': self.attribute_registry.get_normalization_rules(attr_type)
                }
                for attr_type in self.attribute_registry.get_types()
            },
            'prompts': self.prompts,
            'templates': self.templates,
            'custom_rules': self.custom_rules
        }
    
    def get_ai_strategy(self, strategy_name: str = "default") -> AIStrategyConfig:
        """Get AI strategy configuration"""
        return self.ai_strategies.get(strategy_name, AIStrategyConfig())
    
    def validate(self) -> List[str]:
        """Validate domain configuration and return list of issues"""
        issues = []
        
        if not self.domain_name:
            issues.append("Domain name is required")
        
        if not self.entity_registry.get_types():
            issues.append("At least one entity type must be registered")
        
        if not self.ai_strategies:
            issues.append("At least one AI strategy must be configured")
        
        return issues