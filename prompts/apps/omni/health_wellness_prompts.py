#!/usr/bin/env python
"""
Health & Wellness ⚕️ Category Prompts for Omni MCP Server
Health and wellness guidance and educational content development
"""

from core.logging import get_logger

logger = get_logger(__name__)


def register_health_wellness_prompts(mcp):
    """Register Health & Wellness ⚕️ category prompts with the MCP server"""

    @mcp.prompt("wellness_guide_prompt")
    async def wellness_guide_prompt(
        subject: str = "", depth: str = "deep", reference_urls: str = "", reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive wellness guide creation

        This prompt guides creation of evidence-based wellness content with
        practical guidance for health improvement and lifestyle optimization.

        Args:
            subject: The wellness topic or health area to address
            depth: Guide depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials

        Keywords: wellness, health, guide, lifestyle, prevention, evidence-based
        Category: health_wellness
        """

        prompt_template = f"""
# Wellness Specialist with Evidence-Based Health Expertise

## Wellness Guide Request
**Topic**: "{subject}"
**Depth**: {depth} wellness guide
**Content Type**: Health and wellness guide

## Context & Requirements
- **Target Audience**: Individuals seeking evidence-based wellness guidance and health improvement
- **Content Purpose**: Practical, actionable wellness advice based on current health science
- **Research Requirement**: Peer-reviewed health research, medical guidelines, and expert recommendations
- **Quality Standard**: Evidence-based wellness content with safety considerations and professional disclaimer

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Wellness overview with health benefits and scientific foundation
- Evidence-based recommendations with research citations
- Practical implementation strategies and action steps
- Safety considerations and potential contraindications
- Lifestyle integration and habit formation guidance
- Progress tracking and measurement methods
- Professional consultation recommendations when appropriate
- {depth} level guide: {{"shallow" = "essential wellness practices and key recommendations", "deep" = "comprehensive wellness program with detailed implementation"}}
- Resources for further learning and professional support

## Important Health Disclaimers
- Include appropriate medical disclaimers
- Recommend professional consultation for serious health concerns
- Emphasize that content is for educational purposes only
- Acknowledge individual health variations and needs

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create an evidence-based wellness guide that promotes safe and effective health improvement.
"""

        return prompt_template.strip()

    logger.debug("Health & Wellness ⚕️ prompts registered successfully")


# For compatibility with auto-discovery
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_health_wellness_prompts(mcp)
