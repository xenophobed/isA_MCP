# Memory Service Design Documentation

## Overview

The Memory Service provides a comprehensive memory management system with support for multiple memory types, each optimized for different use cases and cognitive patterns. The service is built using MCP (Model Context Protocol) tools and provides both storage and retrieval capabilities with advanced search functionality.

## Memory Types

### 1. Factual Memory (FACTUAL)
**Purpose**: Store structured facts and relationships between entities.

**Structure**:
- `subject`: The main entity or topic
- `predicate`: The relationship or property
- `object_value`: The value or related entity
- `fact_type`: Category of the fact (person, organization, etc.)
- `context`: Additional contextual information
- `confidence`: Confidence level (0.0 to 1.0)

**Use Cases**:
- Personal information about contacts
- Business relationships
- Data points and statistics
- Entity attributes and properties

**Example**:
```json
{
  "user_id": "user123",
  "fact_type": "person",
  "subject": "Sarah Chen",
  "predicate": "role",
  "object_value": "Data Scientist",
  "context": "Team member information",
  "confidence": 0.9
}
```

### 2. Semantic Memory (SEMANTIC)
**Purpose**: Store concepts, definitions, and knowledge with rich relationships.

**Structure**:
- `concept_type`: The main concept or term
- `definition`: Detailed explanation or definition
- `category`: Classification category
- `properties`: JSON object with additional attributes
- `related_concepts`: JSON array of related concepts

**Use Cases**:
- Technical documentation
- Business terminology
- Academic concepts
- Domain-specific knowledge

**Example**:
```json
{
  "user_id": "user123",
  "concept_type": "RESTful API",
  "definition": "Representational State Transfer API is an architectural style for designing networked applications using HTTP methods",
  "category": "software_architecture",
  "properties": {
    "complexity": "intermediate",
    "domain": "computer_science",
    "applications": ["web_development", "data_processing"]
  },
  "related_concepts": ["HTTP", "JSON", "Web Services"]
}
```

### 3. Episodic Memory (EPISODIC)
**Purpose**: Store events, experiences, and time-bound episodes.

**Structure**:
- `event_type`: Type of event (meeting, learning, milestone, etc.)
- `content`: Description of the event
- `location`: Where the event occurred
- `participants`: JSON array of participants
- `emotional_valence`: Emotional tone (-1.0 to 1.0)

**Use Cases**:
- Meeting records
- Learning experiences
- Project milestones
- Personal experiences

**Example**:
```json
{
  "user_id": "user123",
  "event_type": "meeting",
  "content": "Weekly team standup: discussed Q4 goals, reviewed sprint progress",
  "location": "Conference Room A",
  "participants": ["Alice Chen", "Bob Smith", "Carol Johnson"],
  "emotional_valence": 0.2
}
```

### 4. Procedural Memory (PROCEDURAL)
**Purpose**: Store step-by-step procedures, workflows, and skills.

**Structure**:
- `skill_type`: Name of the skill or procedure
- `steps`: JSON array of ordered steps
- `domain`: Domain or field (software_engineering, cooking, etc.)
- `difficulty_level`: Complexity level (beginner, intermediate, advanced)
- `prerequisites`: JSON array of required knowledge or skills

**Use Cases**:
- Standard operating procedures
- Recipes and instructions
- Workflow documentation
- Training materials

**Example**:
```json
{
  "user_id": "user123",
  "skill_type": "Software Development Process",
  "steps": [
    {"step": 1, "description": "Gather requirements", "duration": "30 min"},
    {"step": 2, "description": "Design solution", "duration": "2 hours"}
  ],
  "domain": "software_engineering",
  "difficulty_level": "intermediate",
  "prerequisites": ["Programming knowledge", "Version control"]
}
```

### 5. Session Memory (SESSION)
**Purpose**: Store conversation context and dialogue state.

**Structure**:
- `session_id`: Unique identifier for the session
- `content`: Current interaction content
- `interaction_sequence`: Order in the conversation
- `conversation_state`: JSON object with context variables
- `session_type`: Type of session (chat, support, meeting, etc.)

**Use Cases**:
- Chatbot conversations
- Customer support interactions
- Meeting dialogues
- Learning sessions

**Example**:
```json
{
  "user_id": "user123",
  "session_id": "chat-session-12345",
  "content": "Customer asking about recent billing charges",
  "interaction_sequence": 3,
  "conversation_state": {
    "context": "customer_support",
    "issue_type": "billing_inquiry",
    "sentiment": "neutral"
  },
  "session_type": "customer_support"
}
```

### 6. Working Memory (WORKING)
**Purpose**: Store temporary, task-oriented information with TTL.

**Structure**:
- `task_id`: Unique identifier for the task
- `content`: Current task information
- `task_context`: JSON object with task variables
- `ttl_hours`: Time to live in hours
- `priority`: Priority level (1-10)

