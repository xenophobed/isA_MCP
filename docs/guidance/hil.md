# Human-in-the-Loop (HIL)

Four interaction patterns for human oversight in AI workflows.

## Overview

HIL enables AI agents to request human input, approval, or review during execution. ISA MCP supports four HIL methods:

| Method | Status Returned | Use Case |
|--------|-----------------|----------|
| Authorization | `authorization_requested` | Approve/reject actions |
| Input | `human_input_requested` | Collect credentials or data |
| Review | `human_input_requested` | Review and edit content |
| Combined | `authorization_requested` | Input + authorization |

## 1. Authorization

Request approval for an action before execution.

### Example Tool Call

```python
result = await client.call_and_parse("test_authorization_low_risk", {})
```

### Response

```python
if result.get('status') == 'authorization_requested':
    print(f"HIL Type: {result['hil_type']}")  # authorization
    print(f"Action: {result['action']}")       # ask_human

    data = result['data']
    print(f"Request Action: {data['action']}")
    print(f"Risk Level: {data['risk_level']}")  # low, medium, high
    print(f"Reason: {data['reason']}")
    print(f"Options: {result['options']}")  # ['approve', 'reject']
```

**Output:**
```
HIL Type: authorization
Action: ask_human
Request Action: Update cache TTL configuration
Risk Level: low
Reason: Increase cache duration from 5 minutes to 10 minutes...
Options: ['approve', 'reject']
```

### Risk Levels

| Level | Description | Typical Actions |
|-------|-------------|-----------------|
| `low` | Minimal impact | Config changes, read operations |
| `medium` | Moderate impact | Data modifications, API calls |
| `high` | Significant impact | Deletions, payments, credentials |

## 2. Input Collection

Request user input (credentials, configuration, etc.).

### Example Tool Call

```python
result = await client.call_and_parse("test_input_credentials", {})
```

### Response

```python
if result.get('status') == 'human_input_requested':
    print(f"HIL Type: {result['hil_type']}")  # input
    print(f"Action: {result['action']}")       # ask_human

    data = result['data']
    print(f"Prompt: {data['prompt']}")
    print(f"Input Type: {data['input_type']}")
    print(f"Options: {result['options']}")  # ['submit', 'skip', 'cancel']
```

**Output:**
```
HIL Type: input
Action: ask_human
Prompt: Enter OpenAI API Key
Input Type: credentials
Options: ['submit', 'skip', 'cancel']
```

### Input Types

| Type | Description |
|------|-------------|
| `credentials` | API keys, passwords, tokens |
| `text` | Free-form text input |
| `selection` | Choose from options |
| `confirmation` | Yes/no confirmation |

## 3. Content Review

Request human review and optional editing of content.

### Example Tool Call

```python
result = await client.call_and_parse("test_review_execution_plan", {})
```

### Response

```python
if result.get('status') == 'human_input_requested':
    print(f"HIL Type: {result['hil_type']}")  # review
    print(f"Action: {result['action']}")       # ask_human

    data = result['data']
    print(f"Content Type: {data['content_type']}")  # execution_plan
    print(f"Editable: {data['editable']}")          # True/False

    # Content is structured
    content = data['content']
    print(f"Plan Title: {content['plan_title']}")
    print(f"Tasks: {content['total_tasks']}")
    print(f"Options: {result['options']}")  # ['approve', 'edit', 'reject']
```

**Output:**
```
HIL Type: review
Action: ask_human
Content Type: execution_plan
Editable: True
Plan Title: E-commerce Website Deployment Plan
Tasks: 4
Options: ['approve', 'edit', 'reject']
```

### Content Types

| Type | Description |
|------|-------------|
| `execution_plan` | Multi-step plans |
| `generated_content` | AI-generated text |
| `code` | Generated code |
| `data_changes` | Database modifications |

## 4. Combined Input + Authorization

Request input and approval in one step (e.g., payment amount + confirmation).

### Example Tool Call

```python
result = await client.call_and_parse("test_input_with_auth_payment", {})
```

### Response

```python
if result.get('status') == 'authorization_requested':
    print(f"HIL Type: {result['hil_type']}")  # input_with_authorization

    data = result['data']
    print(f"Input Prompt: {data['input_prompt']}")
    print(f"Input Type: {data['input_type']}")
    print(f"Authorization Reason: {data['authorization_reason']}")
    print(f"Risk Level: {data['risk_level']}")
```

