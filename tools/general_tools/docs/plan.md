# Plan Tools Documentation

## Overview

The `plan_tools.py` provides intelligent execution planning capabilities for MCP clients. It generates detailed task execution plans using AI-powered analysis, automatically determining the best execution modes and optimal task counts.

## Available Tools

### `create_execution_plan`

Creates an intelligent execution plan based on guidance, available tools, and user request. The AI automatically determines the best execution mode and optimal number of tasks.

**Function Signature:**
```python
async def create_execution_plan(
    guidance: str,
    available_tools: str,  # JSON array or comma-separated list
    request: str
) -> str
```

**Parameters:**
- `guidance` (required): Task guidance and instructions for the AI planner
- `available_tools` (required): List of available tools (JSON array format `["tool1", "tool2"]` or comma-separated `"tool1, tool2, tool3"`)
- `request` (required): The actual task request to be planned

**Returns:**
JSON response with execution plan structure including AI-determined execution mode and task count

## Execution Modes

The AI automatically selects the most appropriate execution mode based on the request:

### Sequential
Tasks run one after another in order. Each task waits for the previous one to complete.
```
Task 1 → Task 2 → Task 3
```

### Parallel
Independent tasks run simultaneously when possible.
```
Task 1 ┐
Task 2 ┼ → Results
Task 3 ┘
```

### Fan Out
One task spawns multiple parallel subtasks.
```
Task 1 → ┌ Task 2a
         ├ Task 2b
         └ Task 2c → Task 3
```

### Pipeline
Output of one task feeds directly into the next task.
```
Task 1 → Task 2 → Task 3
```

## Usage Examples

### Basic Usage
```python
# AI determines best execution approach
result = await mcp_client.call_tool("create_execution_plan", {
    "guidance": "Research and analyze products on Amazon",
    "available_tools": '["web_search", "web_crawl", "content_synthesis"]',
    "request": "Find the best gaming laptops under $1500"
})
```

### Complex Analysis Request
```python
# AI will choose appropriate execution mode and task count
result = await mcp_client.call_tool("create_execution_plan", {
    "guidance": "Perform comprehensive market research with multiple data sources and analysis approaches",
    "available_tools": '["web_search", "web_automation", "web_crawl", "pdf_analyzer", "content_synthesis", "format_response"]',
    "request": "Create a market analysis report for electric vehicles in 2024"
})
```

### Simple Information Gathering
```python
# AI will create fewer tasks for simpler requests
result = await mcp_client.call_tool("create_execution_plan", {
    "guidance": "Collect basic information from web sources",
    "available_tools": "web_search, format_response",
    "request": "What are the top 3 programming languages in 2024?"
})
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "action": "create_execution_plan",
  "data": {
    "plan_title": "Intelligent Execution Plan",
    "request": "Original user request",
    "guidance": "Provided guidance",
    "execution_mode": "sequential",
    "max_tasks_reasoning": "Brief explanation of why this number of tasks is optimal",
    "available_tools": ["tool1", "tool2", "tool3"],
    "total_tasks": 3,
    "billing": {
      "cost_usd": 0.00234,
      "input_tokens": 426,
      "output_tokens": 438,
      "total_tokens": 864,
      "operation": "chat",
      "timestamp": "2025-07-11T23:52:22.044436+00:00",
      "currency": "USD"
    },
    "tasks": [
      {
        "id": 1,
        "title": "Task Title",
        "description": "Detailed task description",
        "tools": ["web_search"],
        "execution_type": "sequential",
        "dependencies": [],
        "expected_output": "What this task should produce",
        "priority": "high"
      },
      {
        "id": 2,
        "title": "Second Task",
        "description": "Another task description",
        "tools": ["web_crawl", "content_synthesis"],
        "execution_type": "sequential",
        "dependencies": ["1"],
        "expected_output": "Expected output description",
        "priority": "medium"
      }
    ]
  },
  "timestamp": "2025-07-11T16:52:22.071592"
}
```

### Error Response
```json
{
  "status": "error",
  "action": "create_execution_plan",
  "data": {},
  "timestamp": "2025-07-11T16:52:22.071592",
  "error": "Error description"
}
```

## Task Structure

Each generated task contains:

- `id`: Unique task identifier (integer)
- `title`: Human-readable task name
- `description`: Detailed explanation of what the task does
- `tools`: Array of tools required for this task
- `execution_type`: How this specific task should be executed
- `dependencies`: Array of task IDs that must complete before this task
- `expected_output`: Description of what the task should produce
- `priority`: Task priority level ("high", "medium", "low")

