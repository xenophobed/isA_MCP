#!/usr/bin/env python
"""
Lifestyle & Personal 🌟 Category Prompts for Omni MCP Server
Personal development and lifestyle optimization guidance
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_lifestyle_personal_prompts(mcp):
    """Register Lifestyle & Personal 🌟 category prompts with the MCP server"""
    
    @mcp.prompt("productivity_guide_prompt")
    async def productivity_guide_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive productivity guide creation
        
        This prompt guides creation of practical productivity systems with
        time management, efficiency optimization, and goal achievement strategies.
        
        Args:
            subject: The productivity topic or area to optimize
            depth: Guide depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: productivity, efficiency, time management, optimization, goals, systems
        Category: lifestyle_personal
        """
        
        prompt_template = f"""
# Productivity Expert with Personal Development Expertise

## Productivity Guide Request
**Topic**: "{subject}"
**Depth**: {depth} productivity guide
**Content Type**: Productivity and personal optimization guide

## Context & Requirements
- **Target Audience**: Professionals and individuals seeking improved productivity and life optimization
- **Content Purpose**: Practical systems and strategies for enhanced efficiency and goal achievement
- **Research Requirement**: Productivity research, behavioral science, and proven methodologies
- **Quality Standard**: Evidence-based productivity guidance with measurable improvement strategies

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Productivity assessment and current state analysis
- Evidence-based productivity principles and methodologies
- Practical implementation strategies and tools
- Time management and priority optimization techniques
- Goal setting and achievement frameworks
- Habit formation and behavior change guidance
- Technology and tools recommendations
- {depth} level guide: {{"shallow" = "essential productivity techniques and quick wins", "deep" = "comprehensive productivity system with advanced optimization strategies"}}
- Progress measurement and continuous improvement methods

## Productivity Framework Areas
- Time management and scheduling optimization
- Task prioritization and decision-making
- Focus and attention management
- Energy and motivation optimization
- Workflow and process improvement
- Work-life integration and balance

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a practical productivity guide that delivers measurable improvement in efficiency and goal achievement.
"""
        
        return prompt_template.strip()

    logger.info("Lifestyle & Personal 🌟 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_lifestyle_personal_prompts(mcp)