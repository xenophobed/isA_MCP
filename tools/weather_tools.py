#!/usr/bin/env python
"""
Weather Tools for MCP Server
Handles weather information with caching
"""
import json
import sqlite3
import random
from datetime import datetime

from core.security import get_security_manager
from core.logging import get_logger

logger = get_logger(__name__)

# Mock weather data
MOCK_WEATHER_DATA = {
    "beijing": {"temperature": 15, "condition": "Sunny", "humidity": 45, "wind": "5 km/h NE"},
    "default": {"temperature": random.randint(10, 30), "condition": random.choice(["Sunny", "Cloudy", "Rainy"]), "humidity": random.randint(30, 80), "wind": f"{random.randint(2, 15)} km/h N"}
}

def register_weather_tools(mcp):
    """Register all weather tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    async def get_weather(city: str, user_id: str = "default") -> str:
        """Get weather information with caching and monitoring
        
        This tool provides current weather conditions, temperature, 
        humidity and forecast data for any city worldwide.
        
        Keywords: weather, temperature, forecast, climate, rain, sunny, cloudy, wind
        Category: weather
        """
        city_lower = city.lower()
        
        conn = sqlite3.connect("memory.db")
        try:
            # Check cache
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
            else:
                # Get fresh data
                if city_lower in MOCK_WEATHER_DATA:
                    weather_data = MOCK_WEATHER_DATA[city_lower].copy()
                else:
                    weather_data = MOCK_WEATHER_DATA["default"].copy()
                
                weather_data.update({
                    "city": city,
                    "cached": False,
                    "retrieved_at": datetime.now().isoformat()
                })
                
                # Cache result
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO weather_cache (city, weather_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (city_lower, json.dumps(weather_data), now, now))
                conn.commit()
                
                result = weather_data
            
            response = {
                "status": "success",
                "action": "get_weather",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Weather requested for {city} by {user_id}")
            return json.dumps(response)
        finally:
            conn.close() 