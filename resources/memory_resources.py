#!/usr/bin/env python
"""
Memory Resources for MCP Server
Provides access to memory data as resources
"""
import json
import sqlite3
from datetime import datetime

from core.logging import get_logger
from core.monitoring import monitor_manager

logger = get_logger(__name__)

def register_memory_resources(mcp):
    """Register all memory resources with the MCP server"""
    
    @mcp.resource("memory://all")
    async def get_all_memories() -> str:
        """Get all memories with monitoring"""
        monitor_manager.log_request("get_all_memories", "system", True, 0.1, "LOW")
        
        conn = sqlite3.connect("memory.db")
        try:
            cursor = conn.execute("""
                SELECT key, value, category, importance, created_at, updated_at, created_by
                FROM memories ORDER BY importance DESC, created_at DESC
            """)
            memories = cursor.fetchall()
            
            memory_list = []
            for key, value, category, importance, created_at, updated_at, created_by in memories:
                memory_list.append({
                    "key": key,
                    "value": value,
                    "category": category,
                    "importance": importance,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "created_by": created_by
                })
            
            result = {
                "status": "success",
                "data": {"memories": memory_list, "count": len(memory_list)},
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"All memories resource accessed: {len(memory_list)} items")
            return json.dumps(result)
        finally:
            conn.close()

    @mcp.resource("memory://category/{category}")
    async def get_memories_by_category(category: str) -> str:
        """Get memories filtered by category"""
        conn = sqlite3.connect("memory.db")
        try:
            cursor = conn.execute("""
                SELECT key, value, category, importance, created_at, updated_at, created_by
                FROM memories 
                WHERE category = ?
                ORDER BY importance DESC, created_at DESC
            """, (category,))
            memories = cursor.fetchall()
            
            memory_list = []
            for key, value, cat, importance, created_at, updated_at, created_by in memories:
                memory_list.append({
                    "key": key,
                    "value": value,
                    "category": cat,
                    "importance": importance,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "created_by": created_by
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
        finally:
            conn.close()

    @mcp.resource("weather://cache")
    async def get_weather_cache() -> str:
        """Get cached weather data"""
        conn = sqlite3.connect("memory.db")
        try:
            cursor = conn.execute("""
                SELECT city, weather_data, updated_at
                FROM weather_cache 
                ORDER BY updated_at DESC
            """)
            cache_entries = cursor.fetchall()
            
            cache_list = []
            for city, weather_data, updated_at in cache_entries:
                try:
                    weather_info = json.loads(weather_data)
                    cache_list.append({
                        "city": city,
                        "weather": weather_info,
                        "cached_at": updated_at
                    })
                except json.JSONDecodeError:
                    cache_list.append({
                        "city": city,
                        "weather": weather_data,
                        "cached_at": updated_at,
                        "error": "Invalid JSON data"
                    })
            
            result = {
                "status": "success",
                "data": {"cache_entries": cache_list, "count": len(cache_list)},
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Weather cache resource accessed: {len(cache_list)} entries")
            return json.dumps(result)
        finally:
            conn.close()

    logger.info("Memory resources registered successfully") 