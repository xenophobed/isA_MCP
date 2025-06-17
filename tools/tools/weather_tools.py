#!/usr/bin/env python
"""
Weather tools for MCP Server
"""
import json
import random
from datetime import datetime
from core.security import security_check
from resources.database.sqlite.models import DatabaseManager, WeatherCacheModel

# Initialize database components
db_manager = DatabaseManager()
weather_cache = WeatherCacheModel(db_manager)

# Mock weather data
MOCK_WEATHER_DATA = {
    "beijing": {"temperature": 15, "condition": "Sunny", "humidity": 45, "wind": "5 km/h NE"},
    "default": {"temperature": random.randint(10, 30), "condition": random.choice(["Sunny", "Cloudy", "Rainy"]), "humidity": random.randint(30, 80), "wind": f"{random.randint(2, 15)} km/h N"}
}

@security_check
async def get_weather(city: str, user_id: str = "default") -> str:
    """Get weather information with caching and monitoring"""
    city_lower = city.lower()
    
    # Check cache
    cached = weather_cache.get_cached_weather(city_lower)
    
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
        weather_cache.cache_weather(city_lower, weather_data)
        result = weather_data
    
    return json.dumps({
        "status": "success",
        "action": "get_weather",
        "data": result,
        "timestamp": datetime.now().isoformat()
    })