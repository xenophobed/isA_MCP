# Enhanced Plan Tools Documentation

## Overview

Enhanced autonomous planning tools inspired by the **MCP Sequential Thinking** pattern, adding powerful state management, dynamic adjustment, and execution tracking capabilities to your planning system.

## 🎯 Key Enhancements from Sequential Thinking Pattern

### 1. **Execution History Tracking**
```typescript
// Sequential Thinking Pattern
private thoughtHistory: ThoughtData[] = [];
private branches: Record<string, ThoughtData[]> = {};
```

```python
# Our Implementation
class PlanStateManager:
    def add_execution_event(plan_id, event) -> bool
    def get_execution_history(plan_id) -> List[Dict]
    def get_branches(plan_id) -> List[Dict]
```

**Benefit**: Complete audit trail of all plan modifications and task updates.

---

### 2. **Dynamic Plan Adjustment**
```typescript
// Sequential Thinking: Thoughts can adjust total mid-execution
if (validatedInput.thoughtNumber > validatedInput.totalThoughts) {
  validatedInput.totalThoughts = validatedInput.thoughtNumber;
}
```

```python
# Our Implementation
async def adjust_execution_plan(
    plan_id: str,
    adjustment_type: str,  # "expand", "revise", "branch"
    ...
)
```

**Benefit**: Plans adapt to discoveries during execution - no rigid constraints.

---

### 3. **Plan Branching & Revision**
```typescript
// Sequential Thinking Pattern
interface ThoughtData {
  isRevision?: boolean;
  revisesThought?: number;
  branchFromThought?: number;
  branchId?: string;
}
```

```python
# Our Implementation
{
    "is_revision": True,
    "revises_task_id": 2,
    "branch_from_task_id": 3,
    "branch_id": "branch_abc123"
}
```

**Benefit**: Support non-linear problem solving with backtracking.

---

### 4. **Rich Visual Feedback**
```typescript
// Sequential Thinking Pattern
const prefix = isRevision ? chalk.yellow('🔄 Revision') :
               branchFromThought ? chalk.green('🌿 Branch') :
               chalk.blue('💭 Thought');
```

```python
# Our Implementation
def _format_task_status(task, status):
    emojis = {
        "pending": "⏳", "in_progress": "🔄",
        "completed": "✅", "failed": "❌",
        "revision": "🔄", "branch": "🌿"
    }
```

**Benefit**: Immediate, contextual feedback during execution.

---

### 5. **State Persistence**
```python
# Hybrid Storage Architecture
┌────────────────────────────────┐
│  PlanStateManager (Abstract)   │
└────────┬───────────────────────┘
         │
    ┌────┴─────┐
    │          │
┌───▼────┐  ┌─▼──────┐
│ Redis  │  │InMemory│
│Backend │  │Backend │
└────────┘  └────────┘
```

**Benefit**: Graceful degradation - works with or without Redis.

---

## 🏗️ Architecture

### Components

1. **plan_state_manager.py**
   - Abstract interface for state storage
   - InMemoryStateStore (fallback, development)
   - RedisStateStore (production, persistence)
   - Factory function with auto-detection

2. **plan_tools_enhanced.py**
   - EnhancedAutonomousPlanner class
   - Hypothesis-driven planning
   - Dynamic adjustment capabilities
   - Real-time status monitoring

3. **MCP Tools Registration**
   - `create_execution_plan_v2` - Enhanced plan creation
   - `adjust_plan` - Dynamic plan modification
   - `update_task_status` - Task status updates
   - `get_plan_status` - Real-time monitoring
   - `get_execution_history` - Audit trail
   - `list_active_plans` - Plan management

---

## 📦 Storage Backend Comparison

| Backend | Persistence | Distributed | Use Case | Setup Required |
|---------|-------------|-------------|----------|----------------|
| **InMemory** | ❌ No | ❌ No | Development, Testing | None |
| **Redis** | ✅ Yes | ✅ Yes | Production, Multi-instance | Redis gRPC Service |

### Auto-Detection Logic

```python
# Automatically chooses best available backend
planner = EnhancedAutonomousPlanner()  # Auto-detects
# or
state_mgr = create_state_manager(prefer_redis=True)
planner = EnhancedAutonomousPlanner(state_manager=state_mgr)
```

**Selection Priority:**
1. Try Redis if `prefer_redis=True` and service available
2. Fallback to InMemory if Redis unavailable
3. Log warning about persistence limitations

---

## 🚀 Usage Examples

### Example 1: Basic Plan Creation

```python
from tools.general_tools.plan_tools_enhanced import EnhancedAutonomousPlanner

planner = EnhancedAutonomousPlanner()

result = await planner.create_execution_plan(
    guidance="Build a data pipeline with error handling",
    available_tools=["extractor", "transformer", "loader", "validator"],
    request="Create ETL pipeline for customer data"
)

plan = json.loads(result)['data']
plan_id = plan['plan_id']
```

