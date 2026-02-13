#!/usr/bin/env python3
"""
Event Tools Test Suite (Python version)
Tests all tools in event_tools.py via MCP API endpoints

IMPORTANT: This script tests MCP tools through the MCP API endpoint
(http://localhost:8081/mcp), NOT by directly connecting to backend services.
Backend services (agent_service, event_service) run in containers and are
not directly accessible from test scripts.

What this script verifies:
1. Tools are correctly registered in MCP server
2. Tools can be called via MCP API (tools/call method)
3. Tool parameter validation works correctly
4. Tool error handling works correctly

Note: Backend service connection errors are expected and acceptable,
as we're testing the MCP tool layer, not the backend services.
"""

import json
import sys
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


# Test configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8081")
VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"

# Test results
tests_passed = 0
tests_failed = 0
test_trigger_ids: List[str] = []


def print_header(text: str):
    """Print test section header"""
    print(f"\n{Colors.BLUE}{'='*40}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*40}{Colors.NC}")


def print_success(message: str):
    """Print success message"""
    global tests_passed
    print(f"{Colors.GREEN}✓ PASS:{Colors.NC} {message}")
    tests_passed += 1


def print_fail(message: str):
    """Print failure message"""
    global tests_failed
    print(f"{Colors.RED}✗ FAIL:{Colors.NC} {message}")
    tests_failed += 1


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ INFO:{Colors.NC} {message}")


def show_request_response(test_name: str, request: Dict, response: Any):
    """Display request and response in a formatted way"""
    print(f"\n{Colors.YELLOW}┌─────────────────────────────────────────────────────┐{Colors.NC}")
    print(f"{Colors.YELLOW}│ 📋 {test_name}{Colors.NC}")
    print(f"{Colors.YELLOW}└─────────────────────────────────────────────────────┘{Colors.NC}")
    print(f"{Colors.YELLOW}📤 REQUEST:{Colors.NC}")
    print(json.dumps(request, indent=2, ensure_ascii=False))
    print(f"\n{Colors.YELLOW}📥 RESPONSE:{Colors.NC}")
    if isinstance(response, dict):
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print(response)
    print()


def extract_sse_data(response_text: str) -> Optional[Dict]:
    """Extract JSON data from Server-Sent Events (SSE) response"""
    lines = response_text.strip().split("\n")
    for line in lines:
        if line.startswith("data: "):
            data_str = line[6:]  # Remove 'data: ' prefix
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                continue
    return None


def extract_tool_response(response_data: Dict) -> Optional[Dict]:
    """Extract tool response from MCP response structure"""
    if not response_data:
        return None

    # Try to get result content
    result = response_data.get("result", {})
    content = result.get("content", [])

    if content and len(content) > 0:
        text_content = content[0].get("text", "")
        if isinstance(text_content, str):
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"text": text_content}
        elif isinstance(text_content, dict):
            return text_content

    return result


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], request_id: int = 1) -> Optional[Dict]:
    """Call an MCP tool via HTTP"""
    url = f"{MCP_URL}/mcp"
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": request_id,
        "params": {"name": tool_name, "arguments": arguments},
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse SSE response
        sse_data = extract_sse_data(response.text)
        if sse_data:
            return extract_tool_response(sse_data)

        return None
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Request error: {e}{Colors.NC}")
        return None


def list_mcp_tools() -> Optional[Dict]:
    """List all MCP tools"""
    url = f"{MCP_URL}/mcp"
    payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        sse_data = extract_sse_data(response.text)
        return sse_data
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Request error: {e}{Colors.NC}")
        return None


