#!/usr/bin/env python
"""
News & Current Events 📰 Category Prompts for Omni MCP Server
News analysis and current events commentary development
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_news_current_events_prompts(mcp):
    """Register News & Current Events 📰 category prompts with the MCP server"""
    
    @mcp.prompt("news_analysis_prompt")
    async def news_analysis_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive news analysis and current events commentary
        
        This prompt guides creation of balanced news analysis with
        multiple perspectives, fact-checking, and contextual understanding.
        
        Args:
            subject: The news topic or current event to analyze
            depth: Analysis depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: news, analysis, current events, journalism, perspective, fact-checking
        Category: news_current_events
        """
        
        prompt_template = f"""
# News Analyst with Investigative Journalism Expertise

## News Analysis Request
**Topic**: "{subject}"
**Depth**: {depth} news analysis
**Content Type**: News analysis and current events commentary

## Context & Requirements
- **Target Audience**: Informed readers seeking balanced and comprehensive news analysis
- **Content Purpose**: Objective analysis of current events with multiple perspectives and context
- **Research Requirement**: Multiple credible news sources, fact-checking, and contextual information
- **Quality Standard**: Journalistic integrity with balanced reporting and source verification

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Event summary with key facts and timeline
- Multiple perspective analysis with stakeholder viewpoints
- Background context and historical relevance
- Impact assessment on various sectors and communities
- Source verification and fact-checking methodology
- Expert opinions and authoritative commentary
- Future implications and potential developments
- {depth} level analysis: {{"shallow" = "key facts and immediate implications", "deep" = "comprehensive analysis with historical context and expert perspectives"}}
- Balanced conclusion with acknowledged uncertainties

## Journalistic Standards
- Multiple source verification and cross-referencing
- Clear distinction between facts and analysis/opinion
- Acknowledgment of conflicting information or perspectives
- Transparent source attribution and credibility assessment
- Objective tone with balanced representation

## Analysis Framework
- Who: Key players and stakeholders involved
- What: Core facts and developments
- When: Timeline and sequence of events
- Where: Geographic and contextual location
- Why: Underlying causes and motivations
- How: Methods, processes, and mechanisms

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create balanced, well-researched news analysis that informs and provides context for current events.
"""
        
        return prompt_template.strip()

    logger.debug("News & Current Events 📰 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_news_current_events_prompts(mcp)