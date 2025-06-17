#!/usr/bin/env python
"""
Enhanced MCP Server with Dynamic Prompt Selection and Human-in-the-Loop Support
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
    conn.execute("DROP TABLE IF EXISTS prompt_usage")
    
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
    
    # Create prompt usage tracking table
    conn.execute("""
    CREATE TABLE prompt_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt_name TEXT NOT NULL,
        arguments TEXT NOT NULL,
        used_at TEXT NOT NULL,
        context TEXT
    )
    """)
    
    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weather_city ON weather_cache(city)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_usage_name ON prompt_usage(prompt_name)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

# Create MCP server
mcp = FastMCP("Enhanced Dynamic MCP Server")

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

@mcp.resource("prompts://usage")
async def get_prompt_usage_stats() -> str:
    """Get prompt usage statistics"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT prompt_name, COUNT(*) as usage_count, MAX(used_at) as last_used
            FROM prompt_usage 
            GROUP BY prompt_name 
            ORDER BY usage_count DESC
        """)
        usage_stats = cursor.fetchall()
        
        stats_list = []
        for prompt_name, usage_count, last_used in usage_stats:
            stats_list.append({
                "prompt_name": prompt_name,
                "usage_count": usage_count,
                "last_used": last_used
            })
        
        return json.dumps({
            "prompt_usage_stats": stats_list,
            "total_prompts": len(stats_list),
            "retrieved_at": datetime.now().isoformat()
        })
    finally:
        conn.close()

# =====================
# MCP TOOLS
# =====================

@mcp.tool()
async def remember(key: str, value: str, category: str = "general", importance: int = 1) -> str:
    """Store information in long-term memory"""
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        
        # Try to update existing memory
        cursor = conn.execute("""
            UPDATE memories 
            SET value = ?, category = ?, importance = ?, updated_at = ?
            WHERE key = ?
        """, (value, category, importance, now, key))
        
        if cursor.rowcount == 0:
            # Insert new memory
            conn.execute("""
                INSERT INTO memories (key, value, category, importance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now))
        
        conn.commit()
        return f"Memory stored: {key} = {value} (category: {category}, importance: {importance})"
    finally:
        conn.close()

@mcp.tool()
async def recall(key: str) -> str:
    """Retrieve specific information from memory"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT value, category, importance, created_at, updated_at 
            FROM memories WHERE key = ?
        """, (key,))
        result = cursor.fetchone()
        
        if result:
            value, category, importance, created_at, updated_at = result
            return json.dumps({
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": created_at,
                "updated_at": updated_at
            })
        else:
            return f"No memory found for key: {key}"
    finally:
        conn.close()

@mcp.tool()
async def forget(key: str) -> str:
    """Remove information from memory"""
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        if cursor.rowcount > 0:
            conn.commit()
            return f"Memory deleted: {key}"
        else:
            return f"No memory found for key: {key}"
    finally:
        conn.close()

