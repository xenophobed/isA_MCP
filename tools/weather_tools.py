from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import random
import logging

logger = logging.getLogger(__name__)

@tool
async def get_weather(location: str) -> Dict[str, Any]:
    """
    Get the current weather for a specified location.
    
    Args:
        location: The city or location to get weather for (e.g., "Tokyo", "New York")
        
    Returns:
        Weather information including temperature, conditions, and humidity
    """
    try:
        logger.info(f"Getting weather for location: {location}")
        
        # This is a mock implementation that returns random weather data
        weather_conditions = ["Sunny", "Partly cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy", "Windy"]
        
        # Generate random weather data
        temp_c = random.randint(-10, 35)
        temp_f = (temp_c * 9/5) + 32
        condition = random.choice(weather_conditions)
        humidity = random.randint(30, 95)
        wind_speed = random.randint(0, 30)
        
        # Return formatted weather data
        return {
            "location": location,
            "temperature": {
                "celsius": temp_c,
                "fahrenheit": round(temp_f, 1)
            },
            "condition": condition,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "units": {
                "temperature": "C/F",
                "wind_speed": "km/h"
            },
            "forecast": "Not available in this version"
        }
    except Exception as e:
        logger.error(f"Error getting weather for {location}: {str(e)}")
        return {
            "error": f"Could not retrieve weather for {location}: {str(e)}",
            "location": location
        }

@tool
async def get_coolest_cities() -> List[Dict[str, Any]]:
    """
    Get a list of cities with currently cool temperatures.
    Returns a list of cities and their current temperatures.
    """
    try:
        logger.info("Getting list of coolest cities")
        
        # Mock data of cool cities
        cities = [
            {"name": "Reykjavik", "country": "Iceland", "temperature": {"celsius": random.randint(-5, 10)}},
            {"name": "Oslo", "country": "Norway", "temperature": {"celsius": random.randint(-2, 15)}},
            {"name": "Stockholm", "country": "Sweden", "temperature": {"celsius": random.randint(0, 15)}},
            {"name": "Helsinki", "country": "Finland", "temperature": {"celsius": random.randint(-2, 12)}},
            {"name": "Anchorage", "country": "USA", "temperature": {"celsius": random.randint(-10, 5)}},
            {"name": "Wellington", "country": "New Zealand", "temperature": {"celsius": random.randint(5, 15)}},
            {"name": "San Francisco", "country": "USA", "temperature": {"celsius": random.randint(10, 20)}},
            {"name": "Vancouver", "country": "Canada", "temperature": {"celsius": random.randint(5, 15)}},
            {"name": "Ushuaia", "country": "Argentina", "temperature": {"celsius": random.randint(0, 10)}},
            {"name": "Hobart", "country": "Australia", "temperature": {"celsius": random.randint(5, 15)}}
        ]
        
        # Sort by temperature
        cities.sort(key=lambda x: x["temperature"]["celsius"])
        
        # Add Fahrenheit temperatures
        for city in cities:
            city["temperature"]["fahrenheit"] = round((city["temperature"]["celsius"] * 9/5) + 32, 1)
            
        return cities
        
    except Exception as e:
        logger.error(f"Error getting coolest cities: {str(e)}")
        return [{"error": f"Could not retrieve coolest cities: {str(e)}"}]
