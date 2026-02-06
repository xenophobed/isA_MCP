#!/usr/bin/env python3
"""
Utility Tools - Common system utilities for MCP

Provides basic utility functions like getting current time, date,
timezone info, and other commonly needed operations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_utility_tools(mcp: FastMCP):
    """Register utility tools with the MCP server."""

    @mcp.tool()
    async def get_current_time(
        timezone_name: Optional[str] = None,
        format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the current date and time.

        Returns the current timestamp in multiple formats, useful for
        scheduling, logging, time-based calculations, and displaying
        the current time to users.

        Args:
            timezone_name: Optional timezone name (e.g., "UTC", "US/Eastern", "Asia/Shanghai").
                          Defaults to UTC if not specified.
            format: Optional custom strftime format string (e.g., "%Y-%m-%d %H:%M:%S").
                   If not provided, returns multiple standard formats.

        Returns:
            {
                "iso": "2024-01-15T10:30:45.123456+00:00",
                "date": "2024-01-15",
                "time": "10:30:45",
                "datetime": "2024-01-15 10:30:45",
                "timestamp": 1705315845,
                "timezone": "UTC",
                "day_of_week": "Monday",
                "formatted": "..." (if custom format provided)
            }

        Keywords: time, date, now, current, today, timestamp, clock, datetime
        """
        try:
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)

            # Handle timezone conversion if specified
            if timezone_name and timezone_name.upper() != "UTC":
                try:
                    import zoneinfo
                    tz = zoneinfo.ZoneInfo(timezone_name)
                    now = now_utc.astimezone(tz)
                    tz_name = timezone_name
                except Exception as e:
                    logger.warning(f"Invalid timezone '{timezone_name}': {e}, using UTC")
                    now = now_utc
                    tz_name = "UTC"
            else:
                now = now_utc
                tz_name = "UTC"

            result = {
                "iso": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": int(now.timestamp()),
                "timezone": tz_name,
                "day_of_week": now.strftime("%A"),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second
            }

            # Add custom formatted output if format string provided
            if format:
                try:
                    result["formatted"] = now.strftime(format)
                except Exception as e:
                    result["format_error"] = f"Invalid format string: {e}"

            logger.info(f"get_current_time() → {result['datetime']} ({tz_name})")
            return result

        except Exception as e:
            logger.error(f"get_current_time() failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_current_date() -> Dict[str, Any]:
        """
        Get the current date (simple version).

        A simplified version of get_current_time that returns just the date.
        Useful for quick date checks and comparisons.

        Returns:
            {
                "date": "2024-01-15",
                "year": 2024,
                "month": 1,
                "day": 15,
                "day_of_week": "Monday",
                "day_of_year": 15,
                "week_number": 3
            }

        Keywords: date, today, current date, calendar
        """
        try:
            now = datetime.now(timezone.utc)

            result = {
                "date": now.strftime("%Y-%m-%d"),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "day_of_week": now.strftime("%A"),
                "day_of_year": now.timetuple().tm_yday,
                "week_number": now.isocalendar()[1]
            }

            logger.info(f"get_current_date() → {result['date']}")
            return result

        except Exception as e:
            logger.error(f"get_current_date() failed: {e}")
            return {"error": str(e)}

    logger.debug("✅ Utility tools registered: get_current_time, get_current_date")