@mcp.tool()
async def search_memories(query: str, category: str = None, min_importance: int = 1) -> str:
    """Search through memories with optional filters"""
    conn = sqlite3.connect("memory.db")
    try:
        sql = """
            SELECT key, value, category, importance, created_at, updated_at 
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
        
        if results:
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
                "query": query,
                "results": memories,
                "count": len(memories)
            })
        else:
            return f"No memories found matching: {query}"
    finally:
        conn.close()

@mcp.tool()
async def get_weather(city: str) -> str:
    """Get weather information for a city"""
    city_lower = city.lower()
    
    # Check cache first
    conn = sqlite3.connect("memory.db")
    try:
        cursor = conn.execute("""
            SELECT weather_data, updated_at 
            FROM weather_cache 
            WHERE city = ? AND datetime(updated_at) > datetime('now', '-1 hour')
        """, (city_lower,))
        cached = cursor.fetchone()
        
        if cached:
            weather_data, updated_at = cached
            result = json.loads(weather_data)
            result["cached"] = True
            result["cached_at"] = updated_at
            return json.dumps(result)
        
        # Get weather data (mock for demo)
        if city_lower in MOCK_WEATHER_DATA:
            weather_data = MOCK_WEATHER_DATA[city_lower].copy()
        else:
            weather_data = MOCK_WEATHER_DATA["default"].copy()
        
        weather_data["city"] = city
        weather_data["cached"] = False
        
        # Cache the result
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT OR REPLACE INTO weather_cache (city, weather_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (city_lower, json.dumps(weather_data), now, now))
        conn.commit()
        
        return json.dumps(weather_data)
    finally:
        conn.close()

@mcp.tool()
async def calculate(expression: str) -> str:
    """Perform mathematical calculations safely"""
    try:
        # Simple safety check - only allow basic math operations
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        
        # Evaluate the expression
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"

@mcp.tool()
async def get_current_time() -> str:
    """Get the current date and time"""
    now = datetime.now()
    return json.dumps({
        "current_time": now.isoformat(),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": "Local"
    })

@mcp.tool()
async def analyze_sentiment(text: str) -> str:
    """Analyze the sentiment of text (simple keyword-based)"""
    positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "happy", "joy"]
    negative_words = ["bad", "terrible", "awful", "hate", "dislike", "sad", "angry", "frustrated", "disappointed"]
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment = "positive"
        confidence = min(0.9, 0.5 + (positive_count - negative_count) * 0.1)
    elif negative_count > positive_count:
        sentiment = "negative"
        confidence = min(0.9, 0.5 + (negative_count - positive_count) * 0.1)
    else:
        sentiment = "neutral"
        confidence = 0.5
    
    return json.dumps({
        "text": text,
        "sentiment": sentiment,
        "confidence": confidence,
        "positive_indicators": positive_count,
        "negative_indicators": negative_count
    })

# =====================
# MCP PROMPTS
# =====================

@mcp.prompt()
async def weather_advisor(city: str, activity: str = "general") -> str:
    """Generate weather-based advice for activities"""
    
    # Track prompt usage
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO prompt_usage (prompt_name, arguments, used_at, context)
            VALUES (?, ?, ?, ?)
        """, ("weather_advisor", json.dumps({"city": city, "activity": activity}), now, f"Weather advice for {activity} in {city}"))
        conn.commit()
    finally:
        conn.close()
    
    return f"""You are a helpful weather advisor. Based on the weather conditions in {city}, provide specific advice for {activity} activities.

Instructions:
1. First, get the current weather for {city} using the get_weather tool
2. Analyze how the weather conditions affect {activity} activities
3. Provide practical recommendations including:
   - Whether the activity is recommended
   - What preparations or equipment might be needed
   - Alternative suggestions if conditions are unfavorable
   - Safety considerations if relevant

Be specific, practical, and consider the user's safety and comfort."""

@mcp.prompt()
async def memory_assistant(task: str, context: str = "") -> str:
    """Help with memory-related tasks"""
    
    # Track prompt usage
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO prompt_usage (prompt_name, arguments, used_at, context)
            VALUES (?, ?, ?, ?)
        """, ("memory_assistant", json.dumps({"task": task, "context": context}), now, f"Memory task: {task}"))
        conn.commit()
    finally:
        conn.close()
    
    return f"""You are a sophisticated memory assistant with access to a persistent memory system.

Current task: {task}
Context: {context}

Available memory operations:
- remember(key, value, category, importance): Store information
- recall(key): Retrieve specific information
- search_memories(query, category, min_importance): Search through memories
- forget(key): Remove information

Instructions:
1. Understand what the user wants to accomplish with their memory
2. Use appropriate memory operations to help them
3. Organize information logically with meaningful keys and categories
4. Set appropriate importance levels (1-5, where 5 is most important)
5. Provide clear feedback about what was stored or retrieved

Be proactive in suggesting how to better organize and categorize information."""

@mcp.prompt()
async def data_analyst(data_source: str, analysis_type: str = "general") -> str:
    """Analyze data from various sources"""
    
    # Track prompt usage
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO prompt_usage (prompt_name, arguments, used_at, context)
            VALUES (?, ?, ?, ?)
        """, ("data_analyst", json.dumps({"data_source": data_source, "analysis_type": analysis_type}), now, f"Analyzing {data_source} for {analysis_type}"))
        conn.commit()
    finally:
        conn.close()
    
    return f"""You are an expert data analyst with access to memory and calculation tools.

Data source: {data_source}
Analysis type: {analysis_type}

Available tools:
- Memory tools: remember, recall, search_memories
- calculate: Perform mathematical calculations
- Weather data: get_weather for weather-related analysis
- Sentiment analysis: analyze_sentiment for text data

Instructions:
1. First, understand what data is available from {data_source}
2. Access or retrieve the relevant data using available tools
3. Perform {analysis_type} analysis appropriate to the data
4. Use calculations where needed for statistical analysis
5. Store key findings in memory for future reference
6. Present insights in a clear, structured format
7. Suggest actionable recommendations based on the analysis

Focus on accuracy, clarity, and practical insights."""

