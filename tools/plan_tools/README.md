# Enhanced Autonomous Planning and Execution Tools

## 📁 Package Structure

```
tools/plan_tools/
├── __init__.py                     # Package exports
├── plan_tools.py                   # Enhanced planner with state management
├── plan_state_manager.py           # State persistence (Redis/InMemory)
├── README.md                       # This file
├── docs/
│   ├── ENHANCED_PLAN_TOOLS_README.md
│   └── INTEGRATION_SUMMARY.md
└── tests/
    └── test_plan_enhanced.sh       # MCP endpoint test script
```

## 🚀 Features

- **Hypothesis-Driven Planning**: AI generates execution plans with solution hypotheses
- **State Management**: Persistent plan storage (Redis or in-memory fallback)
- **Dynamic Plan Adjustment**: Expand, revise, or branch plans during execution
- **Execution History**: Full audit trail of all plan events
- **Real-time Status Monitoring**: Track progress and task completion
- **Plan Branching**: Create alternative execution paths

## 📦 Migration Complete

This package has been migrated from `tools/general_tools/` and now lives in `tools/plan_tools/`.

### Changes:
- ✅ Combined enhanced features into single `plan_tools.py`
- ✅ Updated all imports to use `tools.plan_tools`
- ✅ Removed old files from `tools/general_tools/`
- ✅ Created comprehensive MCP endpoint test script

## 🔧 Usage

### Import in Code

```python
from tools.plan_tools import EnhancedAutonomousPlanner, register_plan_tools

# Create planner instance
planner = EnhancedAutonomousPlanner()

# Or register with MCP
from mcp.server.fastmcp import FastMCP
mcp = FastMCP()
register_plan_tools(mcp)
```

### Available MCP Tools

1. **create_execution_plan** - Create intelligent execution plans
2. **replan_execution** - Replan based on feedback
3. **adjust_plan** - Dynamically adjust plans (expand/revise/branch)
4. **update_task_status** - Update task status
5. **get_plan_status** - Get real-time plan status
6. **get_execution_history** - Get full execution history
7. **list_active_plans** - List all active plans

## 🧪 Testing

### Run MCP Endpoint Tests

The test script tests all MCP endpoints directly via HTTP:

```bash
# Start your MCP server first
# Then run the test script:
cd tools/plan_tools/tests
./test_plan_enhanced.sh

# Or with custom host/port:
MCP_HOST=localhost MCP_PORT=3000 ./test_plan_enhanced.sh
```

### Test Output

The script will:
- ✅ Test all 8 MCP tool endpoints
- 🎨 Display colored output for pass/fail
- 📊 Show JSON responses
- 📈 Provide summary statistics

## 💾 State Management

The planner supports two storage backends:

### In-Memory (Development)
```python
from tools.plan_tools import create_state_manager
state_manager = create_state_manager(prefer_redis=False)
```

### Redis (Production)
```python
state_manager = create_state_manager(
    prefer_redis=True,
    redis_host="localhost",
    redis_port=50055
)
```

## 📖 Documentation

See the `docs/` directory for detailed documentation:
- `ENHANCED_PLAN_TOOLS_README.md` - Complete feature documentation
- `INTEGRATION_SUMMARY.md` - Integration guide

## 🎯 Key Improvements

1. **Unified Package**: Single consolidated package instead of scattered files
2. **Enhanced Features**: Hypothesis-driven planning, branching, dynamic adjustment
3. **Better Testing**: Comprehensive MCP endpoint test script
4. **State Persistence**: Redis support with automatic fallback
5. **Full Audit Trail**: Complete execution history tracking

---

**Last Updated**: 2025-10-31
**Version**: v0.1.0 (Enhanced with state management)
