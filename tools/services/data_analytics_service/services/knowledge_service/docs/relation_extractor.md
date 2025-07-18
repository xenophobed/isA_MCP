# Relation Extractor Service

## Overview

The Relation Extractor Service extracts relationships between entities from text using both LLM-based intelligent extraction and pattern-based fallback methods. It provides robust, configurable relation extraction with high accuracy and reliability.

## Features

- **Dual Extraction Methods**: LLM-based intelligent extraction with regex pattern fallback
- **Configurable Relationship Types**: Supports 12+ predefined relationship types
- **Automatic Fallback**: Falls back to pattern-based extraction when LLM is unavailable
- **Relation Deduplication**: Automatically merges duplicate or similar relations
- **Confidence Scoring**: Provides confidence scores for extracted relations
- **Statistics and Analytics**: Built-in relation statistics and analysis

## Supported Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `IS_A` | Taxonomic/classification | "Apple is a company" |
| `PART_OF` | Component/compositional | "Engine is part of car" |
| `LOCATED_IN` | Spatial/location | "Apple is located in Cupertino" |
| `WORKS_FOR` | Employment/affiliation | "Tim Cook works for Apple" |
| `OWNS` | Ownership | "Apple owns iPhone patents" |
| `CREATED_BY` | Creation/authorship | "iPhone was created by Apple" |
| `HAPPENED_AT` | Temporal/event | "Meeting happened at 3PM" |
| `CAUSED_BY` | Causal | "Error caused by network" |
| `SIMILAR_TO` | Similarity | "iPad similar to tablet" |
| `RELATES_TO` | General semantic | "Product relates to market" |
| `DEPENDS_ON` | Dependency | "App depends on framework" |
| `CUSTOM` | Domain-specific | Custom business relations |

## Installation & Setup

```python
from tools.services.data_analytics_service.services.knowledge_extraction_service import RelationExtractor
from tools.services.data_analytics_service.processors.file_processors.regex_extractor import Entity, Relation, RelationType
```

## Usage

### Basic Usage

```python
import asyncio
from tools.services.data_analytics_service.services.knowledge_extraction_service import RelationExtractor
from tools.services.data_analytics_service.processors.file_processors.regex_extractor import Entity

async def extract_relations():
    # Initialize extractor
    extractor = RelationExtractor({
        'use_llm': True,
        'fallback_to_patterns': True
    })
    
    # Define entities with proper positioning
    entities = [
        Entity(text="Apple", entity_type="ORGANIZATION", start_pos=0, end_pos=5, confidence=0.9),
        Entity(text="company", entity_type="CONCEPT", start_pos=11, end_pos=18, confidence=0.8),
        Entity(text="Tim Cook", entity_type="PERSON", start_pos=20, end_pos=28, confidence=0.9)
    ]
    
    # Extract relations
    text = "Apple is a company. Tim Cook works for Apple and leads the organization."
    relations = await extractor.extract_relations(text, entities)
    
    # Process results
    for relation in relations:
        print(f"{relation.subject.text} --[{relation.predicate}]--> {relation.object.text}")
        print(f"Type: {relation.relation_type.value}, Confidence: {relation.confidence}")
        print(f"Context: {relation.context}")
    
    return relations

# Run extraction
relations = asyncio.run(extract_relations())
```

### Configuration Options

```python
# LLM-only extraction
config_llm = {
    'use_llm': True,
    'fallback_to_patterns': False
}

# Pattern-only extraction
config_pattern = {
    'use_llm': False,
    'fallback_to_patterns': True
}

# Hybrid with fallback (recommended)
config_hybrid = {
    'use_llm': True,
    'fallback_to_patterns': True
}

extractor = RelationExtractor(config_hybrid)
```

### Extraction Methods

```python
# Specific extraction methods
relations = await extractor.extract_relations(text, entities, methods=['llm'])      # LLM only
relations = await extractor.extract_relations(text, entities, methods=['pattern']) # Pattern only
relations = await extractor.extract_relations(text, entities, methods=['hybrid'])  # Both combined
```

### Custom Patterns

```python
# Add custom relation patterns
extractor.add_custom_pattern(RelationType.CUSTOM, r'(.+?)\\s+develops\\s+(.+)')

# Text: "Apple develops innovative products"
# Will extract: Apple --[develops]--> products (CUSTOM)
```

## Input Format

### Entity Requirements

Entities must include:
- `text`: The entity text
- `entity_type`: Type of entity (ORGANIZATION, PERSON, LOCATION, PRODUCT, etc.)
- `start_pos`: Start position in text (for pattern matching)
- `end_pos`: End position in text (for pattern matching)
- `confidence`: Confidence score (0.0-1.0)

