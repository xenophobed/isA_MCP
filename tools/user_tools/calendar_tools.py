#!/usr/bin/env python3
"""
Calendar Management Tools
Calendar event management with external calendar sync integration

Scenarios:
1. Create calendar events (meetings, reminders, appointments)
2. Query calendar events (list, filter by date, category)
3. Update and delete calendar events
4. Get upcoming events and today's events
5. Sync with external calendars (Google, Apple, Outlook)

Integrates with:
- Calendar Service: Calendar event management (port 8240)
- External Calendar Providers: Google Calendar, Apple Calendar, Outlook

Architecture:
- Uses ServiceConfig for service URL configuration
- Supports external calendar sync via OAuth
"""

import asyncio
import httpx
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
from core.config.service_config import ServiceConfig

logger = get_logger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class CalendarEventRequest(BaseModel):
    """Calendar event creation/update request"""
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    start_time: str = Field(..., description="Start time in ISO format (e.g., 2025-10-23T10:00:00)")
    end_time: str = Field(..., description="End time in ISO format (e.g., 2025-10-23T11:00:00)")
    all_day: bool = Field(False, description="Whether this is an all-day event")
    category: Optional[str] = Field(None, description="Event category: work, personal, meeting, reminder, holiday, birthday, other")
    color: Optional[str] = Field(None, description="Event color in hex format (e.g., #FF5733)")
    reminders: Optional[List[int]] = Field(None, description="Reminder times in minutes before event (e.g., [15, 60])")
    recurrence_type: Optional[str] = Field(None, description="Recurrence type: none, daily, weekly, monthly, yearly")
    is_shared: bool = Field(False, description="Whether event is shared with others")


# ============================================================================
# Calendar Tools Class
# ============================================================================

