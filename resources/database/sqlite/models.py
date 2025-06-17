#!/usr/bin/env python
"""
Database models and data access layer
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Optional, Tuple

class DatabaseManager:
    """Centralized database management"""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)

class MemoryModel:
    """Memory data access layer"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_or_update(self, key: str, value: str, category: str = "general", 
                        importance: int = 1, user_id: str = "default") -> Dict:
        """Create or update a memory entry"""
        conn = self.db_manager.get_connection()
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
            
            return {
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
        finally:
            conn.close()
    
    def delete(self, key: str) -> Dict:
        """Delete a memory entry"""
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            
            success = cursor.rowcount > 0
            return {
                "status": "success" if success else "not_found",
                "action": "forget",
                "data": {"key": key, "deleted": success},
                "timestamp": datetime.now().isoformat()
            }
        finally:
            conn.close()
    
    def search(self, query: str, category: Optional[str] = None, min_importance: int = 1) -> Dict:
        """Search memories"""
        conn = self.db_manager.get_connection()
        try:
            sql = """
                SELECT key, value, category, importance, created_at, updated_at, created_by
                FROM memories 
                WHERE (key LIKE ? OR value LIKE ?) AND importance >= ?
            """
            params = [f"%{query}%", f"%{query}%", min_importance]
            
            if category:
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
            
            return {
                "status": "success",
                "action": "search_memories",
                "data": {
                    "query": query,
                    "results": memories,
                    "count": len(memories)
                },
                "timestamp": datetime.now().isoformat()
            }
        finally:
            conn.close()
    
    def get_all(self) -> Dict:
        """Get all memories"""
        conn = self.db_manager.get_connection()
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
            
            return {
                "status": "success",
                "data": {"memories": memory_list, "count": len(memory_list)},
                "retrieved_at": datetime.now().isoformat()
            }
        finally:
            conn.close()

class WeatherCacheModel:
    """Weather cache data access layer"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_cached_weather(self, city: str) -> Optional[Tuple[str, str]]:
        """Get cached weather data if not expired"""
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.execute("""
                SELECT weather_data, updated_at 
                FROM weather_cache 
                WHERE city = ? AND datetime(updated_at) > datetime('now', '-1 hour')
            """, (city.lower(),))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def cache_weather(self, city: str, weather_data: Dict):
        """Cache weather data"""
        conn = self.db_manager.get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO weather_cache (city, weather_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (city.lower(), json.dumps(weather_data), now, now))
            conn.commit()
        finally:
            conn.close()