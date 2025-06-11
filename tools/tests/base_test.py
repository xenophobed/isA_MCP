from unittest.mock import AsyncMock, MagicMock
from app.capability.registry.tool_graph_manager import SearchResult

class BaseToolTest:
    """Base class for tool tests with common mocks"""
    
    @staticmethod
    async def create_mock_graph_manager():
        """Create a mock graph manager for testing"""
        mock_manager = MagicMock()
        
        # Define common test data
        weather_tool = SearchResult(
            tool_id="tool_get_weather",
            name="get_weather",
            description="Get weather for location",
            concept="weather",
            domain="weather-service",
            operation="get",
            usage_context="real-time-query",
            score=0.95
        )
        
        cities_tool = SearchResult(
            tool_id="tool_get_coolest_cities",
            name="get_coolest_cities",
            description="Get list of coolest cities",
            concept="weather",
            domain="weather-service",
            operation="list",
            usage_context="comparison-query",
            score=0.85
        )
        
        # Set up mock methods
        mock_manager.sync_tools = AsyncMock()
        mock_manager.search_by_capability = AsyncMock(
            return_value=[weather_tool, cities_tool]
        )
        mock_manager.search_by_text = AsyncMock(
            return_value=[weather_tool]
        )
        
        return mock_manager 