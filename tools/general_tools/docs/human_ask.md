# Human-in-the-Loop Information Request Documentation

## Overview

The `ask_human` tool provides a standardized mechanism for AI systems to request additional information or clarification from human users during operations. This creates an interactive workflow where the AI can pause execution, ask questions, receive human input, and then continue with the enhanced information.

## Tool Details

### `ask_human` (Interaction Tool)

**Purpose**: Request human input or clarification during operations

**File**: `tools/general_tools/interaction_tools.py`

**Parameters**:
- `question` (string, required): The question to ask the human user
- `context` (string, optional): Additional context about the question (default: "")
- `user_id` (string, optional): ID of the user being asked (default: "default")

## Human-in-the-Loop Workflow

### Step 1: AI Encounters Need for Human Input

When the AI system needs clarification or additional information, it calls the `ask_human` tool:

```python
# AI needs clarification about user preferences
response = await client.call_tool("ask_human", {
    "question": "What file format would you prefer for the export?",
    "context": "I found multiple export options: CSV, JSON, Excel, and PDF. Each has different advantages.",
    "user_id": "user123"
})
```

**Response from AI System**:
```json
{
  "status": "human_input_requested",
  "action": "ask_human",
  "data": {
    "question": "What file format would you prefer for the export?",
    "context": "I found multiple export options: CSV, JSON, Excel, and PDF. Each has different advantages.",
    "user_id": "user123",
    "instruction": "This request requires human input. The client should handle the interaction."
  },
  "timestamp": "2025-07-12T10:45:00Z"
}
```

### Step 2: Client Application Handles Human Interaction

The client application receives the response and presents the question to the human user:

```python
def handle_human_input_request(response):
    """Handle human input request from AI system"""
    if response["status"] == "human_input_requested":
        data = response["data"]
        
        # Display to user
        print(f"\n> AI Question: {data['question']}")
        if data['context']:
            print(f"=� Context: {data['context']}")
        
        # Get human response
        human_answer = input("\n=d Your response: ")
        
        return {
            "question": data['question'],
            "answer": human_answer,
            "user_id": data['user_id'],
            "timestamp": datetime.now().isoformat()
        }
```

### Step 3: Human Provides Response

The human user sees the question and provides their input:

```
> AI Question: What file format would you prefer for the export?
=� Context: I found multiple export options: CSV, JSON, Excel, and PDF. Each has different advantages.

=d Your response: I'll take Excel format please, with separate sheets for each data category.
```

### Step 4: AI Continues with Human Input

The AI system receives the human response and continues execution:

```python
def continue_with_human_input(human_response):
    """AI continues processing with human input"""
    answer = human_response["answer"]
    
    # AI processes the human response
    if "excel" in answer.lower():
        format_choice = "xlsx"
        use_sheets = "separate sheets" in answer.lower()
        
        print(f" Got it! I'll export as Excel format with {'separate sheets' if use_sheets else 'single sheet'}")
        
        # Continue with the export process
        return export_data(format=format_choice, separate_sheets=use_sheets)
```

## Use Case Examples

### 1. File Format Selection

```python
# AI needs to know user's preferred format
response = await client.call_tool("ask_human", {
    "question": "What file format would you prefer for the data export?",
    "context": "Available formats: CSV (simple), JSON (structured), Excel (formatted), PDF (report-style)",
    "user_id": "user123"
})

# Human responds: "Excel with charts and formatting please"
# AI continues with Excel export including visualization
```

### 2. Ambiguous Data Clarification

```python
# AI encounters ambiguous data
response = await client.call_tool("ask_human", {
    "question": "I found two 'John Smith' entries. Which one should I update?",
    "context": "John Smith (Manager, IT Dept, hired 2020) vs John Smith (Developer, Marketing, hired 2022)",
    "user_id": "admin_user"
})

# Human responds: "The IT Manager one, hired in 2020"
# AI continues with the correct record
```

### 3. Configuration Preferences

```python
# AI needs user preferences for setup
response = await client.call_tool("ask_human", {
    "question": "How would you like me to handle duplicate entries?",
    "context": "I found 15 potential duplicates. Options: Skip duplicates, Merge data, Create separate entries, or Ask for each one?",
    "user_id": "data_admin"
})

# Human responds: "Merge the data automatically, but show me a summary"
# AI continues with merge strategy
```

