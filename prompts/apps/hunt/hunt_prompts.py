#!/usr/bin/env python3
"""
Hunt Application Prompts - Query Enhancement and Web Research
"""

from mcp.server.fastmcp import FastMCP

def register_hunt_prompts(mcp: FastMCP):
    """Register hunt application prompts for query enhancement and web research"""
    
    @mcp.prompt()
    def hunt_web_analysis_prompt(
        query: str,
        tool_type: str = "web_search",
        analysis_focus: str = "product_research_and_comparison",
        include_pricing: bool = True,
        include_reviews: bool = True,
        include_specifications: bool = True,
        max_results: int = 10,
        output_format: str = "structured_search_results"
    ) -> str:
        """
        Enhanced query prompt for Hunt web analysis and product research
        
        Transforms simple user queries into comprehensive, context-rich research requests
        optimized for product discovery, price comparison, and market analysis.
        
        Keywords: hunt, web-analysis, product-research, query-enhancement, e-commerce
        Category: hunt
        """
        
        # Build analysis components based on parameters
        analysis_components = []
        if include_pricing:
            analysis_components.append("pricing analysis and comparison")
        if include_reviews:
            analysis_components.append("user reviews and ratings analysis")
        if include_specifications:
            analysis_components.append("technical specifications and features")
        
        analysis_text = ", ".join(analysis_components)
        
        # Determine research approach based on tool type
        tool_approach = {
            "web_search": "comprehensive web search across multiple sources",
            "web_crawl": "deep crawling of specific websites and product pages", 
            "web_automation": "automated interaction with e-commerce platforms and databases"
        }.get(tool_type, "web search")
        
        return f"""You are a specialized product research and market analysis assistant. Transform the user's query into a comprehensive research request.

## ORIGINAL USER QUERY:
"{query}"

## ENHANCED RESEARCH REQUEST:
Conduct {tool_approach} to provide comprehensive {analysis_focus} for the query: "{query}"

## RESEARCH OBJECTIVES:
1. **Product Discovery**: Find relevant products, models, and variations
2. **Market Analysis**: Identify key players, brands, and market positioning  
3. **Comprehensive Comparison**: {analysis_text}
4. **Consumer Insights**: Gather user feedback, common issues, and recommendations
5. **Purchase Intelligence**: Best deals, availability, and purchasing options

## SEARCH STRATEGY:
- **Breadth**: Cover multiple product categories and price ranges
- **Depth**: Detailed analysis of top products and alternatives
- **Currency**: Focus on current market conditions and recent releases
- **Diversity**: Include different sources, retailers, and perspectives
- **Quality**: Prioritize authoritative sources and verified information

## OUTPUT REQUIREMENTS:
- **Format**: {output_format}
- **Results Limit**: Up to {max_results} comprehensive results
- **Source Attribution**: Include reliable source links and citations
- **Structured Data**: Organize findings in clear, comparable format
- **Actionable Insights**: Provide clear recommendations and next steps

## ANALYSIS FOCUS: {analysis_focus}
Ensure the research addresses:
- Product specifications and key features
- Price ranges and value propositions  
- User satisfaction and common concerns
- Availability and purchasing options
- Competitive landscape and alternatives

Transform the simple query "{query}" into actionable market intelligence that helps users make informed decisions."""

    @mcp.prompt()
    def general_content_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = None,
        reference_text: str = ""
    ) -> str:
        """
        General content research prompt for Hunt application
        
        Provides flexible content research capabilities that can be adapted
        for various Hunt use cases including web search, analysis, and research.
        
        Keywords: hunt, general-content, research, analysis, flexible
        Category: hunt
        """
        
        depth_instructions = {
            "surface": "Provide a quick overview with key highlights",
            "medium": "Conduct thorough research with multiple perspectives", 
            "deep": "Perform comprehensive analysis with detailed insights and comparisons"
        }.get(depth.lower(), "Conduct thorough research")
        
        reference_context = ""
        if reference_urls:
            reference_context += f"\n## REFERENCE URLS:\n{reference_urls}\n"
        if reference_text:
            reference_context += f"\n## ADDITIONAL CONTEXT:\n{reference_text}\n"
        
        return f"""You are a comprehensive research assistant specializing in gathering and analyzing information.

## RESEARCH SUBJECT:
{subject}

## RESEARCH DEPTH:
{depth_instructions}

{reference_context}

## RESEARCH METHODOLOGY:
1. **Information Gathering**: Collect data from multiple reliable sources
2. **Cross-Verification**: Validate information across different sources
3. **Analysis & Synthesis**: Organize findings into coherent insights
4. **Contextual Understanding**: Consider broader implications and connections
5. **Actionable Intelligence**: Provide practical recommendations and takeaways

## OUTPUT STRUCTURE:
- **Executive Summary**: Key findings and main insights
- **Detailed Analysis**: Comprehensive examination of the subject
- **Supporting Evidence**: Citations, data points, and source references
- **Comparative Context**: How this relates to alternatives or competition
- **Practical Implications**: Actionable insights and recommendations
- **Further Research**: Areas for deeper investigation if needed

## QUALITY STANDARDS:
- **Accuracy**: Verify information from multiple sources
- **Relevance**: Focus on information that directly addresses the subject
- **Timeliness**: Prioritize current and up-to-date information
- **Comprehensiveness**: Cover all important aspects of the subject
- **Clarity**: Present complex information in accessible format

Conduct thorough research on "{subject}" and provide comprehensive analysis that delivers maximum value to the user."""

    @mcp.prompt()
    def web_search_analysis_prompt(
        query: str,
        search_type: str = "web_search",
        analysis_types: list = None,
        output_format: str = "structured_search_results",
        include_sources: bool = True,
        max_results: int = 10
    ) -> str:
        """
        Specialized web search analysis prompt for Hunt application
        
        Optimized for transforming user queries into enhanced web search requests
        with specific analysis types and structured output requirements.
        
        Keywords: hunt, web-search, analysis, structured-results, enhancement
        Category: hunt
        """
        
        if analysis_types is None:
            analysis_types = ['product_analysis']
        
        # Map analysis types to specific instructions
        analysis_instructions = {
            'product_analysis': 'Focus on product features, specifications, pricing, and comparisons',
            'market_research': 'Analyze market trends, competitors, and industry insights',
            'price_comparison': 'Compare prices across multiple retailers and platforms',
            'review_analysis': 'Aggregate and analyze user reviews and ratings',
            'technical_specs': 'Detailed technical specifications and compatibility information',
            'availability_check': 'Current availability, stock status, and delivery options'
        }
        
        analysis_focus = []
        for analysis_type in analysis_types:
            if analysis_type in analysis_instructions:
                analysis_focus.append(f"- **{analysis_type.replace('_', ' ').title()}**: {analysis_instructions[analysis_type]}")
        
        analysis_focus_text = "\n".join(analysis_focus) if analysis_focus else "- **General Analysis**: Comprehensive information gathering and analysis"
        
        search_approach = {
            "web_search": "systematic web search using multiple search engines and sources",
            "web_crawl": "targeted crawling of specific websites and databases",
            "web_automation": "automated data extraction from e-commerce and review platforms"
        }.get(search_type, "web search")
        
        return f"""You are an expert web research analyst. Transform the user's query into an enhanced search and analysis request.

## USER QUERY TO ENHANCE:
"{query}"

## SEARCH ENHANCEMENT STRATEGY:
Transform "{query}" into a comprehensive {search_approach} that provides maximum value and actionable insights.

## ANALYSIS REQUIREMENTS:
{analysis_focus_text}

## SEARCH EXECUTION PLAN:
1. **Query Expansion**: Identify related terms, synonyms, and variations
2. **Source Diversification**: Search across multiple platforms and databases
3. **Data Validation**: Cross-reference information from different sources
4. **Content Analysis**: Extract key insights and organize findings
5. **Result Synthesis**: Compile comprehensive, structured results

## OUTPUT SPECIFICATIONS:
- **Format**: {output_format}
- **Maximum Results**: {max_results} high-quality results
- **Source Inclusion**: {'Include source citations and links' if include_sources else 'Focus on content without detailed sources'}
- **Structure**: Organized, scannable, and actionable format
- **Quality**: Verified, current, and relevant information only

## ENHANCED SEARCH OBJECTIVES:
For the query "{query}", provide:
- **Comprehensive Coverage**: All relevant aspects and variations
- **Competitive Intelligence**: Compare options, alternatives, and market position
- **User-Centric Insights**: Information that helps with decision-making
- **Actionable Data**: Pricing, availability, specifications, and recommendations
- **Current Information**: Up-to-date market conditions and product status

Execute this enhanced search strategy to transform the simple query "{query}" into comprehensive, actionable intelligence."""

    print("Hunt application prompts registered successfully")