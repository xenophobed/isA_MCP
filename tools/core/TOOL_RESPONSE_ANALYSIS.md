# Tool Response Pattern Analysis

## Objective
Analyze all MCP tools to identify common response patterns and design a unified Pydantic model system.

## Tools Reviewed (12 files, ~3100 lines)

### General Tools
1. `admin_tools.py` - System administration
2. `interaction_tools.py` - HIL interactions (ask_human, request_authorization)
3. `plan_tools.py` - Task planning and execution

### Service Tools
4. `data_analytics_tools.py` - Data analysis
5. `data_tools.py` - Data operations
6. `digital_tools.py` - Digital analytics
7. `audio_tools.py` - Audio processing
8. `image_gen_tools.py` - Image generation
9. `vision_tools.py` - Vision analysis
10. `memory_tools.py` - Memory management
11. `web_tools.py` - Web search/crawl/automation
12. `weather_tools.py` - Weather (test/mock)

## Response Pattern Categories

### 1. Standard Success Response
```python
{
    "status": "success",
    "action": "tool_name",
    "data": {...},
    "timestamp": "2025-10-18T..."
}
```

**Used by**: Most tools (web_search, memory, admin, etc.)

### 2. Error Response
```python
{
    "status": "error",
    "action": "tool_name",
    "data": {},
    "error": "Error message",
    "timestamp": "2025-10-18T..."
}
```

**Used by**: All tools for error handling

### 3. HIL Response - Ask Human
```python
{
    "status": "human_input_requested",
    "action": "ask_human",
    "data": {
        "question": "...",
        "context": "...",
        "user_id": "...",
        "instruction": "..."
    },
    "timestamp": "..."
}
```

**Used by**: interaction_tools.py

### 4. HIL Response - Request Authorization
```python
{
    "status": "authorization_requested",
    "action": "request_authorization",
    "data": {
        "request_id": "...",
        "tool_name": "...",
        "tool_args": {...},
        "reason": "...",
        "security_level": "HIGH",
        "user_id": "...",
        "expires_at": "...",
        "instruction": "..."
    },
    "timestamp": "..."
}
```

**Used by**: interaction_tools.py, security system

### 5. HIL Response - Web Automation (Credential Usage)
```python
{
    "hil_required": true,
    "status": "authorization_required",
    "action": "request_authorization",
    "message": "Found stored credentials for Google. Authorize usage?",
    "data": {
        "auth_type": "social",
        "provider": "google",
        "url": "...",
        "credential_preview": {
            "provider": "google",
            "vault_id": "vault_xxx",
            "stored_at": "2025-01-15"
        },
        "screenshot": "...",
        "details": "..."
    }
}
```

**Used by**: web_automation_service.py

### 6. HIL Response - Manual Intervention
```python
{
    "hil_required": true,
    "status": "credential_required" | "human_required",
    "action": "ask_human",
    "message": "CAPTCHA detected. Please solve manually.",
    "data": {
        "intervention_type": "captcha|login|payment|wallet|verification",
        "provider": "...",
        "url": "...",
        "screenshot": "...",
        "details": "...",
        "instructions": "..."
    }
}
```

**Used by**: web_automation_service.py

### 7. Task Planning Response
```python
{
    "status": "in_progress" | "created" | "pending",
    "action": "create_execution_plan",
    "data": {
        "plan_id": "...",
        "tasks": [...],
        "execution_mode": "parallel|sequential",
        "dependencies": {...}
    },
    "timestamp": "..."
}
```

**Used by**: plan_tools.py

### 8. Streaming Progress (SSE)
```
data: {"type": "progress", "content": "Processing...", "step": 1, "total": 5}
data: {"type": "content", "content": "Result data..."}
data: {"type": "done"}
```

**Used by**: Agent streaming, not yet in MCP tools

## Common Field Patterns

### Always Present
- `status`: str - Operation status
- `action`: str - Tool/action name
- `data`: dict - Main response data
- `timestamp`: str (ISO 8601) - Response timestamp

### Optional Fields
- `error`: str - Error message (when status="error")
- `message`: str - User-friendly message (HIL responses)
- `hil_required`: bool - Indicates HIL needed
- `billing`: dict - Billing information (deprecated, now event-driven)

### HIL-Specific Fields
- `question`: str - Question to ask user
- `context`: str - Additional context
- `instruction`: str - User instructions
- `request_id`: str - Authorization request ID
- `security_level`: str - Security level (LOW, MEDIUM, HIGH, CRITICAL)
- `intervention_type`: str - Type of intervention needed
- `provider`: str - Service provider
- `credential_preview`: dict - Preview of stored credentials

## Status Values Observed

### Standard Statuses
- `success` - Operation succeeded
- `error` - Operation failed
- `pending` - Operation pending
- `in_progress` - Operation running
- `created` - Resource created

### HIL Statuses
- `human_input_requested` - User input needed
- `authorization_requested` - Authorization needed
- `authorization_required` - Authorization required (alt naming)
- `credential_required` - Credentials needed
- `human_required` - Manual intervention needed

