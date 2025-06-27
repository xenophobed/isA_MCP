#!/usr/bin/env python
"""
Memory Tools for MCP Server
Handles remember, forget, and search_memories operations with security
"""
import json
from datetime import datetime
from typing import Dict, Any

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager
from core.supabase_client import get_supabase_client

logger = get_logger(__name__)

def register_memory_tools(mcp):
    """Register all memory tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def remember(key: str, value: str, category: str = "general", importance: int = 1, user_id: str = "default") -> str:
        """Store information in long-term memory with authorization
        
        This tool stores information persistently for later retrieval,
        with categorization and importance levels for organization.
        
        Keywords: memory, remember, store, save, information, data, persist
        Category: memory
        """
        supabase = get_supabase_client()
        try:
            success = await supabase.set_memory(key, value, category, importance, user_id)
            
            if success:
                # Return structured JSON
                result = {
                    "status": "success",
                    "action": "remember",
                    "data": {
                        "key": key,
                        "value": value,
                        "category": category,
                        "importance": importance,
                        "created_by": user_id
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Memory stored: {key} by {user_id}")
                return json.dumps(result)
            else:
                raise Exception("Failed to store memory in Supabase")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def forget(key: str, user_id: str = "default") -> str:
        """Remove information from memory with high security authorization
        
        This tool permanently deletes stored information from memory,
        requiring high-level authorization for security.
        
        Keywords: memory, forget, delete, remove, erase, clear, security
        Category: memory
        """
        supabase = get_supabase_client()
        try:
            success = await supabase.delete_memory(key)
            
            result = {
                "status": "success" if success else "not_found",
                "action": "forget",
                "data": {"key": key, "deleted": success},
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Memory {'deleted' if success else 'not found'}: {key} by {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def update_memory(key: str, value: str, category: str | None = None, importance: int | None = None, user_id: str = "default") -> str:
        """Update existing memory entry with new value/metadata
        
        This tool modifies existing memory entries with new values
        or metadata while preserving the original key.
        
        Keywords: memory, update, modify, change, edit, metadata
        Category: memory
        """
        conn = sqlite3.connect("memory.db")
        try:
            # First check if the key exists
            cursor = conn.execute("SELECT key, value, category, importance FROM memories WHERE key = ?", (key,))
            existing = cursor.fetchone()
            
            if not existing:
                result = {
                    "status": "not_found",
                    "action": "update_memory",
                    "data": {"key": key, "message": "Memory entry not found"},
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"Memory update failed - not found: {key} by {user_id}")
                return json.dumps(result)
            
            # Use existing values if not provided
            old_key, old_value, old_category, old_importance = existing
            update_category = category if category is not None else old_category
            update_importance = importance if importance is not None else old_importance
            now = datetime.now().isoformat()
            
            # Update the memory
            conn.execute("""
                UPDATE memories 
                SET value = ?, category = ?, importance = ?, updated_at = ?
                WHERE key = ?
            """, (value, update_category, update_importance, now, key))
            conn.commit()
            
            result = {
                "status": "success",
                "action": "update_memory",
                "data": {
                    "key": key,
                    "old_value": old_value,
                    "new_value": value,
                    "category": update_category,
                    "importance": update_importance,
                    "updated_by": user_id
                },
                "timestamp": now
            }
            
            logger.info(f"Memory updated: {key} by {user_id}")
            return json.dumps(result)
        finally:
            conn.close()

    @mcp.tool()
    @security_manager.security_check
    async def search_memories(query: str, category: str = "", min_importance: int = 1, user_id: str = "default") -> str:
        """Search through memories with security checks
        
        This tool searches through stored memories using keywords,
        with filtering by category and importance level.
        
        Keywords: memory, search, find, query, lookup, retrieve, filter
        Category: memory
        """
        supabase = get_supabase_client()
        try:
            # Use Supabase search with filtering
            search_category = category if category and category.strip() else None
            memories_data = await supabase.search_memories(query, search_category, limit=10)
            
            # Filter by minimum importance
            filtered_memories = [
                mem for mem in memories_data 
                if mem.get('importance', 1) >= min_importance
            ]
            
            memories = []
            for mem in filtered_memories:
                memories.append({
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
                "action": "search_memories",
                "data": {
                    "query": query,
                    "results": memories,
                    "count": len(memories)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Memory search: '{query}' found {len(memories)} results")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            raise 