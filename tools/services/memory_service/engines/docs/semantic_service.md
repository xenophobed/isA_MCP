# Semantic Memory Service

## Overview

The Semantic Memory Service provides intelligent storage and retrieval of conceptual knowledge by automatically extracting definitions, principles, theories, and relationships from raw human-AI dialog content. This service transforms conversational explanations into a structured knowledge base using advanced text analysis to identify concepts, their properties, and interconnections.

## Features

- **Intelligent Concept Extraction**: Automatically extracts definitions, principles, and theories from dialog
- **Multi-concept Processing**: Handles multiple related concepts from a single conversation
- **Concept Merging**: Updates existing concepts with new information and properties
- **Relationship Mapping**: Tracks connections between related concepts
- **Abstraction Levels**: Organizes concepts by complexity (concrete, medium, abstract)
- **Comprehensive Search**: Multiple search dimensions for knowledge retrieval

## Core Method: `store_semantic_memory()`

### Input

```python
async def store_semantic_memory(
    user_id: str,
    dialog_content: str,
    importance_score: float = 0.5
) -> MemoryOperationResult
```

**Parameters:**
- `user_id` (str): User identifier for memory ownership
- `dialog_content` (str): Raw dialog between human and AI containing conceptual information
- `importance_score` (float): Manual importance override (0.0-1.0, defaults to 0.5)

### Output

Returns `MemoryOperationResult` with:
- `success` (bool): Whether the operation succeeded
- `memory_id` (str): Unique identifier for the stored concept (single concept) or first concept ID
- `operation` (str): Operation type ("store_semantic_memory")
- `message` (str): Status message indicating number of concepts processed
- `data` (dict): Additional metadata including `stored_concepts` list and `total_concepts` count

### Extracted Information

The service automatically extracts:

1. **Concepts**: List of conceptual knowledge with:
   - `concept_type`: Category (definition, principle, theory, classification, relationship)
   - `definition`: Clear explanation of the concept
   - `properties`: Key attributes and characteristics as dictionary
   - `abstraction_level`: Complexity level (concrete, medium, abstract)
   - `category`: Knowledge domain (technology, science, philosophy, business)
   - `related_concepts`: List of connected concept names
   - `importance_score`: Significance level (0.0-1.0)

2. **Knowledge Domain**: Primary field of knowledge discussed
3. **Key Relationships**: Important connections between concepts
4. **Extraction Confidence**: Overall quality of extraction process

## Usage Examples

### AI and Machine Learning Concepts

```python
from tools.services.memory_service.engines.semantic_engine import SemanticMemoryEngine

engine = SemanticMemoryEngine()

# Conceptual explanation dialog
ml_dialog = """
Human: Can you explain what machine learning is and how it relates to artificial intelligence?

AI: Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns.

Artificial intelligence is the broader field that encompasses any technique enabling machines to mimic human intelligence. Machine learning is one approach to achieving AI, along with other methods like rule-based systems and expert systems.

The key principle behind machine learning is that systems can automatically learn and improve from experience. This makes it particularly powerful for tasks like image recognition, natural language processing, and predictive analytics.
"""

result = await engine.store_semantic_memory(
    user_id="user123",
    dialog_content=ml_dialog
)

# Result will extract multiple concepts:
# - Concept 1: Machine learning definition (subset of AI, pattern recognition)
# - Concept 2: Artificial intelligence definition (broad field, human intelligence mimicry)
# - Concept 3: Learning principle (automatic improvement from experience)
# All with appropriate properties, relationships, and abstraction levels
```

### Scientific Principles

```python
# Physics concepts dialog
physics_dialog = """
Human: What is entropy and how does it relate to the second law of thermodynamics?

AI: Entropy is a measure of disorder or randomness in a system. In thermodynamics, it quantifies the amount of thermal energy unavailable for doing useful work.

The second law of thermodynamics states that the entropy of an isolated system never decreases over time. This means that natural processes tend to move toward maximum disorder.

This principle explains why heat flows from hot to cold objects and why perpetual motion machines are impossible. It's a fundamental concept that governs energy transformations in the universe.
"""

result = await engine.store_semantic_memory(
    user_id="user123",
    dialog_content=physics_dialog
)

# Extracts concepts like:
# - Entropy definition (measure of disorder, thermal energy)
# - Second law of thermodynamics (entropy never decreases)
# - Energy transformation principles
```

### Business and Economic Concepts

