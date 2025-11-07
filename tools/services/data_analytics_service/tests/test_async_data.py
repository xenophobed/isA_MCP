#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Async Data Tools with Real-time SSE Progress Monitoring
============================================================

This script tests the async background task approach for data_tools
to verify if HTTP clients can monitor real-time progress via SSE streaming.

Test Flow:
1. Call data_ingest() with operation_id -> Monitor progress via SSE
2. Call data_search() -> Get search results
3. Call data_query() with operation_id -> Monitor query progress via SSE

Expected Outcome:
 HTTP client should see real-time progress updates as data pipeline executes
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import tempfile
import os


class AsyncDataClient:
    """Client for testing async data tools with SSE monitoring"""

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
                                    "status": status
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


def create_test_csv():
    """Create a temporary test CSV file for data ingestion in Docker-accessible directory"""
    test_data = """customer_type,region,product,quantity,sales_amount,order_date
Enterprise,North America,Software License,10,15000.00,2024-01-15
Individual,Europe,Cloud Service,5,2500.50,2024-01-16
Enterprise,Asia Pacific,Consulting,8,12000.75,2024-01-17
Individual,North America,Training,3,900.00,2024-01-18
Enterprise,Europe,Support,15,22500.00,2024-01-19
Individual,Asia Pacific,Software License,2,3000.00,2024-01-20
Enterprise,North America,Cloud Service,20,10000.00,2024-01-21
Individual,Europe,Consulting,4,3200.00,2024-01-22
"""

    # Create test directory in Docker-accessible location
    # Docker mounts project root (/Users/xenodennis/Documents/Fun/isA_MCP) as /app
    # IMPORTANT: /app/cache is a Docker VOLUME, not part of the bind mount!
    # So we use /app/tmp which IS part of the bind mount
    # File is at: isA_MCP/tools/services/data_analytics_service/tests/test_async_data.py
    # Need 5 dirname calls to get to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    test_dir = os.path.join(project_root, 'tmp', 'test_data')
    os.makedirs(test_dir, exist_ok=True)

    # Create CSV file in accessible directory
    import uuid
    filename = f"test_sales_{uuid.uuid4().hex[:8]}.csv"
    host_path = os.path.join(test_dir, filename)

    # Calculate the Docker container path
    # Host: /Users/xenodennis/Documents/Fun/isA_MCP/tmp/test_data/file.csv
    # Docker: /app/tmp/test_data/file.csv
    docker_path = f"/app/tmp/test_data/{filename}"

    with open(host_path, 'w') as f:
        f.write(test_data)

    print(f"Created test CSV:")
    print(f"  Host path: {host_path}")
    print(f"  Docker path: {docker_path}")

    # Return the Docker container path since MCP server runs in Docker
    return docker_path


