#!/usr/bin/env python
"""
MCP Server with Memory Management, Weather Tools, and Dynamic Prompts
"""
import asyncio
import json
import sqlite3
import os
from datetime import datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Dict, List, Optional, Any
import random

from mcp.server.fastmcp import FastMCP

# Mock weather data
MOCK_WEATHER_DATA = {
    "beijing": {
        "temperature": 15,
        "condition": "Sunny",
        "humidity": 45,
        "wind": "5 km/h NE",
        "description": "Clear skies with pleasant temperature"
    },
    "shanghai": {
        "temperature": 22,
        "condition": "Partly Cloudy",
        "humidity": 65,
        "wind": "8 km/h SE",
        "description": "Mild weather with some clouds"
    },
    "guangzhou": {
        "temperature": 28,
        "condition": "Cloudy",
        "humidity": 75,
        "wind": "3 km/h S",
        "description": "Warm and humid with overcast skies"
    },
    "default": {
        "temperature": random.randint(10, 30),
        "condition": random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
        "humidity": random.randint(30, 80),
        "wind": f"{random.randint(2, 15)} km/h {random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])}",
        "description": "Weather conditions vary"
    }
}

def init_database():
    """Initialize database tables"""
    conn = sqlite3.connect("memory.db")
    
    # Drop existing tables to ensure correct structure
    conn.execute("DROP TABLE IF EXISTS memories")
    conn.execute("DROP TABLE IF EXISTS weather_cache")
    
    # Create memories table
    conn.execute("""
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        importance INTEGER DEFAULT 1
    )
    """)
    
    # Create weather cache table
    conn.execute("""
    CREATE TABLE weather_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        weather_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_city ON weather_cache(city)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

# Create MCP server
mcp = FastMCP("Dynamic MCP Server")

# =====================
# MCP RESOURCES
# =====================

@mcp.resource("memory://all")
async def get_all_memories() -> str:
    """Get all memories from the database"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT key, value, category, importance, created_at, updated_at 
            FROM memories ORDER BY importance DESC, created_at DESC
        """)
        memories = cursor.fetchall()
        
        if not memories:
            return json.dumps({"memories": [], "count": 0})
        
        memory_list = []
        for key, value, category, importance, created_at, updated_at in memories:
            memory_list.append({
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at
            })
        
        return json.dumps({
            "memories": memory_list,
            "count": len(memory_list),
            "retrieved_at": datetime.now().isoformat()
        })
    finally:
        conn.close()

@mcp.resource("memory://category/{category}")
async def get_memories_by_category(category: str) -> str:
    """Get memories by specific category"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT key, value, category, importance, created_at, updated_at 
            FROM memories WHERE category = ? ORDER BY importance DESC, created_at DESC
        """, (category,))
        memories = cursor.fetchall()
        
        memory_list = []
        for key, value, cat, importance, created_at, updated_at in memories:
            memory_list.append({
                "key": key,
                "value": value,
                "category": cat,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at
            })
        
        return json.dumps({
            "category": category,
            "memories": memory_list,
            "count": len(memory_list),
            "retrieved_at": datetime.now().isoformat()
        })
    finally:
        conn.close()

@mcp.resource("weather://cache")
async def get_weather_cache() -> str:
    """Get cached weather data"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT city, weather_data, created_at, updated_at 
            FROM weather_cache ORDER BY updated_at DESC
        """)
        cache_data = cursor.fetchall()
        
        cache_list = []
        for city, weather_data, created_at, updated_at in cache_data:
            cache_list.append({
                "city": city,
                "weather_data": json.loads(weather_data),
                "created_at": created_at,
                "updated_at": updated_at
            })
        
        return json.dumps({
            "weather_cache": cache_list,
            "count": len(cache_list),
            "retrieved_at": datetime.now().isoformat()
        })
    finally:
        conn.close()

# =====================
# MCP TOOLS
# =====================

@mcp.tool()
async def get_weather(city: str) -> str:
    """Get weather information for a city with mock data"""
    city_lower = city.lower()
    
    # Get weather data (mock)
    if city_lower in MOCK_WEATHER_DATA:
        weather_data = MOCK_WEATHER_DATA[city_lower].copy()
    else:
        weather_data = MOCK_WEATHER_DATA["default"].copy()
    
    # Add timestamp
    weather_data["city"] = city
    weather_data["timestamp"] = datetime.now().isoformat()
    
    # Cache the weather data
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        
        # Check if city already exists in cache
        cursor = conn.execute("SELECT id FROM weather_cache WHERE city = ?", (city,))
        existing = cursor.fetchone()
        
        if existing:
            conn.execute("""
                UPDATE weather_cache 
                SET weather_data = ?, updated_at = ? 
                WHERE city = ?
            """, (json.dumps(weather_data), now, city))
        else:
            conn.execute("""
                INSERT INTO weather_cache (city, weather_data, created_at, updated_at) 
                VALUES (?, ?, ?, ?)
            """, (city, json.dumps(weather_data), now, now))
        
        conn.commit()
    finally:
        conn.close()
    
    return json.dumps({
        "success": True,
        "city": city,
        "weather": weather_data,
        "source": "mock_api",
        "cached": True
    })

@mcp.tool()
async def save_memory(key: str, value: str, category: str = "general", importance: int = 1) -> str:
    """Save a memory to the database"""
    conn = sqlite3.connect("memory.db")
    now = datetime.now().isoformat()
    
    try:
        # Check if memory already exists
        cursor = conn.execute("SELECT id FROM memories WHERE key = ?", (key,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing memory
            conn.execute("""
                UPDATE memories 
                SET value = ?, category = ?, updated_at = ?, importance = ? 
                WHERE key = ?
            """, (value, category, now, importance, key))
            action = "updated"
        else:
            # Insert new memory
            conn.execute("""
                INSERT INTO memories (key, value, category, created_at, updated_at, importance) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, value, category, now, now, importance))
            action = "saved"
        
        conn.commit()
        
        return json.dumps({
            "success": True,
            "action": action,
            "key": key,
            "value": value,
            "category": category,
            "importance": importance,
            "timestamp": now
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "key": key
        })
    finally:
        conn.close()

