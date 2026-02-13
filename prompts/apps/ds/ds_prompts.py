#!/usr/bin/env python3
"""
Data Science Application Prompts - CSV Analysis Enhancement Template
"""

from mcp.server.fastmcp import FastMCP


def register_ds_prompts(mcp: FastMCP):
    """Register data science prompts for CSV analysis enhancement"""

    @mcp.prompt()
    def csv_analyze_prompt(
        prompt: str = "", csv_url: str = "", depth: str = "comprehensive"
    ) -> str:
        """
        CSV data analysis prompt enhancer for user requests

        Transforms simple user analysis requests into comprehensive,
        professional data analysis inquiries with proper statistical
        context and business intelligence focus.

        Keywords: csv, data-analysis, prompt-enhancement, statistics, insights
        Category: data-science
        """

        depth_modifiers = {
            "basic": "please conduct basic data exploration and key metric analysis",
            "comprehensive": "please conduct comprehensive data analysis including statistical insights and business recommendations",
            "advanced": "please conduct advanced data analysis including predictive modeling, hypothesis testing, and deep statistical analysis",
        }.get(depth.lower(), "please conduct comprehensive data analysis")

        return f"""As a professional data analyst, {depth_modifiers}.

**Data Source**: {csv_url}

**Analysis Request**: {prompt}

**Specific Requirements**:

1. **Data Quality Assessment**: Check data integrity, missing values, outliers, and data types. Provide data cleaning recommendations.

2. **Exploratory Data Analysis**: 
   - Provide descriptive statistical summaries
   - Analyze data distribution characteristics and correlations
   - Identify patterns and trends in the data

3. **Key Insights Discovery**:
   - Answer core business questions based on the data
   - Identify statistically significant findings
   - Discover anomalous patterns or opportunity areas

4. **Visualization Recommendations**: Suggest the most appropriate chart types to display findings and explain the reasoning behind your choices.

5. **Business Value**: Transform analysis results into actionable business recommendations and decision support.

6. **Methodology Transparency**: Explain the statistical methods used, underlying assumptions, and analysis limitations.

Please ensure the analysis results are statistically rigorous while maintaining business relevance and actionability. Focus on insights that directly support decision-making."""

    # Registration complete (debug-level event)


# Auto-registration for MCP server discovery
if __name__ != "__main__":
    # This ensures the prompts are available for import and registration
    pass
