# Episodic Memory Service

## Overview

The Episodic Memory Service provides intelligent storage and retrieval of episodic memories by automatically extracting structured information from raw human-AI dialog content. Unlike traditional memory systems that require manual structuring, this service uses advanced text analysis to understand context, participants, emotions, and events from conversational text.

## Features

- **Intelligent Dialog Processing**: Automatically extracts event type, participants, location, and emotional context from raw dialog
- **Multi-layer Analysis**: Combines schema-based extraction, entity recognition, and sentiment analysis
- **Vector-based Storage**: Uses embeddings for similarity-based memory retrieval
- **Comprehensive Validation**: Ensures data quality with robust validation and fallback mechanisms

## Core Method: `store_episode()`

### Input

```python
async def store_episode(
    user_id: str,
    dialog_content: str,
    episode_date: Optional[datetime] = None,
    importance_score: float = 0.5
) -> MemoryOperationResult
```

**Parameters:**
- `user_id` (str): User identifier for memory ownership
- `dialog_content` (str): Raw dialog between human and AI
- `episode_date` (Optional[datetime]): When the episode occurred (defaults to now)
- `importance_score` (float): Manual importance override (0.0-1.0, defaults to 0.5)

### Output

Returns `MemoryOperationResult` with:
- `success` (bool): Whether the operation succeeded
- `memory_id` (str): Unique identifier for the stored memory
- `operation` (str): Operation type ("store_episode")
- `message` (str): Status message
- `data` (dict): Additional metadata about the stored memory

### Extracted Information

The service automatically extracts:

1. **Event Type**: Categorizes the interaction
   - `question_answering`: Simple Q&A
   - `planning_session`: Planning or organizing activities
   - `troubleshooting`: Problem-solving discussions
   - `brainstorming`: Creative or ideation sessions
   - `learning`: Educational interactions
   - `meeting_planning`: Organizing meetings or events
   - `conversation`: General dialog

2. **Clean Content**: Concise 2-3 sentence summary of what happened

3. **Location**: Physical or virtual locations mentioned in the dialog

4. **Participants**: People mentioned in the conversation (excludes AI references)

5. **Emotional Valence**: Sentiment score from -1.0 (negative) to 1.0 (positive)

6. **Vividness**: Detail level from 0.0 (vague) to 1.0 (very detailed)

7. **Importance Score**: Significance from 0.0 (trivial) to 1.0 (very important)

8. **Key Topics**: Main subjects discussed

9. **Outcomes**: Decisions, conclusions, or results

## Usage Examples

### Simple Q&A Dialog

```python
from tools.services.memory_service.engines.episodic_engine import EpisodicMemoryEngine

engine = EpisodicMemoryEngine()

# Simple question-answer interaction
simple_dialog = """
Human: What's the capital of France?
AI: The capital of France is Paris.
"""

result = await engine.store_episode(
    user_id="user123",
    dialog_content=simple_dialog
)

# Result will extract:
# - event_type: "question_answering"
# - clean_content: "User asked about the capital of France, AI provided the answer."
# - participants: []
# - emotional_valence: 0.0 (neutral)
# - vividness: 0.3 (simple exchange)
```

### Complex Planning Dialog

```python
# Complex planning session
planning_dialog = """
Human: Can you help me plan our team meeting for next Friday? We need to discuss Q4 roadmap and Alice, Bob, and Carol will be joining us in Conference Room A.

AI: I'd be happy to help you plan your team meeting. For your Q4 roadmap discussion with Alice, Bob, and Carol in Conference Room A next Friday, here are some suggestions for your agenda:

1. Review Q3 achievements (10 minutes)
2. Q4 goals and priorities (20 minutes)
3. Resource allocation discussion (15 minutes)
4. Timeline planning (10 minutes)
5. Next steps and action items (5 minutes)

Would you like me to elaborate on any of these sections?
"""

result = await engine.store_episode(
    user_id="user123",
    dialog_content=planning_dialog,
    importance_score=0.8
)

# Result will extract:
# - event_type: "planning_session"
# - clean_content: "Team discussed Q4 roadmap planning with participants Alice, Bob, and Carol in Conference Room A."
# - location: "Conference Room A"
# - participants: ["Alice", "Bob", "Carol"]
# - emotional_valence: 0.6 (positive planning tone)
# - vividness: 0.8 (detailed planning)
# - importance_score: 0.8 (high importance meeting)
# - key_topics: ["Q4 roadmap", "team meeting", "agenda planning"]
```