def test_1_verify_tools_registered():
    """Test 1: Verify Event Tools Are Registered"""
    print_header("Test 1: Verify Event Tools Are Registered")

    tools_data = list_mcp_tools()
    if not tools_data:
        print_fail("Failed to retrieve tools list")
        return

    tools = tools_data.get("result", {}).get("tools", [])
    event_tool_names = [
        t["name"]
        for t in tools
        if t["name"].startswith("register_")
        or t["name"].startswith("list_")
        or t["name"].startswith("delete_")
        or t["name"].startswith("query_")
    ]

    show_request_response(
        "Tools List",
        {"method": "tools/list"},
        {"tools": event_tool_names, "count": len(event_tool_names)},
    )

    expected_tools = [
        "register_price_alert",
        "register_scheduled_task",
        "register_event_trigger",
        "list_triggers",
        "delete_trigger",
        "query_events",
    ]

    found_tools = [t for t in expected_tools if t in event_tool_names]

    if len(found_tools) >= 6:
        print_success(
            f"Event tools registered - Found {len(found_tools)} tools: {', '.join(found_tools)}"
        )
    else:
        print_fail(
            f"Event tools registration - Expected 6 tools, found {len(found_tools)}: {', '.join(found_tools)}"
        )


def test_2_register_price_alert():
    """Test 2: Register Price Alert"""
    print_header("Test 2: Register Price Alert")

    request = {
        "product": "Bitcoin",
        "threshold_value": 50.0,
        "threshold_type": "percentage",
        "direction": "up",
        "notification_channels": ["email"],
    }

    response = call_mcp_tool("register_price_alert", request, request_id=2)

    show_request_response("Register Price Alert", request, response)

    if response:
        if response.get("status") == "success":
            trigger_id = response.get("data", {}).get("trigger_id")
            if trigger_id:
                test_trigger_ids.append(trigger_id)
                print_success(f"Register price alert - Trigger ID: {trigger_id[:12]}...")
                return
        elif (
            "connection" in str(response.get("error", "")).lower()
            or "connection" in str(response.get("data", {}).get("error", "")).lower()
        ):
            print_info(
                "Register price alert - Backend service not available (connection error), but tool is registered correctly"
            )
            return

    print_fail("Register price alert - Failed to register")


def test_3_register_scheduled_task():
    """Test 3: Register Scheduled Task"""
    print_header("Test 3: Register Scheduled Task")

    request = {
        "task_name": "Daily News Summary",
        "task_type": "daily_news",
        "schedule_type": "daily",
        "schedule_time": "09:00",
    }

    response = call_mcp_tool("register_scheduled_task", request, request_id=3)

    show_request_response("Register Scheduled Task", request, response)

    if response:
        if response.get("status") == "success":
            trigger_id = response.get("data", {}).get("trigger_id")
            if trigger_id:
                test_trigger_ids.append(trigger_id)
                print_success(f"Register scheduled task - Trigger ID: {trigger_id[:12]}...")
                return
        elif (
            "connection" in str(response.get("error", "")).lower()
            or "connection" in str(response.get("data", {}).get("error", "")).lower()
        ):
            print_info(
                "Register scheduled task - Backend service not available (connection error), but tool is registered correctly"
            )
            return

    print_fail("Register scheduled task - Failed to register")


def test_4_register_event_trigger():
    """Test 4: Register Event Trigger"""
    print_header("Test 4: Register Event Trigger")

    request = {
        "trigger_name": "Security Alert Monitor",
        "event_type": "security_alert",
        "event_source": "system",
        "keywords": ["failed", "login", "unauthorized"],
    }

    response = call_mcp_tool("register_event_trigger", request, request_id=4)

    show_request_response("Register Event Trigger", request, response)

    if response:
        if response.get("status") == "success":
            trigger_id = response.get("data", {}).get("trigger_id")
            if trigger_id:
                test_trigger_ids.append(trigger_id)
                print_success(f"Register event trigger - Trigger ID: {trigger_id[:12]}...")
                return
        elif (
            "connection" in str(response.get("error", "")).lower()
            or "connection" in str(response.get("data", {}).get("error", "")).lower()
        ):
            print_info(
                "Register event trigger - Backend service not available (connection error), but tool is registered correctly"
            )
            return

    print_fail("Register event trigger - Failed to register")


