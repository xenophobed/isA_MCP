#!/usr/bin/env python3
"""
NotebookLM Tools for MCP Server

Provides NotebookLM access for agents via browser automation.
Uses the WebAutomationService from isA_OS for Playwright-based browser control.

Migrated from isA_Vibe/src/agents/mcp_servers/notebooklm_mcp.py

Environment:
    NOTEBOOKLM_SESSION_ID: Session ID for persistent auth (default: notebooklm_default)
    WEB_SERVICE_URL: URL to web automation service (default: http://localhost:8083)
    NOTEBOOKLM_DEFAULT_NOTEBOOK: Default notebook ID to use
"""

import json
import os
from typing import Optional, Dict, Any

import httpx

from mcp.server.fastmcp import FastMCP
from core.logging import get_logger
from tools.base_tool import BaseTool

logger = get_logger(__name__)
tools = BaseTool()

# Configuration
NOTEBOOKLM_SESSION_ID = os.getenv("NOTEBOOKLM_SESSION_ID", "notebooklm_default")
WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://localhost:8083")
NOTEBOOKLM_DEFAULT_NOTEBOOK = os.getenv("NOTEBOOKLM_DEFAULT_NOTEBOOK", "")
NOTEBOOKLM_BASE_URL = "https://notebooklm.google.com"

# State management (module-level)
_state = {"current_notebook_id": NOTEBOOKLM_DEFAULT_NOTEBOOK or None, "is_authenticated": False}


