# How to Use Event Service

## Overview

The Event Service provides powerful background task management and event monitoring capabilities through MCP tools. It enables autonomous monitoring of web content, scheduled tasks, news digests, and intelligent event processing.

## Quick Start

### Prerequisites
- Event Service running on port 8101
- Valid user_id in the system
- MCP client configured

### Basic Workflow
1. **Create Configuration** ’ **Create Task** ’ **Monitor & Control**

## Available MCP Tools

### 1. `get_event_service_status`
Get current service health and statistics.

**Usage:**
```python
result = await mcp_client.call_tool_and_parse('get_event_service_status', {})
```

**Response:**
```json
{
  "status": "success",
  "service_status": {
    "service_running": true,
    "total_tasks": 5,
    "active_tasks": 4,
    "paused_tasks": 1
  },
  "database_statistics": {
    "events": {"total": 15, "processed": 12, "unprocessed": 3},
    "background_tasks": {"total": 5, "statuses": {"active": 4, "paused": 1}}
  }
}
```

### 2. `create_web_monitor_config`
Generate configuration for web monitoring tasks.

**Usage:**
```python
result = await mcp_client.call_tool_and_parse('create_web_monitor_config', {
    'urls': ['https://techcrunch.com', 'https://news.ycombinator.com'],
    'keywords': ['AI', 'artificial intelligence', 'machine learning'],
    'check_interval_minutes': 15
})
```

**Response:**
```json
{
  "status": "success",
  "config": {
    "urls": ["https://techcrunch.com", "https://news.ycombinator.com"],
    "keywords": ["AI", "artificial intelligence", "machine learning"],
    "check_interval_minutes": 15
  },
  "config_json": "{\"urls\":[...],\"keywords\":[...],\"check_interval_minutes\":15}"
}
```

### 3. `create_background_task`
Create background monitoring tasks.

**Supported Task Types:**
- `web_monitor` - Monitor websites for content changes
- `schedule` - Execute tasks on schedule (daily/interval)
- `news_digest` - Generate daily news summaries
- `threshold_watch` - Monitor for threshold breaches

#### Web Monitor Task
```python
task_config = {
    'urls': ['https://techcrunch.com', 'https://news.ycombinator.com'],
    'keywords': ['AI breakthrough', 'new technology', 'startup'],
    'check_interval_minutes': 30
}

result = await mcp_client.call_tool_and_parse('create_background_task', {
    'task_type': 'web_monitor',
    'description': 'Monitor tech news for AI developments',
    'config': json.dumps(task_config),
    'user_id': 'test-user-001'
})
```

#### Schedule Task
```python
schedule_config = {
    'type': 'daily',
    'hour': 9,
    'minute': 30
}

result = await mcp_client.call_tool_and_parse('create_background_task', {
    'task_type': 'schedule',
    'description': 'Daily morning report at 9:30 AM',
    'config': json.dumps(schedule_config),
    'user_id': 'test-user-001'
})
```

#### News Digest Task
```python
news_config = {
    'news_urls': ['https://techcrunch.com', 'https://arstechnica.com'],
    'hour': 8
}

result = await mcp_client.call_tool_and_parse('create_background_task', {
    'task_type': 'news_digest',
    'description': 'Daily tech news digest',
    'config': json.dumps(news_config),
    'user_id': 'test-user-001'
})
```

**Success Response:**
```json
{
  "status": "success",
  "task_id": "c9a22c51-d44c-462c-acff-0fc567d13a6d",
  "description": "Monitor tech news for AI developments",
  "task_type": "web_monitor",
  "message": "Background task 'Monitor tech news for AI developments' created successfully"
}
```

### 4. `list_background_tasks`
List all background tasks for a user.

**Usage:**
```python
# List all tasks for a user
result = await mcp_client.call_tool_and_parse('list_background_tasks', {
    'user_id': 'test-user-001'
})

# List tasks with status filter
result = await mcp_client.call_tool_and_parse('list_background_tasks', {
    'user_id': 'test-user-001',
    'status_filter': 'active'
})

# Admin view (all users)
result = await mcp_client.call_tool_and_parse('list_background_tasks', {
    'user_id': 'admin'
})
```

**Response:**
```json
{
  "status": "success",
  "service_tasks": [
    {
      "task_id": "c9a22c51-d44c-462c-acff-0fc567d13a6d",
      "task_type": "web_monitor",
      "description": "Monitor tech news for AI developments",
      "status": "active",
      "user_id": "test-user-001",
      "created_at": "2025-07-25T10:30:00Z",
      "config": {"urls": [...], "keywords": [...]}
    }
  ],
  "database_tasks": [...],
  "total_service_tasks": 1,
  "total_database_tasks": 1
}
```

### 5. `control_background_task`
Control task lifecycle (pause/resume/delete).

