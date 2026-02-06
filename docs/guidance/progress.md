# Progress Tracking

Real-time progress monitoring for long-running operations.

## Overview

ISA MCP provides two methods for tracking progress:

| Method | Transport | Use Case |
|--------|-----------|----------|
| SSE Streaming | Server-Sent Events | Real-time updates, recommended |
| HTTP Polling | REST API | Fallback, simpler implementation |

## SSE Streaming (Recommended)

Real-time progress updates via Server-Sent Events.

### Implementation

```python
import httpx
import json

async def stream_progress(base_url: str, operation_id: str, callback=None):
    """Monitor progress via SSE streaming"""
    stream_url = f"{base_url}/progress/{operation_id}/stream"

    async with httpx.AsyncClient(timeout=300.0) as http_client:
        async with http_client.stream('GET', stream_url) as response:
            if response.status_code != 200:
                return {"status": "error", "error": f"HTTP {response.status_code}"}

            event_type = None
            final_data = None

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
                        final_data = data
                        if callback:
                            callback(data)

                    elif event_type == 'done':
                        if final_data:
                            final_data['final_status'] = data.get('status')
                        return final_data or data

                    elif event_type == 'error':
                        return {"status": "error", "error": data.get('error')}

    return final_data or {"status": "error", "error": "Stream ended"}
```

### Complete Example

```python
async def start_and_stream(base_url: str, task_type: str,
                          duration_seconds: int = 30, steps: int = 10,
                          callback=None):
    """Start task and stream progress"""
    client = MCPClient(base_url)

    # Start task
    response = await client.call_and_parse("start_long_task", {
        "task_type": task_type,
        "duration_seconds": duration_seconds,
        "steps": steps
    })

    if response.get('status') != 'success':
        return response

    operation_id = response['data']['operation_id']

    # Stream progress
    final_data = await stream_progress(base_url, operation_id, callback)

    # Get final result
    if final_data and final_data.get('status') == 'completed':
        result = await client.call_and_parse("get_task_result", {
            "operation_id": operation_id
        })
        return result

    return final_data


# Usage
async def main():
    def on_progress(data):
        print(f"Progress: {data['progress']:.0f}% - {data['message']}")

    result = await start_and_stream(
        base_url="http://localhost:8081",
        task_type="data_analysis",
        duration_seconds=10,
        steps=5,
        callback=on_progress
    )

    print(f"Final result: {result}")
```

**Output:**
```
Progress: 20% - Processing step 1/5 - data_analysis
Progress: 40% - Processing step 2/5 - data_analysis
Progress: 60% - Processing step 3/5 - data_analysis
Progress: 80% - Processing step 4/5 - data_analysis
Progress: 100% - Processing step 5/5 - data_analysis
Progress: 100% - Completed 5 steps successfully
Final result: {...}
```

### SSE Event Types

| Event | Description |
|-------|-------------|
| `progress` | Progress update with percentage and message |
| `done` | Operation completed successfully |
| `error` | Operation failed |

### SSE Data Format

```json
{
  "progress": 60.0,
  "message": "Processing step 3/5 - data_analysis",
  "status": "running",
  "operation_id": "abc123",
  "started_at": "2026-01-08T10:00:00Z",
  "elapsed_seconds": 6.5
}
```

## HTTP Polling (Fallback)

Poll for progress updates at intervals.

### Implementation

```python
async def poll_progress(client: MCPClient, operation_id: str,
                       interval: float = 1.0, timeout: float = 300.0):
    """Poll for progress updates"""
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        progress = await client.call_and_parse("get_task_progress", {
            "operation_id": operation_id
        })

        if progress.get('status') == 'success':
            data = progress['data']
            prog = data['progress']
            msg = data['message']
            status = data['status']

            print(f"{prog:.0f}% - {msg} [{status}]")

            if status == 'completed':
                return data
            elif status == 'failed':
                return {"status": "error", "error": data.get('error')}

        await asyncio.sleep(interval)

    return {"status": "error", "error": "Timeout"}
```

