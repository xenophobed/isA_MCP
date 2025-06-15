from typing import Dict, List, Any, Optional
from inspect import signature, getdoc
from langchain_core.tools import BaseTool
import logging
from pydantic import BaseModel, Field
import re

logger = logging.getLogger(__name__)

class SemanticVector(BaseModel):
    """Essential semantic properties of a tool"""
    core_concept: str = Field(description="Primary function concept")
    domain: str = Field(description="Primary domain")
    service_type: str = Field(description="Primary service type")

class FunctionalVector(BaseModel):
    """Essential functional properties of a tool"""
    operation: str = Field(description="Primary operation type")
    input_spec: Dict[str, str] = Field(description="Input specification")
    output_spec: Dict[str, str] = Field(description="Output specification")

class ContextualVector(BaseModel):
    """Essential contextual properties of a tool"""
    usage_context: str = Field(description="Primary usage context")
    prerequisites: List[str] = Field(description="Critical requirements")
    constraints: List[str] = Field(description="Critical limitations")

class ToolVectorMetadata(BaseModel):
    """Core tool vector metadata"""
    capability_id: str
    semantic_vector: SemanticVector
    functional_vector: FunctionalVector
    contextual_vector: ContextualVector

class ToolMetadataExtractor:
    """Extracts essential tool metadata for vectorization"""
    
    @staticmethod
    def extract_from_tool(tool: BaseTool) -> ToolVectorMetadata:
        """Extract core metadata from tool docstring annotations"""
        try:
            if not tool:
                raise ValueError("Tool cannot be None")
                
            doc = getdoc(tool.func) or ""
            sections = ToolMetadataExtractor._parse_docstring_sections(doc)
            
            return ToolVectorMetadata(
                capability_id=f"tool_{tool.name}",
                semantic_vector=ToolMetadataExtractor._extract_semantic(sections),
                functional_vector=ToolMetadataExtractor._extract_functional(tool, sections),
                contextual_vector=ToolMetadataExtractor._extract_contextual(sections)
            )
            
        except Exception as e:
            logger.error(f"Error extracting tool metadata: {str(e)}")
            raise
            
    @staticmethod
    def _parse_docstring_sections(doc: str) -> Dict[str, Dict[str, str]]:
        """Parse structured docstring sections"""
        sections = {}
        current_section = None
        section_content = []
        
        # Split into lines and clean
        lines = [line.strip() for line in doc.split('\n')]
        
        for line in lines:
            if not line:
                continue
                
            # Check for section start
            if line.startswith('@'):
                # Save previous section if exists
                if current_section and section_content:
                    sections[current_section] = ToolMetadataExtractor._parse_section_content(section_content)
                    section_content = []
                # Remove @ and : from section name
                current_section = line.lstrip('@').rstrip(':').strip().lower()
            elif current_section and ':' in line:
                # Add content line
                section_content.append(line)
                
        # Save last section
        if current_section and section_content:
            sections[current_section] = ToolMetadataExtractor._parse_section_content(section_content)
            
        return sections
    
    @staticmethod
    def _parse_section_content(content: List[str]) -> Dict[str, str]:
        """Parse section content into key-value pairs"""
        section_data = {}
        for line in content:
            if ':' in line:
                key, value = [x.strip() for x in line.split(':', 1)]
                if value:  # Only add if value is not empty
                    section_data[key] = value.strip()
        return section_data
            
    @staticmethod
    def _extract_semantic(sections: Dict) -> SemanticVector:
        """Extract core semantic properties"""
        semantic = sections.get('semantic', {})
        
        return SemanticVector(
            core_concept=semantic.get('concept', 'unknown'),
            domain=semantic.get('domain', 'general'),
            service_type=semantic.get('type', 'query')
        )
        
    @staticmethod
    def _extract_functional(tool: BaseTool, sections: Dict) -> FunctionalVector:
        """Extract core functional properties"""
        functional = sections.get('functional', {})
        
        # Get input specs
        input_spec = {}
        if 'input' in functional:
            for input_def in functional['input'].split(','):
                if ':' in input_def:
                    name, type_ = input_def.split(':')
                    input_spec[name.strip()] = type_.strip()
                    
        # Fallback to signature if no input spec found
        if not input_spec:
            sig = signature(tool.func)
            input_spec = {
                name: param.annotation.__name__
                for name, param in sig.parameters.items()
            }
            
        # Get output spec from docstring or fallback to signature
        output_type = functional.get('output', '').split(':')[-1].strip()
        if not output_type:
            sig = signature(tool.func)
            output_type = sig.return_annotation.__name__
        
        output_spec = {"type": output_type}
            
        return FunctionalVector(
            operation=functional.get('operation', tool.name.split('_')[0]),
            input_spec=input_spec,
            output_spec=output_spec
        )
        
    @staticmethod
    def _extract_contextual(sections: Dict) -> ContextualVector:
        """Extract core contextual properties"""
        context = sections.get('context', {})
        
        return ContextualVector(
            usage_context=context.get('usage', 'general-query'),
            prerequisites=[p.strip() for p in context.get('prereq', '').split(',') if p.strip()],
            constraints=[c.strip() for c in context.get('constraint', '').split(',') if c.strip()]
        )