### Problem-Solving Dialog

```python
# Troubleshooting session
troubleshooting_dialog = """
Human: I'm having issues with our deployment pipeline. It keeps failing at the Docker build step and Sarah from DevOps mentioned it might be a memory issue.

AI: Let's troubleshoot this Docker build issue. Memory problems during builds are common. Here are some steps to diagnose and fix this:

1. Check your Docker build logs for specific memory error messages
2. Increase Docker's memory allocation in your build environment
3. Optimize your Dockerfile to use multi-stage builds
4. Consider using Docker BuildKit for better memory efficiency

Can you share the specific error message you're seeing?
"""

result = await engine.store_episode(
    user_id="user123",
    dialog_content=troubleshooting_dialog
)

# Result will extract:
# - event_type: "troubleshooting"
# - clean_content: "User discussed Docker deployment pipeline issues with DevOps team member Sarah."
# - participants: ["Sarah"]
# - emotional_valence: -0.3 (slightly negative due to problem)
# - vividness: 0.7 (detailed technical discussion)
# - key_topics: ["deployment pipeline", "Docker", "memory issues", "DevOps"]
# - outcomes: ["troubleshooting steps provided"]
```

## Search Methods

The Episodic Memory Service provides comprehensive search capabilities to retrieve episodes based on various criteria:

### 1. Event Type Search

```python
episodes = await engine.search_episodes_by_event_type(
    user_id="user123",
    event_type="planning_session",
    limit=10
)
```

**Use Cases:**
- Find all planning sessions
- Retrieve troubleshooting episodes
- Get learning interactions

### 2. Participant Search

```python
episodes = await engine.search_episodes_by_participant(
    user_id="user123",
    participant="Alice",
    limit=10
)
```

**Use Cases:**
- Find all episodes involving a specific person
- Track interactions with team members
- Analyze collaboration patterns

### 3. Location Search

```python
episodes = await engine.search_episodes_by_location(
    user_id="user123",
    location="Conference Room",
    limit=10
)
```

**Use Cases:**
- Find episodes that occurred in specific locations
- Partial location matching (e.g., "Conference" matches "Conference Room A")
- Track meeting locations

### 4. Timeframe Search

```python
from datetime import datetime

episodes = await engine.search_episodes_by_timeframe(
    user_id="user123",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    limit=10
)
```

**Use Cases:**
- Find episodes within specific date ranges
- Monthly or weekly reviews
- Historical analysis

### 5. Emotional Tone Search

```python
# Find positive episodes
positive_episodes = await engine.search_episodes_by_emotional_tone(
    user_id="user123",
    min_valence=0.5,
    max_valence=1.0,
    limit=10
)

# Find negative episodes
negative_episodes = await engine.search_episodes_by_emotional_tone(
    user_id="user123",
    min_valence=-1.0,
    max_valence=-0.1,
    limit=10
)
```

**Use Cases:**
- Find episodes with specific emotional tones
- Analyze positive vs. negative interactions
- Track emotional patterns over time

### 6. Importance Search

```python
# Find high-importance episodes
important_episodes = await engine.search_episodes_by_importance(
    user_id="user123",
    min_importance=0.8,
    limit=10
)
```

**Use Cases:**
- Retrieve critical or important episodes
- Focus on high-value interactions
- Priority-based memory retrieval

### 7. Vector Similarity Search (Inherited)

```python
from tools.services.memory_service.models import MemorySearchQuery

# Semantic similarity search using embeddings
query = MemorySearchQuery(
    query="team planning and roadmap",
    user_id="user123",
    top_k=5,
    similarity_threshold=0.7
)

episodes = await engine.search_memories(query)
```

**Use Cases:**
- Find semantically similar episodes
- Content-based retrieval
- Fuzzy matching of topics

