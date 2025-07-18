# Event Service Documentation

## Overview

The Event Service provides background task management and event monitoring capabilities for the MCP server. It enables autonomous monitoring of web content, scheduled tasks, and intelligent event processing through integration with the chat API.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Tools     │────│  Event Sourcing  │────│  Agent Receiver │
│                 │    │     Service      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   Database       │
                    │   (Supabase)     │
                    └──────────────────┘
                                 │
                    ┌──────────────────┐
                    │   Chat API       │
                    │   Integration    │
                    └──────────────────┘
```

## Components

### 1. Event Sourcing Service (`event_sourcing_services.py`)
- **Purpose**: Core background task management and monitoring
- **Features**:
  - Web content monitoring with keyword detection
  - Scheduled task execution
  - News digest generation
  - Threshold monitoring
- **Task Types**:
  - `WEB_MONITOR`: Monitor websites for content changes
  - `SCHEDULE`: Execute tasks on schedule (daily/interval)
  - `NEWS_DIGEST`: Generate daily news summaries
  - `THRESHOLD_WATCH`: Monitor for threshold breaches

### 2. Agent Receiver (`agent_receiver.py`)
- **Purpose**: HTTP server for receiving event callbacks
- **Features**:
  - Receives events from monitoring tasks
  - Processes events with chat API
  - Stores events in database
  - Provides health and status endpoints
- **Endpoints**:
  - `POST /event_callback`: Receive event notifications
  - `GET /health`: Health check
  - `GET /status`: Service status and statistics

### 3. Database Service (`event_database_service.py`)
- **Purpose**: Database operations for events and tasks
- **Features**:
  - Store/retrieve background tasks
  - Store/retrieve events
  - Event processing status tracking
  - Statistics and analytics
- **Tables Used**:
  - `user_tasks`: Background task storage
  - `events`: Event storage and processing

### 4. MCP Tools (`event_tools.py`)
- **Purpose**: MCP integration for external access
- **Tools Available**:
  - `create_background_task`: Create monitoring tasks
  - `list_background_tasks`: List user tasks
  - `control_background_task`: Pause/resume/delete tasks
  - `get_event_service_status`: Service health and stats
  - `get_recent_events`: Retrieve recent events
  - `create_web_monitor_config`: Helper for web monitor setup

## Installation and Setup

### Prerequisites
- Python 3.8+
- Supabase database with `events` and `user_tasks` tables
- Optional: Chat API for intelligent processing

### Environment Variables
```bash
# Service Configuration
EVENT_SERVICE_PORT=8101
CHAT_API_URL=http://localhost:8080

# Database Configuration
DB_SCHEMA=dev
SUPABASE_LOCAL_URL=http://127.0.0.1:54321
SUPABASE_LOCAL_SERVICE_ROLE_KEY=your_service_role_key

# Environment
ENV=development
```

### Database Schema
The service expects these tables in your Supabase schema:

```sql
-- User Tasks Table
CREATE TABLE user_tasks (
    task_id VARCHAR PRIMARY KEY,
    task_type VARCHAR NOT NULL,
    description TEXT,
    config JSONB,
    callback_url VARCHAR,
    user_id VARCHAR,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_check TIMESTAMP
);