**Usage:**
```python
# Pause a task
result = await mcp_client.call_tool_and_parse('control_background_task', {
    'task_id': 'c9a22c51-d44c-462c-acff-0fc567d13a6d',
    'action': 'pause',
    'user_id': 'test-user-001'
})

# Resume a task
result = await mcp_client.call_tool_and_parse('control_background_task', {
    'task_id': 'c9a22c51-d44c-462c-acff-0fc567d13a6d',
    'action': 'resume',
    'user_id': 'test-user-001'
})

# Delete a task
result = await mcp_client.call_tool_and_parse('control_background_task', {
    'task_id': 'c9a22c51-d44c-462c-acff-0fc567d13a6d',
    'action': 'delete',
    'user_id': 'test-user-001'
})
```

**Response:**
```json
{
  "status": "success",
  "message": "Task pause succeeded",
  "task_id": "c9a22c51-d44c-462c-acff-0fc567d13a6d",
  "action": "pause"
}
```

### 6. `get_recent_events`
Retrieve recent events generated by background tasks.

**Usage:**
```python
# Get recent events (default limit: 20)
result = await mcp_client.call_tool_and_parse('get_recent_events', {
    'limit': 10
})

# Filter by task ID
result = await mcp_client.call_tool_and_parse('get_recent_events', {
    'limit': 5,
    'task_id': 'c9a22c51-d44c-462c-acff-0fc567d13a6d'
})

# Filter by event type
result = await mcp_client.call_tool_and_parse('get_recent_events', {
    'limit': 5,
    'event_type': 'web_content_change'
})
```

**Response:**
```json
{
  "status": "success",
  "events": [
    {
      "event_id": "cb1fdbdd-c840-4627-bd23-6a9bead50ab0",
      "task_id": "1d995f31-a523-4e30-8834-737793795632",
      "event_type": "scheduled_trigger",
      "processed": false,
      "created_at": "2025-07-25T10:45:00Z"
    }
  ],
  "count": 1,
  "filters": {
    "limit": 10,
    "task_id": null,
    "event_type": null
  }
}
```

## Real-World Examples

### Example 1: AI News Monitoring System

```python
import asyncio
import json
from tools.mcp_client import MCPClient

async def setup_ai_news_monitoring():
    client = MCPClient()
    user_id = 'your-user-id'
    
    # Step 1: Create web monitor configuration
    config_result = await client.call_tool_and_parse('create_web_monitor_config', {
        'urls': [
            'https://techcrunch.com/category/artificial-intelligence/',
            'https://news.ycombinator.com',
            'https://arstechnica.com/science/'
        ],
        'keywords': [
            'artificial intelligence',
            'machine learning',
            'neural network',
            'deep learning',
            'AI breakthrough',
            'GPT',
            'LLM'
        ],
        'check_interval_minutes': 20
    })
    
    if config_result.get('status') == 'success':
        config_json = config_result.get('config_json')
        
        # Step 2: Create monitoring task
        task_result = await client.call_tool_and_parse('create_background_task', {
            'task_type': 'web_monitor',
            'description': 'AI News Monitoring - Track latest AI developments',
            'config': config_json,
            'user_id': user_id
        })
        
        if task_result.get('status') == 'success':
            task_id = task_result.get('task_id')
            print(f" AI News Monitor created: {task_id}")
            return task_id
    
    return None

# Usage
task_id = asyncio.run(setup_ai_news_monitoring())
```

### Example 2: Daily Report System

```python
async def setup_daily_reports():
    client = MCPClient()
    user_id = 'your-user-id'
    
    # Morning news digest
    news_config = {
        'news_urls': [
            'https://techcrunch.com',
            'https://arstechnica.com',
            'https://news.ycombinator.com'
        ],
        'hour': 8  # 8 AM daily
    }
    
    digest_result = await client.call_tool_and_parse('create_background_task', {
        'task_type': 'news_digest',
        'description': 'Daily Tech News Digest - 8 AM',
        'config': json.dumps(news_config),
        'user_id': user_id
    })
    
    # Daily status report
    schedule_config = {
        'type': 'daily',
        'hour': 17,  # 5 PM daily
        'minute': 0
    }
    
    report_result = await client.call_tool_and_parse('create_background_task', {
        'task_type': 'schedule',
        'description': 'Daily Status Report - 5 PM',
        'config': json.dumps(schedule_config),
        'user_id': user_id
    })
    
    return {
        'news_digest': digest_result.get('task_id'),
        'status_report': report_result.get('task_id')
    }
```

### Example 3: Task Management Dashboard

```python
async def get_task_dashboard(user_id):
    client = MCPClient()
    
    # Get service status
    status = await client.call_tool_and_parse('get_event_service_status', {})
    
    # Get user tasks
    tasks = await client.call_tool_and_parse('list_background_tasks', {
        'user_id': user_id
    })
    
    # Get recent events
    events = await client.call_tool_and_parse('get_recent_events', {
        'limit': 20
    })
    
    dashboard = {
        'service_health': status.get('service_status', {}),
        'user_tasks': tasks.get('database_tasks', []),
        'recent_events': events.get('events', []),
        'summary': {
            'total_tasks': len(tasks.get('database_tasks', [])),
            'active_tasks': len([t for t in tasks.get('database_tasks', []) if t.get('status') == 'active']),
            'recent_events_count': len(events.get('events', []))
        }
    }
    
    return dashboard
```