async def call_web_automation(
    url: str,
    task: str,
    task_context: Optional[Dict[str, Any]] = None,
    routing_strategy: str = "dom_first",
    max_steps: int = 10,
) -> Dict[str, Any]:
    """
    Call the web automation service via HTTP API.

    Args:
        url: Target URL
        task: Natural language task description
        task_context: Additional context for the task
        routing_strategy: Automation strategy (dom_first, intelligent, etc.)
        max_steps: Maximum automation steps

    Returns:
        Automation result dict
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "url": url,
            "task": task,
            "provider": "self_hosted",
            "routing_strategy": routing_strategy,
            "task_context": task_context or {},
            "max_steps": max_steps,
            "user_id": NOTEBOOKLM_SESSION_ID,
        }

        response_data = None
        async with client.stream(
            "POST",
            f"{WEB_SERVICE_URL}/api/v1/web/automation/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "data" in data:
                            response_data = data["data"]
                    except json.JSONDecodeError:
                        continue

        return response_data or {"success": False, "error": "No response received"}


def get_notebook_url(notebook_id: Optional[str] = None) -> str:
    """Get the full URL for a notebook."""
    nid = notebook_id or _state["current_notebook_id"]
    if nid:
        return f"{NOTEBOOKLM_BASE_URL}/notebook/{nid}"
    return NOTEBOOKLM_BASE_URL


def register_notebooklm_tools(mcp: FastMCP):
    """Register NotebookLM tools with the MCP server."""

    @mcp.tool()
    async def notebooklm_login(notebook_id: Optional[str] = None) -> dict:
        """Open NotebookLM in browser for Google authentication. Run this first to authenticate.

        Args:
            notebook_id: Optional notebook ID to navigate to after login

        Returns:
            Dict with authentication status
        """
        try:
            url = get_notebook_url(notebook_id)

            result = await call_web_automation(
                url=url,
                task="Wait for page to load. If on Google login page, wait for user to complete login. Once logged in and on NotebookLM, confirm the page shows the notebook interface.",
                routing_strategy="intelligent",
                max_steps=3,
            )

            if result.get("success"):
                _state["is_authenticated"] = True
                if notebook_id:
                    _state["current_notebook_id"] = notebook_id

                return tools.create_response(
                    status="success",
                    action="notebooklm_login",
                    data={
                        "authenticated": True,
                        "message": "Successfully logged in to NotebookLM",
                        "notebook_id": _state["current_notebook_id"],
                        "final_url": result.get("final_url", url),
                    },
                )
            else:
                return tools.create_response(
                    status="success",
                    action="notebooklm_login",
                    data={
                        "authenticated": False,
                        "message": "Browser opened. Please complete Google login manually.",
                        "url": url,
                        "error": result.get("error"),
                    },
                )

        except httpx.TimeoutException:
            return tools.create_response(
                status="error",
                action="notebooklm_login",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Web automation service timeout. Check if web service is running.",
            )
        except httpx.ConnectError:
            return tools.create_response(
                status="error",
                action="notebooklm_login",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Cannot connect to web automation service. Start the web service or port-forward.",
            )
        except Exception as e:
            logger.error(f"Error in notebooklm_login: {e}")
            return tools.create_response(
                status="error", action="notebooklm_login", data={}, error_message=str(e)
            )

    @mcp.tool()
    async def notebooklm_chat(
        message: str, notebook_id: Optional[str] = None, wait_for_complete: bool = True
    ) -> dict:
        """Send a message to NotebookLM and get the AI response. Requires prior authentication.

        Args:
            message: The message/question to send to NotebookLM
            notebook_id: Notebook ID to use (optional, uses current if not specified)
            wait_for_complete: Wait for complete response (default: true)

        Returns:
            Dict with sent message and AI response
        """
        try:
            if notebook_id:
                _state["current_notebook_id"] = notebook_id

            url = get_notebook_url()
            if not _state["current_notebook_id"]:
                return tools.create_response(
                    status="error",
                    action="notebooklm_chat",
                    data={},
                    error_message="No notebook specified. Use 'navigate' or provide notebook_id.",
                )

            combined_task = f"""
            Complete these steps in order:

            1. Find the chat input textarea (it may have placeholder text like "Ask anything about your sources" or similar)
            2. Click on it to focus
            3. Type the following message exactly: {message}
            4. Find and click the send button (arrow icon) OR press Enter to submit
            5. Wait 15 seconds for the AI response to fully stream in and complete
            6. Find and extract the AI's response text - it will be in a chat message bubble/container below the user's question
            7. The task is complete when you can see and read the AI's full response
            """

            result = await call_web_automation(
                url=url,
                task=combined_task,
                task_context={"message": message, "action": "chat", "wait_for_response": True},
                routing_strategy="intelligent",
                max_steps=10,
            )

            # Extract response from automation result
            response_text = ""

            if result.get("success"):
                automation_result = result.get("automation_result", {})

                for step in automation_result.get("steps", []):
                    if step.get("extracted_text"):
                        response_text = step.get("extracted_text", "")
                    if (
                        step.get("description")
                        and "response" in step.get("description", "").lower()
                    ):
                        if not response_text:
                            response_text = step.get("description", "")

                verification = result.get("verification", {})
                if verification.get("reasoning"):
                    if not response_text:
                        response_text = verification.get("reasoning", "")

            if not response_text:
                response_text = "Message sent successfully. AI response captured but text extraction pending - use extract_content to get the full response."

            total_time = result.get("performance_metrics", {}).get("time_elapsed", 0)

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="notebooklm_chat",
                data={
                    "message_sent": message,
                    "notebook_id": _state["current_notebook_id"],
                    "response": response_text,
                    "automation_result": {
                        "success": result.get("success"),
                        "method": result.get("performance_metrics", {}).get("method_used"),
                        "time_elapsed": total_time,
                    },
                },
            )

        except httpx.TimeoutException:
            return tools.create_response(
                status="error",
                action="notebooklm_chat",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Web automation service timeout",
            )
        except httpx.ConnectError:
            return tools.create_response(
                status="error",
                action="notebooklm_chat",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Cannot connect to web automation service",
            )
        except Exception as e:
            logger.error(f"Error in notebooklm_chat: {e}")
            return tools.create_response(
                status="error",
                action="notebooklm_chat",
                data={"message": message},
                error_message=str(e),
            )

    @mcp.tool()
    async def notebooklm_navigate(notebook_id: str) -> dict:
        """Navigate to a specific NotebookLM notebook

        Args:
            notebook_id: The notebook ID to navigate to

        Returns:
            Dict with navigation status
        """
        try:
            if not notebook_id:
                return tools.create_response(
                    status="error",
                    action="notebooklm_navigate",
                    data={},
                    error_message="notebook_id is required",
                )

            _state["current_notebook_id"] = notebook_id
            url = get_notebook_url(notebook_id)

            result = await call_web_automation(
                url=url,
                task="Navigate to the notebook and wait for it to fully load. Confirm the notebook interface is visible.",
                routing_strategy="dom_first",
                max_steps=3,
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="notebooklm_navigate",
                data={
                    "notebook_id": notebook_id,
                    "url": url,
                    "message": f"Navigated to notebook {notebook_id}",
                },
            )

        except httpx.TimeoutException:
            return tools.create_response(
                status="error",
                action="notebooklm_navigate",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Web automation service timeout",
            )
        except httpx.ConnectError:
            return tools.create_response(
                status="error",
                action="notebooklm_navigate",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Cannot connect to web automation service",
            )
        except Exception as e:
            logger.error(f"Error in notebooklm_navigate: {e}")
            return tools.create_response(
                status="error",
                action="notebooklm_navigate",
                data={"notebook_id": notebook_id},
                error_message=str(e),
            )

    @mcp.tool()
    async def notebooklm_get_sources(notebook_id: Optional[str] = None) -> dict:
        """Get the list of sources (documents) in the current notebook

        Args:
            notebook_id: Notebook ID (optional, uses current if not specified)

        Returns:
            Dict with list of sources
        """
        try:
            if notebook_id:
                _state["current_notebook_id"] = notebook_id

            url = get_notebook_url()
            if not _state["current_notebook_id"]:
                return tools.create_response(
                    status="error",
                    action="notebooklm_get_sources",
                    data={},
                    error_message="No notebook specified",
                )

            result = await call_web_automation(
                url=url,
                task="Find and list all the sources/documents in this notebook. Look for a sources panel or list that shows uploaded documents, PDFs, or links.",
                routing_strategy="intelligent",
                max_steps=5,
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="notebooklm_get_sources",
                data={
                    "notebook_id": _state["current_notebook_id"],
                    "sources": result.get("extracted_data", []),
                    "automation_result": result,
                },
            )

        except httpx.TimeoutException:
            return tools.create_response(
                status="error",
                action="notebooklm_get_sources",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Web automation service timeout",
            )
        except httpx.ConnectError:
            return tools.create_response(
                status="error",
                action="notebooklm_get_sources",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Cannot connect to web automation service",
            )
        except Exception as e:
            logger.error(f"Error in notebooklm_get_sources: {e}")
            return tools.create_response(
                status="error", action="notebooklm_get_sources", data={}, error_message=str(e)
            )

    @mcp.tool()
    async def notebooklm_set_default_notebook(notebook_id: str) -> dict:
        """Set the default notebook ID for subsequent operations

        Args:
            notebook_id: The notebook ID to set as default

        Returns:
            Dict with old and new notebook IDs
        """
        try:
            if not notebook_id:
                return tools.create_response(
                    status="error",
                    action="notebooklm_set_default_notebook",
                    data={},
                    error_message="notebook_id is required",
                )

            old_notebook = _state["current_notebook_id"]
            _state["current_notebook_id"] = notebook_id

            return tools.create_response(
                status="success",
                action="notebooklm_set_default_notebook",
                data={
                    "old_notebook_id": old_notebook,
                    "new_notebook_id": notebook_id,
                    "message": f"Default notebook set to {notebook_id}",
                },
            )

        except Exception as e:
            logger.error(f"Error in notebooklm_set_default_notebook: {e}")
            return tools.create_response(
                status="error",
                action="notebooklm_set_default_notebook",
                data={"notebook_id": notebook_id},
                error_message=str(e),
            )

    @mcp.tool()
    async def notebooklm_healthcheck() -> dict:
        """Check if NotebookLM MCP is ready and authenticated

        Returns:
            Dict with health status and configuration
        """
        try:
            web_service_healthy = False
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{WEB_SERVICE_URL}/health")
                    web_service_healthy = response.status_code == 200
            except Exception:
                pass

            return tools.create_response(
                status="success" if web_service_healthy else "warning",
                action="notebooklm_healthcheck",
                data={
                    "healthy": web_service_healthy,
                    "web_service_url": WEB_SERVICE_URL,
                    "web_service_available": web_service_healthy,
                    "authenticated": _state["is_authenticated"],
                    "current_notebook_id": _state["current_notebook_id"],
                    "session_id": NOTEBOOKLM_SESSION_ID,
                },
            )

        except Exception as e:
            logger.error(f"Error in notebooklm_healthcheck: {e}")
            return tools.create_response(
                status="error", action="notebooklm_healthcheck", data={}, error_message=str(e)
            )

    @mcp.tool()
    async def notebooklm_extract_content(notebook_id: Optional[str] = None) -> dict:
        """Extract the current chat history or content from the notebook

        Args:
            notebook_id: Notebook ID (optional, uses current if not specified)

        Returns:
            Dict with extracted content
        """
        try:
            if notebook_id:
                _state["current_notebook_id"] = notebook_id

            url = get_notebook_url()
            if not _state["current_notebook_id"]:
                return tools.create_response(
                    status="error",
                    action="notebooklm_extract_content",
                    data={},
                    error_message="No notebook specified",
                )

            result = await call_web_automation(
                url=url,
                task="Extract all visible content from the notebook page, including chat history, source summaries, and any generated content.",
                routing_strategy="dom_first",
                max_steps=3,
            )

            return tools.create_response(
                status="success" if result.get("success") else "error",
                action="notebooklm_extract_content",
                data={
                    "notebook_id": _state["current_notebook_id"],
                    "content": result.get("extracted_data", ""),
                    "url": url,
                },
            )

        except httpx.TimeoutException:
            return tools.create_response(
                status="error",
                action="notebooklm_extract_content",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Web automation service timeout",
            )
        except httpx.ConnectError:
            return tools.create_response(
                status="error",
                action="notebooklm_extract_content",
                data={"service_url": WEB_SERVICE_URL},
                error_message="Cannot connect to web automation service",
            )
        except Exception as e:
            logger.error(f"Error in notebooklm_extract_content: {e}")
            return tools.create_response(
                status="error", action="notebooklm_extract_content", data={}, error_message=str(e)
            )

    logger.debug("Registered 7 NotebookLM tools")