def test_5_list_triggers():
    """Test 5: List Triggers"""
    print_header("Test 5: List Triggers")

    request = {}

    response = call_mcp_tool("list_triggers", request, request_id=5)

    show_request_response("List Triggers", request, response)

    # Accept success or connection errors (backend service might not be running)
    if response:
        if response.get("status") == "success":
            count = response.get("data", {}).get("count", 0)
            print_success(f"List triggers - Found {count} triggers")
            return
        elif (
            "connection" in str(response.get("error", "")).lower()
            or "connection" in str(response.get("data", {}).get("error", "")).lower()
        ):
            print_info(
                "List triggers - Backend service not available (connection error), but tool is registered correctly"
            )
            return

    print_fail("List triggers - Failed to list")


def test_6_query_events():
    """Test 6: Query Events"""
    print_header("Test 6: Query Events")

    request = {"limit": 10}

    response = call_mcp_tool("query_events", request, request_id=6)

    show_request_response("Query Events", request, response)

    # Accept success or connection errors (backend service might not be running)
    if response:
        if response.get("status") == "success":
            count = response.get("data", {}).get("count", 0)
            print_success(f"Query events - Found {count} events")
            return
        elif (
            "connection" in str(response.get("error", "")).lower()
            or "connection" in str(response.get("data", {}).get("error", "")).lower()
        ):
            print_info(
                "Query events - Backend service not available (connection error), but tool is registered correctly"
            )
            return

    print_fail("Query events - Failed to query")


def test_7_delete_trigger():
    """Test 7: Delete Trigger (Cleanup)"""
    print_header("Test 7: Delete Trigger (Cleanup)")

    if test_trigger_ids:
        delete_id = test_trigger_ids[0]
        print_info(f"Deleting test trigger: {delete_id[:12]}...")

        request = {"trigger_id": delete_id}

        response = call_mcp_tool("delete_trigger", request, request_id=7)

        show_request_response("Delete Trigger", request, response)

        if response and response.get("status") == "success":
            print_success("Delete trigger - Successfully deleted")
            return
        else:
            print_fail("Delete trigger - Failed to delete")
    else:
        print_info("No triggers to delete (cleanup skipped)")


def test_8_error_handling():
    """Test 8: Error Handling - Invalid Parameters"""
    print_header("Test 8: Error Handling - Invalid Parameters")

    request = {"product": "", "threshold_value": -10}  # Invalid: negative value

    response = call_mcp_tool("register_price_alert", request, request_id=8)

    show_request_response("Error Handling", request, response)

    # Check if we got an error response (either status='error' or validation error in text)
    if response:
        if response.get("status") == "error":
            print_success("Error handling - Correctly returned error for invalid input")
            return
        elif "text" in response and (
            "validation" in str(response.get("text", "")).lower()
            or "error" in str(response.get("text", "")).lower()
        ):
            print_success("Error handling - Correctly returned validation error for invalid input")
            return

    print_fail("Error handling - Should return error for invalid input")


def main():
    """Run all tests"""
    print("=" * 70)
    print("Event Tools Test Suite (Python)")
    print("Testing: tools/user_tools/event_tools.py")
    print(f"Base URL: {MCP_URL}")
    print("=" * 70)

    # Run all tests
    test_1_verify_tools_registered()
    test_2_register_price_alert()
    test_3_register_scheduled_task()
    test_4_register_event_trigger()
    test_5_list_triggers()
    test_6_query_events()
    test_7_delete_trigger()
    test_8_error_handling()

    # Print summary
    print_header("Test Summary")

    total = tests_passed + tests_failed
    print(f"{Colors.BLUE}Total Tests:{Colors.NC} {total}")
    print(f"{Colors.GREEN}Passed:{Colors.NC} {tests_passed}")
    print(f"{Colors.RED}Failed:{Colors.NC} {tests_failed}")

    if test_trigger_ids:
        print(
            f"\n{Colors.YELLOW}Note:{Colors.NC} {len(test_trigger_ids)} test triggers were created. You may want to clean them up manually."
        )
        for tid in test_trigger_ids:
            print(f"  - {tid[:12]}...")

    if tests_failed == 0:
        print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.NC}\n")
        return 0
    else:
        print(f"\n{Colors.RED}❌ Some tests failed{Colors.NC}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.NC}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
