from typing import List, Dict, Any
from app.services.agent.tools.tools_manager import tools_manager
import logging
from tavily import TavilyClient
import os

logger = logging.getLogger(__name__)

def web_search_error_handler(state):
    """Handle web search tool errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Web search error: {error}. Please try again later.",
            "type": "error"
        }]
    }

@tools_manager.register_tool(error_handler=web_search_error_handler)
def web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Perform web search using Tavily API.
    
    @semantic:
        concept: web-search
        domain: search-service
        type: real-time
    
    @functional:
        operation: search
        input: query:string,max_results:integer
        output: search_results:list
    
    @context:
        usage: information-query
        prereq: tavily_api_key
        constraint: api_dependent,query_required
    """
    try:
        # Initialize Tavily client
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
            
        client = TavilyClient(api_key=tavily_api_key)
        
        # Perform search
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"
        )
        
        # Return results
        return response.get("results", [])
        
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        raise