## Search Method Characteristics

### Performance
- **Event Type, Location, Timeframe, Emotional Tone, Importance**: Direct database queries with indexing
- **Participant**: Client-side filtering (considers optimization for large datasets)
- **Vector Similarity**: Embedding-based search with configurable similarity thresholds

### Error Handling
All search methods gracefully handle errors and return empty lists on failure, ensuring robust operation even with database issues.

### Result Ordering
- **Event Type, Location, Participant, Timeframe**: Ordered by episode_date (most recent first)
- **Emotional Tone**: Ordered by vividness (most vivid first)
- **Importance**: Ordered by importance_score (highest first), then episode_date
- **Vector Similarity**: Ordered by similarity score (highest first)

## Analysis Layers

### 1. Schema-based Extraction

Uses a predefined schema to extract structured information:

```python
episodic_schema = {
    "event_type": "Type of interaction or event",
    "clean_content": "Clean, concise summary (2-3 sentences max)",
    "location": "Any location mentioned in the conversation",
    "participants": "List of people mentioned (exclude AI assistant)",
    "emotional_valence": "Emotional tone (-1.0 to 1.0)",
    "vividness": "Detail level (0.0 to 1.0)",
    "importance_score": "Importance (0.0 to 1.0)",
    "key_topics": "Main topics discussed",
    "outcomes": "Decisions, conclusions, or results"
}
```

### 2. Entity Recognition

Automatically detects:
- **PERSON**: Names of people mentioned
- **LOCATION**: Places, rooms, or virtual locations
- **TIME**: Dates, times, or temporal references
- **ORGANIZATION**: Companies, teams, or groups

### 3. Sentiment Analysis

Converts emotional tone to numerical valence:
- **Positive sentiment** → 0.1 to 1.0 valence
- **Negative sentiment** → -1.0 to -0.1 valence
- **Neutral sentiment** → 0.0 valence

## Data Validation

The service includes robust validation:

- **Event Type**: Normalized to lowercase with underscores
- **Participants**: Filters out AI references (ai, assistant, claude, bot)
- **Numerical Fields**: Clamped to valid ranges and defaulted on invalid input
- **Content Fallback**: Uses original dialog snippet if extraction fails
- **Location Filtering**: Removes placeholder values like "None" or "N/A"

## Integration with Base Memory Engine

The episodic engine extends the base memory engine, inheriting:

- **Vector Embeddings**: Automatic embedding generation for content
- **Similarity Search**: Find related memories using vector similarity
- **Database Storage**: Supabase integration with JSON field handling
- **Access Tracking**: Cognitive decay modeling with usage statistics

## Error Handling

The service gracefully handles:

- **Extraction Failures**: Falls back to basic content storage
- **Invalid Input**: Applies defaults and validation
- **Database Errors**: Returns detailed error messages
- **Network Issues**: Logs errors and returns failure status

## Performance Considerations

- **Batch Processing**: Can process multiple dialogs efficiently
- **Caching**: Embeddings and analysis results are cached
- **Async Operations**: All operations are non-blocking
- **Memory Efficient**: Processes large dialogs without memory issues

## Best Practices

### Storage
1. **Dialog Length**: Works best with dialogs of 50-2000 words
2. **Context Clarity**: Include sufficient context for accurate extraction
3. **Importance Scoring**: Use manual importance scores for critical episodes
4. **Regular Cleanup**: Implement memory decay for old, less relevant episodes

### Search
5. **Search Strategy**: Use specific searches (event type, participant) before semantic similarity
6. **Limit Results**: Use reasonable limits (5-20) for better performance
7. **Combine Searches**: Chain multiple search criteria for precise results
8. **Error Handling**: Always check for empty results and handle gracefully

## Testing

The service includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tools/services/memory_service/engines/tests/test_episodic_service.py -v

# Test results: ✅ 14 passed, 0 failed
```

**Test Coverage:**
- ✅ Intelligent dialog storage with extraction
- ✅ All 6 search methods with realistic scenarios  
- ✅ Error handling and edge cases
- ✅ Data validation and processing
- ✅ Database interaction patterns