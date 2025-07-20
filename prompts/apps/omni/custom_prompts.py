#!/usr/bin/env python
"""
Custom ⚡ Category Prompts for Omni MCP Server
Flexible custom content creation for general purposes and research reports
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_custom_prompts(mcp):
    """Register Custom ⚡ category prompts with the MCP server"""
    
    @mcp.prompt("general_content_prompt")
    async def general_content_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for general content creation with research capabilities
        
        This prompt guides content creation for comprehensive, well-researched content
        on any topic with proper citations and professional quality.
        
        Args:
            subject: The main topic or subject for content creation
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: general, content, research, comprehensive, professional, citations
        Category: custom
        """
        
        prompt_template = f"""
# Expert Content Creator with Research Capabilities

## Content Request
**Topic**: "{subject}"
**Depth**: {depth} analysis
**Content Type**: General content

## Context & Requirements
- **Target Audience**: General readers seeking comprehensive information
- **Content Purpose**: Informative and engaging content that provides value
- **Research Requirement**: Use current data and multiple authoritative sources
- **Quality Standard**: Professional-grade content with proper citations

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Well-researched content with current information (2024-2025)
- Include relevant statistics, examples, and expert insights
- Proper source attribution and fact-checking
- Engaging writing style with clear structure
- {depth} level analysis: {{"shallow" = "overview focus", "deep" = "comprehensive analysis"}}

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create comprehensive, well-sourced content that meets these specifications.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("research_report_prompt")
    async def research_report_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for detailed research analysis and academic-style reports
        
        This prompt guides creation of comprehensive research reports with
        academic rigor and detailed analysis.
        
        Args:
            subject: The research topic or subject
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: research, report, academic, analysis, detailed, scholarly
        Category: custom
        """
        
        prompt_template = f"""
# Research Analyst with Academic Expertise

## Research Request
**Topic**: "{subject}"
**Depth**: {depth} research analysis
**Content Type**: Research report

## Context & Requirements
- **Target Audience**: Researchers, academics, and professionals requiring detailed analysis
- **Content Purpose**: Comprehensive research findings with academic rigor
- **Research Requirement**: Current academic sources, peer-reviewed materials, and authoritative data
- **Quality Standard**: Academic-grade research with methodology and citations

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Executive summary with key findings
- Literature review and background research
- Methodology and analytical framework
- Detailed findings with supporting evidence
- Data analysis and statistical insights where applicable
- Conclusions and recommendations
- Comprehensive bibliography and citations
- {depth} level analysis: {{"shallow" = "summary findings", "deep" = "comprehensive research analysis"}}

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a professional research report that meets academic standards.
"""
        
        return prompt_template.strip()

    logger.info("Custom ⚡ prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_custom_prompts(mcp)