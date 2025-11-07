#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Async Web Automation with Real-time SSE Progress Monitoring
================================================================

This script tests the async background task approach for web_automation
to verify if HTTP clients can monitor real-time progress via SSE streaming.

Test Flow:
1. Call web_automation() with operation_id -> Monitor 5-step workflow via SSE
2. Test basic automation (search)
3. Test form automation (filling forms)

Expected Outcome:
 HTTP client should see real-time progress updates for all 5 steps:
   1. Capturing (20%) - Screenshot
   2. Understanding (40%) - Page analysis
   3. Detecting (60%) - UI detection
   4. Planning (80%) - Action generation
   5. Executing (100%) - Action execution
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class AsyncWebAutomationClient:
    """Client for testing async web automation with SSE monitoring"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
        self.progress_stream_url = f"{base_url}/progress"

    async def call_tool(self, tool_name: str, arguments: dict, debug: bool = False):
        """Call MCP tool"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                response_text = await response.text()

                if debug:
                    print(f"\n[DEBUG] Response length: {len(response_text)} chars")
                    print(f"[DEBUG] Response preview: {response_text[:200]}...")

                # Handle SSE format (data: {...})
                if "data: " in response_text:
                    lines = response_text.strip().split('\n')
                    result_data = None

                    # Parse all SSE messages and find the last one with result
                    for line in lines:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                # Look for result field (tool response)
                                if "result" in data:
                                    result = data["result"]
                                    if "content" in result and len(result["content"]) > 0:
                                        content = result["content"][0]
                                        if content.get("type") == "text":
                                            try:
                                                result_data = json.loads(content["text"])
                                            except json.JSONDecodeError:
                                                result_data = {"text": content["text"], "status": "unknown"}
                            except json.JSONDecodeError:
                                continue

                    if result_data:
                        if debug:
                            print(f"[DEBUG] Parsed response: {json.dumps(result_data, indent=2)[:300]}")
                        return result_data

                    if debug:
                        print(f"[DEBUG] No result found in SSE messages")
                    return {"status": "error", "error": "No result in response"}

                # Handle plain JSON
                parsed = json.loads(response_text)
                if debug:
                    print(f"[DEBUG] Plain JSON response: {json.dumps(parsed, indent=2)[:200]}")
                return parsed

    async def stream_progress_with_httpx(self, operation_id: str):
        """
        Monitor progress via SSE using httpx (supports HTTP/2)
        """
        try:
            import httpx

            stream_url = f"{self.progress_stream_url}/{operation_id}/stream"
            progress_updates = []

            print(f"[SSE] Connecting to SSE stream: {stream_url}\n")

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream('GET', stream_url) as response:
                    if response.status_code != 200:
                        print(f"[ERROR] SSE connection failed: HTTP {response.status_code}")
                        return progress_updates

                    event_type = None

                    async for line in response.aiter_lines():
                        if line.startswith('event:'):
                            event_type = line.split(':', 1)[1].strip()

                        elif line.startswith('data:'):
                            data_str = line.split(':', 1)[1].strip()
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            if event_type == 'progress':
                                progress = data.get('progress', 0)
                                message = data.get('message', '')
                                status = data.get('status', '')
                                current = data.get('current', 0)
                                total = data.get('total', 0)

                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                print(f"  [{timestamp}] {progress:5.1f}% | Stage {current}/{total} | {message} [{status}]")

                                progress_updates.append({
                                    "timestamp": timestamp,
                                    "progress": progress,
                                    "message": message,
                                    "status": status,
                                    "current": current,
                                    "total": total
                                })

                            elif event_type == 'done':
                                print(f"\n[SUCCESS] Task completed!")
                                return progress_updates

                            elif event_type == 'error':
                                print(f"\n[ERROR] Task failed: {data.get('error')}")
                                return progress_updates

            return progress_updates

        except ImportError:
            print("[ERROR] httpx not installed. Install with: pip install httpx")
            return []
        except Exception as e:
            print(f"[ERROR] SSE streaming error: {e}")
            return []


