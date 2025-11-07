#!/usr/bin/env python
"""
RAG-specific prompts for intelligent retrieval and summarization
These prompts guide agents on how to use RAG tools and resources effectively
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_rag_prompts(mcp):
    """Register RAG-specific prompts with the MCP server"""
    
    @mcp.prompt("intelligent_rag_search_prompt")
    async def intelligent_rag_search_prompt(
        query: str = "",
        available_tools: str = "",
        available_resources: str = "",
        context: str = ""
    ) -> str:
        """
        Generate a prompt for intelligent RAG search and retrieval workflow
        
        This prompt guides agents on how to effectively use RAG tools and resources
        to search, retrieve, and synthesize information from document collections.
        
        Args:
            query: The user's search query or information need
            available_tools: List of available RAG tools
            available_resources: List of available RAG resources
            context: Additional context about the search requirements
        
        Keywords: rag, search, retrieval, intelligent, workflow, strategy, tools, resources
        Category: rag
        """
        
        prompt_template = f"""
# Intelligent RAG Search and Retrieval Strategy

## User Query: "{query}"

## Your Mission
You are an intelligent RAG (Retrieval-Augmented Generation) assistant. Your task is to help the user find relevant information by strategically using the available tools and resources.

## Available Tools
{available_tools if available_tools else "Use the discovery system to find RAG tools"}

## Available Resources  
{available_resources if available_resources else "Use the discovery system to find RAG resources"}

## Intelligent Search Workflow

### Step 1: Discovery & Planning
1. **Analyze the query**: What type of information is the user seeking?
2. **Check available resources**: Look for `rag://discover/{{query}}` or `rag://collections` to understand what collections exist
3. **Identify relevant collections**: Which collections are most likely to contain relevant information?

### Step 2: Strategic Search
1. **Start with targeted search**: If you found specific collections, search within them first
2. **Use appropriate search type**:
   - **Vector search** (`search_type='vector'`) for conceptual/semantic queries
   - **Text search** (`search_type='text'`) for exact term matching
3. **Adjust parameters**:
   - Lower `threshold` for broader results
   - Higher `limit` for comprehensive search
   - Specific `collection` for focused search

### Step 3: Retrieval & Analysis
1. **Examine search results**: Look at document content, metadata, and relevance scores
2. **Iterative refinement**: If results aren't satisfactory, try:
   - Different search terms
   - Different collections
   - Different search types
   - Broader or narrower queries

### Step 4: Synthesis & Response
1. **Synthesize information**: Combine relevant findings from multiple documents
2. **Provide context**: Explain which collections and documents the information came from
3. **Suggest follow-up**: Recommend additional searches or collections to explore

## Best Practices

### For Semantic/Conceptual Queries:
- Use vector search first
- Try synonyms and related terms
- Search across multiple collections

### For Factual/Specific Queries:
- Use text search first
- Include exact terms and phrases
- Focus on specific collections if known

### For Exploratory Queries:
- Start with `rag://discover/{{query}}` to find relevant collections
- Use broad vector searches
- Explore multiple collections

## Error Handling
- If no results found, try broader terms
- If too many results, add more specific terms or use collection filtering
- If search fails, check collection existence with `list_rag_collections`

## Additional Context
{context if context else "No additional context provided"}

## Expected Output Format
1. **Search Strategy**: Explain your approach
2. **Results Summary**: Key findings from the search
3. **Source Information**: Which collections/documents provided the information
4. **Confidence Level**: How confident you are in the results
5. **Follow-up Suggestions**: Additional searches or actions recommended

