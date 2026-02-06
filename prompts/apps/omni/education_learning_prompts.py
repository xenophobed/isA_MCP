#!/usr/bin/env python
"""
Education & Learning 📚 Category Prompts for Omni MCP Server
Educational content creation and learning material development
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_education_learning_prompts(mcp):
    """Register Education & Learning 📚 category prompts with the MCP server"""
    
    @mcp.prompt("tutorial_prompt")
    async def tutorial_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive tutorial creation
        
        This prompt guides creation of step-by-step educational tutorials
        with practical examples and hands-on learning approaches.
        
        Args:
            subject: The tutorial topic or skill to teach
            depth: Tutorial depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: tutorial, education, learning, step-by-step, practical, teaching
        Category: education_learning
        """
        
        prompt_template = f"""
# Educational Content Creator with Tutorial Expertise

## Tutorial Request
**Topic**: "{subject}"
**Depth**: {depth} tutorial
**Content Type**: Educational tutorial

## Context & Requirements
- **Target Audience**: Learners seeking practical, hands-on instruction
- **Content Purpose**: Step-by-step guidance with practical application
- **Learning Approach**: Progressive skill building with examples and exercises
- **Quality Standard**: Clear, accessible instruction with measurable learning outcomes

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Clear learning objectives and expected outcomes
- Prerequisites and recommended background knowledge
- Step-by-step instructions with detailed explanations
- Practical examples and real-world applications
- Hands-on exercises and practice activities
- Common mistakes and troubleshooting guidance
- Progress checkpoints and assessment methods
- {depth} level tutorial: {{"shallow" = "basic introduction and key steps", "deep" = "comprehensive instruction with advanced techniques"}}
- Additional resources and next learning steps

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create an engaging, practical tutorial that facilitates effective learning.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("course_material_prompt")
    async def course_material_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive course material development
        
        This prompt guides creation of structured educational course content
        with academic rigor and systematic learning progression.
        
        Args:
            subject: The course topic or subject area
            depth: Course depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: course, curriculum, education, structured, academic, learning
        Category: education_learning
        """
        
        prompt_template = f"""
# Academic Course Designer with Curriculum Expertise

## Course Material Request
**Topic**: "{subject}"
**Depth**: {depth} course material
**Content Type**: Academic course content

## Context & Requirements
- **Target Audience**: Students and educators seeking structured learning content
- **Content Purpose**: Comprehensive educational material for formal or self-directed learning
- **Learning Approach**: Systematic curriculum with progressive skill development
- **Quality Standard**: Academic-level content with clear learning pathways

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Course overview with learning objectives and outcomes
- Detailed curriculum outline with module breakdown
- Comprehensive content for each learning module
- Reading lists and supplementary materials
- Assessment methods and evaluation criteria
- Interactive elements and engagement strategies
- Practical assignments and project ideas
- {depth} level course: {{"shallow" = "introductory course with essential concepts", "deep" = "comprehensive course with advanced topics and specializations"}}
- Professional development and certification pathways

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create structured course material that supports effective teaching and learning.
"""
        
        return prompt_template.strip()

    logger.debug("Education & Learning 📚 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_education_learning_prompts(mcp)