@mcp.prompt()
async def creative_writer(genre: str, theme: str, length: str = "medium") -> str:
    """Generate creative writing with memory integration"""
    
    # Track prompt usage
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO prompt_usage (prompt_name, arguments, used_at, context)
            VALUES (?, ?, ?, ?)
        """, ("creative_writer", json.dumps({"genre": genre, "theme": theme, "length": length}), now, f"Creative writing: {genre} with theme {theme}"))
        conn.commit()
    finally:
        conn.close()
    
    return f"""You are a creative writer with access to a memory system for maintaining consistency and inspiration.

Writing parameters:
- Genre: {genre}
- Theme: {theme}
- Length: {length}

Available tools:
- Memory system: Use remember/recall to maintain character details, plot points, world-building elements
- search_memories: Find inspiration from previous creative work
- get_current_time: For dating your creative work

Instructions:
1. Search memories for any existing creative work that might relate to this {genre} and {theme}
2. Create compelling content that fits the specified genre and explores the theme
3. Store important creative elements (characters, plot points, world details) in memory for future reference
4. Ensure consistency with any existing creative work in your memory
5. Length guidelines:
   - Short: 1-2 paragraphs
   - Medium: 3-5 paragraphs
   - Long: 6+ paragraphs

Focus on engaging storytelling, vivid descriptions, and thematic depth."""

@mcp.prompt()
async def task_planner(goal: str, timeframe: str, constraints: str = "") -> str:
    """Create comprehensive task plans with memory integration"""
    
    # Track prompt usage
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO prompt_usage (prompt_name, arguments, used_at, context)
            VALUES (?, ?, ?, ?)
        """, ("task_planner", json.dumps({"goal": goal, "timeframe": timeframe, "constraints": constraints}), now, f"Planning for: {goal}"))
        conn.commit()
    finally:
        conn.close()
    
    return f"""You are an expert task planner with access to memory and time tracking tools.

Planning parameters:
- Goal: {goal}
- Timeframe: {timeframe}
- Constraints: {constraints}

Available tools:
- Memory system: Store and retrieve planning information, track progress
- get_current_time: Get current date/time for scheduling
- calculate: Perform time and resource calculations

Instructions:
1. Break down the goal into specific, actionable tasks
2. Create a realistic timeline within the given timeframe
3. Consider the specified constraints in your planning
4. Store the plan in memory with appropriate categorization
5. Include milestones and checkpoints
6. Provide resource estimates where relevant
7. Include contingency planning for potential obstacles
8. Format the plan clearly with priorities and dependencies

Focus on practicality, achievability, and clear next steps."""

# =====================
# SERVER LIFECYCLE
# =====================

async def cleanup():
    """Cleanup function"""
    print("🧹 Cleaning up MCP server...")

def main():
    """Main server function"""
    print("🚀 Starting Enhanced MCP Server...")
    
    # Initialize database
    init_database()
    
    # Add some sample data
    conn = sqlite3.connect("memory.db")
    try:
        now = datetime.now().isoformat()
        
        # Sample memories
        sample_memories = [
            ("user_name", "Assistant User", "personal", 5),
            ("favorite_color", "blue", "preferences", 3),
            ("last_project", "MCP Server Development", "work", 4),
            ("meeting_reminder", "Weekly team sync every Tuesday 10 AM", "schedule", 4),
            ("api_key_location", "Stored in .env.local file", "technical", 5)
        ]
        
        for key, value, category, importance in sample_memories:
            conn.execute("""
                INSERT OR IGNORE INTO memories (key, value, category, importance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now))
        
        conn.commit()
        print("✅ Sample data initialized")
    finally:
        conn.close()
    
    print("🎯 Enhanced MCP Server ready!")
    print("Available capabilities:")
    print("  📝 Tools: remember, recall, forget, search_memories, get_weather, calculate, get_current_time, analyze_sentiment")
    print("  📚 Resources: memory://all, memory://category/{category}, weather://cache, prompts://usage")
    print("  🎭 Prompts: weather_advisor, memory_assistant, data_analyst, creative_writer, task_planner")
    
    # Run the server
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()