## Error Handling

### Common Error Patterns

```python
async def robust_task_creation():
    client = MCPClient()
    
    try:
        result = await client.call_tool_and_parse('create_background_task', {
            'task_type': 'web_monitor',
            'description': 'Test task',
            'config': json.dumps({'urls': [...], 'keywords': [...]}),
            'user_id': 'test-user'
        })
        
        if result.get('status') == 'error':
            error_msg = result.get('message', 'Unknown error')
            
            if 'Invalid task type' in error_msg:
                print("L Task type not supported")
            elif 'User not found' in error_msg:
                print("L Invalid user ID")
            elif 'Invalid JSON' in error_msg:
                print("L Configuration format error")
            else:
                print(f"L Error: {error_msg}")
                
        else:
            print(f" Task created: {result.get('task_id')}")
            
    except Exception as e:
        print(f"L Exception: {e}")
```

### Error Response Format

```json
{
  "status": "error",
  "message": "Invalid task type: invalid_type. Valid types: ['web_monitor', 'schedule', 'news_digest', 'threshold_watch']",
  "timestamp": "2025-07-25T10:30:00Z"
}
```

## Performance Considerations

### Best Practices

1. **Task Creation**: Average response time < 100ms
2. **Batch Operations**: Use efficient task listing with filters
3. **Event Monitoring**: Regular polling vs. webhook callbacks
4. **Resource Management**: Clean up unused tasks

### Rate Limits

- Task creation: No hard limits (monitored for abuse)
- Event retrieval: Recommended limit d 100 events per request
- Status checks: Can be called frequently

## Monitoring and Debugging

### Health Checks

```python
async def monitor_service_health():
    client = MCPClient()
    
    status = await client.call_tool_and_parse('get_event_service_status', {})
    
    if status.get('status') == 'success':
        service_status = status.get('service_status', {})
        
        # Check service health
        is_running = service_status.get('service_running', False)
        active_tasks = service_status.get('active_tasks', 0)
        total_tasks = service_status.get('total_tasks', 0)
        
        health_score = (active_tasks / total_tasks * 100) if total_tasks > 0 else 100
        
        print(f"Service Running: {is_running}")
        print(f"Health Score: {health_score:.1f}%")
        print(f"Active/Total Tasks: {active_tasks}/{total_tasks}")
```

### Debug Events

```python
async def debug_task_events(task_id):
    client = MCPClient()
    
    # Get events for specific task
    events = await client.call_tool_and_parse('get_recent_events', {
        'task_id': task_id,
        'limit': 50
    })
    
    if events.get('status') == 'success':
        for event in events.get('events', []):
            print(f"Event: {event.get('event_type')} - {event.get('created_at')}")
            print(f"Processed: {event.get('processed')}")
            if event.get('processed') and event.get('agent_response'):
                print(f"Response: {event.get('agent_response')}")
```

## Integration with User Service

The Event Service automatically integrates with User Service for:

- **User Validation**: Verifies user existence before task creation
- **Permission Checks**: Validates user permissions for task types
- **Credit Management**: Automatic credit deduction for premium features
- **Usage Tracking**: Records usage for billing and analytics

### Credit Costs

| Task Type | Base Cost | Additional Factors |
|-----------|-----------|-------------------|
| `web_monitor` | 1.0 credits | +0.5 per URL, +0.1 per keyword |
| `schedule` | 0.5 credits | - |
| `news_digest` | 2.0 credits | - |
| `threshold_watch` | 1.5 credits | - |

## Troubleshooting

### Common Issues

1. **Task Not Starting**
   - Check user permissions
   - Verify task configuration
   - Check service status

2. **Events Not Generated**
   - Verify task is active
   - Check URL accessibility
   - Review keyword matching

3. **Performance Issues**
   - Reduce check intervals
   - Limit concurrent tasks
   - Monitor system resources

### Support

For issues or questions:
- Check service status with `get_event_service_status`
- Review recent events with `get_recent_events`
- Monitor task health through listing tools

## API Reference Summary

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_event_service_status` | Service health | None |
| `create_web_monitor_config` | Config helper | urls, keywords, interval |
| `create_background_task` | Task creation | task_type, config, user_id |
| `list_background_tasks` | Task listing | user_id, status_filter |
| `control_background_task` | Task control | task_id, action, user_id |
| `get_recent_events` | Event retrieval | limit, task_id, event_type |

---

**Event Service** provides powerful automation capabilities for monitoring, scheduling, and event processing. Start with simple web monitoring tasks and expand to complex multi-task workflows as needed.