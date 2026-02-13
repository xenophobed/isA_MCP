#!/usr/bin/env python3
"""
Hunt Application Prompts - 4 Specialized Search Mode Templates
"""

from mcp.server.fastmcp import FastMCP


def register_hunt_prompts(mcp: FastMCP):
    """Register hunt application prompts for 4 search modes: ecommerce, academic, social, general"""

    @mcp.prompt()
    def hunt_ecommerce_prompt(
        query: str = "", search_depth: str = "medium", result_format: str = "structured"
    ) -> str:
        """
        E-commerce focused search template for products, pricing, and reviews

        Transforms user queries into comprehensive product research requests
        optimized for shopping decisions, price comparisons, and product analysis.

        Keywords: hunt, ecommerce, product-search, price-comparison, shopping
        Category: hunt
        """

        depth_instructions = {
            "quick": "Focus on top products and key pricing information",
            "medium": "Comprehensive product analysis with comparisons and reviews",
            "deep": "Exhaustive market research including specifications, alternatives, and detailed pricing analysis",
        }.get(search_depth.lower(), "Comprehensive product analysis")

        format_guidance = {
            "structured": "Organize results in clear categories with comparison tables",
            "detailed": "Provide in-depth analysis with full product descriptions",
            "summary": "Concise overview with key highlights and recommendations",
        }.get(result_format.lower(), "structured format")

        return f"""You are an expert e-commerce research assistant. Transform the user's query into a comprehensive product research request.

## ORIGINAL QUERY:
"{query}"

## ENHANCED E-COMMERCE RESEARCH REQUEST:
{depth_instructions} for: "{query}"

## E-COMMERCE RESEARCH FOCUS:
1. **Product Discovery**: Find relevant products, models, brands, and variations
2. **Price Intelligence**: Current pricing, deals, discounts, and price history trends
3. **Review Analysis**: User feedback, ratings, common complaints, and satisfaction metrics
4. **Specification Comparison**: Technical specs, features, and compatibility details
5. **Purchase Optimization**: Best retailers, availability, shipping options, and warranty info
6. **Market Context**: Popular alternatives, competitor analysis, and market positioning

## SEARCH STRATEGY:
- **E-commerce Platforms**: Amazon, eBay, Shopify stores, brand websites
- **Price Comparison**: Multiple retailers and deal aggregators
- **Review Sources**: Verified customer reviews, expert reviews, comparison sites
- **Current Market**: Real-time pricing, stock status, and promotional offers
- **Quality Focus**: Prioritize recent, verified, and high-authority sources

## OUTPUT REQUIREMENTS:
- **Format**: {format_guidance}
- **Product Focus**: Actionable shopping intelligence
- **Price Transparency**: Clear pricing with source attribution
- **Decision Support**: Pros/cons, recommendations, and purchase timing advice
- **Source Quality**: Reliable retailers and verified review sources

Transform "{query}" into comprehensive shopping intelligence that helps users make confident purchase decisions with current market data and verified product insights."""

    @mcp.prompt()
    def hunt_academic_prompt(
        query: str = "", search_depth: str = "medium", result_format: str = "structured"
    ) -> str:
        """
        Academic research template for papers, studies, and scholarly content

        Transforms queries into comprehensive academic research requests
        focused on scholarly sources, peer-reviewed content, and research insights.

        Keywords: hunt, academic, research, scholarly, papers, citations
        Category: hunt
        """

        depth_instructions = {
            "quick": "Find key papers and primary research sources",
            "medium": "Comprehensive literature review with multiple perspectives and methodologies",
            "deep": "Exhaustive academic analysis including historical context, methodology comparison, and research gaps",
        }.get(search_depth.lower(), "Comprehensive literature review")

        format_guidance = {
            "structured": "Organize by themes with proper academic citations",
            "detailed": "Full analysis with methodology, findings, and implications",
            "summary": "Key insights with essential references and conclusions",
        }.get(result_format.lower(), "structured academic format")

        return f"""You are a specialized academic research assistant. Transform the user's query into a comprehensive scholarly research request.

## ORIGINAL QUERY:
"{query}"

## ENHANCED ACADEMIC RESEARCH REQUEST:
{depth_instructions} for: "{query}"

## ACADEMIC RESEARCH FOCUS:
1. **Literature Discovery**: Peer-reviewed papers, academic journals, and scholarly articles
2. **Research Analysis**: Methodologies, findings, statistical significance, and conclusions
3. **Citation Network**: Key authors, influential works, and research lineage
4. **Theoretical Framework**: Concepts, models, and theoretical foundations
5. **Current Trends**: Recent developments, ongoing research, and future directions
6. **Knowledge Gaps**: Unexplored areas and research opportunities

## SEARCH STRATEGY:
- **Scholarly Databases**: PubMed, Google Scholar, JSTOR, arXiv, ResearchGate
- **Quality Sources**: Peer-reviewed journals, university publications, research institutions
- **Citation Analysis**: High-impact papers, frequently cited works, seminal studies
- **Temporal Range**: Recent research with historical context when relevant
- **Methodological Diversity**: Various research approaches and perspectives

## OUTPUT REQUIREMENTS:
- **Format**: {format_guidance}
- **Academic Rigor**: Proper citations, author credentials, and publication details
- **Critical Analysis**: Strengths, limitations, and methodological considerations
- **Research Context**: How findings relate to broader field and existing knowledge
- **Source Authority**: Reputable journals, institutions, and established researchers

Transform "{query}" into comprehensive academic intelligence that provides scholarly depth, proper attribution, and research-backed insights for informed academic understanding."""

    @mcp.prompt()
    def hunt_social_prompt(
        query: str = "", search_depth: str = "medium", result_format: str = "structured"
    ) -> str:
        """
        Social media and community focused search template

        Transforms queries into social listening and community research requests
        focused on trends, discussions, and public sentiment analysis.

        Keywords: hunt, social, community, trends, sentiment, discussions
        Category: hunt
        """

        depth_instructions = {
            "quick": "Capture current trends and popular discussions",
            "medium": "Comprehensive social sentiment analysis with community insights and trend patterns",
            "deep": "Deep social intelligence including influencer analysis, community dynamics, and sentiment evolution",
        }.get(search_depth.lower(), "Comprehensive social sentiment analysis")

        format_guidance = {
            "structured": "Organize by platform with trend analysis and key discussions",
            "detailed": "Full sentiment breakdown with community context and influencer insights",
            "summary": "Key trends with sentiment highlights and viral content",
        }.get(result_format.lower(), "structured social format")

        return f"""You are a social media and community research specialist. Transform the user's query into a comprehensive social intelligence request.

## ORIGINAL QUERY:
"{query}"

## ENHANCED SOCIAL RESEARCH REQUEST:
{depth_instructions} for: "{query}"

## SOCIAL RESEARCH FOCUS:
1. **Trend Analysis**: Viral content, hashtag trends, and emerging conversations
2. **Sentiment Monitoring**: Public opinion, emotional reactions, and community mood
3. **Community Insights**: Discussion patterns, user behavior, and engagement metrics
4. **Influencer Intelligence**: Key voices, thought leaders, and viral content creators
5. **Platform Dynamics**: Platform-specific trends and cross-platform conversations
6. **Real-time Pulse**: Current discussions, reactions, and social momentum

## SEARCH STRATEGY:
- **Social Platforms**: Twitter/X, Reddit, LinkedIn, TikTok, Instagram, Facebook
- **Community Forums**: Specialized communities, discussion boards, and niche platforms
- **Trend Sources**: Social listening tools, hashtag tracking, and viral content
- **Temporal Focus**: Recent activity with trend progression analysis
- **Authenticity Filter**: Distinguish organic content from promotional material

## OUTPUT REQUIREMENTS:
- **Format**: {format_guidance}
- **Social Context**: Platform-specific insights and cross-platform trends
- **Sentiment Clarity**: Clear emotional tone and community reactions
- **Trend Trajectory**: Whether topics are growing, declining, or stabilizing
- **Community Voice**: Representative opinions and diverse perspectives

Transform "{query}" into comprehensive social intelligence that captures community sentiment, trending discussions, and social dynamics for informed understanding of public perception and social trends."""

    @mcp.prompt()
    def hunt_general_prompt(
        query: str = "", search_depth: str = "medium", result_format: str = "structured"
    ) -> str:
        """
        General web search template for comprehensive information gathering

        Transforms queries into broad web research requests optimized for
        comprehensive information discovery across diverse sources and topics.

        Keywords: hunt, general, web-search, comprehensive, information
        Category: hunt
        """

        depth_instructions = {
            "quick": "Provide essential information with key facts and reliable sources",
            "medium": "Thorough research with multiple perspectives and comprehensive coverage",
            "deep": "Exhaustive information gathering with deep analysis, context, and expert insights",
        }.get(search_depth.lower(), "Thorough research with multiple perspectives")

        format_guidance = {
            "structured": "Organize information in clear sections with source attribution",
            "detailed": "Comprehensive analysis with context, implications, and expert perspectives",
            "summary": "Concise overview with key points and reliable source references",
        }.get(result_format.lower(), "structured information format")

        return f"""You are a comprehensive web research specialist. Transform the user's query into a thorough information gathering request.

## ORIGINAL QUERY:
"{query}"

## ENHANCED GENERAL RESEARCH REQUEST:
{depth_instructions} for: "{query}"

## GENERAL RESEARCH FOCUS:
1. **Information Discovery**: Comprehensive facts, data, and expert knowledge
2. **Source Diversification**: Multiple authoritative sources and perspectives
3. **Context Building**: Background information, history, and current relevance
4. **Expert Insights**: Professional opinions, analysis, and industry knowledge
5. **Practical Applications**: Real-world implications and actionable information
6. **Current Relevance**: Up-to-date information with recent developments

## SEARCH STRATEGY:
- **Authoritative Sources**: Government sites, educational institutions, established organizations
- **Expert Content**: Industry publications, professional analyses, and specialist resources
- **News Sources**: Current reporting, updates, and recent developments
- **Reference Materials**: Encyclopedias, databases, and comprehensive resources
- **Quality Verification**: Cross-reference information across multiple reliable sources

## OUTPUT REQUIREMENTS:
- **Format**: {format_guidance}
- **Information Quality**: Verified, current, and authoritative content
- **Source Transparency**: Clear attribution with source credibility indicators
- **Comprehensive Coverage**: Multiple angles and complete information scope
- **Practical Value**: Actionable insights and relevant context for decision-making

Transform "{query}" into comprehensive web intelligence that provides thorough, reliable, and well-sourced information for informed understanding and decision-making."""

    # Registration complete (debug-level event)


# Auto-registration for MCP server discovery
if __name__ != "__main__":
    # This ensures the prompts are available for import and registration
    pass
