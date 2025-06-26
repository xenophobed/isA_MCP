#!/usr/bin/env python
"""
Memory Tools for MCP Server
Handles remember, forget, and search_memories operations with security
"""
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager

logger = get_logger(__name__)

def register_memory_tools(mcp):
    """Register all memory tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def remember(key: str, value: str, category: str = "general", importance: int = 1, user_id: str = "default") -> str:
        """Store information in long-term memory with authorization"""
        conn = sqlite3.connect("memory.db")
        try:
            now = datetime.now().isoformat()
            
            cursor = conn.execute("""
                UPDATE memories 
                SET value = ?, category = ?, importance = ?, updated_at = ?
                WHERE key = ?
            """, (value, category, importance, now, key))
            
            if cursor.rowcount == 0:
                conn.execute("""
                    INSERT INTO memories (key, value, category, importance, created_at, updated_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (key, value, category, importance, now, now, user_id))
            
            conn.commit()
            
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
                "timestamp": now
            }
            
            logger.info(f"Memory stored: {key} by {user_id}")
            return json.dumps(result)
        finally:
            conn.close()

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def forget(key: str, user_id: str = "default") -> str:
        """Remove information from memory with high security authorization"""
        conn = sqlite3.connect("memory.db")
        try:
            cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            
            success = cursor.rowcount > 0
            result = {
                "status": "success" if success else "not_found",
                "action": "forget",
                "data": {"key": key, "deleted": success},
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Memory {'deleted' if success else 'not found'}: {key} by {user_id}")
            return json.dumps(result)
        finally:
            conn.close()

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def update_memory(key: str, value: str, category: str | None = None, importance: int | None = None, user_id: str = "default") -> str:
        """Update existing memory entry with new value/metadata"""
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
        """Search through memories with security checks"""
        conn = sqlite3.connect("memory.db")
        try:
            sql = """
                SELECT key, value, category, importance, created_at, updated_at, created_by
                FROM memories 
                WHERE (key LIKE ? OR value LIKE ?) AND importance >= ?
            """
            params = [f"%{query}%", f"%{query}%", min_importance]
            
            if category and category.strip():
                sql += " AND category = ?"
                params.append(category)
            
            sql += " ORDER BY importance DESC, updated_at DESC LIMIT 10"
            
            cursor = conn.execute(sql, params)
            results = cursor.fetchall()
            
            memories = []
            for key, value, cat, importance, created_at, updated_at, created_by in results:
                memories.append({
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
        finally:
            conn.close() 