```python
entity = Entity(
    text="Apple",
    entity_type="ORGANIZATION",
    start_pos=0,
    end_pos=5,
    confidence=0.9
)
```

### Text Requirements

- Plain text string
- Should contain the entities mentioned
- Works best with clear, grammatical sentences
- Supports long text (>3000 chars automatically uses LLM)

## Output Format

### Relation Object

```python
class Relation:
    subject: Entity          # Subject entity
    predicate: str          # Relationship description
    object: Entity          # Object entity
    relation_type: RelationType  # Relationship type enum
    confidence: float       # Confidence score (0.0-1.0)
    context: str           # Supporting text snippet
    properties: dict       # Additional properties
    temporal_info: dict    # Temporal information
```

### Example Output

```python
Relation(
    subject=Entity(text='Tim Cook', entity_type='PERSON'),
    predicate='works for',
    object=Entity(text='Apple', entity_type='ORGANIZATION'),
    relation_type=RelationType.WORKS_FOR,
    confidence=1.0,
    context='Tim Cook works for Apple',
    properties={},
    temporal_info={}
)
```

## Analytics & Statistics

```python
# Get relation statistics
stats = extractor.get_relation_statistics(relations)

# Returns:
{
    "total": 3,
    "by_type": {"IS_A": 1, "WORKS_FOR": 1, "CUSTOM": 1},
    "average_confidence": 1.0,
    "high_confidence": 3,
    "subject_entity_types": {"ORGANIZATION": 1, "PERSON": 2},
    "object_entity_types": {"CONCEPT": 1, "ORGANIZATION": 2},
    "unique_subjects": 2,
    "unique_objects": 2
}
```

## Performance Considerations

### Text Length Optimization

- **Short text (<1000 chars)**: Uses patterns by default
- **Medium text (1000-3000 chars)**: Uses LLM if available
- **Long text (>3000 chars)**: Automatically prioritizes LLM

### Fallback Strategy

1. **Primary**: LLM extraction via intelligence service
2. **Fallback**: Pattern-based regex extraction
3. **Hybrid**: Combines both methods and deduplicates

### Entity Positioning

For optimal pattern matching, ensure entities have accurate `start_pos` and `end_pos` values corresponding to their position in the text.

## Error Handling

The service handles various error conditions gracefully:

- **LLM Service Unavailable**: Automatically falls back to patterns
- **Invalid Entity Indices**: Skips invalid relations
- **Malformed Responses**: Handles parsing errors
- **Empty Input**: Returns empty results

## Testing

The service includes comprehensive tests covering:
- Pattern-based extraction
- LLM extraction with mocking
- Fallback mechanisms
- Hybrid extraction
- Error conditions
- Configuration options

Run tests with:
```bash
python -m pytest tools/services/data_analytics_service/services/knowledge_extraction_service/tests/test_relation_extractor.py -v
```

## Integration Examples

### With Document Processing

```python
# Extract entities first, then relations
from tools.services.data_analytics_service.processors.file_processors.pdf_processor import PDFProcessor

# Process document
pdf_processor = PDFProcessor()
document_data = await pdf_processor.process_file("document.pdf")

# Extract entities (from another service)
entities = await entity_extractor.extract_entities(document_data['text'])

# Extract relations
relations = await relation_extractor.extract_relations(document_data['text'], entities)
```

### With Knowledge Graphs

```python
# Build knowledge graph from relations
for relation in relations:
    graph.add_edge(
        relation.subject.text,
        relation.object.text,
        relation_type=relation.relation_type.value,
        predicate=relation.predicate,
        confidence=relation.confidence
    )
```

## Limitations

1. **Entity Dependencies**: Requires pre-extracted entities with positions
2. **Language Support**: Primarily optimized for English text
3. **Context Window**: LLM extraction limited by intelligence service context window
4. **Pattern Complexity**: Pattern matching may miss complex grammatical structures

## Best Practices

1. **Use Hybrid Mode**: Combines accuracy of LLM with reliability of patterns
2. **Proper Entity Positioning**: Ensure accurate start/end positions for pattern matching
3. **Configure Fallback**: Always enable fallback for production use
4. **Validate Results**: Review extracted relations for domain-specific accuracy
5. **Monitor Performance**: Use statistics to track extraction quality

## Support

For issues or questions about the Relation Extractor Service, refer to the test suite for usage examples or check the implementation in `relation_extractor.py`.