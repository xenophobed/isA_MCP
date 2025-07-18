# Memory MCP Tools Documentation

## Overview

The Memory MCP Tools provide intelligent memory storage and retrieval capabilities using natural dialog processing. These tools automatically extract and store different types of memories from conversations between humans and AI assistants, supporting six distinct memory types based on cognitive science principles.

## Core Design Philosophy

The memory tools use **intelligent processing** - you simply provide `user_id` and `dialog_content`, and the system automatically:
- Analyzes the conversation content
- Extracts relevant information
- Classifies and stores it in the appropriate memory type
- Creates semantic embeddings for intelligent search

## Available MCP Tools

### Intelligent Dialog Processing Tools

These tools automatically process natural conversations and extract memories:

#### `store_factual_memory_from_dialog`
Automatically extracts and stores factual information from conversations.

**Parameters:**
- `user_id` (string): User identifier
- `dialog_content` (string): Natural dialog content between human and AI
- `importance_score` (float, optional): Importance level 0.0-1.0 (default: 0.5)

**Usage:**
```json
{
  "name": "store_factual_memory_from_dialog",
  "arguments": {
    "user_id": "user123",
    "dialog_content": "I work at TechCorp as a Senior Developer. My manager is Sarah Chen and my email is john@techcorp.com",
    "importance_score": 0.8
  }
}
```

**Keywords:** memory, fact, dialog, intelligent, extraction, natural, conversation

---

#### `store_episodic_memory_from_dialog`
Automatically extracts and stores episodic experiences from conversations.

**Parameters:**
- `user_id` (string): User identifier
- `dialog_content` (string): Natural dialog content between human and AI
- `episode_date` (string, optional): ISO date string for when the episode occurred
- `importance_score` (float, optional): Importance level 0.0-1.0 (default: 0.5)

**Usage:**
```json
{
  "name": "store_episodic_memory_from_dialog",
  "arguments": {
    "user_id": "user123",
    "dialog_content": "Yesterday we had our quarterly team meeting. Alice presented the new feature roadmap, Bob discussed the backend architecture changes, and we decided to move forward with the microservices approach. The meeting was very productive.",
    "episode_date": "2024-12-14T14:00:00Z",
    "importance_score": 0.7
  }
}
```

**Keywords:** memory, episode, dialog, intelligent, extraction, experience, event, story

---

#### `store_semantic_memory_from_dialog`
Automatically extracts and stores conceptual knowledge from conversations.

**Parameters:**
- `user_id` (string): User identifier
- `dialog_content` (string): Natural dialog content between human and AI
- `importance_score` (float, optional): Importance level 0.0-1.0 (default: 0.5)

**Usage:**
```json
{
  "name": "store_semantic_memory_from_dialog",
  "arguments": {
    "user_id": "user123",
    "dialog_content": "A microservice is an architectural pattern where applications are built as a collection of small, independent services. Each service runs in its own process and communicates via APIs. This approach provides better scalability and maintainability compared to monolithic architectures.",
    "importance_score": 0.6
  }
}
```

**Keywords:** memory, semantic, dialog, intelligent, extraction, concept, definition, knowledge

---

#### `store_procedural_memory_from_dialog`
Automatically extracts and stores step-by-step procedures from conversations.

**Parameters:**
- `user_id` (string): User identifier
- `dialog_content` (string): Natural dialog content between human and AI
- `importance_score` (float, optional): Importance level 0.0-1.0 (default: 0.5)

**Usage:**
```json
{
  "name": "store_procedural_memory_from_dialog",
  "arguments": {
    "user_id": "user123",
    "dialog_content": "To deploy our application to production, here's what we do: First, run the test suite to make sure everything passes. Then create a production build using 'npm run build'. Next, upload the build artifacts to the staging environment for final testing. After staging approval, deploy to production using our CI/CD pipeline. Finally, monitor the deployment for any issues.",
    "importance_score": 0.8
  }
}
```

**Keywords:** memory, procedure, dialog, intelligent, extraction, process, steps, how-to

---

#### `store_working_memory_from_dialog`
Automatically extracts and stores temporary task information from conversations.

**Parameters:**
- `user_id` (string): User identifier
- `dialog_content` (string): Natural dialog content between human and AI
- `current_task_context` (string, optional): JSON object with current task context
- `ttl_hours` (integer, optional): Time to live in hours (default: 24)
- `importance_score` (float, optional): Importance level 0.0-1.0 (default: 0.5)

**Usage:**
```json
{
  "name": "store_working_memory_from_dialog",
  "arguments": {
    "user_id": "user123",
    "dialog_content": "I'm currently working on the user authentication feature. I've implemented the login flow and password hashing, but I still need to add password reset functionality and two-factor authentication. The deadline is next Friday.",
    "current_task_context": "{\"project\": \"auth_system\", \"deadline\": \"2024-12-20\"}",
    "ttl_hours": 168,
    "importance_score": 0.7
  }
}
```

**Keywords:** memory, working, dialog, intelligent, extraction, task, temporary, context

---

### Direct Storage Tools (Legacy/Structured)

For when you have structured data and want direct control:

#### `store_fact`
Store structured factual information.

**Parameters:**
- `user_id` (string): User identifier
- `fact_type` (string): Type of fact (personal_info, preference, skill, knowledge, relationship)
- `subject` (string): What the fact is about
- `predicate` (string): Relationship or attribute
- `object_value` (string): Value or related entity
- `context` (string, optional): Additional context
- `confidence` (float, optional): Confidence level 0.0-1.0 (default: 0.8)

#### `store_episode`
Store episodic memory for specific events.