Remember: Your goal is to provide comprehensive, accurate, and well-sourced information using the RAG system effectively.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("rag_collection_analysis_prompt")
    async def rag_collection_analysis_prompt(
        collection_name: str = "",
        user_query: str = "",
        analysis_type: str = "overview"
    ) -> str:
        """
        Generate a prompt for analyzing and understanding RAG collections
        
        This prompt helps agents understand collection contents, structure,
        and relevance for specific queries.
        
        Args:
            collection_name: Name of the collection to analyze
            user_query: Optional user query for context
            analysis_type: Type of analysis (overview, content, relevance)
        
        Keywords: rag, collection, analysis, overview, content, structure
        Category: rag
        """
        
        prompt_template = f"""
# RAG Collection Analysis Guide

## Collection: {collection_name}
## Analysis Type: {analysis_type}
{f"## User Query Context: {user_query}" if user_query else ""}

## Your Task
Analyze the specified RAG collection to provide insights about its content, structure, and usefulness.

## Analysis Framework

### 1. Collection Overview
- **Size**: Use `get_rag_collection_stats` to get document count and statistics
- **Content Type**: What kind of information does this collection contain?
- **Coverage**: How comprehensive is the information?

### 2. Content Analysis
- **Sample Content**: Use `search_rag_documents` with broad terms to see sample content
- **Topics Covered**: What are the main themes/topics?
- **Content Quality**: How detailed and useful is the information?

### 3. Relevance Assessment
{f"- **Query Relevance**: How well does this collection match the query '{user_query}'?" if user_query else ""}
- **Use Cases**: What types of queries would this collection be good for?
- **Limitations**: What information might be missing or incomplete?

### 4. Search Recommendations
- **Best Search Terms**: What keywords work well with this collection?
- **Search Strategy**: Should users prefer vector or text search?
- **Complementary Collections**: What other collections might be useful alongside this one?

## Analysis Steps

1. **Get Statistics**: Use `get_rag_collection_stats` for basic metrics
2. **Sample Content**: Search with general terms to see representative documents
3. **Topic Exploration**: Try different search terms to understand scope
4. **Quality Assessment**: Evaluate information depth and accuracy

## Output Format

### Collection Profile
- **Name**: {collection_name}
- **Size**: [Document count and character statistics]
- **Content Type**: [Description of what's in the collection]
- **Last Updated**: [When was content last added]

### Content Overview
- **Main Topics**: [List of primary subjects covered]
- **Content Style**: [Academic, casual, technical, etc.]
- **Information Depth**: [Surface level, detailed, comprehensive]

### Usage Recommendations
- **Best For**: [Types of queries this collection excels at]
- **Search Tips**: [Recommended search strategies]
- **Complementary Collections**: [Other collections that work well together]

{f"### Query-Specific Assessment" if user_query else ""}
{f"- **Relevance Score**: [How well this collection matches '{user_query}']" if user_query else ""}
{f"- **Expected Results**: [What kind of information you might find]" if user_query else ""}
{f"- **Search Strategy**: [Recommended approach for this specific query]" if user_query else ""}

Remember: Provide actionable insights that help users understand whether and how to use this collection effectively.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("rag_synthesis_prompt")
    async def rag_synthesis_prompt(
        search_results: str = "",
        original_query: str = "",
        sources_info: str = ""
    ) -> str:
        """
        Generate a prompt for synthesizing RAG search results into coherent responses
        
        This prompt guides agents on how to combine multiple search results
        into comprehensive, well-sourced answers.
        
        Args:
            search_results: The raw search results from RAG queries
            original_query: The user's original question or information need
            sources_info: Information about the sources and collections searched
        
        Keywords: rag, synthesis, summarization, integration, sources, analysis
        Category: rag
        """
        
        prompt_template = f"""
# RAG Results Synthesis Guide

## Original Query: "{original_query}"

## Search Results to Synthesize:
{search_results}

## Source Information:
{sources_info if sources_info else "Source information will be provided in the search results"}

## Your Task
Synthesize the RAG search results into a comprehensive, accurate, and well-sourced response to the user's query.

## Synthesis Framework

### 1. Information Assessment
- **Relevance**: How well do the results address the original query?
- **Completeness**: Do the results provide a complete answer?
- **Consistency**: Are there any contradictions between sources?
- **Reliability**: How trustworthy are the sources?

### 2. Content Organization
- **Main Points**: Identify the key information that answers the query
- **Supporting Details**: Find evidence and examples that support main points
- **Context**: Provide necessary background information
- **Gaps**: Identify what information might be missing

### 3. Source Integration
- **Attribution**: Clearly indicate which information comes from which sources
- **Cross-Reference**: Note when multiple sources support the same point
- **Conflict Resolution**: Address any contradictions between sources
- **Source Quality**: Comment on the reliability of different sources

## Synthesis Guidelines

### Structure Your Response:
1. **Direct Answer**: Start with a clear answer to the query
2. **Key Details**: Provide important supporting information
3. **Context**: Add relevant background or context
4. **Sources**: Clearly cite your sources
5. **Limitations**: Note any gaps or uncertainties

### Quality Standards:
- **Accuracy**: Only include information directly supported by the search results
- **Clarity**: Use clear, understandable language
- **Completeness**: Address all aspects of the query if possible
- **Transparency**: Be clear about what you know and don't know

### Source Attribution:
- Reference specific documents or collections
- Use phrases like "According to [source]..." or "Multiple sources indicate..."
- Distinguish between confirmed facts and single-source claims
- Note the relevance score or collection source when helpful

## Response Template

### Answer Summary
[Provide a direct, concise answer to the original query]

### Detailed Information
[Expand on the answer with key details and supporting information]

### Evidence and Sources
- **Source 1**: [Document/Collection name] - [Key information from this source]
- **Source 2**: [Document/Collection name] - [Key information from this source]
- [Continue for all relevant sources]

### Additional Context
[Provide relevant background or context that helps understand the answer]

### Confidence and Limitations
- **Confidence Level**: [High/Medium/Low] - [Brief explanation]
- **Information Gaps**: [What information might be missing or unclear]
- **Suggested Follow-up**: [Additional searches or questions that might be helpful]

## Quality Checklist
- ✅ Directly answers the original query
- ✅ Properly attributes information to sources
- ✅ Identifies any contradictions or uncertainties
- ✅ Provides appropriate level of detail
- ✅ Suggests follow-up actions if relevant

Remember: Your goal is to transform raw search results into a helpful, accurate, and well-sourced response that fully addresses the user's information need.
"""
        
        return prompt_template.strip()

    logger.info("RAG prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(register_rag_prompts(mcp))
        else:
            loop.run_until_complete(register_rag_prompts(mcp))
    except:
        asyncio.run(register_rag_prompts(mcp))