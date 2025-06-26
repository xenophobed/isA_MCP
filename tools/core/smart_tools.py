#!/usr/bin/env python
"""
Smart Tools for MCP Server
Tool metadata extraction and dynamic loading system
"""
import json
import sqlite3
import re
from datetime import datetime
from typing import Dict, List
from isa_model.inference import AIFactory

from core.logging import get_logger

logger = get_logger(__name__)

def extract_tool_info_from_docstring(docstring: str) -> Dict[str, any]:  # type: ignore
    """Extract tool information from docstring"""
    if not docstring:
        return {"description": "", "keywords": [], "category": "general"}
    
    lines = docstring.strip().split('\n')
    description_lines = []
    keywords = []
    category = "general"
    
    in_description = True
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("Keywords:"):
            in_description = False
            # Extract keywords
            keywords_text = line.replace("Keywords:", "").strip()
            keywords = [kw.strip() for kw in keywords_text.split(',')]
        elif line.startswith("Category:"):
            category = line.replace("Category:", "").strip()
        elif in_description:
            description_lines.append(line)
    
    description = " ".join(description_lines)
    return {
        "description": description,
        "keywords": keywords,
        "category": category
    }

async def get_all_tool_info() -> Dict[str, Dict]:
    """Get all tool information"""
    from mcp.server.fastmcp import FastMCP
    
    # Create temporary MCP server to get tool information
    temp_mcp = FastMCP("temp", stateless_http=True)
    
    # Import and register all tools
    from tools.weather_tools import register_weather_tools
    from tools.memory_tools import register_memory_tools
    from tools.image_gen_tools import register_image_gen_tools
    from tools.shopify_tools import register_realistic_shopify_tools
    from tools.admin_tools import register_admin_tools
    from tools.client_interaction_tools import register_client_interaction_tools
    from tools.event_sourcing_tools import register_event_sourcing_tools
    from tools.autonomous_tools import register_autonomous_tools
    from tools.web_tools import register_web_tools
    
    # Register all tools
    register_weather_tools(temp_mcp)
    register_memory_tools(temp_mcp)
    register_image_gen_tools(temp_mcp)
    register_realistic_shopify_tools(temp_mcp)
    register_admin_tools(temp_mcp)
    register_client_interaction_tools(temp_mcp)
    register_event_sourcing_tools(temp_mcp)
    register_web_tools(temp_mcp)
    register_autonomous_tools(temp_mcp)
    
    # Get tool list
    tools = await temp_mcp.list_tools()  # type: ignore
    
    tool_info = {}
    for tool in tools:
        # Get tool information from tool
        tool_name = tool.name
        description = tool.description or f"Tool: {tool_name}"
        
        # Categorize based on tool name
        if "weather" in tool_name:
            category = "weather"
            keywords = ["weather", "temperature", "forecast", "climate"]
        elif "image" in tool_name or "generate" in tool_name:
            category = "image" 
            keywords = ["image", "generate", "picture", "visual", "art"]
        elif "remember" in tool_name or "recall" in tool_name or "memory" in tool_name:
            category = "memory"
            keywords = ["memory", "remember", "store", "recall"]
        elif "shopify" in tool_name or "product" in tool_name or "order" in tool_name:
            category = "shopify"
            keywords = ["shopify", "store", "product", "order", "ecommerce"]
        elif "admin" in tool_name or "system" in tool_name:
            category = "admin"
            keywords = ["admin", "system", "manage", "configuration"]
        elif "client" in tool_name or "interaction" in tool_name:
            category = "client"
            keywords = ["client", "interaction", "communication"]
        elif "event" in tool_name or "sourcing" in tool_name:
            category = "event"
            keywords = ["event", "sourcing", "history", "log"]
        elif "web" in tool_name or "browser" in tool_name:
            category = "web"
            keywords = ["web", "browser", "automation", "scrape"]
        else:
            category = "general"
            keywords = [tool_name]
        
        tool_info[tool_name] = {
            "description": description,
            "keywords": keywords,
            "category": category
        }
    
    return tool_info

async def get_tool_categories() -> Dict[str, List[str]]:
    """Get tool categories"""
    tool_info = await get_all_tool_info()
    categories = {}
    
    for tool_name, info in tool_info.items():
        category = info.get("category", "general")
        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)
    
    return categories