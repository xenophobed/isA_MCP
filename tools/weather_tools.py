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

def _is_cache_valid(cached_data: Dict[str, Any], cache_duration_minutes: int = 60) -> bool:
    """Check if cached data is still valid"""
    if "cached_at" not in cached_data:
        return False
    
    cached_time = datetime.fromisoformat(cached_data["cached_at"])
    expiry_time = cached_time + timedelta(minutes=cache_duration_minutes)
    
    return datetime.now() < expiry_time

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
            
            # Check in-memory cache first
            if city_lower in _weather_cache:
                cached_data = _weather_cache[city_lower]
                if _is_cache_valid(cached_data):
                    logger.info(f"Returning cached weather data for {city} (user: {user_id})")
                    return json.dumps({
                        "status": "success",
                        "action": "get_weather",
                        "data": cached_data,
                        "timestamp": current_time.isoformat(),
                        "source": "mock_cache"
                    })
            
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
            
            # Cache the result in memory
            _weather_cache[city_lower] = weather_data.copy()
            _weather_cache[city_lower]["cached"] = True
            
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
    
    @mcp.tool()
    @security_manager.security_check
    async def clear_weather_cache(user_id: str = "admin") -> str:
        """Clear the in-memory weather cache for testing purposes
        
        This tool clears all cached weather data, useful for testing
        cache behavior and forcing fresh data generation.
        
        Args:
            user_id: User identifier for logging purposes
        
        Returns:
            JSON string confirming cache clear operation
        
        Keywords: weather, cache, clear, reset, test, admin
        Category: weather
        """
        try:
            cache_size = len(_weather_cache)
            _weather_cache.clear()
            
            response = {
                "status": "success",
                "action": "clear_weather_cache",
                "message": f"Cleared {cache_size} cached weather entries",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_admin"
            }
            
            logger.info(f"Weather cache cleared by {user_id} ({cache_size} entries)")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error clearing weather cache: {str(e)}")
            return json.dumps({
                "status": "error",
                "action": "clear_weather_cache",
                "error": f"Failed to clear cache: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_error"
            })
    
    @mcp.tool()
    @security_manager.security_check
    async def get_weather_cache_status(user_id: str = "default") -> str:
        """Get current weather cache status for debugging
        
        This tool provides information about the current state of the
        weather cache, including number of entries and their ages.
        
        Args:
            user_id: User identifier for logging purposes
        
        Returns:
            JSON string with cache status information
        
        Keywords: weather, cache, status, debug, info, test
        Category: weather
        """
        try:
            current_time = datetime.now()
            cache_info = {
                "total_entries": len(_weather_cache),
                "cities": list(_weather_cache.keys()),
                "entries": []
            }
            
            for city, data in _weather_cache.items():
                if "cached_at" in data:
                    cached_time = datetime.fromisoformat(data["cached_at"])
                    age_minutes = (current_time - cached_time).total_seconds() / 60
                    is_valid = _is_cache_valid(data)
                    
                    cache_info["entries"].append({
                        "city": city,
                        "cached_at": data["cached_at"],
                        "age_minutes": round(age_minutes, 2),
                        "is_valid": is_valid,
                        "condition": data.get("condition", "Unknown")
                    })
            
            response = {
                "status": "success",
                "action": "get_weather_cache_status",
                "data": cache_info,
                "timestamp": current_time.isoformat(),
                "source": "mock_debug"
            }
            
            logger.info(f"Weather cache status requested by {user_id}")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting weather cache status: {str(e)}")
            return json.dumps({
                "status": "error",
                "action": "get_weather_cache_status",
                "error": f"Failed to get cache status: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "source": "mock_error"
            }) 