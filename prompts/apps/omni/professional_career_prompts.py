#!/usr/bin/env python
"""
Professional & Career 👔 Category Prompts for Omni MCP Server
Career development and professional advancement guidance
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_professional_career_prompts(mcp):
    """Register Professional & Career 👔 category prompts with the MCP server"""
    
    @mcp.prompt("career_guide_prompt")
    async def career_guide_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive career development guidance
        
        This prompt guides creation of strategic career advice with
        professional development, skill building, and advancement strategies.
        
        Args:
            subject: The career topic or professional development area
            depth: Guide depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: career, professional, development, advancement, skills, guidance
        Category: professional_career
        """
        
        prompt_template = f"""
# Career Development Specialist with Professional Growth Expertise

## Career Guide Request
**Topic**: "{subject}"
**Depth**: {depth} career guide
**Content Type**: Professional development and career guidance

## Context & Requirements
- **Target Audience**: Professionals seeking career advancement and development guidance
- **Content Purpose**: Strategic career advice for professional growth and advancement
- **Research Requirement**: Industry trends, career data, and professional development best practices
- **Quality Standard**: Professional-grade career guidance with actionable strategies

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Career assessment and current state analysis
- Industry landscape and opportunity identification
- Skill development and competency mapping
- Professional networking and relationship building
- Personal branding and visibility strategies
- Career progression planning and goal setting
- Interview preparation and negotiation tactics
- {depth} level guide: {{"shallow" = "essential career strategies and immediate actions", "deep" = "comprehensive career development system with long-term planning"}}
- Professional development resources and continuing education

## Career Development Framework
- Self-assessment and strengths identification
- Market analysis and opportunity evaluation
- Skill gap analysis and development planning
- Strategic positioning and differentiation
- Network building and relationship management
- Performance optimization and achievement demonstration

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a strategic career guide that accelerates professional growth and advancement.
"""
        
        return prompt_template.strip()

    logger.info("Professional & Career 👔 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_professional_career_prompts(mcp)