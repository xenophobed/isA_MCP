# Session Memory Engine Documentation

## Overview

The Session Memory Engine is a specialized component designed to manage conversational sessions with intelligent dialog processing and automatic summarization capabilities. It handles both individual message storage and session-level summaries to prevent data explosion during long conversations.

## Architecture

### Database Schema

The session engine uses a dual-table approach:

1. **`session_messages`** - Stores individual messages with intelligent processing
2. **`session_memories`** - Stores session-level summaries and metadata

### Core Components

- **TextExtractor Integration**: Intelligent analysis of message content
- **TextSummarizer Integration**: Automatic conversation summarization
- **Dual Storage Strategy**: Messages + summaries for efficient retrieval
- **Intelligent Triggers**: Automatic summarization based on conversation length

## Key Features

### 1. Intelligent Message Processing

The engine processes each message through TextExtractor to extract:
- Main topics and themes
- Questions asked/answered
- Requests made
- Entities mentioned
- Emotional tone and sentiment
- Information provided (for AI messages)

### 2. Automatic Summarization

Summarization is triggered when:
- Message count exceeds 10 messages
- Total conversation length exceeds 10,000 characters
- Messages since last summary exceeds 5

### 3. Session Context Management

Provides comprehensive session context including:
- Recent message history
- Session summaries
- Key decisions and action items
- Conversation metadata

## Usage Examples

### Basic Message Storage

```python
from tools.services.memory_service.engines.session_engine import SessionMemoryEngine

# Initialize engine
engine = SessionMemoryEngine()

# Store a user message
result = await engine.store_session_message(
    user_id="user123",
    session_id="session456",
    message_content="I need help with Python data analysis",
    message_type="human",
    role="user"
)

# Store an AI response
result = await engine.store_session_message(
    user_id="user123",
    session_id="session456",
    message_content="I can help you with Python data analysis! What specific area?",
    message_type="ai",
    role="assistant"
)
```

### Session Summarization

```python
# Manual summarization
result = await engine.summarize_session(
    user_id="user123",
    session_id="session456",
    force_update=True,
    compression_level="medium"
)

# Automatic summarization (triggered by message count/length)
# Happens automatically when storing messages
```

### Retrieving Session Context

```python
# Get comprehensive session context
context = await engine.get_session_context(
    user_id="user123",
    session_id="session456",
    include_summaries=True,
    max_recent_messages=5
)

# Returns:
# {
#     "success": True,
#     "session_id": "session456",
#     "total_messages": 25,
#     "summary_available": True,
#     "summary": {
#         "content": "User requested help with Python data analysis...",
#         "key_points": ["Python data analysis", "pandas library"],
#         "quality_score": 0.85,
#         "compression_ratio": 0.3
#     },
#     "recent_messages": [...]
# }
```

### Message Retrieval

```python
# Get all messages for a session
messages = await engine.get_session_messages("user123", "session456")

# Messages include processed metadata:
# {
#     "id": "msg_123",
#     "content": "I need help with Python",
#     "role": "user",
#     "message_metadata": {
#         "entities": {"Python": {"confidence": 0.9}},
#         "sentiment": {"label": "positive", "score": 0.8},
#         "extracted_info": {...}
#     }
# }
```

## Configuration

### Engine Properties

```python
# Summarization triggers
engine.summary_trigger_count = 10      # Messages before summarization
engine.max_session_length = 10000      # Characters before summarization

# Database tables
engine.table_name = "session_memories"         # For summaries
engine.messages_table_name = "session_messages"  # For messages
```

### Message Types

The engine supports different message types:
- `"human"` / `"user"` - User messages
- `"ai"` / `"assistant"` - AI responses
- Custom types can be added

## Advanced Features

### 1. Intelligent Extraction Schemas

The engine uses different extraction schemas based on message type:

**User Messages:**
- main_topics
- questions_asked
- requests_made
- entities_mentioned
- emotional_tone

