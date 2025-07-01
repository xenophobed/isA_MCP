#!/usr/bin/env python
"""
Memory Resources for MCP Server
Provides access to memory data as resources
"""
import json
from datetime import datetime

from core.logging import get_logger
from core.monitoring import monitor_manager
from core.supabase_client import get_supabase_client

logger = get_logger(__name__)

def register_memory_resources(mcp):
    """Register all memory resources with the MCP server"""
    
    @mcp.resource("memory://all")
    async def get_all_memories() -> str:
        """Get all memories with monitoring"""
        monitor_manager.log_request("get_all_memories", "system", True, 0.1, "LOW")
        
        supabase = get_supabase_client()
        try:
            memories_data = await supabase.get_all_memories()
            
            memory_list = []
            for mem in memories_data:
                memory_list.append({
                    "key": mem.get('key'),
                    "value": mem.get('value'),
                    "category": mem.get('category'),
                    "importance": mem.get('importance'),
                    "created_at": mem.get('created_at'),
                    "updated_at": mem.get('updated_at'),
                    "created_by": mem.get('created_by')
                })
            
            result = {
                "status": "success",
                "data": {"memories": memory_list, "count": len(memory_list)},
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"All memories resource accessed: {len(memory_list)} items")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            raise

    @mcp.resource("memory://category/{category}")
    async def get_memories_by_category(category: str) -> str:
        """Get memories filtered by category"""
        supabase = get_supabase_client()
        try:
            memories_data = await supabase.search_memories("", category, limit=100)
            
            memory_list = []
            for mem in memories_data:
                memory_list.append({
                    "key": mem.get('key'),
                    "value": mem.get('value'),
                    "category": mem.get('category'),
                    "importance": mem.get('importance'),
                    "created_at": mem.get('created_at'),
                    "updated_at": mem.get('updated_at'),
                    "created_by": mem.get('created_by')
                })
            
            result = {
                "status": "success",
                "data": {
                    "category": category,
                    "memories": memory_list, 
                    "count": len(memory_list)
                },
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Category '{category}' memories resource accessed: {len(memory_list)} items")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting memories by category: {e}")
            raise

    @mcp.resource("weather://cache")
    async def get_weather_cache() -> str:
        """Get cached weather data"""
        supabase = get_supabase_client()
        try:
            cache_entries = await supabase.get_weather_cache()
            
            cache_list = []
            for entry in cache_entries:
                try:
                    weather_data = entry.get('weather_data')
                    if isinstance(weather_data, str):
                        weather_info = json.loads(weather_data)
                    else:
                        weather_info = weather_data
                    
                    cache_list.append({
                        "city": entry.get('city'),
                        "weather": weather_info,
                        "cached_at": entry.get('updated_at')
                    })
                except json.JSONDecodeError:
                    cache_list.append({
                        "city": entry.get('city'),
                        "weather": entry.get('weather_data'),
                        "cached_at": entry.get('updated_at'),
                        "error": "Invalid JSON data"
                    })
            
            result = {
                "status": "success",
                "data": {"cache_entries": cache_list, "count": len(cache_list)},
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Weather cache resource accessed: {len(cache_list)} entries")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting weather cache: {e}")
            raise

    logger.info("Memory resources registered successfully") 