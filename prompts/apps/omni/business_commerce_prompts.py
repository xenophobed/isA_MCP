#!/usr/bin/env python
"""
Business & Commerce 💼 Category Prompts for Omni MCP Server
Professional business analysis and strategic planning prompts
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_business_commerce_prompts(mcp):
    """Register Business & Commerce 💼 category prompts with the MCP server"""
    
    @mcp.prompt("market_analysis_prompt")
    async def market_analysis_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive market analysis and competitive intelligence
        
        This prompt guides creation of investment-grade market research with
        data-driven insights for business strategy and investment decisions.
        
        Args:
            subject: The market or industry to analyze
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: market, analysis, competitive, intelligence, investment, strategy
        Category: business_commerce
        """
        
        prompt_template = f"""
# Market Research Analyst with Industry Intelligence

## Market Analysis Request
**Topic**: "{subject}"
**Depth**: {depth} market analysis
**Content Type**: Market analysis report

## Context & Requirements
- **Target Audience**: Business professionals, investors, and strategic decision-makers
- **Content Purpose**: Comprehensive market insights for business strategy and investment decisions
- **Research Requirement**: Current market data, competitor analysis, and industry trends
- **Quality Standard**: Investment-grade market research with data-driven insights

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Market size and growth projections with supporting data
- Competitive landscape analysis with key player profiles
- Industry trends and market dynamics assessment
- SWOT analysis for market opportunities and threats
- Consumer behavior insights and market segmentation
- Financial metrics and market performance indicators
- {depth} level analysis: {{"shallow" = "market overview and key trends", "deep" = "comprehensive market intelligence report"}}
- Strategic recommendations with implementation considerations

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a professional market analysis that meets investment-grade standards.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("business_strategy_prompt")
    async def business_strategy_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for strategic business planning and development
        
        This prompt guides creation of McKinsey/BCG-level strategic consulting
        deliverables with actionable recommendations.
        
        Args:
            subject: The business strategy topic or challenge
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: strategy, business, planning, consulting, framework, strategic
        Category: business_commerce
        """
        
        prompt_template = f"""
# Business Strategy Consultant with Strategic Planning Expertise

## Strategy Request
**Topic**: "{subject}"
**Depth**: {depth} strategic analysis
**Content Type**: Business strategy document

## Context & Requirements
- **Target Audience**: C-suite executives, business owners, and strategic planning teams
- **Content Purpose**: Strategic framework and actionable business strategy recommendations
- **Research Requirement**: Industry analysis, competitive positioning, and market opportunities
- **Quality Standard**: McKinsey/BCG-level strategic consulting deliverable

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Strategic situation analysis with current state assessment
- SWOT analysis with strategic implications
- Strategic objectives and key performance indicators
- Competitive positioning and differentiation strategy
- Implementation roadmap with timeline and milestones
- Resource requirements and budget considerations
- Risk assessment and mitigation strategies
- {depth} level analysis: {{"shallow" = "strategic overview and key recommendations", "deep" = "comprehensive strategic plan with detailed implementation"}}
- Success metrics and monitoring framework

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a professional business strategy document that meets consulting standards.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("financial_analysis_prompt")
    async def financial_analysis_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive financial analysis and modeling
        
        This prompt guides creation of detailed financial assessments with
        quantitative analysis and investment recommendations.
        
        Args:
            subject: The financial analysis topic or entity
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: financial, analysis, modeling, investment, valuation, metrics
        Category: business_commerce
        """
        
        prompt_template = f"""
# Financial Analyst with Investment Expertise

## Financial Analysis Request
**Topic**: "{subject}"
**Depth**: {depth} financial analysis
**Content Type**: Financial analysis report

## Context & Requirements
- **Target Audience**: Investors, financial professionals, and business decision-makers
- **Content Purpose**: Comprehensive financial assessment for investment and strategic decisions
- **Research Requirement**: Financial statements, market data, and industry benchmarks
- **Quality Standard**: Investment-grade financial analysis with quantitative rigor

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Financial performance analysis with key metrics
- Profitability and efficiency assessment
- Liquidity and solvency analysis
- Cash flow analysis and projections
- Valuation analysis using multiple methodologies
- Industry benchmarking and peer comparison
- Risk assessment and sensitivity analysis
- {depth} level analysis: {{"shallow" = "key financial metrics and summary", "deep" = "comprehensive financial modeling and valuation"}}
- Investment recommendations with rationale

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a professional financial analysis that meets investment-grade standards.
"""
        
        return prompt_template.strip()

    logger.debug("Business & Commerce 💼 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_business_commerce_prompts(mcp)