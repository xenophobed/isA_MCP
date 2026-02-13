#!/usr/bin/env python3
"""
Basic Example Tools Suite
Simple demonstration tools for ISA MCP system

Scenarios:
1. Calculator - Basic arithmetic operations
2. Weather Tools - Query, batch processing, streaming updates

All tools inherit from BaseTool with concise descriptions for embedding similarity matching
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Annotated
from pydantic import BaseModel, Field

# MCP SDK imports
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

# ISA imports
from tools.base_tool import BaseTool
from core.security import SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Pydantic Models
# ============================================================================


class WeatherData(BaseModel):
    """Current weather data"""

    temperature: float
    condition: str
    humidity: int = Field(ge=0, le=100)
    wind: str
    pressure: str
    visibility: str


class ForecastDay(BaseModel):
    """Single day forecast"""

    date: str
    high: float
    low: float
    condition: str
    precipitation_chance: int = Field(ge=0, le=100)


class WeatherResponse(BaseModel):
    """Complete weather response"""

    city: str
    current: WeatherData
    forecast: Optional[List[ForecastDay]] = None
    retrieved_at: str
    is_mock: bool = True
    cache_ttl: int


# ============================================================================
# Mock Data
# ============================================================================

MOCK_WEATHER_DATA = {
    "beijing": {
        "temperature": 15,
        "condition": "Sunny",
        "humidity": 45,
        "wind": "5 km/h NE",
        "pressure": "1013 hPa",
        "visibility": "10 km",
    },
    "shanghai": {
        "temperature": 22,
        "condition": "Partly Cloudy",
        "humidity": 68,
        "wind": "8 km/h SW",
        "pressure": "1015 hPa",
        "visibility": "8 km",
    },
    "tokyo": {
        "temperature": 18,
        "condition": "Rainy",
        "humidity": 85,
        "wind": "12 km/h E",
        "pressure": "1008 hPa",
        "visibility": "5 km",
    },
    "london": {
        "temperature": 12,
        "condition": "Foggy",
        "humidity": 90,
        "wind": "3 km/h N",
        "pressure": "1010 hPa",
        "visibility": "2 km",
    },
    "new york": {
        "temperature": 20,
        "condition": "Cloudy",
        "humidity": 55,
        "wind": "10 km/h W",
        "pressure": "1012 hPa",
        "visibility": "12 km",
    },
}


def _generate_random_weather() -> Dict[str, Any]:
    """Generate random weather for unknown cities"""
    conditions = ["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Stormy", "Foggy", "Snowy"]
    wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return {
        "temperature": random.randint(-10, 35),
        "condition": random.choice(conditions),
        "humidity": random.randint(20, 95),
        "wind": f"{random.randint(0, 25)} km/h {random.choice(wind_directions)}",
        "pressure": f"{random.randint(980, 1040)} hPa",
        "visibility": f"{random.randint(1, 15)} km",
    }


def _generate_forecast(base_temp: float, days: int = 7) -> List[ForecastDay]:
    """Generate mock forecast"""
    forecast = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        forecast.append(
            ForecastDay(
                date=date,
                high=base_temp + random.randint(-3, 8),
                low=base_temp + random.randint(-8, 3),
                condition=random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
                precipitation_chance=random.randint(0, 80),
            )
        )
    return forecast


# ============================================================================
# Basic Example Tools Class
# ============================================================================


class BasicExampleTools(BaseTool):
    """Basic example tools suite with calculator and weather functionality"""

    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Dict] = {}

    def register_tools(self, mcp):
        """Register basic example tools"""

        # Calculator - Basic tool
        self.register_tool(
            mcp,
            self.calculator_impl,
            name="calculator",
            description="Calculate add subtract multiply divide numbers arithmetic math compute",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        )

        # Weather - Basic weather query
        self.register_tool(
            mcp,
            self.get_weather_impl,
            name="get_weather",
            description="Get check query weather temperature forecast conditions city location",
            security_level=SecurityLevel.LOW,
            timeout=30.0,
            rate_limit_calls=100,
            rate_limit_period=3600,
            annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        )

        # Batch weather query
        self.register_tool(
            mcp,
            self.batch_weather_impl,
            name="batch_weather",
            description="Batch multiple cities weather query parallel sequential list processing",
            security_level=SecurityLevel.LOW,
            timeout=120.0,
            rate_limit_calls=10,
            rate_limit_period=3600,
        )

        # Stream weather updates
        self.register_tool(
            mcp,
            self.stream_weather_impl,
            name="stream_weather",
            description="Stream continuous real-time weather updates live monitoring periodic",
            security_level=SecurityLevel.LOW,
            timeout=60.0,
            annotations=ToolAnnotations(readOnlyHint=True),
        )

        logger.debug(f"Registered {len(self.registered_tools)} basic example tools")

    # ========================================================================
    # Calculator Implementation
    # ========================================================================

    async def calculator_impl(
        self,
        operation: Annotated[
            str, Field(description="Math operation: add, subtract, multiply, or divide")
        ],
        a: Annotated[float, Field(description="First number")],
        b: Annotated[float, Field(description="Second number")],
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Calculator - Basic tool demonstration"""
        await self.log_info(ctx, f"Calculator: {a} {operation} {b}")

        try:
            if operation == "add":
                result = a + b
                formula = f"{a} + {b}"
            elif operation == "subtract":
                result = a - b
                formula = f"{a} - {b}"
            elif operation == "multiply":
                result = a * b
                formula = f"{a} x {b}"
            elif operation == "divide":
                if b == 0:
                    return self.create_response(
                        "error", "calculator", {"error": "Division by zero", "operation": operation}
                    )
                result = a / b
                formula = f"{a} / {b}"
            else:
                return self.create_response(
                    "error", "calculator", {"error": f"Unknown operation: {operation}"}
                )

            await self.log_info(ctx, f"Result: {formula} = {result}")

            return self.create_response(
                "success",
                "calculator",
                {
                    "result": result,
                    "formula": formula,
                    "operation": operation,
                    "inputs": {"a": a, "b": b},
                },
            )

        except Exception as e:
            await self.log_error(ctx, f"Calculator error: {str(e)}")
            return self.create_response(
                "error", "calculator", {"error": str(e), "operation": operation}
            )

    # ========================================================================
    # Weather Tools - Simplified Implementations
    # ========================================================================

    async def get_weather_impl(
        self,
        city: Annotated[str, Field(description="The city name, e.g. Tokyo, New York, London")],
        include_forecast: Annotated[
            bool, Field(description="Whether to include 7-day weather forecast")
        ] = False,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Get weather - Simple weather query with optional forecast"""
        # Step 1: Validate
        await self.log_info(ctx, f"Weather query: {city}")

        city_lower = city.lower().strip()

        # Step 2: Fetch data
        await self.log_debug(ctx, "Fetching weather data")
        await asyncio.sleep(0.2)  # Simulate network delay

        if city_lower in MOCK_WEATHER_DATA:
            weather_data_raw = MOCK_WEATHER_DATA[city_lower].copy()
        else:
            weather_data_raw = _generate_random_weather()

        # Step 3: Billing
        await self.log_debug(ctx, f"Calling ISA billing: {city}")

        try:
            await self._publish_billing_event(
                user_id=user_id,
                service_type="weather",
                operation="get_weather",
                input_units=1.0,
                metadata={
                    "city": city,
                    "model": "weather-mock-v1",
                    "provider": "mock_weather",
                    "cost_usd": 0.0001,
                },
            )
        except Exception as e:
            await self.log_warning(ctx, f"Billing failed: {e}")

        # Step 4: Generate forecast if requested
        forecast_data = None
        if include_forecast:
            forecast_data = _generate_forecast(weather_data_raw["temperature"])
            await self.log_info(ctx, f"Generated {len(forecast_data)} day forecast")

        # Complete
        response = WeatherResponse(
            city=city.title(),
            current=WeatherData(**weather_data_raw),
            forecast=forecast_data,
            retrieved_at=datetime.now().isoformat(),
            cache_ttl=3600,
        )

        await self.log_info(
            ctx,
            f"Weather data: {city} - {weather_data_raw['temperature']}C, {weather_data_raw['condition']}",
        )

        return self.create_response("success", "get_weather", response.model_dump())

    async def batch_weather_impl(
        self,
        cities: Annotated[List[str], Field(description="List of city names to query weather for")],
        parallel: Annotated[
            bool, Field(description="Whether to process cities in parallel or sequentially")
        ] = False,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Batch weather query - Demonstrates batch processing"""
        total = len(cities)
        await self.log_info(ctx, f"Batch query for {total} cities")

        results = []
        successful = 0
        failed = 0

        if parallel:
            await self.log_info(ctx, "Parallel processing")
            tasks = [self.get_weather_impl(city, user_id=user_id, ctx=ctx) for city in cities]

            for i, task in enumerate(asyncio.as_completed(tasks)):
                try:
                    result = await task
                    results.append({"city": cities[i], "status": "success", "data": result})
                    successful += 1
                except Exception as e:
                    results.append({"city": cities[i], "status": "error", "error": str(e)})
                    failed += 1
        else:
            await self.log_info(ctx, "Sequential processing")
            for i, city in enumerate(cities):
                try:
                    result = await self.get_weather_impl(city, user_id=user_id, ctx=ctx)
                    results.append({"city": city, "status": "success", "data": result})
                    successful += 1
                except Exception as e:
                    results.append({"city": city, "status": "error", "error": str(e)})
                    failed += 1
                    await self.log_error(ctx, f"Failed {city}: {e}")

        await self.log_info(ctx, f"Batch complete: {successful} succeeded, {failed} failed")

        return self.create_response(
            "success",
            "batch_weather",
            {"total_cities": total, "successful": successful, "failed": failed, "results": results},
        )

    async def stream_weather_impl(
        self,
        city: Annotated[str, Field(description="City name for weather updates")],
        updates: Annotated[int, Field(description="Number of updates to stream", ge=1, le=20)] = 5,
        user_id: str = "default",
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Stream weather updates - Demonstrates streaming"""
        await self.log_info(ctx, f"Streaming {city} ({updates} updates)")

        city_lower = city.lower().strip()
        base_data = MOCK_WEATHER_DATA.get(city_lower, _generate_random_weather())
        updates_list = []

        for i in range(updates):
            current_temp = base_data["temperature"] + random.randint(-2, 2)
            update_data = {
                "update_number": i + 1,
                "timestamp": datetime.now().isoformat(),
                "temperature": current_temp,
                "condition": base_data["condition"],
            }

            updates_list.append(update_data)
            await self.log_info(
                ctx,
                f"Update {i+1}/{updates}: {current_temp}C - {base_data['condition']}",
                extra_data=update_data,
            )

            await asyncio.sleep(0.5)

        await self.log_info(ctx, f"Completed {updates} updates")

        return self.create_response(
            "success",
            "stream_weather",
            {"city": city, "total_updates": updates, "updates": updates_list},
        )


# ============================================================================
# Registration - Auto-discovery
# ============================================================================


def register_basic_example_tools(mcp):
    """
    Register basic example tools suite

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For basic_example_tools.py, function must be: register_basic_example_tools(mcp)

    This allows auto-discovery system to find and register tools
    """
    tool = BasicExampleTools()
    tool.register_tools(mcp)
    logger.debug(f"✅ Basic example tools registered successfully")
    return tool