**Parameters:**
- `user_id` (string): User identifier
- `event_type` (string): Type of event
- `content` (string): Description of the event
- `location` (string, optional): Where it occurred
- `participants` (string, optional): JSON array of participants
- `emotional_valence` (float, optional): Emotional tone -1.0 to 1.0

#### `store_concept`
Store semantic memory for concepts.

**Parameters:**
- `user_id` (string): User identifier
- `concept_type` (string): Name of the concept
- `definition` (string): Clear definition
- `category` (string): Category or domain
- `properties` (string, optional): JSON object with properties
- `related_concepts` (string, optional): JSON array of related concepts

#### `store_procedure`
Store procedural memory for processes.

**Parameters:**
- `user_id` (string): User identifier
- `skill_type` (string): Name of the skill/procedure
- `steps` (string): JSON array of step objects
- `domain` (string): Domain category
- `difficulty_level` (string, optional): Difficulty level
- `prerequisites` (string, optional): JSON array of prerequisites

---

### Search and Retrieval Tools

#### `search_memories`
Search across all memory types using semantic similarity.

**Parameters:**
- `user_id` (string): User identifier
- `query` (string): Natural language search query
- `memory_types` (string, optional): JSON array of memory types to search
- `limit` (integer, optional): Maximum results (default: 10)
- `similarity_threshold` (float, optional): Minimum similarity 0.0-1.0 (default: 0.7)
- `importance_min` (float, optional): Minimum importance filter
- `confidence_min` (float, optional): Minimum confidence filter

**Usage:**
```json
{
  "name": "search_memories",
  "arguments": {
    "user_id": "user123",
    "query": "team meetings about authentication system",
    "memory_types": "[\"EPISODIC\", \"WORKING\"]",
    "limit": 5,
    "similarity_threshold": 0.6
  }
}
```

#### Specialized Search Tools
- `search_facts_by_type` - Search facts by type
- `search_episodes_by_participant` - Find episodes involving specific people
- `search_concepts_by_category` - Find concepts in specific categories
- `search_procedures_by_domain` - Find procedures in specific domains

---

### Session Management Tools

#### `store_session_message`
Store individual messages in conversations with intelligent processing.

**Parameters:**
- `user_id` (string): User identifier
- `session_id` (string): Unique session identifier
- `message_content` (string): Content of the message
- `message_type` (string, optional): Type ('human', 'ai', 'system')
- `role` (string, optional): Role ('user', 'assistant', 'system')
- `importance_score` (float, optional): Importance level (default: 0.5)

#### `summarize_session`
Generate intelligent summaries of conversations.

**Parameters:**
- `user_id` (string): User identifier
- `session_id` (string): Session identifier
- `force_update` (boolean, optional): Force summarization
- `compression_level` (string, optional): Level ('brief', 'medium', 'detailed')

#### `get_session_context`
Get comprehensive session context including summaries and recent messages.

**Parameters:**
- `user_id` (string): User identifier
- `session_id` (string): Session identifier
- `include_summaries` (boolean, optional): Include summaries (default: true)
- `max_recent_messages` (integer, optional): Max recent messages (default: 5)

---

### Working Memory Tools

#### `get_active_working_memories`
Get all active (non-expired) working memories.

**Parameters:**
- `user_id` (string): User identifier

**Usage:**
```json
{
  "name": "get_active_working_memories",
  "arguments": {
    "user_id": "user123"
  }
}
```

---

### Utility Tools

#### `get_memory_statistics`
Get comprehensive memory statistics and analytics.

**Parameters:**
- `user_id` (string): User identifier

#### `cleanup_expired_memories`
Remove expired working memories.

**Parameters:**
- `user_id` (string, optional): User identifier (if None, cleans all users)

#### `intelligent_memory_consolidation`
Perform intelligent memory optimization and consolidation.

**Parameters:**
- `user_id` (string): User identifier

---

## Response Format

All memory tools return standardized JSON responses:

**Success Response:**
```json
{
  "status": "success",
  "action": "store_factual_memory_from_dialog",
  "data": {
    "memory_id": "mem_123456",
    "operation": "stored",
    "message": "Successfully stored factual memory",
    "total_facts": 3,
    "stored_facts": ["John works at TechCorp", "Sarah Chen is John's manager"]
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "action": "store_factual_memory_from_dialog", 
  "data": {"user_id": "user123"},
  "error_message": "Invalid input parameters"
}
```

## Memory Types

The system automatically classifies and stores information into these memory types:

- **FACTUAL**: Structured facts about people, places, things
- **EPISODIC**: Personal experiences and events
- **SEMANTIC**: Concepts, definitions, knowledge
- **PROCEDURAL**: Step-by-step processes and procedures
- **WORKING**: Temporary task-related information (with TTL)
- **SESSION**: Conversation context and dialogue history

## Key Features

### Intelligent Processing
- Automatic content analysis and classification
- Natural language understanding
- Semantic relationship detection
- Context-aware importance scoring

### Search Capabilities
- Vector-based semantic similarity search
- Cross-memory-type search
- Similarity threshold filtering
- Importance and confidence filtering

### Memory Management
- Automatic expiration for working memories
- Intelligent consolidation and optimization
- Comprehensive analytics and statistics
- Session-based conversation tracking

### Security
- User-isolated memory storage
- Security level enforcement
- Comprehensive error handling
- Audit logging for all operations

## Testing

The memory tools include comprehensive test coverage with 47 test cases across 6 test files:
- `test_fact.py` - Factual memory tests (6 tests)
- `test_concept.py` - Semantic memory tests (8 tests)  
- `test_episode.py` - Episodic memory tests (8 tests)
- `test_procedure.py` - Procedural memory tests (6 tests)
- `test_session.py` - Session memory tests (9 tests)
- `test_working.py` - Working memory tests (8 tests)

All tests validate MCP tool functionality, intelligent processing, and error handling.