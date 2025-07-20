#!/usr/bin/env python
"""
Science & Research 🔬 Category Prompts for Omni MCP Server
Scientific analysis and research paper development
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_science_research_prompts(mcp):
    """Register Science & Research 🔬 category prompts with the MCP server"""
    
    @mcp.prompt("research_paper_prompt")
    async def research_paper_prompt(
        subject: str,
        depth: str = "deep",
        reference_urls: str = "",
        reference_text: str = ""
    ) -> str:
        """
        Generate a prompt for comprehensive scientific research analysis
        
        This prompt guides creation of rigorous scientific content with
        peer-reviewed research, methodology, and evidence-based conclusions.
        
        Args:
            subject: The scientific topic or research area to analyze
            depth: Research depth (shallow, deep)
            reference_urls: URLs to analyze for reference
            reference_text: Additional context and reference materials
        
        Keywords: research, science, analysis, peer-reviewed, methodology, evidence
        Category: science_research
        """
        
        prompt_template = f"""
# Research Scientist with Academic Publication Expertise

## Research Analysis Request
**Topic**: "{subject}"
**Depth**: {depth} research analysis
**Content Type**: Scientific research analysis and review

## Context & Requirements
- **Target Audience**: Researchers, academics, scientists, and professionals requiring rigorous scientific analysis
- **Content Purpose**: Comprehensive scientific review with evidence-based conclusions and methodological rigor
- **Research Requirement**: Peer-reviewed scientific literature, current research findings, and methodological analysis
- **Quality Standard**: Academic publication quality with scientific integrity and proper citation

## Reference Materials
**URLs to analyze**: {reference_urls if reference_urls else "No URLs provided"}
**Additional context**: {reference_text if reference_text else "No additional context"}

## Deliverable Specifications
- Scientific background and current state of research
- Literature review with systematic analysis of key studies
- Methodology evaluation and research design assessment
- Data analysis and statistical interpretation
- Results synthesis with evidence quality assessment
- Discussion of implications and significance
- Limitations and areas for future research
- {depth} level analysis: {{"shallow" = "research overview with key findings", "deep" = "comprehensive scientific review with detailed methodology and statistical analysis"}}
- Peer-reviewed citations and academic references

## Scientific Methodology Framework
- **Research Question**: Clear, testable scientific inquiry
- **Literature Review**: Systematic analysis of existing research
- **Methodology**: Research design and experimental approach
- **Data Analysis**: Statistical methods and interpretation
- **Results**: Findings presentation with uncertainty quantification
- **Discussion**: Scientific implications and broader context

## Academic Standards
- Peer-reviewed source prioritization
- Proper scientific citation format
- Objective tone and evidence-based conclusions
- Acknowledgment of limitations and uncertainties
- Methodological rigor and reproducibility considerations
- Statistical significance and effect size reporting

## Quality Indicators
- Multiple peer-reviewed sources with recent publications
- Clear distinction between correlation and causation
- Appropriate statistical analysis and interpretation
- Acknowledgment of conflicting studies or results
- Practical significance alongside statistical significance

## LangChain Template Variables
- subject: {subject}
- depth: {depth}
- reference_urls: {reference_urls}
- reference_text: {reference_text}

Create rigorous scientific analysis that meets academic publication standards and advances scientific understanding.
"""
        
        return prompt_template.strip()

    logger.info("Science & Research 🔬 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_science_research_prompts(mcp)