**Output:**
```
HIL Type: input_with_authorization
Action: ask_human
Input Prompt: Enter payment amount in USD
Input Type: payment_amount
Authorization Reason: Process payment transaction of $500...
Risk Level: high
```

## Parsing HIL Responses

HIL tools return responses in `structuredContent`:

```python
def parse_hil_response(response: Dict) -> Dict:
    """Parse HIL tool response"""
    if "result" in response:
        result = response["result"]

        # HIL responses use structuredContent
        if "structuredContent" in result:
            structured = result["structuredContent"]
            if "result" in structured:
                return structured["result"]
            return structured

    return response

# Usage
raw_response = await client.call_tool("test_authorization_low_risk", {})
hil_data = parse_hil_response(raw_response)

# Check status
if hil_data.get('status') in ['authorization_requested', 'human_input_requested']:
    hil_type = hil_data['hil_type']
    options = hil_data['options']
    # Present to user...
```

## Implementing HIL in Workflows

### Agent Loop Pattern

```python
async def agent_loop(task: str):
    """Agent that handles HIL requests"""
    messages = [{"role": "user", "content": task}]

    while True:
        # Get next action from LLM
        action = await get_llm_action(messages)

        if action['type'] == 'complete':
            return action['result']

        if action['type'] == 'tool_call':
            result = await client.call_and_parse(
                action['tool'],
                action['arguments']
            )

            # Check for HIL
            if result.get('status') in ['authorization_requested', 'human_input_requested']:
                # Present to user
                user_response = await present_hil_to_user(result)

                # Add user response to context
                messages.append({
                    "role": "user",
                    "content": f"User {user_response['action']}: {user_response.get('input', '')}"
                })
            else:
                # Normal tool result
                messages.append({
                    "role": "assistant",
                    "content": f"Tool result: {json.dumps(result)}"
                })
```

### UI Integration

```python
async def present_hil_to_user(hil_data: Dict) -> Dict:
    """Present HIL request to user and get response"""
    hil_type = hil_data['hil_type']
    options = hil_data['options']

    if hil_type == 'authorization':
        # Show approval dialog
        action = hil_data['data']['action']
        reason = hil_data['data']['reason']
        risk = hil_data['data']['risk_level']

        print(f"Action: {action}")
        print(f"Reason: {reason}")
        print(f"Risk Level: {risk}")
        print(f"Options: {options}")

        choice = input("Your choice: ")
        return {"action": choice}

    elif hil_type == 'input':
        # Show input form
        prompt = hil_data['data']['prompt']
        print(f"Prompt: {prompt}")

        user_input = input("Enter value: ")
        return {"action": "submit", "input": user_input}

    elif hil_type == 'review':
        # Show review interface
        content = hil_data['data']['content']
        editable = hil_data['data']['editable']

        print(f"Content to review:")
        print(json.dumps(content, indent=2))

        if editable:
            edited = input("Edit (or press enter to approve): ")
            if edited:
                return {"action": "edit", "content": edited}

        return {"action": "approve"}
```

## Best Practices

### 1. Always Check HIL Status

```python
result = await client.call_and_parse(tool_name, args)

# Check for HIL before processing
if result.get('status') in ['authorization_requested', 'human_input_requested']:
    # Handle HIL
    ...
elif result.get('status') == 'success':
    # Normal processing
    ...
```

### 2. Use Appropriate Risk Levels

```python
# Low risk - informational actions
await request_authorization("View user profile", risk_level="low")

# High risk - destructive or financial actions
await request_authorization("Delete all data", risk_level="high")
```

### 3. Provide Clear Context

```python
# Good: Clear reason and context
await request_authorization(
    action="Send email to 1000 users",
    reason="Marketing campaign requires bulk email. This will consume API quota.",
    risk_level="medium"
)

# Bad: Vague description
await request_authorization(action="Do something", risk_level="low")
```

## HIL Tools Reference

| Tool | Type | Description |
|------|------|-------------|
| `test_authorization_low_risk` | authorization | Low risk approval |
| `test_authorization_high_risk` | authorization | High risk approval |
| `test_input_credentials` | input | Credential collection |
| `test_input_text` | input | Text input |
| `test_review_execution_plan` | review | Plan review |
| `test_review_generated_content` | review | Content review |
| `test_input_with_auth_payment` | combined | Payment with approval |

## Next Steps

- [Progress Guide](./progress.md) - Track long-running operations
- [Quick Start](./quickstart.md) - Basic client setup
