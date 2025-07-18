#!/usr/bin/env python
"""
Weather Tools for MCP Server - Mock Implementation
Pure mock weather tool for testing purposes without database dependencies
"""
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any

from core.security import get_security_manager
from core.logging import get_logger

logger = get_logger(__name__)

# In-memory cache for mock testing (resets on server restart)
_weather_cache: Dict[str, Dict[str, Any]] = {}

# Extended mock weather data for more realistic testing
MOCK_WEATHER_DATA = {
    "beijing": {
        "temperature": 15,
        "condition": "Sunny",
        "humidity": 45,
        "wind": "5 km/h NE",
        "pressure": "1013 hPa",
        "visibility": "10 km"
    },
    "shanghai": {
        "temperature": 22,
        "condition": "Partly Cloudy",
        "humidity": 68,
        "wind": "8 km/h SW",
        "pressure": "1015 hPa",
        "visibility": "8 km"
    },
    "tokyo": {
        "temperature": 18,
        "condition": "Rainy",
        "humidity": 85,
        "wind": "12 km/h E",
        "pressure": "1008 hPa",
        "visibility": "5 km"
    },
    "london": {
        "temperature": 12,
        "condition": "Foggy",
        "humidity": 90,
        "wind": "3 km/h N",
        "pressure": "1010 hPa",
        "visibility": "2 km"
    },
    "new york": {
        "temperature": 20,
        "condition": "Cloudy",
        "humidity": 55,
        "wind": "10 km/h W",
        "pressure": "1012 hPa",
        "visibility": "12 km"
    }
}

def _generate_random_weather() -> Dict[str, Any]:
    """Generate random weather data for unknown cities"""
    conditions = ["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Stormy", "Foggy", "Snowy"]
    wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    
    return {
        "temperature": random.randint(-10, 35),
        "condition": random.choice(conditions),
        "humidity": random.randint(20, 95),
        "wind": f"{random.randint(0, 25)} km/h {random.choice(wind_directions)}",
        "pressure": f"{random.randint(980, 1040)} hPa",
        "visibility": f"{random.randint(1, 15)} km"
    }


def register_weather_tools(mcp):
    """Register all weather tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    async def get_weather(city: str, user_id: str = "default") -> str:
        """Get mock weather information for testing purposes
        
        This is a mock weather tool that provides simulated weather data
        for testing the MCP framework. It includes in-memory caching
        and realistic weather patterns for common cities.
        
        Args:
            city: Name of the city to get weather for
            user_id: User identifier for logging purposes
        
        Returns:
            JSON string with weather data including temperature, condition,
            humidity, wind, pressure, and visibility
        
        Keywords: weather, temperature, forecast, climate, rain, sunny, cloudy, wind, mock, test
        Category: weather
        """
        try:
            city_lower = city.lower().strip()
            current_time = datetime.now()
            
            # Generate fresh weather data
            if city_lower in MOCK_WEATHER_DATA:
                weather_data = MOCK_WEATHER_DATA[city_lower].copy()
            else:
                weather_data = _generate_random_weather()
            
            # Add metadata
            weather_data.update({
                "city": city.title(),
                "cached": False,
                "cached_at": current_time.isoformat(),
                "retrieved_at": current_time.isoformat(),
                "is_mock": True,
                "data_source": "mock_generator"
            })
            
            
            response = {
                "status": "success",
                "action": "get_weather",
                "data": weather_data,
                "timestamp": current_time.isoformat(),
                "source": "mock_fresh"
            }
            
            logger.info(f"Generated fresh mock weather data for {city} (user: {user_id})")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error in get_weather for {city}: {str(e)}")
            return json.dumps({
                "status": "error",
                "action": "get_weather",
                "error": f"Failed to get weather data: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_error"
            })
    

    