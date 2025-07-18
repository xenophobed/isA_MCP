# Factual Memory Service

## Overview

The Factual Memory Service provides intelligent storage and retrieval of factual information by automatically extracting structured facts from raw human-AI dialog content. This service transforms conversational text into a structured knowledge base using advanced text analysis to identify facts, relationships, and assertions.

## Features

- **Intelligent Fact Extraction**: Automatically extracts subject-predicate-object triples from dialog
- **Multi-fact Processing**: Processes multiple facts from a single dialog interaction
- **Fact Merging**: Automatically merges and updates existing facts with new information
- **Confidence Tracking**: Maintains confidence scores and verification status
- **Comprehensive Search**: Multiple search dimensions for fact retrieval

## Core Method: `store_factual_memory()`

### Input

```python
async def store_factual_memory(
    user_id: str,
    dialog_content: str,
    importance_score: float = 0.5
) -> MemoryOperationResult
```

**Parameters:**
- `user_id` (str): User identifier for memory ownership
- `dialog_content` (str): Raw dialog between human and AI
- `importance_score` (float): Manual importance override (0.0-1.0, defaults to 0.5)

### Output

Returns `MemoryOperationResult` with:
- `success` (bool): Whether the operation succeeded
- `memory_id` (str): Unique identifier for the stored memory (single fact) or first fact ID
- `operation` (str): Operation type ("store_factual_memory")
- `message` (str): Status message indicating number of facts processed
- `data` (dict): Additional metadata including `stored_facts` list and `total_facts` count

### Extracted Information

The service automatically extracts:

1. **Facts**: List of factual statements with:
   - `fact_type`: Category (personal_info, preference, skill, knowledge, relationship)
   - `subject`: What/who the fact is about
   - `predicate`: Relationship or property
   - `object_value`: The value or object
   - `context`: Additional context information
   - `confidence`: Confidence level in the fact (0.0-1.0)

2. **Source**: Origin of information (user_statement, ai_knowledge, external_reference)

3. **Domain**: Knowledge category (technology, personal, business, science)

4. **Extraction Confidence**: Overall quality of extraction process

## Usage Examples

### Personal Information Dialog

```python
from tools.services.memory_service.engines.factual_engine import FactualMemoryEngine

engine = FactualMemoryEngine()

# Personal information sharing
personal_dialog = """
Human: I'm a software engineer at Google, and I specialize in machine learning. My favorite programming language is Python, and I've been working there for 3 years.

AI: That's great! Machine learning is a fascinating field. Python is indeed an excellent choice for ML work.
"""

result = await engine.store_factual_memory(
    user_id="user123",
    dialog_content=personal_dialog
)

# Result will extract multiple facts:
# - Fact 1: user works_at Google (personal_info, confidence: 0.9)
# - Fact 2: user specializes_in machine learning (skill, confidence: 0.9)  
# - Fact 3: user prefers_language Python (preference, confidence: 0.8)
# - Fact 4: user work_duration 3 years (personal_info, confidence: 0.9)
```

### Knowledge Sharing Dialog

```python
# Technical knowledge exchange
knowledge_dialog = """
Human: What's the difference between REST and GraphQL APIs?

AI: REST and GraphQL are both API design paradigms. REST uses multiple endpoints for different resources, while GraphQL uses a single endpoint with flexible queries. GraphQL was developed by Facebook in 2012 and allows clients to request exactly the data they need.
"""

result = await engine.store_factual_memory(
    user_id="user123", 
    dialog_content=knowledge_dialog
)

# Result will extract facts like:
# - Fact 1: REST uses multiple_endpoints (knowledge, confidence: 0.8)
# - Fact 2: GraphQL uses single_endpoint (knowledge, confidence: 0.8)
# - Fact 3: GraphQL developed_by Facebook (knowledge, confidence: 0.9)
# - Fact 4: GraphQL created_in 2012 (knowledge, confidence: 0.9)
```

### Fact Update Dialog

```python
# Correcting previous information
correction_dialog = """
Human: Actually, I've been working at Google for 4 years now, not 3.
AI: Thanks for the correction! I'll update that information.
"""

result = await engine.store_factual_memory(
    user_id="user123",
    dialog_content=correction_dialog
)

# The system will:
# 1. Extract: user work_duration 4 years
# 2. Find existing fact: user work_duration 3 years  
# 3. Merge/update the existing fact with new information
# 4. Increase confidence score for the updated fact
```

## Search Methods

The Factual Memory Service provides comprehensive search capabilities:

### 1. Subject Search

```python
facts = await engine.search_facts_by_subject(
    user_id="user123",
    subject="user",
    limit=10
)
```

**Use Cases:**
- Find all facts about a specific person, company, or entity
- Partial matching support (e.g., "Goog" matches "Google")

### 2. Fact Type Search

```python
skills = await engine.search_facts_by_fact_type(
    user_id="user123",
    fact_type="skill",
    limit=10
)
```