**AI Messages:**
- main_topics
- information_provided
- suggestions_made
- questions_answered
- follow_up_needed

### 2. Summarization Styles

Supports multiple summarization approaches:
- **Narrative**: Conversational summary style
- **Executive**: Concise bullet points
- **Detailed**: Comprehensive analysis

### 3. Compression Levels

- **brief**: Short summaries
- **medium**: Balanced detail
- **detailed**: Comprehensive summaries

### 4. Quality Metrics

Each summary includes:
- Compression ratio
- Quality score
- Word count
- Key points extracted

## Error Handling

The engine includes comprehensive error handling:

```python
# All operations return MemoryOperationResult
result = await engine.store_session_message(...)

if result.success:
    print(f"Message stored: {result.memory_id}")
else:
    print(f"Error: {result.message}")
```

## Integration with Other Services

### TextExtractor Integration

```python
# Automatic extraction on message storage
extraction_result = await self.text_extractor.extract_key_information(
    text=message_content,
    schema=extraction_schema
)

# Sentiment analysis
sentiment_result = await self.text_extractor.analyze_sentiment(
    text=message_content,
    granularity="overall"
)
```

### TextSummarizer Integration

```python
# Conversation summarization
summary_result = await self.text_summarizer.summarize_text(
    text=conversation_text,
    style=SummaryStyle.NARRATIVE,
    length=SummaryLength.MEDIUM
)

# Key points extraction
key_points = await self.text_summarizer.extract_key_points(
    text=conversation_text,
    max_points=8
)
```

## Performance Considerations

### 1. Storage Optimization

- Messages marked as `is_summary_candidate: False` after summarization
- Summaries stored separately from individual messages
- Efficient retrieval through proper indexing

### 2. Memory Management

- Automatic compression of old messages
- TTL-based cleanup for working memory
- Efficient vector embeddings for similarity search

### 3. Scalability

- Asynchronous processing throughout
- Batched operations for large sessions
- Configurable trigger thresholds

## Testing

The engine includes comprehensive test coverage:

```bash
# Run all session engine tests
python -m pytest tools/services/memory_service/engines/tests/test_session_service.py -v

# Test specific functionality
python -m pytest tools/services/memory_service/engines/tests/test_session_service.py::TestSessionMemoryEngine::test_summarize_session_successful -v
```

### Test Coverage

- Message storage and retrieval
- Intelligent extraction processing
- Automatic summarization triggers
- Session context management
- Error handling scenarios
- Database integration
- Performance edge cases

## Future Enhancements

### Planned Features

1. **Multi-modal Support**: Handle images, audio, and other media
2. **Real-time Summarization**: WebSocket-based live updates
3. **Advanced Analytics**: Session quality metrics and insights
4. **Custom Extraction**: User-defined extraction schemas
5. **Export Capabilities**: Session export in various formats

### Integration Opportunities

- **ReviseNode Integration**: Intelligent session revision
- **Graph Analytics**: Session relationship mapping
- **Event Sourcing**: Session event tracking
- **User Analytics**: Conversation pattern analysis

## Best Practices

### 1. Message Management

- Use consistent role naming (`user`, `assistant`)
- Set appropriate importance scores
- Include relevant context in messages

### 2. Summarization

- Allow natural summarization triggers
- Use appropriate compression levels
- Monitor summary quality scores

### 3. Error Handling

- Always check operation results
- Handle extraction failures gracefully
- Log important events for debugging

### 4. Performance

- Batch related operations
- Use appropriate database indexes
- Monitor session sizes and trigger thresholds

## Conclusion

The Session Memory Engine provides a robust foundation for intelligent conversation management with automatic summarization capabilities. Its dual-table architecture and intelligent processing make it ideal for handling both short-term message storage and long-term session context preservation.

The engine's integration with TextExtractor and TextSummarizer services enables sophisticated dialog analysis and compression, preventing data explosion while maintaining conversation context and quality.