## AI Decision Making

The AI planner automatically determines:

### Execution Mode Selection
- **Sequential**: For tasks with clear dependencies or when order matters
- **Parallel**: For independent tasks that can benefit from concurrent execution
- **Fan_out**: When one initial task should spawn multiple specialized subtasks
- **Pipeline**: When data flows naturally from one task to the next

### Task Count Optimization
- **Simple requests**: 2-3 tasks for straightforward information gathering
- **Medium complexity**: 3-4 tasks for analysis and comparison work
- **Complex requests**: 4-6 tasks for comprehensive research and reporting
- **Multi-domain analysis**: 5-8 tasks for extensive market research or analysis

## Best Practices

### Writing Effective Guidance
- Be specific about the domain and context
- Include any constraints or requirements
- Mention the desired output format
- Specify quality expectations

**Good Example:**
```
"You are helping a user research products for purchase. Use web tools to find products on major e-commerce sites, analyze reviews and specifications, and provide a comprehensive comparison report with rankings."
```

**Avoid:**
```
"Find some products"
```

### Tool Selection
- Provide tools that are actually available in your system
- Include tools for different phases: data collection, analysis, synthesis
- Consider the full workflow from start to finish

### Request Clarity
- Clear, specific requests help the AI choose optimal execution modes
- Include context about expected output and use case
- Mention any time constraints or quality requirements

## Integration Examples

### React Agent Integration
```python
# In your React agent loop
plan_response = await mcp_client.call_tool("create_execution_plan", {
    "guidance": agent_guidance,
    "available_tools": json.dumps(available_tool_names),
    "request": user_request
})

plan_data = json.loads(plan_response)
if plan_data["status"] == "success":
    tasks = plan_data["data"]["tasks"]
    execution_mode = plan_data["data"]["execution_mode"]
    
    # Execute tasks according to the AI-determined mode
    if execution_mode == "sequential":
        for task in tasks:
            await execute_task_sequential(task)
    elif execution_mode == "parallel":
        await execute_tasks_parallel(tasks)
    # ... handle other modes
```

### Workflow Orchestration
```python
# For complex workflows
def create_workflow_plan(user_request, available_tools):
    plan = await mcp_client.call_tool("create_execution_plan", {
        "guidance": "Create a comprehensive workflow with data collection, processing, and reporting phases",
        "available_tools": ",".join(available_tools),
        "request": user_request
    })
    
    plan_data = json.loads(plan)["data"]
    print(f"AI chose {plan_data['execution_mode']} mode with {plan_data['total_tasks']} tasks")
    print(f"Reasoning: {plan_data['max_tasks_reasoning']}")
    
    return plan_data["tasks"]
```

## Error Handling

Common error scenarios and handling:

1. **Invalid Tool Names**: Plan will only include tools from the provided list
2. **Complex Requests**: AI will automatically determine optimal task count
3. **ISA Service Issues**: Will return error status with description
4. **JSON Parsing Issues**: Fallback plan will be generated

## Performance Notes

- **Billing**: Each planning request consumes AI tokens (typically $0.002-0.010 per request)
- **Speed**: Planning typically takes 2-5 seconds depending on complexity
- **Quality**: More detailed guidance produces better task breakdowns
- **Scalability**: AI automatically scales task count based on complexity
- **Optimization**: AI considers tool capabilities when determining execution modes

## Status Tool

### `get_autonomous_status`

Get execution status for tracking progress.

**Parameters:**
- `plan_id` (optional): Plan identifier (default: "current")

**Returns:**
```json
{
  "plan_id": "current",
  "status": "in_progress",
  "completed_tasks": 2,
  "total_tasks": 3,
  "current_task": "Task name",
  "progress_percentage": 67,
  "estimated_remaining": "1-2 minutes",
  "errors": [],
  "warnings": []
}
```

## Summary

The plan_tools.py provides intelligent AI-driven execution planning that:
- **Automatically determines optimal execution modes** based on request analysis
- **Intelligently scales task count** from 2-6 tasks based on complexity
- **Provides detailed reasoning** for planning decisions
- **Supports all execution patterns** (sequential, parallel, fan_out, pipeline)
- **Integrates seamlessly with MCP workflows**
- **Handles error cases gracefully** with fallback planning
- **Optimizes for both performance and quality**

Use this tool as the "brain" for your MCP applications. Simply provide guidance and available tools - the AI handles all the complex planning decisions automatically.