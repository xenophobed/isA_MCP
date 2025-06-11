# Import all tools from submodules
from .weather_tools import get_weather, get_coolest_cities

# Export all tool functions for easy import
__all__ = [
    'get_weather',
    'get_coolest_cities',
]