## Action Values by Tool

### General Tools
- `ask_human`
- `request_authorization`
- `check_security_status`
- `format_response`

### Web Tools
- `web_search`
- `web_crawl`
- `web_automation`

### Memory Tools
- `remember`
- `recall`
- `forget`
- `search_memories`

### Plan Tools
- `create_execution_plan`
- `update_task_status`
- `get_execution_status`

## Special Response Patterns

### 1. Multi-Result Responses
Some tools return multiple results with aggregation:
```python
{
    "status": "success",
    "data": {
        "total": 10,
        "results": [...],
        "aggregation": {...}
    }
}
```

### 2. Nested Service Responses
Tools calling ISA services include nested responses:
```python
{
    "status": "success",
    "data": {
        "result": {...},  # Actual result
        "metadata": {...}  # Service metadata
    }
}
```

### 3. Batch Operation Responses
```python
{
    "status": "success",
    "data": {
        "total_processed": 5,
        "successful": 4,
        "failed": 1,
        "results": [...]
    }
}
```

## Inconsistencies Found

### 1. HIL Response Format
- **interaction_tools.py**: Uses `status: "human_input_requested"`, `action: "ask_human"`
- **web_automation**: Uses `hil_required: true`, `status: "authorization_required"`, `action: "request_authorization"`
- **Inconsistency**: Two different patterns for same concept

### 2. Error Handling
- Some tools return `error` field
- Some include error in `data.error`
- Some use `error_message`

### 3. Timestamp Format
- Most use ISO 8601: `datetime.now().isoformat()`
- Some missing timestamps
- Inconsistent field name: `timestamp` vs `created_at`

### 4. Data Structure
- Some return flat `data: {...}`
- Some nest: `data: {result: {...}, metadata: {...}}`
- Inconsistent depth

## Recommendations for Pydantic Models

### Base Models Needed

1. **ToolResponse** (base class)
   - status: str
   - action: str
   - timestamp: datetime
   - data: Dict | BaseModel

2. **SuccessResponse(ToolResponse)**
   - status = "success"
   - data: Any

3. **ErrorResponse(ToolResponse)**
   - status = "error"
   - error: str
   - data: dict = {}

4. **HILResponse(ToolResponse)** (abstract)
   - hil_required: bool = True
   - message: str
   - instruction: Optional[str]

5. **AskHumanResponse(HILResponse)**
   - status: Literal["human_input_requested"]
   - action: Literal["ask_human"]
   - question: str
   - context: Optional[str]

6. **RequestAuthorizationResponse(HILResponse)**
   - status: Literal["authorization_requested"]
   - action: Literal["request_authorization"]
   - request_id: str
   - security_level: SecurityLevel
   - tool_name: str
   - tool_args: dict
   - reason: str
   - expires_at: datetime

7. **ManualInterventionResponse(HILResponse)**
   - status: Literal["credential_required", "human_required"]
   - action: Literal["ask_human"]
   - intervention_type: InterventionType
   - provider: str
   - screenshot: Optional[str]
   - oauth_url: Optional[str]

8. **ProgressResponse** (for streaming)
   - type: Literal["progress"]
   - content: str
   - step: int
   - total: int

### Enums Needed

```python
class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CREATED = "created"
    HUMAN_INPUT_REQUESTED = "human_input_requested"
    AUTHORIZATION_REQUESTED = "authorization_requested"
    AUTHORIZATION_REQUIRED = "authorization_required"
    CREDENTIAL_REQUIRED = "credential_required"
    HUMAN_REQUIRED = "human_required"

class HILAction(str, Enum):
    ASK_HUMAN = "ask_human"
    REQUEST_AUTHORIZATION = "request_authorization"

class InterventionType(str, Enum):
    CAPTCHA = "captcha"
    LOGIN = "login"
    PAYMENT = "payment"
    WALLET = "wallet"
    VERIFICATION = "verification"

class SecurityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

## Migration Strategy

### Phase 1: Create Models
1. Define base models in `tools/core/tool_models.py`
2. Add helper functions for response creation
3. Keep backward compatibility

### Phase 2: Update BaseTool
1. Add methods: `create_success()`, `create_error()`, `create_hil()`
2. Auto-serialize to JSON
3. Type hints everywhere

### Phase 3: Migrate Tools
1. Update high-value tools first (web_tools, memory_tools)
2. Replace dict responses with Pydantic models
3. Add validation

### Phase 4: Deprecate Old Pattern
1. Add deprecation warnings
2. Update documentation
3. Remove legacy support

## Next Steps

1. ✅ Complete this analysis
2. ⏳ Design Pydantic models in `tools/core/tool_models.py`
3. ⏳ Add response helpers to BaseTool
4. ⏳ Create migration guide
5. ⏳ Update 1-2 tools as proof of concept
6. ⏳ Roll out to remaining tools
