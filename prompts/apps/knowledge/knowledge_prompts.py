#!/usr/bin/env python3
"""
Knowledge Management Application Prompts - Document Analysis Enhancement Template
"""

from mcp.server.fastmcp import FastMCP

def register_knowledge_prompts(mcp: FastMCP):
    """Register knowledge management prompts for document analysis enhancement"""
    
    @mcp.prompt()
    def knowledge_analyze_prompt(
        prompt: str = "",
        file_url: str = "",
        depth: str = "comprehensive"
    ) -> str:
        """
        Knowledge document analysis prompt enhancer for user requests
        
        Transforms simple user document analysis requests into comprehensive, 
        professional knowledge extraction inquiries with proper information
        synthesis and insight generation focus.
        
        Keywords: knowledge, document-analysis, prompt-enhancement, insights, synthesis
        Category: knowledge-management
        """
        
        depth_modifiers = {
            "basic": "Focus on key information extraction and main concepts",
            "comprehensive": "Conduct thorough analysis with insights synthesis and knowledge connections", 
            "advanced": "Perform deep knowledge analysis with critical evaluation and strategic implications"
        }.get(depth.lower(), "Conduct thorough analysis with insights synthesis")
        
        return f"""Analyze the document at {file_url} based on this request: "{prompt}"

{depth_modifiers}. Please provide:

**Content Analysis**:
- Extract key information, main concepts, and important details
- Identify core themes, arguments, and conclusions
- Highlight critical insights and breakthrough points

**Knowledge Synthesis**:
- Connect related ideas and map concept relationships  
- Synthesize complex information into clear insights
- Identify patterns, trends, and underlying principles

**Contextual Understanding**:
- Explain relevance within broader context
- Assess credibility and information quality
- Note any limitations, biases, or gaps

**Practical Value**:
- Transform knowledge into actionable insights
- Provide recommendations or next steps
- Structure findings for easy reference and application

Focus on extracting maximum value from the document content while maintaining clarity and practical utility."""

    # Registration complete (debug-level event)

# Auto-registration for MCP server discovery
if __name__ != "__main__":
    # This ensures the prompts are available for import and registration
    pass