class CalendarTools(BaseTool):
    """Calendar management tools for event creation and management"""

    def __init__(self):
        super().__init__()
        self.calendar_service_url = "http://localhost:8240"  # TODO: from config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    def register_tools(self, mcp):
        """Register calendar management tools"""

        # 1. Create calendar event
        self.register_tool(
            mcp,
            self.create_calendar_event_impl,
            name="create_calendar_event",
            description="Create calendar event meeting appointment reminder schedule add new",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 2. Get calendar event
        self.register_tool(
            mcp,
            self.get_calendar_event_impl,
            name="get_calendar_event",
            description="Get retrieve fetch calendar event details information by id",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 3. List calendar events
        self.register_tool(
            mcp,
            self.list_calendar_events_impl,
            name="list_calendar_events",
            description="List query search filter calendar events by date range category",
            security_level=SecurityLevel.LOW,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 4. Update calendar event
        self.register_tool(
            mcp,
            self.update_calendar_event_impl,
            name="update_calendar_event",
            description="Update modify edit change calendar event details time location",
            security_level=SecurityLevel.MEDIUM,
            timeout=30.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 5. Delete calendar event
        self.register_tool(
            mcp,
            self.delete_calendar_event_impl,
            name="delete_calendar_event",
            description="Delete remove cancel calendar event",
            security_level=SecurityLevel.MEDIUM,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 6. Get upcoming events
        self.register_tool(
            mcp,
            self.get_upcoming_events_impl,
            name="get_upcoming_events",
            description="Get retrieve upcoming future calendar events next days",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 7. Get today's events
        self.register_tool(
            mcp,
            self.get_today_events_impl,
            name="get_today_events",
            description="Get retrieve today's calendar events schedule appointments",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        # 8. Sync external calendar
        self.register_tool(
            mcp,
            self.sync_external_calendar_impl,
            name="sync_external_calendar",
            description="Sync synchronize external calendar Google Apple Outlook calendar integration",
            security_level=SecurityLevel.MEDIUM,
            timeout=60.0,
            annotations=ToolAnnotations(readOnlyHint=False)
        )

        # 9. Get sync status
        self.register_tool(
            mcp,
            self.get_sync_status_impl,
            name="get_calendar_sync_status",
            description="Get retrieve calendar sync status external calendar synchronization",
            security_level=SecurityLevel.LOW,
            timeout=10.0,
            annotations=ToolAnnotations(readOnlyHint=True)
        )

        logger.debug(f"Registered {len(self.registered_tools)} calendar management tools")

    # ========================================================================
    # Event Management Implementation
    # ========================================================================

    async def create_calendar_event_impl(
        self,
        title: Annotated[str, Field(description="Event title (e.g., 'Team Meeting', 'Doctor Appointment')")],
        start_time: Annotated[str, Field(description="Start time in ISO format (e.g., '2025-10-23T10:00:00')")],
        end_time: Annotated[str, Field(description="End time in ISO format (e.g., '2025-10-23T11:00:00')")],
        description: Annotated[Optional[str], Field(description="Event description")] = None,
        location: Annotated[Optional[str], Field(description="Event location")] = None,
        category: Annotated[Optional[str], Field(description="Category: work, personal, meeting, reminder, holiday, birthday, other")] = None,
        all_day: Annotated[bool, Field(description="Whether this is an all-day event")] = False,
        reminders: Annotated[Optional[List[int]], Field(description="Reminder times in minutes before event (e.g., [15, 60])")] = None,
        recurrence_type: Annotated[Optional[str], Field(description="Recurrence type: none, daily, weekly, monthly, yearly")] = None,
        is_shared: Annotated[bool, Field(description="Whether event is shared")] = False,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event

        Example usage:
        - "Create a meeting tomorrow at 2pm"
        - "Schedule a doctor appointment next week"
        - "Add a reminder for my birthday"
        """
        await self.log_info(ctx, f"Creating calendar event: {title}")
        await self.report_progress(ctx, 1, 3, "Validating inputs")

        # Validate date format
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            if end_dt <= start_dt:
                return self.create_response(
                    "error", "create_calendar_event",
                    {"error": "End time must be after start time"}
                )
        except ValueError as e:
            return self.create_response(
                "error", "create_calendar_event",
                {"error": f"Invalid date format: {str(e)}"}
            )

        # Validate category
        valid_categories = ["work", "personal", "meeting", "reminder", "holiday", "birthday", "other"]
        if category and category not in valid_categories:
            return self.create_response(
                "error", "create_calendar_event",
                {"error": f"Category must be one of: {', '.join(valid_categories)}"}
            )

        await self.report_progress(ctx, 2, 3, "Creating event in calendar service")

        # Prepare request data
        event_data = {
            "user_id": user_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "all_day": all_day,
            "is_shared": is_shared
        }

        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if category:
            event_data["category"] = category
        if reminders:
            event_data["reminders"] = reminders
        if recurrence_type and recurrence_type != "none":
            event_data["recurrence_type"] = recurrence_type

        # Call calendar service
        try:
            response = await self.http_client.post(
                f"{self.calendar_service_url}/api/v1/calendar/events",
                json=event_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 201:
                result = response.json()
                event_id = result.get("event_id")

                await self.report_progress(ctx, 3, 3, "Complete")
                await self.log_info(ctx, f"Calendar event created: {event_id}")

                return self.create_response(
                    "success", "create_calendar_event",
                    {
                        "event_id": event_id,
                        "title": title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "category": category or "other",
                        "status": "created"
                    }
                )
            else:
                error_msg = response.text
                await self.log_error(ctx, f"Failed to create event: {error_msg}")
                return self.create_response(
                    "error", "create_calendar_event",
                    {"error": f"Creation failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error creating calendar event: {e}")
            return self.create_response(
                "error", "create_calendar_event",
                {"error": str(e)}
            )

    async def get_calendar_event_impl(
        self,
        event_id: Annotated[str, Field(description="Event ID to retrieve")],
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get calendar event details"""
        await self.log_info(ctx, f"Getting calendar event: {event_id}")

        try:
            response = await self.http_client.get(
                f"{self.calendar_service_url}/api/v1/calendar/events/{event_id}",
                params={"user_id": user_id}
            )

            if response.status_code == 200:
                event = response.json()
                await self.log_info(ctx, f"Retrieved event: {event.get('title')}")

                return self.create_response(
                    "success", "get_calendar_event",
                    {
                        "event": event,
                        "event_id": event_id
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "get_calendar_event",
                    {"error": "Event not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_calendar_event",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting calendar event: {e}")
            return self.create_response(
                "error", "get_calendar_event",
                {"error": str(e)}
            )

    async def list_calendar_events_impl(
        self,
        user_id: str = "default",
        start_date: Annotated[Optional[str], Field(description="Start date in ISO format (e.g., '2025-10-01')")] = None,
        end_date: Annotated[Optional[str], Field(description="End date in ISO format (e.g., '2025-10-31')")] = None,
        category: Annotated[Optional[str], Field(description="Filter by category")] = None,
        limit: Annotated[int, Field(description="Max events to return", ge=1, le=1000)] = 100,
        offset: Annotated[int, Field(description="Offset for pagination", ge=0)] = 0,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """List calendar events with optional filters"""
        await self.log_info(ctx, f"Listing calendar events for user {user_id}")

        try:
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if category:
                params["category"] = category

            response = await self.http_client.get(
                f"{self.calendar_service_url}/api/v1/calendar/events",
                params=params
            )

            if response.status_code == 200:
                result = response.json()
                events = result.get("events", [])
                total = result.get("total", 0)

                await self.log_info(ctx, f"Found {total} events")

                return self.create_response(
                    "success", "list_calendar_events",
                    {
                        "total": total,
                        "count": len(events),
                        "events": events,
                        "filters": {
                            "start_date": start_date,
                            "end_date": end_date,
                            "category": category
                        }
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "list_calendar_events",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error listing calendar events: {e}")
            return self.create_response(
                "error", "list_calendar_events",
                {"error": str(e)}
            )

    async def update_calendar_event_impl(
        self,
        event_id: Annotated[str, Field(description="Event ID to update")],
        user_id: str = "default",
        title: Annotated[Optional[str], Field(description="New event title")] = None,
        description: Annotated[Optional[str], Field(description="New event description")] = None,
        location: Annotated[Optional[str], Field(description="New event location")] = None,
        start_time: Annotated[Optional[str], Field(description="New start time in ISO format")] = None,
        end_time: Annotated[Optional[str], Field(description="New end time in ISO format")] = None,
        category: Annotated[Optional[str], Field(description="New category")] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Update calendar event"""
        await self.log_info(ctx, f"Updating calendar event: {event_id}")

        # Build update data
        update_data = {}
        if title:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if location is not None:
            update_data["location"] = location
        if start_time:
            update_data["start_time"] = start_time
        if end_time:
            update_data["end_time"] = end_time
        if category:
            update_data["category"] = category

        if not update_data:
            return self.create_response(
                "error", "update_calendar_event",
                {"error": "No fields to update"}
            )

        try:
            response = await self.http_client.put(
                f"{self.calendar_service_url}/api/v1/calendar/events/{event_id}",
                json=update_data,
                params={"user_id": user_id}
            )

            if response.status_code == 200:
                event = response.json()
                await self.log_info(ctx, f"Event updated: {event_id}")

                return self.create_response(
                    "success", "update_calendar_event",
                    {
                        "event_id": event_id,
                        "event": event,
                        "status": "updated"
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "update_calendar_event",
                    {"error": "Event not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "update_calendar_event",
                    {"error": f"Update failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error updating calendar event: {e}")
            return self.create_response(
                "error", "update_calendar_event",
                {"error": str(e)}
            )

    async def delete_calendar_event_impl(
        self,
        event_id: Annotated[str, Field(description="Event ID to delete")],
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Delete calendar event"""
        await self.log_info(ctx, f"Deleting calendar event: {event_id}")

        try:
            response = await self.http_client.delete(
                f"{self.calendar_service_url}/api/v1/calendar/events/{event_id}",
                params={"user_id": user_id}
            )

            if response.status_code == 204:
                await self.log_info(ctx, f"Event {event_id} deleted")

                return self.create_response(
                    "success", "delete_calendar_event",
                    {
                        "event_id": event_id,
                        "status": "deleted"
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "delete_calendar_event",
                    {"error": "Event not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "delete_calendar_event",
                    {"error": f"Delete failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error deleting calendar event: {e}")
            return self.create_response(
                "error", "delete_calendar_event",
                {"error": str(e)}
            )

    # ========================================================================
    # Query Methods Implementation
    # ========================================================================

    async def get_upcoming_events_impl(
        self,
        user_id: str = "default",
        days: Annotated[int, Field(description="Number of days to look ahead", ge=1, le=365)] = 7,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get upcoming calendar events"""
        await self.log_info(ctx, f"Getting upcoming events for user {user_id} (next {days} days)")

        try:
            response = await self.http_client.get(
                f"{self.calendar_service_url}/api/v1/calendar/upcoming",
                params={"user_id": user_id, "days": days}
            )

            if response.status_code == 200:
                events = response.json()
                await self.log_info(ctx, f"Found {len(events)} upcoming events")

                return self.create_response(
                    "success", "get_upcoming_events",
                    {
                        "count": len(events),
                        "days": days,
                        "events": events
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_upcoming_events",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting upcoming events: {e}")
            return self.create_response(
                "error", "get_upcoming_events",
                {"error": str(e)}
            )

    async def get_today_events_impl(
        self,
        user_id: str = "default",
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get today's calendar events"""
        await self.log_info(ctx, f"Getting today's events for user {user_id}")

        try:
            response = await self.http_client.get(
                f"{self.calendar_service_url}/api/v1/calendar/today",
                params={"user_id": user_id}
            )

            if response.status_code == 200:
                events = response.json()
                await self.log_info(ctx, f"Found {len(events)} events today")

                return self.create_response(
                    "success", "get_today_events",
                    {
                        "count": len(events),
                        "events": events
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_today_events",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting today's events: {e}")
            return self.create_response(
                "error", "get_today_events",
                {"error": str(e)}
            )

    # ========================================================================
    # External Calendar Sync Implementation
    # ========================================================================

    async def sync_external_calendar_impl(
        self,
        provider: Annotated[str, Field(description="Calendar provider: google_calendar, apple_calendar, outlook")],
        user_id: str = "default",
        credentials: Annotated[Optional[Dict[str, Any]], Field(description="OAuth credentials (optional)")] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Sync with external calendar"""
        await self.log_info(ctx, f"Syncing external calendar: {provider} for user {user_id}")

        # Validate provider
        valid_providers = ["google_calendar", "apple_calendar", "outlook"]
        if provider not in valid_providers:
            return self.create_response(
                "error", "sync_external_calendar",
                {"error": f"Provider must be one of: {', '.join(valid_providers)}"}
            )

        try:
            params = {
                "user_id": user_id,
                "provider": provider
            }

            response = await self.http_client.post(
                f"{self.calendar_service_url}/api/v1/calendar/sync",
                params=params,
                json=credentials or {}
            )

            if response.status_code == 200:
                result = response.json()
                await self.log_info(ctx, f"Calendar sync initiated: {provider}")

                return self.create_response(
                    "success", "sync_external_calendar",
                    {
                        "provider": provider,
                        "status": result.get("status"),
                        "synced_events": result.get("synced_events", 0),
                        "last_synced": result.get("last_synced")
                    }
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "sync_external_calendar",
                    {"error": f"Sync failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error syncing external calendar: {e}")
            return self.create_response(
                "error", "sync_external_calendar",
                {"error": str(e)}
            )

    async def get_sync_status_impl(
        self,
        user_id: str = "default",
        provider: Annotated[Optional[str], Field(description="Calendar provider (optional)")] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Get calendar sync status"""
        await self.log_info(ctx, f"Getting sync status for user {user_id}")

        try:
            params = {"user_id": user_id}
            if provider:
                params["provider"] = provider

            response = await self.http_client.get(
                f"{self.calendar_service_url}/api/v1/calendar/sync/status",
                params=params
            )

            if response.status_code == 200:
                status = response.json()
                await self.log_info(ctx, f"Sync status retrieved: {status.get('status')}")

                return self.create_response(
                    "success", "get_calendar_sync_status",
                    {
                        "status": status
                    }
                )
            elif response.status_code == 404:
                return self.create_response(
                    "error", "get_calendar_sync_status",
                    {"error": "Sync status not found"}
                )
            else:
                error_msg = response.text
                return self.create_response(
                    "error", "get_calendar_sync_status",
                    {"error": f"Query failed: {error_msg}"}
                )

        except Exception as e:
            await self.log_error(ctx, f"Error getting sync status: {e}")
            return self.create_response(
                "error", "get_calendar_sync_status",
                {"error": str(e)}
            )

    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()


# ============================================================================
# Registration - Auto-discovery
# ============================================================================

def register_calendar_tools(mcp):
    """
    Register calendar management tools

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For calendar_tools.py, function must be: register_calendar_tools(mcp)
    """
    tool = CalendarTools()
    tool.register_tools(mcp)
    logger.debug(f"Calendar management tools registered successfully")
    return tool