**Output:**
```
🎯 Starting intelligent planning: Create ETL pipeline for customer data
📋 Plan ID: plan_a1b2c3d4
✅ Successfully parsed JSON plan
✅ Plan saved with 4 tasks

============================================================
📊 PLAN SUMMARY
============================================================
Hypothesis: Sequential ETL pipeline with validation at each stage
Execution Mode: pipeline
Total Tasks: 4

Tasks:
  ⏳ Task 1/4 - Extract Customer Data
  ⏳ Task 2/4 - Transform Data Format
  ⏳ Task 3/4 - Validate Data Quality
  ⏳ Task 4/4 - Load to Database
============================================================
```

---

### Example 2: Update Task Status

```python
# Start task
planner.update_task_status(plan_id, 1, "in_progress")

# Complete with result
planner.update_task_status(
    plan_id, 1, "completed",
    {"records_extracted": 10000}
)
```

**Output:**
```
🔄 Task 1/4 - Extract Customer Data
✅ Task 1/4 - Extract Customer Data
```

---

### Example 3: Dynamic Plan Expansion

```python
# Task failed - add recovery tasks
new_tasks = [
    {
        "title": "Retry Failed Records",
        "description": "Retry extraction for failed records",
        "tools": ["retry_service", "extractor"],
        "execution_type": "sequential",
        "dependencies": [1],
        "expected_output": "Failed records recovered",
        "priority": "high"
    }
]

await planner.adjust_execution_plan(
    plan_id=plan_id,
    adjustment_type="expand",
    new_tasks=new_tasks,
    reasoning="Initial extraction had 5% failure rate"
)
```

**Output:**
```
🔧 Adjusting plan plan_a1b2c3d4: expand
✅ Plan expanded with 1 new tasks
```

---

### Example 4: Create Alternative Branch

```python
# Current approach failing - try alternative
branch_tasks = [
    {
        "title": "Use Alternative Data Source",
        "description": "Switch to backup API endpoint",
        "tools": ["backup_api", "extractor"],
        ...
    }
]

await planner.adjust_execution_plan(
    plan_id=plan_id,
    adjustment_type="branch",
    task_id=1,
    new_tasks=branch_tasks,
    reasoning="Primary API consistently failing"
)
```

**Output:**
```
🔧 Adjusting plan plan_a1b2c3d4: branch
✅ Branch branch_x9y8z7 created from task 1
```

---

### Example 5: Real-Time Status Monitoring

```python
planner.get_plan_status(plan_id)
```

**Output:**
```
============================================================
📊 PLAN STATUS: plan_a1b2c3d4
============================================================
Overall: IN_PROGRESS
Progress: 50.0% (2/4 tasks)
Current: Validate Data Quality
✅ Completed: 2 | 🔄 In Progress: 1 | ⏳ Pending: 1
============================================================
```

---

### Example 6: Execution History Audit Trail

```python
history = planner.state_manager.get_execution_history(plan_id)

for event in history:
    print(f"{event['event_type']}: {event['timestamp']}")
```

**Output:**
```
plan_created: 2025-10-18T10:00:00.123Z
task_status_updated: 2025-10-18T10:01:15.456Z
task_status_updated: 2025-10-18T10:02:30.789Z
plan_expanded: 2025-10-18T10:03:45.012Z
branch_created: 2025-10-18T10:05:00.345Z
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Redis Backend (Optional)
REDIS_HOST=localhost
REDIS_PORT=50055

# Storage Preference
PLAN_STORAGE_BACKEND=redis  # or 'memory'
```

### Programmatic Configuration

```python
# Force in-memory (development)
from tools.general_tools.plan_state_manager import InMemoryStateStore
planner = EnhancedAutonomousPlanner(
    state_manager=InMemoryStateStore()
)

# Force Redis (production)
from tools.general_tools.plan_state_manager import RedisStateStore
planner = EnhancedAutonomousPlanner(
    state_manager=RedisStateStore(
        redis_host="redis.example.com",
        redis_port=50055
    )
)

# Auto-detect (recommended)
planner = EnhancedAutonomousPlanner()  # Uses factory
```

---

## 📊 New MCP Tools

### 1. `create_execution_plan_v2`

Enhanced plan creation with hypothesis-driven approach.

**Parameters:**
- `guidance` (str): Task guidance
- `available_tools` (str): JSON array or comma-separated
- `request` (str): Task request
- `plan_id` (str, optional): Custom plan ID

**Returns:** Plan with hypothesis, verification strategy, and tasks

---

### 2. `adjust_plan`

Dynamically modify plans during execution.