async def test_async_basic_automation():
    """
    Test basic automation (search) with real-time SSE monitoring

    This tests the 5-step workflow:
    1. Capturing (20%) - Take screenshot
    2. Understanding (40%) - Analyze page
    3. Detecting (60%) - Find elements
    4. Planning (80%) - Generate actions
    5. Executing (100%) - Execute actions
    """
    print("=" * 80)
    print("TEST 1: Basic Automation (Search) with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncWebAutomationClient()

    # Test automation task
    url = "https://www.google.com"
    task = "search for python programming"

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"URL: {url}")
    print(f"Task: '{task}'")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start automation with custom operation_id (in background)
        print("[STEP 1] Starting web automation with custom operation_id...\n")

        automation_task = asyncio.create_task(
            client.call_tool("web_automation", {
                "url": url,
                "task": task,
                "user_id": "test_user",
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("[STEP 2] Monitoring Real-time Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(automation_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] Automation completed successfully!")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   Initial URL: {result_data.get('initial_url', 'N/A')}")
            print(f"   Final URL: {result_data.get('final_url', 'N/A')}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

            # Show workflow results
            workflow = result_data.get('workflow_results', {})
            if workflow:
                print(f"\n   [WORKFLOW] 5-Step Results:")
                print(f"      Step 1 - Screenshot: {workflow.get('step1_screenshot', 'N/A')}")
                print(f"      Step 2 - Analysis: {len(str(workflow.get('step2_analysis', {})))} chars")
                print(f"      Step 3 - UI Detection: {workflow.get('step3_ui_detection', 0)} elements")
                print(f"      Step 4 - Actions: {len(workflow.get('step4_actions', []))} planned")

                step5 = workflow.get('step5_execution', {})
                print(f"      Step 5 - Execution: {step5.get('actions_executed', 0)} executed, "
                      f"{step5.get('actions_successful', 0)} successful")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time progress updates!")
            print(f"   This proves the async background task approach works for web automation.")
            print()

            # Analyze stage coverage
            stages_seen = set()
            for update in progress_updates:
                current = update.get('current', 0)
                if current > 0:
                    stages_seen.add(current)

            print(f"   Stages captured: {sorted(stages_seen)} (out of 5)")
            print(f"   Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                stage = f"{update.get('current', 0)}/{update.get('total', 5)}"
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% | Stage {stage} | {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. Task completed too quickly")
            print(f"   2. httpx not installed")
            print(f"   3. SSE connection issue")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_async_form_automation():
    """
    Test form automation with real-time SSE monitoring

    This tests a more complex workflow with multiple steps
    """
    print("\n" + "=" * 80)
    print("TEST 2: Form Automation with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncWebAutomationClient()

    # Test form filling task
    url = "https://httpbin.org/forms/post"
    task = "fill name 'John Doe', email 'john@example.com', click submit"

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"URL: {url}")
    print(f"Task: '{task}'")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start automation with custom operation_id (in background)
        print("[STEP 1] Starting form automation with custom operation_id...\n")

        automation_task = asyncio.create_task(
            client.call_tool("web_automation", {
                "url": url,
                "task": task,
                "user_id": "test_user",
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("[STEP 2] Monitoring Real-time Form Automation Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(automation_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final Form Automation Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] Form automation completed!")
            print(f"   Task: {result_data.get('task', 'N/A')}")
            print(f"   Result: {result_data.get('result_description', 'N/A')}")

            # Show action execution details
            workflow = result_data.get('workflow_results', {})
            step5 = workflow.get('step5_execution', {})
            if step5:
                print(f"\n   [EXECUTION] Details:")
                print(f"      Actions executed: {step5.get('actions_executed', 0)}")
                print(f"      Actions successful: {step5.get('actions_successful', 0)}")
                print(f"      Actions failed: {step5.get('actions_failed', 0)}")
                print(f"      Task completed: {step5.get('task_completed', False)}")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time progress updates!")
            print(f"   This proves complex form automation works with SSE monitoring.")
            print()
            print(f"   Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_complete_flow():
    """
    Test complete flow without SSE monitoring (quick validation)
    """
    print("\n" + "=" * 80)
    print("TEST 3: Quick Validation (No SSE Monitoring)")
    print("=" * 80)
    print()

    client = AsyncWebAutomationClient()

    url = "https://www.google.com"
    task = "type 'hello world' in search box"

    try:
        print(f"[TEST] URL: {url}")
        print(f"[TEST] Task: {task}\n")

        result = await client.call_tool("web_automation", {
            "url": url,
            "task": task,
            "user_id": "test_user"
        })

        if result.get('status') == 'success':
            result_data = result.get('data', {})
            print(f"[SUCCESS] Automation completed")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")
            print(f"   Success: {result_data.get('success', False)}")
        else:
            print(f"[ERROR] Failed: {result.get('error')}")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Async Web Automation SSE Streaming Test Suite")
    print("=" * 80)
    print("\nTesting if HTTP clients can see real-time progress via SSE")
    print("Server: http://localhost:8081")
    print("Workflow: 5-step automation (Capture->Understand->Detect->Plan->Execute)")
    print()

    try:
        # Test 1: Basic automation (search) with SSE monitoring
        await test_async_basic_automation()

        # Test 2: Form automation with SSE monitoring
        await test_async_form_automation()

        # Test 3: Quick validation
        await test_complete_flow()

        print("\n" + "=" * 80)
        print("[SUCCESS] All tests completed!")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