async def test_async_data_ingest():
    """
    Test data_ingest with real-time SSE monitoring

    This tests the 4-stage data ingestion pipeline:
    1. Processing (25%) - Data preprocessing and validation
    2. Extraction (50%) - Metadata extraction
    3. Embedding (75%) - Generate vector embeddings
    4. Storing (100%) - Store to MinIO + Vector DB
    """
    print("=" * 80)
    print("TEST 1: Data Ingestion with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncDataClient()

    # Create test CSV file
    csv_path = create_test_csv()
    print(f"Created test CSV: {csv_path}")

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"Dataset Name: sales_data_test")
    print(f"Source Path: {csv_path}")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start data ingestion with custom operation_id (in background)
        print("[STEP 1] Starting data ingestion with custom operation_id...\n")

        ingest_task = asyncio.create_task(
            client.call_tool("data_ingest", {
                "user_id": "test_user",
                "source_path": csv_path,
                "dataset_name": "sales_data_test",
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis (increased wait time)
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
        result, progress_updates = await asyncio.gather(ingest_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] Data ingestion completed successfully!")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   Pipeline ID: {result_data.get('pipeline_id', 'N/A')}")
            print(f"   Dataset Name: {result_data.get('dataset_name', 'N/A')}")
            print(f"   Rows Processed: {result_data.get('rows_processed', 0)}")
            print(f"   Columns Processed: {result_data.get('columns_processed', 0)}")
            print(f"   Data Quality Score: {result_data.get('data_quality_score', 0):.2f}")
            print(f"   Metadata Stored: {result_data.get('metadata_stored', False)}")
            print(f"   Metadata Embeddings: {result_data.get('metadata_embeddings', 0)}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time progress updates!")
            print(f"   This proves the async background task approach works for data tools.")
            print()
            print(f"   Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. Task completed too quickly (small dataset)")
            print(f"   2. httpx not installed")
            print(f"   3. SSE connection issue")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup test CSV file
        # csv_path is Docker path like /app/cache/test_data/file.csv
        # Need to convert to host path for deletion
        try:
            if csv_path.startswith('/app/'):
                # Convert Docker path to host path (need 5 dirname calls to get to project root)
                # e.g., /app/tmp/test_data/file.csv → /Users/.../isA_MCP/tmp/test_data/file.csv
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                host_path = os.path.join(project_root, csv_path[5:])  # Remove '/app/' prefix
                os.unlink(host_path)
                print(f"\n[CLEANUP] Removed test CSV: {host_path}")
            else:
                os.unlink(csv_path)
                print(f"\n[CLEANUP] Removed test CSV: {csv_path}")
        except Exception as e:
            print(f"\n[CLEANUP] Failed to remove test CSV: {e}")


async def test_async_data_query():
    """
    Test data_query with real-time SSE monitoring

    This tests the 4-stage query pipeline:
    1. Processing (25%) - Query analysis
    2. Retrieval (50%) - Data retrieval from MinIO
    3. Execution (75%) - SQL query execution
    4. Visualization (100%) - Generate visualization specs
    """
    print("\n" + "=" * 80)
    print("TEST 2: Data Query with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncDataClient()

    # Test query
    query = "total sales by region"

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"Query: '{query}'")
    print(f"Include Visualization: True")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start data query with custom operation_id (in background)
        print("[STEP 1] Starting data query with custom operation_id...\n")

        query_task = asyncio.create_task(
            client.call_tool("data_query", {
                "user_id": "test_user",
                "natural_language_query": query,
                "include_visualization": True,
                "include_analytics": False,
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis (increased wait time)
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("[STEP 2] Monitoring Real-time Query Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(query_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final Query Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] Data query completed successfully!")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   Rows Returned: {result_data.get('rows_returned', 0)}")
            print(f"   Columns Returned: {result_data.get('columns_returned', 0)}")
            print(f"   Data Source: {result_data.get('data_source', 'N/A')}")
            print(f"   SQL Executed: {result_data.get('sql_executed', 'N/A')[:100]}...")
            print(f"   Services Used: {', '.join(result_data.get('services_used', []))}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

            # Show query data preview
            query_data = result_data.get('query_data', {})
            if query_data:
                data_rows = query_data.get('data', [])
                print(f"\n   [DATA] Preview (first 3 rows):")
                for i, row in enumerate(data_rows[:3], 1):
                    print(f"      {i}. {row}")

            # Show visualization info
            if result_data.get('visualization_ready'):
                print(f"\n   [VISUALIZATION] Chart spec generated")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time query progress updates!")
            print(f"   This proves the async query pipeline works with SSE monitoring.")
            print()
            print(f"   Query Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. Query executed too quickly")
            print(f"   2. httpx not installed")
            print(f"   3. SSE connection issue")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_complete_flow():
    """
    Test complete flow: Ingest -> Search -> Query

    This tests the full data analytics lifecycle without SSE monitoring
    (for quick validation)
    """
    print("\n" + "=" * 80)
    print("TEST 3: Complete Flow (Ingest -> Search -> Query)")
    print("=" * 80)
    print()

    client = AsyncDataClient()

    # Create test CSV file
    csv_path = create_test_csv()

    try:
        # Step 1: Ingest
        print("[STEP 1] Ingesting data...")
        ingest_result = await client.call_tool("data_ingest", {
            "user_id": "test_user_flow",
            "source_path": csv_path,
            "dataset_name": "sales_data_flow"
        })

        if ingest_result.get('status') == 'success':
            result_data = ingest_result.get('data', {})
            rows = result_data.get('rows_processed', 0)
            cols = result_data.get('columns_processed', 0)
            print(f"   [SUCCESS] Ingested {rows} rows, {cols} columns")
        else:
            print(f"   [ERROR] Ingestion failed: {ingest_result.get('error')}")
            return

        # Wait for indexing
        await asyncio.sleep(2)

        # Step 2: Search
        print("\n[STEP 2] Searching data...")
        search_result = await client.call_tool("data_search", {
            "user_id": "test_user_flow",
            "search_query": "sales"
        })

        if search_result.get('status') == 'success':
            result_data = search_result.get('data', {})
            total = result_data.get('database_summary', {}).get('total_embeddings', 0)
            print(f"   [SUCCESS] Found {total} metadata embeddings")
        else:
            print(f"   [ERROR] Search failed: {search_result.get('error')}")
            return

        # Step 3: Query data
        print("\n[STEP 3] Querying data...")
        query_result = await client.call_tool("data_query", {
            "user_id": "test_user_flow",
            "natural_language_query": "total sales by region",
            "include_visualization": True
        })

        if query_result.get('status') == 'success':
            result_data = query_result.get('data', {})
            rows = result_data.get('rows_returned', 0)
            print(f"   [SUCCESS] Query returned {rows} rows")

            # Show data preview
            query_data = result_data.get('query_data', {})
            if query_data:
                data_rows = query_data.get('data', [])
                print(f"\n   [DATA] Results:")
                for i, row in enumerate(data_rows, 1):
                    print(f"      {i}. {row}")
        else:
            print(f"   [ERROR] Query failed: {query_result.get('error')}")

        print("\n[SUCCESS] Complete flow test passed!")

    except Exception as e:
        print(f"\n[ERROR] Complete flow test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup test CSV file
        # csv_path is Docker path like /app/cache/test_data/file.csv
        # Need to convert to host path for deletion
        try:
            if csv_path.startswith('/app/'):
                # Convert Docker path to host path (need 5 dirname calls to get to project root)
                # e.g., /app/tmp/test_data/file.csv → /Users/.../isA_MCP/tmp/test_data/file.csv
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                host_path = os.path.join(project_root, csv_path[5:])  # Remove '/app/' prefix
                os.unlink(host_path)
                print(f"\n[CLEANUP] Removed test CSV: {host_path}")
            else:
                os.unlink(csv_path)
                print(f"\n[CLEANUP] Removed test CSV: {csv_path}")
        except Exception as e:
            print(f"\n[CLEANUP] Failed to remove test CSV: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Async Data Tools SSE Streaming Test Suite")
    print("=" * 80)
    print("\nTesting if HTTP clients can see real-time progress via SSE")
    print("Server: http://localhost:8081")
    print("Mode: Data Analytics Pipeline")
    print()

    try:
        # Test 1: Data ingestion with SSE monitoring
        await test_async_data_ingest()

        # Test 2: Data query with SSE monitoring
        await test_async_data_query()

        # Test 3: Complete flow (quick validation)
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
i