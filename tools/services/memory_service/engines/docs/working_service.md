# Working Memory Service

## Overview

The Working Memory Service provides intelligent storage and retrieval of temporary task-related information by automatically extracting current work context, progress, and task state from raw human-AI dialog content. This service transforms conversational task discussions into structured, time-bounded working memories that automatically expire and support active task management.

## Features

- **Intelligent Task Extraction**: Automatically extracts task context, progress, and priorities from dialog
- **TTL-Based Expiration**: Automatic cleanup of expired working memories
- **Priority Management**: Task prioritization with urgency levels (1-5)
- **Progress Tracking**: Step-by-step progress monitoring with context updates
- **Task Context Management**: Rich context storage with current state, next actions, and blockers
- **Comprehensive Search**: Multiple search dimensions for active task retrieval

## Core Method: `store_working_memory()`

### Input

```python
async def store_working_memory(
    user_id: str,
    dialog_content: str,
    current_task_context: Optional[Dict[str, Any]] = None,
    ttl_seconds: int = 3600,
    importance_score: float = 0.5
) -> MemoryOperationResult
```

**Parameters:**
- `user_id` (str): User identifier for memory ownership
- `dialog_content` (str): Raw dialog between human and AI containing task information
- `current_task_context` (Optional[Dict]): Existing task context to merge with extracted data
- `ttl_seconds` (int): Time to live in seconds (default 1 hour)
- `importance_score` (float): Manual importance override (0.0-1.0, defaults to 0.5)

### Output

Returns `MemoryOperationResult` with:
- `success` (bool): Whether the operation succeeded
- `memory_id` (str): Unique identifier for the stored working memory
- `operation` (str): Operation type ("store_working_memory")
- `message` (str): Status message with extraction details

### Extracted Information

The service automatically extracts:

1. **Task ID**: Unique identifier for the task or objective
2. **Clean Content**: Concise summary of current work context
3. **Task Context**: Rich context information including:
   - `current_step`: What step in the process we're on
   - `next_actions`: List of immediate next actions
   - `interim_results`: Intermediate findings or results
   - `blocking_issues`: Issues preventing progress
   - `time_sensitivity`: Urgency level (low/medium/high/urgent)
4. **Priority**: Task priority from 1 (low) to 5 (urgent)
5. **Importance Score**: Significance level (0.0-1.0)

## Usage Examples

### Data Analysis Project

```python
from tools.services.memory_service.engines.working_engine import WorkingMemoryEngine

engine = WorkingMemoryEngine()

# Active data analysis task
analysis_dialog = """
Human: I'm working on analyzing customer data for our Q4 report. I've imported the data and cleaned it, now I need to run statistical analysis and create visualizations.

AI: Great! For your Q4 customer data analysis, I can help you with the statistical analysis and visualizations. What specific metrics are you looking to analyze?

Human: I need to analyze customer acquisition trends, retention rates, and revenue patterns. This is high priority and needs to be done by next week.
"""

result = await engine.store_working_memory(
    user_id="user123",
    dialog_content=analysis_dialog,
    ttl_seconds=604800  # 1 week
)

# Result will extract:
# - task_id: "q4_customer_analysis" 
# - clean_content: "Analyzing customer data for Q4 report including acquisition trends, retention rates, and revenue patterns"
# - task_context: {"data_status": "imported_and_cleaned", "analysis_types": ["acquisition", "retention", "revenue"], "deadline": "next_week"}
# - priority: 4 (high)
# - importance_score: 0.9
```

### Bug Fix Task

```python
# Critical production issue
bug_dialog = """
Human: There's a critical issue with our authentication service. Users are getting 500 errors when trying to log in. I've checked the database and it's running fine.

AI: That sounds urgent. Let me help you debug this. Have you checked the authentication service logs for any error patterns?

Human: Yes, I see timeout errors from the OAuth provider. I think there might be a network issue. I need to investigate the load balancer configuration and possibly implement retry logic. This needs to be fixed ASAP before peak traffic hits.
"""

result = await engine.store_working_memory(
    user_id="user123",
    dialog_content=bug_dialog,
    ttl_seconds=7200,  # 2 hours for urgent task
    importance_score=1.0
)

# Extracts urgent task with high priority and immediate actions
```

### Meeting Preparation

