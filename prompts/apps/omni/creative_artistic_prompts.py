#!/usr/bin/env python
"""
Creative & Artistic 🎨 Category Prompts for Omni MCP Server
Creative writing, storytelling, and artistic content development
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_creative_artistic_prompts(mcp):
    """Register Creative & Artistic 🎨 category prompts with the MCP server"""
    
    @mcp.prompt("storytelling_prompt")
    async def storytelling_prompt(
        subject: str = "",
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for creative storytelling and narrative development
        
        This prompt guides creation of compelling narratives with
        character development, plot structure, and engaging storytelling techniques.
        
        Args:
            subject: The story topic, theme, or narrative focus
            depth: Story depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: storytelling, narrative, creative, writing, character, plot, fiction
        Category: creative_artistic
        """
        
        prompt_template = f"""
# Master Storyteller with Creative Writing Expertise

## Storytelling Request
**Topic**: "{subject}"
**Depth**: {depth} storytelling development
**Content Type**: Creative narrative and storytelling

## Context & Requirements
- **Target Audience**: Readers seeking engaging, well-crafted narratives and stories
- **Content Purpose**: Creative storytelling that captivates, entertains, and resonates emotionally
- **Creative Approach**: Narrative techniques, character development, and compelling plot structure
- **Quality Standard**: Professional-level creative writing with literary merit and emotional impact

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Story concept and thematic foundation
- Character development with compelling personalities and motivations
- Plot structure with engaging narrative arc
- Setting and world-building details
- Dialogue and voice development
- Literary techniques and stylistic elements
- Emotional resonance and reader engagement strategies
- {depth} level storytelling: {{"shallow" = "complete short story or story outline", "deep" = "comprehensive narrative with detailed character and world development"}}
- Genre conventions and creative innovations

## Storytelling Framework
- **Theme and Message**: Core ideas and emotional truth
- **Character Arc**: Growth, conflict, and transformation
- **Plot Structure**: Beginning, development, climax, and resolution
- **Setting and Atmosphere**: World-building and environmental storytelling
- **Voice and Style**: Narrative perspective and literary techniques
- **Conflict and Tension**: Internal and external challenges

## Creative Elements
- Compelling opening that hooks the reader
- Rich sensory details and vivid imagery
- Authentic dialogue and character voices
- Pacing and rhythm for optimal engagement
- Symbolic elements and deeper meaning
- Satisfying resolution with emotional impact

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create compelling storytelling that engages readers and delivers emotional resonance.
"""
        
        return prompt_template.strip()

    logger.debug("Creative & Artistic 🎨 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_creative_artistic_prompts(mcp)