```python
# Economic theory dialog
economics_dialog = """
Human: Explain supply and demand and how they determine market prices.

AI: Supply and demand are fundamental economic forces that determine prices in a market economy.

Supply refers to the quantity of a good or service that producers are willing and able to offer at various price levels. Generally, higher prices incentivize producers to supply more.

Demand represents the quantity that consumers are willing and able to purchase at different prices. Typically, lower prices increase consumer demand.

Market equilibrium occurs when supply equals demand, determining the market price. When demand exceeds supply, prices tend to rise. When supply exceeds demand, prices typically fall.
"""

result = await engine.store_semantic_memory(
    user_id="user123",
    dialog_content=economics_dialog
)

# Extracts economic concepts with relationships and properties
```

## Search Methods

The Semantic Memory Service provides comprehensive search capabilities:

### 1. Category Search

```python
concepts = await engine.search_concepts_by_category(
    user_id="user123",
    category="technology",
    limit=10
)
```

**Use Cases:**
- Find all concepts in a specific knowledge domain
- Partial matching support (e.g., "tech" matches "technology")
- Results ordered by importance score

### 2. Abstraction Level Search

```python
abstract_concepts = await engine.search_concepts_by_abstraction_level(
    user_id="user123",
    abstraction_level="abstract",
    limit=10
)
```

**Abstraction Levels:**
- `concrete`: Specific, tangible concepts with direct real-world examples
- `medium`: Moderate complexity concepts with some abstraction
- `abstract`: High-level theoretical concepts requiring deep understanding

### 3. Concept Type Search

```python
definitions = await engine.search_concepts_by_type(
    user_id="user123",
    concept_type="definition",
    limit=10
)
```

**Available Concept Types:**
- `definition`: Basic explanations of what something is
- `principle`: Fundamental rules or laws
- `theory`: Explanatory frameworks or models
- `classification`: Categorization systems
- `relationship`: Connections between entities

### 4. Definition Content Search

```python
concepts = await engine.search_concepts_by_definition(
    user_id="user123",
    definition_keyword="intelligence",
    limit=10
)
```

**Use Cases:**
- Find concepts containing specific terms in their definitions
- Search for related ideas using keywords
- Discover concepts with similar explanations

### 5. Related Concept Search

```python
related_concepts = await engine.search_concepts_by_related_concept(
    user_id="user123",
    related_concept_id="machine_learning_concept_id",
    limit=10
)
```

**Use Cases:**
- Find concepts connected to a specific concept
- Explore conceptual networks and relationships
- Discover related ideas and theories

### 6. Vector Similarity Search (Inherited)

```python
from tools.services.memory_service.models import MemorySearchQuery

# Semantic similarity search
query = MemorySearchQuery(
    query="artificial intelligence and machine learning concepts",
    user_id="user123",
    top_k=5,
    similarity_threshold=0.7
)

concepts = await engine.search_memories(query)
```

## Advanced Features

### Concept Merging

When storing concepts that match existing ones (same concept_type and similar definition), the system:

1. **Updates Properties**: Merges new properties with existing ones
2. **Expands Relationships**: Adds new related concepts to the existing list
3. **Increases Importance**: Takes maximum importance score
4. **Tracks Access**: Records additional usage

### Concept Relationships

The service manages relationships between concepts:

```python
# Add relationship between concepts
await engine.add_concept_relation(
    source_concept_id="machine_learning_id",
    target_concept_id="artificial_intelligence_id"
)
```

### Property Updates

Concepts can be enhanced with new properties:

```python
# Update concept properties
new_properties = {
    "applications": ["computer_vision", "nlp", "robotics"],
    "complexity": "high",
    "mathematical_foundation": "statistics_and_linear_algebra"
}

await engine.update_concept_properties("concept_id", new_properties)
```

### Fallback Extraction

When structured extraction fails, the system uses basic heuristics:

- Identifies definition patterns: "X is Y", "X refers to Y", "X means Y"
- Extracts up to 2 basic concepts per dialog
- Assigns moderate confidence (0.6)
- Categorizes as general definitions

## Concept Processing Features

### Data Validation

The service includes robust validation:

- **Required Fields**: Ensures definition is present and meaningful
- **Importance Clamping**: Keeps importance between 0.0 and 1.0
- **Type Normalization**: Converts spaces to underscores, lowercase
- **Abstraction Validation**: Ensures valid abstraction levels
- **Property Filtering**: Removes empty or invalid properties