```python
# Weekly team meeting prep
meeting_dialog = """
Human: I need to prepare for tomorrow's team meeting. I should review the sprint progress, gather feedback on the new feature, and prepare talking points for the project timeline discussion.

AI: Good planning! Let me help you organize this. What specific aspects of the sprint progress do you want to highlight?

Human: I want to cover completed user stories, any blockers we encountered, and our velocity compared to last sprint. Also need to demo the new search feature we just finished.
"""

result = await engine.store_working_memory(
    user_id="user123",
    dialog_content=meeting_dialog,
    ttl_seconds=86400  # 1 day
)

# Creates task with meeting preparation context and action items
```

## Search Methods

The Working Memory Service provides comprehensive search capabilities:

### 1. Active Working Memories

```python
active_memories = await engine.search_active_working_memories(
    user_id="user123",
    limit=20
)
```

**Use Cases:**
- Get all current active tasks and contexts
- Dashboard view of ongoing work
- Task management overview
- Results ordered by priority (highest first), then by creation time

### 2. Task-Specific Search

```python
task_memories = await engine.search_working_memories_by_task(
    user_id="user123",
    task_id="q4_customer_analysis",
    limit=10
)
```

**Use Cases:**
- Find all memories related to a specific task
- Track task evolution and progress
- Partial matching support (e.g., "analysis" matches "q4_customer_analysis")
- Results ordered by priority

### 3. Priority-Based Search

```python
high_priority_tasks = await engine.search_working_memories_by_priority(
    user_id="user123",
    min_priority=4,
    limit=10
)
```

**Priority Levels:**
- `1`: Low priority, routine tasks
- `2`: Normal priority, standard work
- `3`: Medium priority, important but not urgent
- `4`: High priority, needs attention soon
- `5`: Urgent priority, immediate action required

**Use Cases:**
- Focus on most critical tasks
- Emergency task management
- Priority-based task organization

### 4. Time-Sensitive Search

```python
expiring_soon = await engine.search_working_memories_by_time_remaining(
    user_id="user123",
    max_hours_remaining=2.0,
    limit=10
)
```

**Use Cases:**
- Find tasks expiring soon
- Urgent deadline management
- Cleanup preparation
- Results ordered by expiration time (soonest first)

### 5. Context-Based Search

```python
project_tasks = await engine.search_working_memories_by_context_key(
    user_id="user123",
    context_key="project_type",
    limit=10
)
```

**Use Cases:**
- Find tasks with specific context attributes
- Project-based task organization
- Filter by work type, department, or other context keys
- Results ordered by priority

## Advanced Features

### TTL Extension

Extend task lifetimes when work continues:

```python
# Extend task by 2 hours
result = await engine.extend_memory_ttl(
    memory_id="task_memory_id",
    additional_seconds=7200
)
```

### Task Context Updates

Update task information as work progresses:

```python
context_updates = {
    "current_phase": "testing",
    "completion_percentage": 75,
    "blockers_resolved": ["database_connection_issue"],
    "notes": "Testing phase going well, should finish on time"
}

result = await engine.update_task_context(
    memory_id="task_memory_id",
    context_updates=context_updates
)
```

### Progress Tracking

Track detailed task progress:

```python
result = await engine.update_task_progress(
    memory_id="task_memory_id",
    current_step="integration_testing",
    progress_percentage=80.0,
    next_actions=["deploy_to_staging", "user_acceptance_testing"]
)
```

### Task Summary

Get comprehensive overview of all task-related memories:

```python
summary = await engine.get_task_summary(
    user_id="user123",
    task_id="q4_customer_analysis"
)

# Returns detailed task information:
# {
#     'task_id': 'q4_customer_analysis',
#     'total_memories': 3,
#     'highest_priority': 4,
#     'latest_update': '2024-01-15T14:30:00',
#     'current_steps': ['data_analysis', 'visualization'],
#     'next_actions': ['create_report', 'present_findings'],
#     'blocking_issues': [],
#     'status': 'active'
# }
```

### Automatic Cleanup

Clean up expired working memories:

```python
# Clean up expired memories for a user
result = await engine.cleanup_expired_memories(user_id="user123")

# Clean up all expired memories
result = await engine.cleanup_expired_memories()
```

## Task Processing Features

### Intelligent Extraction

The service automatically extracts:

1. **Task Identification**: Unique task IDs from dialog content
2. **Priority Assessment**: Task urgency from 1-5 based on language cues
3. **Context Understanding**: Current step, next actions, blockers, results
4. **Time Sensitivity**: Deadline awareness and urgency detection
5. **Progress Tracking**: Step-by-step progress and completion status

### Data Validation