-- Events Table
CREATE TABLE events (
    event_id VARCHAR PRIMARY KEY,
    task_id VARCHAR,
    event_type VARCHAR NOT NULL,
    event_data JSONB,
    source VARCHAR,
    priority INTEGER DEFAULT 1,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    agent_response JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Usage Examples

### 1. Web Content Monitoring

```python
# Create web monitor configuration
config = {
    "urls": ["https://example.com/news", "https://techcrunch.com"],
    "keywords": ["AI", "machine learning", "breakthrough"],
    "check_interval_minutes": 30
}

# Create monitoring task via MCP
result = await create_background_task(
    task_type="web_monitor",
    description="Monitor tech news for AI developments",
    config=json.dumps(config),
    user_id="user123"
)
```

### 2. Scheduled Tasks

```python
# Daily report generation
config = {
    "type": "daily",
    "hour": 8,
    "minute": 0
}

result = await create_background_task(
    task_type="schedule",
    description="Daily morning report",
    config=json.dumps(config),
    user_id="user123"
)
```

### 3. News Digest

```python
# Daily news digest
config = {
    "news_urls": [
        "https://news.ycombinator.com",
        "https://techcrunch.com",
        "https://arstechnica.com"
    ],
    "hour": 9
}

result = await create_background_task(
    task_type="news_digest",
    description="Daily tech news digest",
    config=json.dumps(config),
    user_id="user123"
)
```

## Event Processing Flow

1. **Task Creation**: User creates a background task via MCP tools
2. **Monitoring**: Event Sourcing Service monitors according to task configuration
3. **Event Generation**: When conditions are met, events are generated
4. **Callback**: Events are sent to Agent Receiver via HTTP callback
5. **Processing**: Agent Receiver processes events with Chat API
6. **Storage**: Events and processing results are stored in database
7. **Notification**: Results can be retrieved via MCP tools

## Event Types

### Web Content Change
```json
{
    "event_type": "web_content_change",
    "data": {
        "url": "https://example.com",
        "content": "Content preview...",
        "keywords_found": ["AI", "breakthrough"],
        "description": "Monitor tech news",
        "user_id": "user123"
    },
    "priority": 3
}
```

### Scheduled Trigger
```json
{
    "event_type": "scheduled_trigger",
    "data": {
        "trigger_time": "2024-01-01T08:00:00",
        "schedule_config": {"type": "daily", "hour": 8},
        "description": "Daily report",
        "user_id": "user123"
    },
    "priority": 2
}
```

### Daily News Digest
```json
{
    "event_type": "daily_news_digest",
    "data": {
        "digest_date": "2024-01-01",
        "news_summaries": [
            {
                "source": "https://techcrunch.com",
                "headlines": ["AI breakthrough...", "New startup..."]
            }
        ],
        "description": "Daily tech news",
        "user_id": "user123"
    },
    "priority": 2
}
```

## Starting the Service

### Method 1: Using the Startup Script
```bash
python tools/services/event_service/start_event_service.py
```

### Method 2: Programmatically
```python
from tools.services.event_service.event_sourcing_services import init_event_sourcing_service
from tools.services.event_service.agent_receiver import start_agent_receiver

# Start services
event_service = await init_event_sourcing_service()
agent_receiver = await start_agent_receiver()

# Services are now running...

# Stop services
await event_service.stop_service()
await agent_receiver.stop_server()
```

### Method 3: Via Development Scripts
The service integrates with the existing deployment infrastructure:
```bash
# Start all services including event service
./deployment/scripts/start_dev.sh
```

## Testing

### Unit Tests
```bash
python tools/services/event_service/tests/test_event_tools.py
```

### Integration Tests
```bash
python tools/services/event_service/tests/test_event_service_integration.py
```

### Demo/Manual Testing
```bash
python tools/services/event_service/demo_monitoring.py
```

## Monitoring and Debugging

### Health Check
```bash
curl http://localhost:8101/health
```

### Service Status
```bash
curl http://localhost:8101/status
```

### View Recent Events
Use the MCP tool:
```python
result = await get_recent_events(limit=10)
```

### Database Queries
```sql
-- View all tasks
SELECT * FROM user_tasks ORDER BY created_at DESC;

-- View recent events
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;

-- Event statistics
SELECT event_type, COUNT(*) FROM events GROUP BY event_type;
```

## Integration with Chat API

The Event Service integrates with the chat API for intelligent event processing:

1. **Event Reception**: Agent Receiver receives events from monitoring tasks
2. **Prompt Generation**: Creates intelligent prompts based on event type and data
3. **API Call**: Sends prompt to chat API for processing
4. **Response Storage**: Stores AI response with event for future reference

### Chat API Prompt Examples

For web content changes:
```
🔔 **Web Content Change Alert**

A monitored website has changed and contains relevant keywords:
- URL: https://example.com
- Keywords Found: AI, breakthrough
- Content Preview: Revolutionary AI system announced...

Please analyze this change and provide:
1. A summary of what might have changed
2. The significance of this change  
3. Any recommended actions
4. Whether this requires immediate attention
```

## Error Handling

The service includes comprehensive error handling:

- **Database Errors**: Graceful fallback with logging
- **Network Errors**: Retry logic for web scraping
- **Callback Failures**: Event logging even when callbacks fail
- **Service Crashes**: Automatic monitor restart in service loop

## Performance Considerations

- **Concurrent Monitoring**: Uses asyncio for efficient concurrent monitoring
- **Rate Limiting**: Configurable check intervals to avoid overwhelming targets
- **Content Limits**: Limits scraped content size for performance
- **Database Optimization**: Uses appropriate indexes and limits

## Security

- **URL Validation**: Validates callback URLs
- **User Isolation**: Tasks are isolated by user_id
- **Content Sanitization**: Limits and sanitizes scraped content
- **Error Information**: Avoids exposing sensitive data in error messages

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check Supabase credentials and network connectivity
   - Verify database schema exists

2. **Event Service Not Starting**
   - Check port availability (default 8101)
   - Verify environment variables

3. **No Events Generated**
   - Check task configuration and keywords
   - Verify target URLs are accessible
   - Check service logs for errors

4. **Chat API Integration Issues**
   - Verify CHAT_API_URL environment variable
   - Check chat API availability
   - Review callback endpoint logs

### Logs and Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check service status:
```python
status = await get_event_service_status()
print(json.dumps(status, indent=2))
```

## Extending the Service

### Adding New Task Types

1. Add new enum value to `EventSourceTaskType`
2. Implement monitoring logic in `EventSourcingService`
3. Add event processing logic in `AgentReceiver`
4. Update documentation and tests

### Custom Event Processors

Create custom event processors by extending the `AgentReceiver`:

```python
async def custom_event_processor(self, event_data):
    # Custom processing logic
    return processed_result
```

## API Reference

See the MCP tool docstrings in `event_tools.py` for detailed API documentation:

- `create_background_task()`
- `list_background_tasks()`
- `control_background_task()`
- `get_event_service_status()`
- `get_recent_events()`
- `create_web_monitor_config()`