### 4. Security Confirmation

```python
# AI needs confirmation for sensitive operation
response = await client.call_tool("ask_human", {
    "question": "This will permanently delete 1,247 old records. Are you sure you want to proceed?",
    "context": "Records are older than 7 years and meet deletion criteria. This action cannot be undone.",
    "user_id": "data_manager"
})

# Human responds: "Yes, proceed with deletion"
# AI continues with deletion process
```

### 5. Creative Decision Making

```python
# AI needs creative input
response = await client.call_tool("ask_human", {
    "question": "What style should I use for the data visualization?",
    "context": "Data shows sales trends over time. Options: Line chart (trends), Bar chart (comparisons), Heatmap (patterns), or Interactive dashboard?",
    "user_id": "analyst"
})

# Human responds: "Interactive dashboard with drill-down capability"
# AI creates interactive visualization
```

## Complete Workflow Example

```python
async def interactive_data_processing():
    """Complete example of human-in-the-loop data processing"""
    
    print("=� Starting interactive data processing...")
    
    # Step 1: AI encounters decision point
    print("> AI: I need your input on data processing options...")
    
    format_response = await client.call_tool("ask_human", {
        "question": "What output format would you prefer?",
        "context": "I can generate: Summary report (PDF), Detailed data (Excel), API data (JSON), or Dashboard (HTML)",
        "user_id": "analyst"
    })
    
    # Step 2: Simulate human response (in real app, this comes from UI)
    human_format_choice = "Detailed Excel with separate sheets for each category"
    
    print(f"=d Human: {human_format_choice}")
    
    # Step 3: AI processes human input and continues
    print("> AI: Perfect! I'll create detailed Excel with separate sheets...")
    
    # AI encounters another decision point
    style_response = await client.call_tool("ask_human", {
        "question": "Should I include data validation rules in the Excel file?",
        "context": "This will add dropdown lists and input validation to prevent errors, but makes the file larger",
        "user_id": "analyst"
    })
    
    # Simulate human response
    human_validation_choice = "Yes, include validation rules for better data quality"
    
    print(f"=d Human: {human_validation_choice}")
    
    # Step 4: AI completes processing with all human input
    print("> AI: Generating Excel file with validation rules and separate sheets...")
    print(" Processing complete! File created with your specifications.")
    
    return {
        "format": "excel",
        "separate_sheets": True,
        "validation_rules": True,
        "human_interactions": 2,
        "status": "completed"
    }
```

## Client Implementation Patterns

### Pattern 1: Synchronous Interaction

```python
def handle_synchronous_human_input(ai_response):
    """Handle human input synchronously (blocking)"""
    if ai_response["status"] == "human_input_requested":
        data = ai_response["data"]
        
        # Display question
        print(f"\n> {data['question']}")
        if data.get('context'):
            print(f"=� {data['context']}")
        
        # Get immediate response
        answer = input("\n=d Your response: ")
        
        return answer
```

### Pattern 2: Asynchronous Interaction

```python
class AsyncHumanInteractionHandler:
    """Handle human input asynchronously (non-blocking)"""
    
    def __init__(self):
        self.pending_questions = {}
        
    async def request_human_input(self, ai_response):
        """Store question and return future"""
        if ai_response["status"] == "human_input_requested":
            data = ai_response["data"]
            question_id = f"q_{int(time.time())}"
            
            # Store for later resolution
            self.pending_questions[question_id] = {
                "question": data["question"],
                "context": data.get("context", ""),
                "user_id": data["user_id"],
                "created_at": datetime.now()
            }
            
            # Notify UI to show question
            await self.notify_ui_new_question(question_id, data)
            
            return question_id
    
    async def provide_human_answer(self, question_id, answer):
        """Provide answer to pending question"""
        if question_id in self.pending_questions:
            question = self.pending_questions.pop(question_id)
            
            # Continue AI processing with answer
            return await self.continue_ai_processing(question, answer)
```

### Pattern 3: Multi-User Interaction

