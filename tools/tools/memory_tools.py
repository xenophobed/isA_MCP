#!/usr/bin/env python
"""
Memory management tools for MCP Server
"""
import json
from core.security import security_check, require_authorization, SecurityLevel
from resources.database.sqlite.models import DatabaseManager, MemoryModel

# Initialize database components
db_manager = DatabaseManager()
memory_model = MemoryModel(db_manager)

@security_check
@require_authorization(SecurityLevel.MEDIUM)
async def remember(key: str, value: str, category: str = "general", importance: int = 1, user_id: str = "default") -> str:
    """Store information in long-term memory with authorization"""
    result = memory_model.create_or_update(key, value, category, importance, user_id)
    return json.dumps(result)

@security_check
@require_authorization(SecurityLevel.HIGH)
async def forget(key: str, user_id: str = "default") -> str:
    """Remove information from memory with high security authorization"""
    result = memory_model.delete(key)
    return json.dumps(result)

@security_check
async def search_memories(query: str, category: str = None, min_importance: int = 1, user_id: str = "default") -> str:
    """Search through memories with security checks"""
    result = memory_model.search(query, category, min_importance)
    return json.dumps(result)

async def get_all_memories() -> str:
    """Get all memories with monitoring"""
    from core.monitoring import monitor_manager
    monitor_manager.log_request("get_all_memories", "system", True, 0.1, SecurityLevel.LOW)
    
    result = memory_model.get_all()
    return json.dumps(result)