### Example

```python
async def poll_example():
    client = MCPClient()

    # Start task
    response = await client.call_and_parse("start_long_task", {
        "task_type": "data_processing",
        "duration_seconds": 5,
        "steps": 3
    })

    operation_id = response['data']['operation_id']
    print(f"Task started: {operation_id[:8]}...")

    # Poll for progress
    result = await poll_progress(client, operation_id)

    if result.get('status') == 'completed':
        print("Task completed!")
        final = await client.call_and_parse("get_task_result", {
            "operation_id": operation_id
        })
        print(f"Result: {final}")
```

**Output:**
```
Task started: cc31cfe9...
33% - Processing step 1/3 - data_processing [running]
67% - Processing step 2/3 - data_processing [running]
100% - Processing step 3/3 - data_processing [running]
100% - Completed 3 steps successfully [completed]
Task completed!
```

## Progress Tools

### start_long_task

Start a long-running operation.

```python
response = await client.call_and_parse("start_long_task", {
    "task_type": "data_analysis",  # Task identifier
    "duration_seconds": 30,         # Estimated duration
    "steps": 10                     # Number of steps
})

operation_id = response['data']['operation_id']
```

### get_task_progress

Get current progress.

```python
progress = await client.call_and_parse("get_task_progress", {
    "operation_id": operation_id
})

print(f"Progress: {progress['data']['progress']}%")
print(f"Status: {progress['data']['status']}")
```

### get_task_result

Get final result after completion.

```python
result = await client.call_and_parse("get_task_result", {
    "operation_id": operation_id
})

if result['data']['status'] == 'completed':
    print(f"Output: {result['data']['output']}")
```

## Progress Data Structure

```json
{
  "operation_id": "uuid",
  "status": "running|completed|failed",
  "progress": 75.0,
  "message": "Processing step 3/4",
  "started_at": "2026-01-08T10:00:00Z",
  "updated_at": "2026-01-08T10:00:30Z",
  "elapsed_seconds": 30.5,
  "estimated_remaining": 10.2,
  "output": null
}
```

## Best Practices

### 1. Use SSE for Real-Time

```python
# Good: Real-time updates
await stream_progress(operation_id, callback=show_progress)

# Fallback: Polling (simpler but less efficient)
await poll_progress(operation_id, interval=1.0)
```

### 2. Handle Timeouts

```python
async def safe_stream(operation_id: str, timeout: float = 300.0):
    try:
        async with asyncio.timeout(timeout):
            return await stream_progress(operation_id)
    except asyncio.TimeoutError:
        return {"status": "error", "error": "Operation timed out"}
```

### 3. Provide User Feedback

```python
def on_progress(data):
    progress = data['progress']
    message = data['message']

    # Update UI
    progress_bar.set_value(progress)
    status_label.set_text(message)

    # Show ETA if available
    if data.get('estimated_remaining'):
        eta = data['estimated_remaining']
        eta_label.set_text(f"ETA: {eta:.0f}s")
```

### 4. Clean Up Resources

```python
async def monitored_operation():
    operation_id = None
    try:
        # Start operation
        response = await client.call_and_parse("start_long_task", {...})
        operation_id = response['data']['operation_id']

        # Monitor progress
        result = await stream_progress(operation_id)
        return result

    except Exception as e:
        # Cancel if needed
        if operation_id:
            await client.call_and_parse("cancel_task", {
                "operation_id": operation_id
            })
        raise
```

## API Reference

### GET /progress/{operation_id}/stream

SSE endpoint for real-time progress.

**Response Format (SSE):**
```
event: progress
data: {"progress": 50, "message": "Processing...", "status": "running"}

event: done
data: {"status": "completed"}
```

### POST /mcp (get_task_progress)

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "get_task_progress",
    "arguments": {"operation_id": "uuid"}
  }
}
```

## Next Steps

- [HIL Guide](./hil.md) - Human interaction patterns
- [Aggregator Guide](./aggregator.md) - External server progress