```python
class MultiUserInteractionHandler:
    """Handle questions for multiple users"""
    
    def __init__(self):
        self.user_sessions = {}
    
    async def route_question_to_user(self, ai_response):
        """Route question to appropriate user"""
        data = ai_response["data"]
        user_id = data["user_id"]
        
        # Send to specific user's session
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            await session.send_question(data["question"], data.get("context"))
        else:
            # Handle offline user or queue question
            await self.queue_question_for_user(user_id, data)
```

## Response Handling Strategies

### 1. Immediate Processing

```python
# AI immediately processes human response
human_answer = get_human_response(ai_question)
result = continue_ai_processing(human_answer)
```

### 2. Validation and Retry

```python
def validate_human_response(question, answer):
    """Validate human response and retry if needed"""
    
    if question_type == "format_selection":
        valid_formats = ["csv", "json", "excel", "pdf"]
        if not any(fmt in answer.lower() for fmt in valid_formats):
            # Ask for clarification
            return ask_human("Please specify one of: CSV, JSON, Excel, or PDF")
    
    return answer
```

### 3. Context-Aware Processing

```python
def process_contextual_response(question_context, human_answer):
    """Process human response with context awareness"""
    
    if question_context == "file_format":
        # Extract format and options from natural language
        format_map = {
            "excel": {"format": "xlsx", "features": ["charts", "formatting"]},
            "csv": {"format": "csv", "features": ["simple", "lightweight"]},
            "json": {"format": "json", "features": ["structured", "api-ready"]}
        }
        
        for keyword, config in format_map.items():
            if keyword in human_answer.lower():
                return config
    
    return {"format": "default", "features": []}
```

## Error Handling

### Common Scenarios

1. **No Human Response**: Timeout handling for absent users
2. **Invalid Response**: Validation and retry mechanisms  
3. **Ambiguous Response**: Clarification requests
4. **Multiple Users**: Routing and session management

### Example Error Handling

```python
async def robust_human_interaction(question, context="", timeout=300):
    """Robust human interaction with error handling"""
    
    try:
        # Request human input
        response = await client.call_tool("ask_human", {
            "question": question,
            "context": context,
            "user_id": "current_user"
        })
        
        # Wait for human response with timeout
        human_answer = await wait_for_human_response(timeout=timeout)
        
        if not human_answer:
            # Timeout - use default or retry
            return await handle_timeout_scenario(question)
        
        # Validate response
        if not validate_response(human_answer, question):
            # Invalid - ask for clarification
            return await ask_clarification(question, human_answer)
        
        return human_answer
        
    except Exception as e:
        # Fallback to default behavior
        logger.error(f"Human interaction failed: {e}")
        return await fallback_behavior(question)
```

## Integration with Other Systems

### 1. Authorization System Integration

```python
# Combine human input with authorization
auth_response = await client.call_tool("request_authorization", {
    "tool_name": "delete_sensitive_data",
    "reason": "User requested data deletion"
})

# Ask human for additional confirmation
human_response = await client.call_tool("ask_human", {
    "question": "Please confirm the specific data categories to delete",
    "context": "This will permanently remove: user profiles, transaction history, and preferences"
})

# Process both authorization and human input
```

### 2. Monitoring and Logging

```python
# Log human interactions for audit
def log_human_interaction(question, answer, user_id):
    logger.info(f"Human interaction: User {user_id} answered '{question}' with '{answer}'")
    
    # Store in audit log
    audit_log.record({
        "type": "human_interaction",
        "question": question,
        "answer": answer, 
        "user_id": user_id,
        "timestamp": datetime.now()
    })
```

## Best Practices

### 1. Clear Questions
- Be specific and actionable
- Provide context and options
- Avoid technical jargon

### 2. Efficient Interaction
- Minimize interruptions
- Batch related questions
- Provide defaults when possible

### 3. User Experience
- Show progress indicators
- Allow easy navigation
- Support undo/retry operations

### 4. Security
- Validate all human input
- Log interactions for audit
- Implement timeout mechanisms

## Keywords

Human-in-the-loop, interactive AI, user input, clarification, decision making, workflow interruption, client interaction, question-answer, user experience

## Related Documentation

- [Interaction Tools Documentation](./interaction.md)
- [Authorization System Documentation](./authorization.md)
- Client Integration Guidelines
- User Experience Best Practices