The service includes robust validation:

- **Task ID Normalization**: Converts to lowercase, replaces spaces with underscores
- **Priority Clamping**: Ensures priority stays between 1-5
- **Importance Scoring**: Keeps importance between 0.0-1.0
- **TTL Management**: Validates and manages expiration times
- **Content Length**: Limits content to reasonable sizes

### Fallback Mechanisms

When extraction fails:

- **Basic Task ID**: Generated from dialog content or timestamp
- **Default Values**: Reasonable defaults for missing information
- **Graceful Degradation**: Continues operation with reduced functionality
- **Error Logging**: Detailed logging for debugging and improvement

## Integration with Base Memory Engine

The working engine extends the base memory engine, inheriting:

- **Vector Embeddings**: Automatic embedding generation for semantic search
- **Database Storage**: Supabase integration with TTL and JSON field handling
- **Access Tracking**: Usage statistics and cognitive decay modeling
- **Association Discovery**: Automatic task relationship detection

## Best Practices

### Storage
1. **Clear Descriptions**: Include specific task details and current status
2. **Context Rich**: Provide relevant background and interim results
3. **Action Oriented**: Specify next steps and blockers clearly
4. **Time Aware**: Include deadlines and time sensitivity information

### TTL Management
5. **Appropriate Duration**: Set TTL based on task length and urgency
6. **Extension Strategy**: Extend TTL for ongoing tasks
7. **Cleanup Regular**: Regular cleanup of expired memories
8. **Priority Based**: Shorter TTL for low priority, longer for critical tasks

### Search Strategy
9. **Priority First**: Check high-priority tasks before others
10. **Time Aware**: Monitor expiring tasks regularly
11. **Context Filtering**: Use context keys for organized retrieval
12. **Task Grouping**: Group related memories by task ID

## Testing

The service includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tools/services/memory_service/engines/tests/test_working_service.py -v

# Test results: ✅ 16 passed, 0 failed
```

**Test Coverage:**
- ✅ Intelligent dialog processing with task extraction
- ✅ TTL management and expiration handling
- ✅ All 4 search methods with realistic task scenarios
- ✅ Task context updates and progress tracking
- ✅ Priority-based organization and filtering
- ✅ Time-sensitive task management
- ✅ Data validation and error handling
- ✅ Complex task extraction with detailed context

## Error Handling

The service gracefully handles:

- **Extraction Failures**: Falls back to basic task creation
- **Invalid Input**: Applies defaults and validation
- **Database Errors**: Returns detailed error messages
- **TTL Issues**: Handles expiration and extension errors
- **Network Issues**: Logs errors and returns failure status

## Performance Considerations

- **TTL Efficiency**: Automatic expiration reduces storage overhead
- **Priority Indexing**: Optimized queries for priority-based searches
- **Context Management**: Efficient JSON storage and retrieval
- **Async Operations**: All operations are non-blocking
- **Memory Efficient**: Handles complex task discussions without memory issues
- **Query Optimization**: Database searches use appropriate indexing strategies

## Comparison with Other Memory Types

| Feature | Episodic | Factual | Procedural | Semantic | Working |
|---------|----------|---------|------------|----------|----------|
| **Content Type** | Events & experiences | Facts & statements | Procedures & workflows | Concepts & knowledge | Tasks & progress |
| **Structure** | Temporal narrative | Subject-predicate-object | Step-by-step instructions | Definitions & relationships | Context & actions |
| **Key Fields** | participants, location, emotional_valence | subject, predicate, object_value | steps, prerequisites, difficulty_level | concept_type, definition, properties | task_id, task_context, priority, expires_at |
| **Search Focus** | When, where, who | What, confidence, verification | How, success_rate, tools_needed | Why, abstraction_level, relationships | Current, urgent, progress |
| **Use Cases** | Personal history, context | Knowledge base, assertions | Task execution, learning | Understanding, conceptual frameworks | Active task management, deadlines |
| **Time Behavior** | Permanent with decay | Permanent with updates | Permanent with versioning | Permanent with expansion | Temporary with TTL |

The Working Memory Service excels at managing temporary, task-oriented information, making it ideal for:

- **Active Project Management**: Current tasks and their progress
- **Meeting Preparation**: Temporary preparation contexts
- **Issue Tracking**: Bug fixes and urgent problems
- **Deadline Management**: Time-sensitive work organization
- **Context Switching**: Maintaining state between work sessions
- **Task Prioritization**: Urgency-based work organization