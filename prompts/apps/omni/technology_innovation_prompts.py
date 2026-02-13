#!/usr/bin/env python
"""
Technology & Innovation 💻 Category Prompts for Omni MCP Server
Technical analysis and implementation guidance for technology solutions
"""

from core.logging import get_logger

logger = get_logger(__name__)


def register_technology_innovation_prompts(mcp):
    """Register Technology & Innovation 💻 category prompts with the MCP server"""

    @mcp.prompt("tech_review_prompt")
    async def tech_review_prompt(
        subject: str = "", depth: str = "deep", reference_urls: str = "", reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive technology review and analysis

        This prompt guides creation of detailed technology assessments with
        technical evaluation and strategic recommendations.

        Args:
            subject: The technology or technical solution to review
            depth: Review depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials

        Keywords: technology, review, analysis, evaluation, technical, assessment
        Category: technology_innovation
        """

        prompt_template = f"""
# Technology Analyst with Technical Expertise

## Technology Review Request
**Topic**: "{subject}"
**Depth**: {depth} technology review
**Content Type**: Technical review and analysis

## Context & Requirements
- **Target Audience**: Technical professionals, decision-makers, and technology evaluators
- **Content Purpose**: Comprehensive technology assessment for adoption and strategic decisions
- **Research Requirement**: Technical specifications, performance data, and industry comparisons
- **Quality Standard**: Professional technical analysis with objective evaluation

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Technology overview with key features and capabilities
- Technical architecture and implementation requirements
- Performance analysis with benchmarks and metrics
- Comparative analysis with alternative solutions
- Strengths and limitations assessment
- Use case scenarios and application suitability
- Cost-benefit analysis and ROI considerations
- {depth} level review: {{"shallow" = "overview and key features assessment", "deep" = "comprehensive technical evaluation with detailed analysis"}}
- Implementation recommendations and next steps

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a professional technology review that supports informed decision-making.
"""

        return prompt_template.strip()

    @mcp.prompt("implementation_guide_prompt")
    async def implementation_guide_prompt(
        subject: str = "", depth: str = "deep", reference_urls: str = "", reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for detailed implementation guidance and best practices

        This prompt guides creation of comprehensive implementation guides with
        practical steps, best practices, and troubleshooting guidance.

        Args:
            subject: The technology or solution to implement
            depth: Implementation depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials

        Keywords: implementation, guide, best practices, deployment, technical, setup
        Category: technology_innovation
        """

        prompt_template = f"""
# Implementation Specialist with Technical Architecture Expertise

## Implementation Guide Request
**Topic**: "{subject}"
**Depth**: {depth} implementation guide
**Content Type**: Technical implementation guide

## Context & Requirements
- **Target Audience**: Technical teams, developers, and implementation professionals
- **Content Purpose**: Practical guidance for successful technology implementation
- **Research Requirement**: Best practices, technical documentation, and real-world case studies
- **Quality Standard**: Production-ready implementation guidance with proven methodologies

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Implementation overview with scope and objectives
- Prerequisites and system requirements
- Step-by-step implementation procedures
- Configuration and setup instructions
- Best practices and recommended approaches
- Security considerations and compliance requirements
- Testing and validation procedures
- {depth} level guide: {{"shallow" = "basic setup and key implementation steps", "deep" = "comprehensive implementation with advanced configuration and optimization"}}
- Troubleshooting guide and common issues resolution
- Maintenance and ongoing management procedures

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create a practical implementation guide that ensures successful deployment.
"""

        return prompt_template.strip()

    logger.debug("Technology & Innovation 💻 prompts registered successfully")


# For compatibility with auto-discovery
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_technology_innovation_prompts(mcp)