**Parameters:**
- `plan_id` (str): Plan to adjust
- `adjustment_type` (str): "expand", "revise", or "branch"
- `task_id` (int, optional): Task to adjust
- `new_tasks_json` (str, optional): JSON array of new tasks
- `reasoning` (str): Reason for adjustment

**Returns:** Updated plan

---

### 3. `update_task_status`

Update task execution status.

**Parameters:**
- `plan_id` (str): Plan ID
- `task_id` (int): Task ID
- `status` (str): "pending", "in_progress", "completed", "failed", "blocked"
- `result_json` (str, optional): Result data

**Returns:** Updated task info

---

### 4. `get_plan_status`

Get real-time plan execution status.

**Parameters:**
- `plan_id` (str): Plan ID

**Returns:** Status summary with progress metrics

---

### 5. `get_execution_history`

Retrieve complete execution audit trail.

**Parameters:**
- `plan_id` (str): Plan ID

**Returns:** List of all execution events

---

### 6. `list_active_plans`

List all active plans in storage.

**Returns:** Array of plan IDs

---

## 🧪 Testing

Run the example script:

```bash
cd /Users/xenodennis/Documents/Fun/isA_MCP
python tools/general_tools/examples/enhanced_plan_example.py
```

Expected output:
- ✅ Plan creation with state tracking
- ✅ Task status updates with visual feedback
- ✅ Real-time status monitoring
- ✅ Dynamic plan expansion
- ✅ Plan branching
- ✅ Execution history retrieval
- ✅ Active plan listing
- ✅ Storage backend comparison

---

## 🆚 Comparison: Original vs Enhanced

| Feature | Original plan_tools.py | Enhanced plan_tools.py |
|---------|----------------------|----------------------|
| **Plan Creation** | ✅ Yes | ✅ Yes (with hypothesis) |
| **State Persistence** | ❌ No | ✅ Yes (Redis/Memory) |
| **Execution History** | ❌ No | ✅ Full audit trail |
| **Dynamic Adjustment** | ❌ No | ✅ Expand/Revise/Branch |
| **Task Tracking** | ⚠️ Mock only | ✅ Real-time |
| **Branching** | ❌ No | ✅ Alternative paths |
| **Visual Feedback** | ⚠️ Basic | ✅ Rich with emojis |
| **Replanning** | ✅ Yes | ✅ Yes (preserved) |
| **Input Validation** | ⚠️ Minimal | ✅ Comprehensive |
| **Storage Backend** | ❌ None | ✅ Pluggable (Redis/Memory) |

---

## 🔄 Migration Guide

### Using Enhanced Tools Alongside Original

Both implementations can coexist:

```python
# Original tools (backward compatible)
from tools.general_tools.plan_tools import register_plan_tools
register_plan_tools(mcp)

# Enhanced tools (new features)
from tools.general_tools.plan_tools_enhanced import register_enhanced_plan_tools
register_enhanced_plan_tools(mcp)
```

### Gradual Migration

1. **Week 1**: Deploy enhanced tools as `*_v2` tools
2. **Week 2**: Test with production workloads
3. **Week 3**: Migrate critical workflows
4. **Week 4**: Deprecate original tools

---

## 🐛 Troubleshooting

### Redis Connection Failed

```
⚠️ Redis unavailable, falling back to InMemory: ...
```

**Solution**: Check Redis gRPC service is running:
```bash
# Check service
grpcurl -plaintext localhost:50055 list

# Or start service
docker-compose up redis-service
```

---

### Plan Not Found

```
❌ Plan plan_abc123 not found
```

**Cause**: Plan expired (24h TTL) or using InMemory without persistence

**Solution**:
- Use Redis for persistence
- Increase TTL in `RedisStateStore.save_plan()`
- Re-create plan

---

### Import Error

```
ImportError: Failed to import isa_common.redis_client
```

**Solution**: Install isa-common package:
```bash
pip install -e /path/to/isA_Cloud/isA_common
```

---

## 📚 Additional Resources

- **Sequential Thinking MCP**: https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
- **isa-common Redis Client**: `/Users/xenodennis/Documents/Fun/isA_Cloud/isA_common/examples/redis_client_examples.py`
- **Original plan_tools.py**: `/Users/xenodennis/Documents/Fun/isA_MCP/tools/general_tools/plan_tools.py`

---

## 🤝 Contributing

Enhancements welcome! Key areas:

1. **Additional Storage Backends**: NATS KV, PostgreSQL, etc.
2. **Plan Visualization**: Generate diagrams from plan structure
3. **Metrics & Analytics**: Track plan success rates
4. **Plan Templates**: Pre-built templates for common workflows

---

## 📝 License

Same as parent project (isA_MCP)

---

**Generated**: 2025-10-18
**Version**: 1.0.0
**Inspired by**: MCP Sequential Thinking Pattern