@mcp.tool()
async def recall_memory(key: str) -> str:
    """Recall a specific memory by key"""
    conn = sqlite3.connect("memory.db")
    
    try:
        cursor = conn.execute("""
            SELECT value, category, created_at, importance, updated_at 
            FROM memories WHERE key = ? ORDER BY importance DESC LIMIT 1
        """, (key,))
        result = cursor.fetchone()
        
        if result:
            value, category, created_at, importance, updated_at = result
            return json.dumps({
                "success": True,
                "found": True,
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at
            })
        else:
            return json.dumps({
                "success": True,
                "found": False,
                "key": key,
                "message": f"No memory found for key '{key}'"
            })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "key": key
        })
    finally:
        conn.close()

@mcp.tool()
async def search_memories(category: str = "", importance_min: int = 1, limit: int = 10) -> str:
    """Search memories with optional filters"""
    conn = sqlite3.connect("memory.db")
    
    try:
        if category:
            cursor = conn.execute("""
                SELECT key, value, category, importance, created_at, updated_at 
                FROM memories 
                WHERE category = ? AND importance >= ? 
                ORDER BY importance DESC, created_at DESC 
                LIMIT ?
            """, (category, importance_min, limit))
        else:
            cursor = conn.execute("""
                SELECT key, value, category, importance, created_at, updated_at 
                FROM memories 
                WHERE importance >= ? 
                ORDER BY importance DESC, created_at DESC 
                LIMIT ?
            """, (importance_min, limit))
        
        results = cursor.fetchall()
        
        memories = []
        for key, value, cat, importance, created_at, updated_at in results:
            memories.append({
                "key": key,
                "value": value,
                "category": cat,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at
            })
        
        return json.dumps({
            "success": True,
            "memories": memories,
            "count": len(memories),
            "filters": {
                "category": category,
                "importance_min": importance_min,
                "limit": limit
            }
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
    finally:
        conn.close()

# =====================
# MCP PROMPTS
# =====================

@mcp.prompt()
def weather_assistant_prompt(user_query: str, city: str = "") -> str:
    """Dynamic prompt for weather-related queries"""
    return f"""You are an intelligent weather assistant with access to weather data and memory capabilities.

Current User Query: {user_query}
Target City: {city}

Your capabilities:
1. **Weather Tools**: Use get_weather(city) to fetch current weather information
2. **Memory Tools**: 
   - save_memory(key, value, category, importance) to store information
   - recall_memory(key) to retrieve stored information
   - search_memories(category, importance_min, limit) to find relevant memories
3. **Resources**: Access memory://all and weather://cache for historical data

**Workflow for Weather Queries:**
1. First, check if you have recent weather memory for the requested city
2. If not found or outdated, call get_weather(city) to get current data
3. Save the weather information to memory with category="weather" and appropriate importance
4. Provide a natural, conversational response about the weather
5. If user asks follow-up questions, use memory to maintain context

**Memory Strategy:**
- Weather data: category="weather", importance=2-3
- User preferences: category="user_preferences", importance=3-4
- Conversation context: category="conversation", importance=1-2

**Response Style:**
- Be conversational and helpful
- Include relevant details but don't overwhelm
- Mention if data is cached or freshly retrieved
- Offer additional information if appropriate

Remember: You have access to MCP resources and tools - use them dynamically based on the user's needs."""

@mcp.prompt()
def general_assistant_prompt(user_query: str, context: str = "") -> str:
    """General purpose assistant prompt with memory integration"""
    return f"""You are an intelligent assistant with persistent memory capabilities.

Current User Query: {user_query}
Additional Context: {context}

**Your Architecture:**
- You operate through MCP (Model Context Protocol) with dynamic tool access
- All your capabilities come from MCP tools and resources - nothing is hardcoded
- You can access and store memories, fetch external data, and maintain conversation context

**Available MCP Components:**
1. **Tools**: Dynamic tool calling based on user needs
   - Memory management (save_memory, recall_memory, search_memories)
   - Weather information (get_weather)
   - Any other tools available in the MCP server

2. **Resources**: Access to structured data
   - memory://all - Complete memory database
   - memory://category/{{category}} - Category-specific memories
   - weather://cache - Cached weather data

3. **Prompts**: Context-aware prompt templates
   - weather_assistant_prompt - For weather-related queries
   - general_assistant_prompt - For general assistance

**Operational Principles:**
1. **Dynamic Discovery**: Always check what tools and resources are available
2. **Memory First**: Check existing memories before making new requests
3. **Context Preservation**: Save important information for future reference
4. **Intelligent Routing**: Use appropriate tools based on query type
5. **Conversational Flow**: Maintain natural interaction while leveraging capabilities

**Response Guidelines:**
- Be helpful and conversational
- Explain your reasoning when using tools
- Save important information to memory
- Reference previous context when relevant
- Adapt your approach based on available MCP components

You are not just an AI - you are an AI with a persistent, searchable memory and dynamic tool access through MCP."""

@mcp.prompt()
def memory_management_prompt(operation: str, context: str = "") -> str:
    """Specialized prompt for memory operations"""
    return f"""You are a memory management specialist operating through MCP.

Current Operation: {operation}
Context: {context}

**Memory Categories:**
- **weather**: Weather information and forecasts
- **user_preferences**: User's stated preferences and settings
- **conversation**: Important conversation context and history
- **facts**: General facts and information
- **tasks**: User tasks and reminders
- **general**: Miscellaneous information

**Importance Levels:**
- **1**: Low importance, temporary information
- **2**: Medium importance, useful context
- **3**: High importance, key information
- **4**: Very high importance, critical user data
- **5**: Maximum importance, essential information

**Memory Operations:**
1. **Storage**: Choose appropriate category and importance level
2. **Retrieval**: Search by key, category, or content similarity
3. **Organization**: Maintain clean, searchable memory structure
4. **Maintenance**: Update or remove outdated information

**Best Practices:**
- Use descriptive, searchable keys
- Include relevant context in values
- Set appropriate importance levels
- Organize by logical categories
- Maintain memory hygiene (update/remove stale data)

Focus on creating a well-organized, easily searchable memory system that enhances the user experience."""

if __name__ == "__main__":
    print("Initializing database...")
    
    # Initialize database if it doesn't exist
    if not os.path.exists("memory.db"):
        init_database()
    
    print("Starting Dynamic MCP Server...")
    mcp.run(transport="streamable-http")