### Multi-Concept Support

A single dialog can contain multiple concepts:

- Each concept is processed independently
- Relationships between concepts are automatically detected
- Concepts can reference each other in their related_concepts lists
- Maintains conceptual coherence within conversations

## Search Method Characteristics

### Performance
- **Category, Type, Definition**: Database queries with indexing and partial matching
- **Abstraction Level**: Direct categorical filtering
- **Related Concepts**: In-memory filtering of relationship lists
- **Vector Similarity**: Embedding-based semantic search

### Result Ordering
- **Category, Type, Definition**: By importance_score (highest first)
- **Abstraction Level**: By importance_score (highest first)
- **Related Concepts**: By importance_score (highest first)
- **Vector Similarity**: By semantic similarity score

### Error Handling
All search methods return empty lists on errors and log warnings for debugging.

## Integration with Base Memory Engine

The semantic engine extends the base memory engine, inheriting:

- **Vector Embeddings**: Automatic embedding generation for semantic search
- **Database Storage**: Supabase integration with JSON field handling
- **Access Tracking**: Usage statistics and cognitive decay modeling
- **Association Discovery**: Automatic concept relationship detection

## Best Practices

### Storage
1. **Dialog Quality**: Include complete conceptual explanations with context
2. **Concept Clarity**: Ensure clear, unambiguous definitions
3. **Relationship Context**: Mention related concepts for automatic linking
4. **Property Details**: Include relevant attributes and characteristics

### Search
5. **Search Strategy**: Use specific searches (category, type) before semantic similarity
6. **Abstraction Matching**: Filter by appropriate complexity level
7. **Relationship Exploration**: Use related concept search to discover connections
8. **Definition Search**: Use keyword search for specific terminology

### Knowledge Management
9. **Concept Updates**: Regularly update properties with new information
10. **Relationship Building**: Add explicit relationships between related concepts
11. **Knowledge Organization**: Use consistent categorization and abstraction levels
12. **Validation**: Verify concept accuracy and completeness

## Testing

The service includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tools/services/memory_service/engines/tests/test_semantic_service.py -v

# Test results: ✅ 15 passed, 0 failed
```

**Test Coverage:**
- ✅ Intelligent dialog processing with multi-concept extraction
- ✅ Existing concept merging and property updates
- ✅ All 5 search methods with realistic concept scenarios
- ✅ Concept relationship management
- ✅ Property updates and validation
- ✅ Fallback extraction mechanisms
- ✅ Data validation and error handling

## Error Handling

The service gracefully handles:

- **Extraction Failures**: Falls back to basic definition pattern matching
- **Invalid Input**: Applies defaults and validation
- **Database Errors**: Returns detailed error messages
- **Concept Conflicts**: Handles concept merging and updates
- **Network Issues**: Logs errors and returns failure status

## Performance Considerations

- **Multi-Concept Processing**: Efficiently handles dialogs with many concepts
- **Property Management**: Optimized storage and retrieval of concept attributes
- **Relationship Tracking**: Lightweight management of concept connections
- **Async Operations**: All operations are non-blocking
- **Memory Efficient**: Processes complex conceptual discussions without memory issues
- **Query Optimization**: Database searches use appropriate indexing strategies

## Comparison with Other Memory Types

| Feature | Episodic | Factual | Procedural | Semantic |
|---------|----------|---------|------------|----------|
| **Content Type** | Events & experiences | Facts & statements | Procedures & workflows | Concepts & knowledge |
| **Structure** | Temporal narrative | Subject-predicate-object | Step-by-step instructions | Definitions & relationships |
| **Key Fields** | participants, location, emotional_valence | subject, predicate, object_value | steps, prerequisites, difficulty_level | concept_type, definition, properties |
| **Search Focus** | When, where, who | What, confidence, verification | How, success_rate, tools_needed | Why, abstraction_level, relationships |
| **Use Cases** | Personal history, context | Knowledge base, assertions | Task execution, learning | Understanding, conceptual frameworks |

The Semantic Memory Service excels at capturing and organizing conceptual knowledge, making it ideal for:

- **Educational Content**: Definitions, theories, and principles
- **Knowledge Management**: Conceptual frameworks and relationships
- **Research Notes**: Academic and scientific concepts
- **Domain Expertise**: Professional knowledge and terminology
- **Learning Systems**: Adaptive educational content organization