**Use Cases**:
- Active project state
- Temporary calculations
- Current workflow context
- Short-term task tracking

**Example**:
```json
{
  "user_id": "user123",
  "task_id": "task-memory-integration-001",
  "content": "Currently working on integrating memory service with MCP tools",
  "task_context": {
    "project": "Memory Service Integration",
    "phase": "testing",
    "priority": "high"
  },
  "ttl_hours": 24,
  "priority": 8
}
```

## Available MCP Tools

### Core Memory Tools
- `store_fact`: Store factual memories
- `store_concept`: Store semantic concepts
- `store_episode`: Store episodic events
- `store_procedure`: Store procedural knowledge
- `store_session_memory`: Store session context
- `store_working_memory`: Store working memory with TTL

### Search and Retrieval
- `search_memories`: Search across memory types with similarity matching
- `get_active_working_memories`: Retrieve active working memories
- `cleanup_expired_memories`: Clean up expired working memories

### Memory Management
- `store_memory`: Generic memory storage tool
- `get_session_memory`: Retrieve session-specific memories
- `extract_memories`: Extract and store memories from content

## Search Capabilities

The memory service provides advanced search functionality with:

- **Semantic Similarity**: Vector-based similarity search using embeddings
- **Memory Type Filtering**: Search within specific memory types
- **Similarity Threshold**: Configurable relevance threshold (0.0 to 1.0)
- **Result Limiting**: Control number of returned results
- **Cross-Memory Search**: Search across multiple memory types simultaneously

### Search Parameters
```json
{
  "user_id": "user123",
  "query": "search terms",
  "memory_types": ["FACTUAL", "SEMANTIC"],
  "limit": 5,
  "similarity_threshold": 0.6
}
```

## Implementation Details

### Storage Backend
- **Database**: Supabase with PostgreSQL
- **Vector Storage**: pgvector extension for similarity search
- **Indexing**: Automatic embedding generation and indexing

### Memory Lifecycle
1. **Storage**: Memories are stored with automatic embedding generation
2. **Indexing**: Vector embeddings are indexed for fast retrieval
3. **Search**: Similarity search using vector operations
4. **Expiration**: Working memories expire based on TTL
5. **Cleanup**: Automated cleanup of expired memories

### Error Handling
- **Validation**: Comprehensive input validation with Pydantic models
- **Graceful Degradation**: Service continues operation during partial failures
- **Error Recovery**: Automatic retry mechanisms for transient failures

## Testing Coverage

The memory service includes comprehensive test coverage:

### Test Files
- `test_fact.py`: 6 tests covering factual memory operations
- `test_concept.py`: 8 tests covering semantic memory operations
- `test_episode.py`: 8 tests covering episodic memory operations
- `test_procedure.py`: 6 tests covering procedural memory operations
- `test_session.py`: 9 tests covering session memory operations
- `test_working.py`: 8 tests covering working memory operations

### Test Coverage Areas
- **Capability Discovery**: MCP tool availability and discovery
- **Storage Operations**: Memory creation and validation
- **Search Functionality**: Cross-memory type search with similarity matching
- **Error Handling**: Validation error handling and graceful degradation
- **Memory Management**: TTL handling, cleanup, and lifecycle management

## Integration

### MCP Integration
The memory service integrates seamlessly with MCP-compatible clients:

- **Tool Discovery**: Automatic discovery of memory tools based on user requests
- **Parameter Validation**: Comprehensive validation using Pydantic models
- **Response Formatting**: Standardized response formats for all tools

### Usage Patterns
```python
# Store a fact
await client.call_tool_and_parse("store_fact", {
    "user_id": "user123",
    "fact_type": "person",
    "subject": "John Doe",
    "predicate": "email",
    "object_value": "john@example.com"
})

# Search memories
await client.call_tool_and_parse("search_memories", {
    "user_id": "user123",
    "query": "John Doe contact information",
    "memory_types": ["FACTUAL"],
    "limit": 5
})
```

## Future Enhancements

### Planned Features
- **Memory Merging**: Automatic conflict resolution and memory consolidation
- **Temporal Queries**: Time-based memory retrieval and filtering
- **Memory Analytics**: Usage patterns and memory health metrics
- **Batch Operations**: Bulk memory operations for improved performance
- **Memory Hierarchies**: Nested and hierarchical memory structures

### Performance Optimizations
- **Caching Layer**: Redis-based caching for frequently accessed memories
- **Index Optimization**: Advanced indexing strategies for large datasets
- **Compression**: Memory content compression for storage efficiency
- **Sharding**: Horizontal scaling for high-volume deployments

## Security Considerations

- **User Isolation**: Strict user-based memory isolation
- **Data Encryption**: Encryption at rest and in transit
- **Access Control**: Role-based access control for memory operations
- **Audit Logging**: Comprehensive audit trails for all memory operations
- **Data Retention**: Configurable retention policies and compliance features