**Available Fact Types:**
- `personal_info`: Personal details and demographics
- `preference`: Likes, dislikes, and preferences
- `skill`: Abilities and expertise areas
- `knowledge`: General knowledge and facts
- `relationship`: Connections and associations

### 3. Confidence Search

```python
# Find high-confidence facts
verified_facts = await engine.search_facts_by_confidence(
    user_id="user123",
    min_confidence=0.8,
    limit=10
)
```

**Use Cases:**
- Retrieve only well-established facts
- Filter out uncertain information
- Focus on verified knowledge

### 4. Source Search

```python
facts = await engine.search_facts_by_source(
    user_id="user123",
    source="Wikipedia",
    limit=10
)
```

**Use Cases:**
- Find facts from specific sources
- Track information provenance
- Verify source reliability

### 5. Verification Status Search

```python
verified_facts = await engine.search_facts_by_verification(
    user_id="user123",
    verification_status="verified",
    limit=10
)
```

**Verification Statuses:**
- `verified`: Confirmed accurate
- `unverified`: Not yet confirmed
- `disputed`: Conflicting information exists

### 6. Vector Similarity Search (Inherited)

```python
from tools.services.memory_service.models import MemorySearchQuery

# Semantic similarity search
query = MemorySearchQuery(
    query="programming languages and software development",
    user_id="user123",
    top_k=5,
    similarity_threshold=0.7
)

facts = await engine.search_memories(query)
```

## Fact Processing Features

### Automatic Fact Merging

When storing facts that match existing ones (same subject, predicate, fact_type), the system:

1. **Updates Values**: Replaces old object_value with new one
2. **Increases Confidence**: Adds 0.1 to existing confidence (max 1.0)
3. **Merges Context**: Combines additional context information
4. **Tracks Updates**: Records last confirmation timestamp

### Fallback Extraction

When structured extraction fails, the system uses basic heuristics:

- Identifies simple patterns: "X is Y", "X has Y", "X was Y"
- Extracts up to 2 basic facts per dialog
- Assigns moderate confidence (0.6)
- Categorizes as general statements

### Data Validation

The service includes robust validation:

- **Required Fields**: Ensures subject, predicate, object_value are present
- **Confidence Clamping**: Keeps confidence between 0.0 and 1.0
- **Type Normalization**: Converts spaces to underscores, lowercase
- **Context Filtering**: Removes empty or meaningless context

## Search Method Characteristics

### Performance
- **Subject, Fact Type, Source**: Database queries with indexing and partial matching
- **Confidence, Verification**: Direct numeric/categorical filtering
- **Vector Similarity**: Embedding-based semantic search

### Result Ordering
- **Subject**: By importance_score (highest first)
- **Fact Type**: By confidence (highest first)
- **Confidence**: By confidence, then importance_score
- **Source**: By creation date (most recent first)
- **Verification**: By confidence (highest first)

### Error Handling
All search methods return empty lists on errors and log warnings for debugging.

## Integration with Base Memory Engine

The factual engine extends the base memory engine, inheriting:

- **Vector Embeddings**: Automatic embedding generation for semantic search
- **Database Storage**: Supabase integration with JSON field handling
- **Access Tracking**: Usage statistics and cognitive decay modeling
- **Association Discovery**: Automatic fact relationship detection

## Best Practices

### Storage
1. **Dialog Quality**: Include sufficient context for accurate fact extraction
2. **Fact Verification**: Use verification methods for critical information
3. **Source Attribution**: Provide source information when available
4. **Regular Updates**: Keep facts current with new information

### Search
5. **Search Strategy**: Use specific searches (subject, type) before semantic similarity
6. **Confidence Filtering**: Apply minimum confidence thresholds for critical applications  
7. **Result Validation**: Verify fact accuracy before using in applications
8. **Batch Operations**: Process multiple related facts together

## Testing

The service includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tools/services/memory_service/engines/tests/test_factual_service.py -v

# Test results:  13 passed, 0 failed
```

**Test Coverage:**
-  Intelligent dialog processing with multi-fact extraction
-  Existing fact merging and updating
-  All 5 search methods with realistic scenarios
-  Fallback extraction mechanisms  
-  Data validation and error handling
-  Confidence and verification workflows

## Error Handling

The service gracefully handles:

- **Extraction Failures**: Falls back to basic pattern matching
- **Invalid Input**: Applies defaults and validation
- **Database Errors**: Returns detailed error messages
- **Merge Conflicts**: Handles fact update scenarios
- **Network Issues**: Logs errors and returns failure status

## Performance Considerations

- **Batch Processing**: Can process multiple facts from single dialog efficiently
- **Caching**: Embeddings and analysis results are cached
- **Async Operations**: All operations are non-blocking
- **Memory Efficient**: Processes large dialogs without memory issues
- **Query Optimization**: Database searches use appropriate indexing strategies