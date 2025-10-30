#!/usr/bin/env python3
"""
Complete Example Tools Suite
Demonstrates all ISA MCP tool system features

Scenarios:
1. Calculator - Basic tool calls
2. Weather Tools - Context, Progress, HIL, Billing, Security
3. Context Tests - Logging, Progress, Human-in-loop
4. Batch and Streaming
5. Long-running and Cancellable Operations
6. Security Levels and Authorization

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


class UserConfirmation(BaseModel):
    """User confirmation schema"""
    confirmed: bool
    reason: str = ""


# ============================================================================
# Mock Data
# ============================================================================

MOCK_WEATHER_DATA = {
    "beijing": {
        "temperature": 15, "condition": "Sunny", "humidity": 45,
        "wind": "5 km/h NE", "pressure": "1013 hPa", "visibility": "10 km"
    },
    "shanghai": {
        "temperature": 22, "condition": "Partly Cloudy", "humidity": 68,
        "wind": "8 km/h SW", "pressure": "1015 hPa", "visibility": "8 km"
    },
    "tokyo": {
        "temperature": 18, "condition": "Rainy", "humidity": 85,
        "wind": "12 km/h E", "pressure": "1008 hPa", "visibility": "5 km"
    },
    "london": {
        "temperature": 12, "condition": "Foggy", "humidity": 90,
        "wind": "3 km/h N", "pressure": "1010 hPa", "visibility": "2 km"
    },
    "new york": {
        "temperature": 20, "condition": "Cloudy", "humidity": 55,
        "wind": "10 km/h W", "pressure": "1012 hPa", "visibility": "12 km"
    }
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
        "visibility": f"{random.randint(1, 15)} km"
    }


def _generate_forecast(base_temp: float, days: int = 7) -> List[ForecastDay]:
    """Generate mock forecast"""
    forecast = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
        forecast.append(ForecastDay(
            date=date,
            high=base_temp + random.randint(-3, 8),
            low=base_temp + random.randint(-8, 3),
            condition=random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
            precipitation_chance=random.randint(0, 80)
        ))
    return forecast


# ============================================================================
# Example Tools Class
# ============================================================================

class ExampleTools(BaseTool):
    """Complete example tools suite demonstrating all MCP SDK + BaseTool features"""

    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Dict] = {}

    def register_tools(self, mcp):
        """Register all example tools"""

        # Calculator - Basic tool
        self.register_tool(
            mcp,
            self.calculator_impl,
            name="calculator",
            description="Calculate add subtract multiply divide numbers arithmetic math compute",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(
                readOnlyHint=True,
                idempotentHint=True
            )
        )

        # Weather - Full features
        self.register_tool(
            mcp,
            self.get_weather_impl,
            name="get_weather",
            description="Get check query weather temperature forecast conditions city location",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            rate_limit_calls=100,
            rate_limit_period=3600,
            annotations=ToolAnnotations(
                readOnlyHint=True,
                idempotentHint=True
            )
        )

        self.register_tool(
            mcp,
            self.batch_weather_impl,
            name="batch_weather",
            description="Batch multiple cities weather query parallel sequential list processing",
            security_level=SecurityLevel.LOW,
            timeout=120.0,
            rate_limit_calls=10,
            rate_limit_period=3600
        )

        self.register_tool(
            mcp,
            self.stream_weather_impl,
            name="stream_weather",
            description="Stream continuous real-time weather updates live monitoring periodic",
            security_level=SecurityLevel.LOW,
            timeout=60.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        self.register_tool(
            mcp,
            self.long_weather_analysis_impl,
            name="long_weather_analysis",
            description="Long-running weather analysis pattern detection cancellable background task",
            security_level=SecurityLevel.MEDIUM,
            timeout=300.0
        )

        self.register_tool(
            mcp,
            self.cancel_analysis_impl,
            name="cancel_weather_analysis",
            description="Cancel stop terminate running weather analysis operation task",
            security_level=SecurityLevel.MEDIUM,
            annotations=ToolAnnotations(destructiveHint=True)
        )

        # Context tests
        self.register_tool(
            mcp,
            self.test_context_info_impl,
            name="test_context_info",
            description="Test extract context information metadata request session client ID",
            security_level=SecurityLevel.LOW
        )

        self.register_tool(
            mcp,
            self.test_context_logging_impl,
            name="test_context_logging",
            description="Test context logging info debug warning error messages",
            security_level=SecurityLevel.LOW
        )

        self.register_tool(
            mcp,
            self.test_context_progress_impl,
            name="test_context_progress",
            description="Test context progress reporting steps percentage tracking",
            security_level=SecurityLevel.LOW
        )

        self.register_tool(
            mcp,
            self.test_context_comprehensive_impl,
            name="test_context_comprehensive",
            description="Test comprehensive workflow context features logging progress combined",
            security_level=SecurityLevel.LOW
        )

        logger.info(f"Registered {len(self.registered_tools)} example tools")

    # ========================================================================
    # Calculator Implementation
    # ========================================================================

    async def calculator_impl(
        self,
        operation: Annotated[str, Field(description="Math operation: add, subtract, multiply, or divide")],
        a: Annotated[float, Field(description="First number")],
        b: Annotated[float, Field(description="Second number")],
        user_id: str = "default",
        ctx: Optional[Context] = None
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
                        "error", "calculator",
                        {"error": "Division by zero", "operation": operation}
                    )
                result = a / b
                formula = f"{a} / {b}"
            else:
                return self.create_response(
                    "error", "calculator",
                    {"error": f"Unknown operation: {operation}"}
                )

            await self.log_info(ctx, f"Result: {formula} = {result}")

            return self.create_response(
                "success", "calculator",
                {
                    "result": result,
                    "formula": formula,
                    "operation": operation,
                    "inputs": {"a": a, "b": b}
                }
            )

        except Exception as e:
            await self.log_error(ctx, f"Calculator error: {str(e)}")
            return self.create_response(
                "error", "calculator",
                {"error": str(e), "operation": operation}
            )

    # ========================================================================
    # Weather Tools - Full Feature Demonstrations
    # ========================================================================

    async def get_weather_impl(
        self,
        city: Annotated[str, Field(description="The city name, e.g. Tokyo, New York, London")],
        include_forecast: Annotated[bool, Field(description="Whether to include 7-day weather forecast")] = False,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get weather - Demonstrates all advanced features"""
        # Step 1: Validate
        await self.log_info(ctx, f"Weather query: {city}")
        await self.report_progress(ctx, 1, 5, "Validating input")

        city_lower = city.lower().strip()

        # Step 2: HIL - Sensitive term detection
        if any(term in city_lower for term in ["military", "restricted", "secret"]):
            await self.log_warning(ctx, f"Sensitive term detected: {city}")

            confirmation = await self.elicit_user_input(
                ctx,
                message=f"Query '{city}' contains sensitive terms. Continue?",
                schema=UserConfirmation
            )

            if not confirmation or not confirmation.confirmed:
                await self.log_info(ctx, "User cancelled query")
                return self.create_response(
                    "success", "get_weather",
                    WeatherResponse(
                        city=city,
                        current=WeatherData(
                            temperature=0, condition="Query Cancelled",
                            humidity=0, wind="N/A", pressure="N/A", visibility="N/A"
                        ),
                        retrieved_at=datetime.now().isoformat(),
                        cache_ttl=0
                    ).model_dump()
                )

        # Step 3: Fetch data
        await self.report_progress(ctx, 2, 5, "Fetching weather data")
        await asyncio.sleep(0.2)  # Simulate network delay

        if city_lower in MOCK_WEATHER_DATA:
            weather_data_raw = MOCK_WEATHER_DATA[city_lower].copy()
        else:
            weather_data_raw = _generate_random_weather()

        # Step 4: Billing
        await self.report_progress(ctx, 3, 5, "Processing billing")
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
                    "cost_usd": 0.0001
                }
            )
        except Exception as e:
            await self.log_warning(ctx, f"Billing failed: {e}")

        # Step 5: Generate forecast
        forecast_data = None
        if include_forecast:
            await self.report_progress(ctx, 4, 5, "Generating 7-day forecast")
            forecast_data = _generate_forecast(weather_data_raw["temperature"])
            await self.log_info(ctx, f"Generated {len(forecast_data)} day forecast")

        # Step 6: Complete
        await self.report_progress(ctx, 5, 5, "Complete")

        response = WeatherResponse(
            city=city.title(),
            current=WeatherData(**weather_data_raw),
            forecast=forecast_data,
            retrieved_at=datetime.now().isoformat(),
            cache_ttl=3600
        )

        await self.log_info(
            ctx,
            f"Weather data: {city} - {weather_data_raw['temperature']}C, {weather_data_raw['condition']}"
        )

        return self.create_response(
            "success", "get_weather", response.model_dump()
        )

    async def batch_weather_impl(
        self,
        cities: Annotated[List[str], Field(description="List of city names to query weather for")],
        parallel: Annotated[bool, Field(description="Whether to process cities in parallel or sequentially")] = False,
        user_id: str = "default",
        ctx: Optional[Context] = None
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

                await self.report_progress(ctx, i + 1, total, f"Processed {i+1}/{total}")
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

                await self.report_progress(ctx, i + 1, total, f"Processed {city}")

        await self.log_info(ctx, f"Batch complete: {successful} succeeded, {failed} failed")

        return self.create_response(
            "success", "batch_weather",
            {
                "total_cities": total,
                "successful": successful,
                "failed": failed,
                "results": results
            }
        )

    async def stream_weather_impl(
        self,
        city: str,
        updates: int = 5,
        user_id: str = "default",
        ctx: Optional[Context] = None
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
                "condition": base_data["condition"]
            }

            updates_list.append(update_data)
            await self.log_info(
                ctx,
                f"Update {i+1}/{updates}: {current_temp}C - {base_data['condition']}",
                extra_data=update_data
            )

            await self.report_progress(ctx, i + 1, updates, f"Update {i+1}")
            await asyncio.sleep(0.5)

        await self.log_info(ctx, f"Completed {updates} updates")

        return self.create_response(
            "success", "stream_weather",
            {
                "city": city,
                "total_updates": updates,
                "updates": updates_list
            }
        )

    async def long_weather_analysis_impl(
        self,
        city: str,
        analysis_id: str,
        duration_seconds: int = 60,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Long-running analysis - Demonstrates cancellable operations"""
        await self.log_info(ctx, f"Starting analysis: {analysis_id} ({duration_seconds}s)")

        async with self.track_operation(analysis_id):
            steps = duration_seconds
            for i in range(steps):
                await asyncio.sleep(1)
                await self.report_progress(
                    ctx, i + 1, steps,
                    f"Analyzing weather patterns ({i+1}/{steps}s)"
                )

                if i % 10 == 0:
                    await self.log_debug(ctx, f"Checkpoint: {i}s")

        await self.log_info(ctx, f"Analysis complete: {analysis_id}")

        return self.create_response(
            "success", "long_weather_analysis",
            {
                "analysis_id": analysis_id,
                "city": city,
                "duration": duration_seconds,
                "analysis_status": "completed",
                "results": {
                    "pattern": "stable",
                    "confidence": 0.87,
                    "recommendation": "Normal weather patterns detected"
                }
            }
        )

    async def cancel_analysis_impl(
        self,
        analysis_id: str,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Cancel analysis - Demonstrates operation cancellation"""
        await self.log_info(ctx, f"Cancelling analysis: {analysis_id}")

        cancelled = await self.cancel_operation(analysis_id)

        if cancelled:
            await self.log_info(ctx, f"Successfully cancelled: {analysis_id}")
            return self.create_response(
                "success", "cancel_weather_analysis",
                {
                    "cancellation_status": "cancelled",
                    "analysis_id": analysis_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            await self.log_warning(ctx, f"Not found or completed: {analysis_id}")
            return self.create_response(
                "success", "cancel_weather_analysis",
                {
                    "cancellation_status": "not_found",
                    "analysis_id": analysis_id,
                    "message": "Analysis not found or already completed"
                }
            )

    # ========================================================================
    # Context Tests
    # ========================================================================

    async def test_context_info_impl(
        self,
        test_message: str = "Testing Context extraction",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test Context information extraction"""
        await self.log_info(ctx, f"Test: Context info extraction")
        await self.log_info(ctx, f"Message: {test_message}")

        context_info = self.extract_context_info(ctx)
        context_available = ctx is not None

        await self.log_info(ctx, f"Context extraction complete - available: {context_available}")

        return self.create_response(
            "success", "test_context_info",
            {
                "test_message": test_message,
                "context_info": context_info,
                "context_available": context_available
            }
        )

    async def test_context_logging_impl(
        self,
        test_all_levels: bool = True,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test Context logging features"""
        logs_sent = []

        await self.log_info(ctx, "Test: Context logging")
        logs_sent.append({"level": "info", "message": "Context logging test"})

        if test_all_levels:
            await self.log_debug(ctx, "DEBUG log")
            logs_sent.append({"level": "debug", "message": "Debug log"})

            await self.log_warning(ctx, "WARNING log")
            logs_sent.append({"level": "warning", "message": "Warning log"})

            await self.log_error(ctx, "ERROR log (test)")
            logs_sent.append({"level": "error", "message": "Error log"})

        await self.log_info(
            ctx, "Log with extra data",
            extra_data={"key": "value", "count": 42}
        )
        logs_sent.append({"level": "info", "message": "Log with extra params"})

        await self.log_info(ctx, f"Sent {len(logs_sent)} logs")

        return self.create_response(
            "success", "test_context_logging",
            {
                "logs_sent": logs_sent,
                "total_logs": len(logs_sent),
                "context_available": ctx is not None
            }
        )

    async def test_context_progress_impl(
        self,
        total_steps: int = 10,
        delay_ms: int = 100,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Test Context progress reporting"""
        await self.log_info(ctx, f"Test: Context progress reporting")
        await self.log_info(ctx, f"Total steps: {total_steps}, delay: {delay_ms}ms")

        progress_reports = []

        for step in range(1, total_steps + 1):
            await self.report_progress(
                ctx, step, total_steps,
                f"Processing step {step}/{total_steps}"
            )

            progress_reports.append({
                "step": step,
                "total": total_steps,
                "percentage": round(step / total_steps * 100, 1)
            })

            await asyncio.sleep(delay_ms / 1000)

        await self.log_info(ctx, f"Progress reporting complete - {total_steps} steps")

        return self.create_response(
            "success", "test_context_progress",
            {
                "total_steps": total_steps,
                "progress_reports": progress_reports,
                "context_available": ctx is not None
            }
        )

    async def test_context_comprehensive_impl(
        self,
        scenario_name: str = "Complete workflow",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Comprehensive test of all Context features"""
        await self.log_info(ctx, f"Test: Comprehensive scenario")
        await self.log_info(ctx, f"Scenario: {scenario_name}")

        context_info = self.extract_context_info(ctx)
        await self.log_debug(ctx, f"Context info: {context_info}")

        steps = [
            "Initialize system",
            "Load data",
            "Process data",
            "Validate results",
            "Save output"
        ]

        results = []
        for i, step in enumerate(steps, 1):
            await self.log_info(ctx, f"Step {i}/{len(steps)}: {step}")
            await self.report_progress(ctx, i, len(steps), step)
            await asyncio.sleep(0.1)

            results.append({
                "step": i,
                "name": step,
                "status": "completed"
            })

        await self.log_info(ctx, f"Comprehensive test complete - {len(steps)} steps")

        return self.create_response(
            "success", "test_context_comprehensive",
            {
                "scenario_name": scenario_name,
                "context_info": context_info,
                "steps_completed": len(steps),
                "results": results,
                "features_tested": [
                    "context_extraction",
                    "logging",
                    "progress_reporting"
                ]
            }
        )


# ============================================================================
# Registration - Auto-discovery
# ============================================================================

def register_example_tools(mcp):
    """
    Register complete example tools suite

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For example_tools.py, function must be: register_example_tools(mcp)

    This allows auto-discovery system to find and register tools
    """
    tool = ExampleTools()
    tool.register_tools(mcp)
    return tool
