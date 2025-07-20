#!/usr/bin/env python
"""
Marketing & Media 📢 Category Prompts for Omni MCP Server
Marketing strategy and content marketing campaign development
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_marketing_media_prompts(mcp):
    """Register Marketing & Media 📢 category prompts with the MCP server"""
    
    @mcp.prompt("campaign_strategy_prompt")
    async def campaign_strategy_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive marketing campaign strategy development
        
        This prompt guides creation of strategic marketing campaigns with
        audience targeting, messaging, and performance optimization.
        
        Args:
            subject: The campaign topic or product/service to promote
            depth: Campaign strategy depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: campaign, strategy, marketing, advertising, targeting, promotion
        Category: marketing_media
        """
        
        prompt_template = f"""
# Marketing Strategist with Campaign Development Expertise

## Campaign Strategy Request
**Topic**: "{subject}"
**Depth**: {depth} campaign strategy
**Content Type**: Marketing campaign strategy

## Context & Requirements
- **Target Audience**: Marketing professionals, brand managers, and business owners
- **Content Purpose**: Strategic marketing campaign framework for effective promotion
- **Research Requirement**: Market analysis, audience insights, and competitive intelligence
- **Quality Standard**: Agency-level campaign strategy with measurable objectives

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Campaign overview with objectives and success metrics
- Target audience analysis and persona development
- Positioning and messaging strategy
- Channel strategy and media mix recommendations
- Creative direction and content themes
- Budget allocation and resource planning
- Timeline and implementation roadmap
- {depth} level strategy: {{"shallow" = "core campaign elements and key tactics", "deep" = "comprehensive campaign strategy with detailed execution plan"}}
- Performance measurement and optimization framework

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a strategic marketing campaign that drives measurable business results.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("content_marketing_prompt")
    async def content_marketing_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive content marketing strategy and execution
        
        This prompt guides creation of content marketing strategies with
        audience engagement, brand building, and lead generation focus.
        
        Args:
            subject: The content marketing topic or brand/industry focus
            depth: Content strategy depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: content, marketing, strategy, engagement, branding, lead generation
        Category: marketing_media
        """
        
        prompt_template = f"""
# Content Marketing Specialist with Digital Strategy Expertise

## Content Marketing Request
**Topic**: "{subject}"
**Depth**: {depth} content marketing strategy
**Content Type**: Content marketing strategy and framework

## Context & Requirements
- **Target Audience**: Content marketers, digital marketers, and brand strategists
- **Content Purpose**: Strategic content framework for audience engagement and business growth
- **Research Requirement**: Audience behavior analysis, content trends, and competitive content audit
- **Quality Standard**: Data-driven content strategy with engagement optimization

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Content strategy overview with business objectives alignment
- Audience research and content persona mapping
- Content pillar development and thematic frameworks
- Content calendar and publishing strategy
- Distribution channel optimization
- SEO and discoverability enhancement
- Engagement and community building tactics
- {depth} level strategy: {{"shallow" = "core content strategy and key tactics", "deep" = "comprehensive content marketing system with advanced optimization"}}
- Performance analytics and content optimization
- Brand voice and storytelling guidelines

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a content marketing strategy that builds audience engagement and drives business growth.
"""
        
        return prompt_template.strip()

    logger.info("Marketing & Media 📢 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_marketing_media_prompts(mcp)