# Attribute Extractor Service

The Attribute Extractor service is a powerful LLM-based component for extracting semantic attributes and properties of entities from text. It uses the intelligence service for sophisticated natural language understanding and provides comprehensive attribute extraction capabilities.

## Overview

The Attribute Extractor leverages AI to identify and extract meaningful attributes for different entity types, including:

- **Structured Attributes**: Emails, phone numbers, URLs, dates, numbers
- **Semantic Attributes**: Occupation, skills, education, company relationships
- **Entity-Specific Attributes**: Customized extraction based on entity type (Person, Organization, Product, Event, Location)

## Key Features

- > **LLM-Powered Extraction**: Uses intelligence service for semantic understanding
- <¯ **Entity-Type Aware**: Custom schemas for different entity types
- = **Type Inference**: Automatic attribute type detection and classification
- ( **Value Normalization**: Standardizes attribute values (phone numbers, emails, URLs, etc.)
- =Ê **Confidence Scoring**: Provides reliability scores for extracted attributes
- = **Batch Processing**: Efficient extraction for multiple entities

## Installation & Setup

```python
from tools.services.data_analytics_service.services.knowledge_extraction_service.attribute_extractor import (
    AttributeExtractor, 
    Attribute, 
    AttributeType,
    Entity,
    EntityType
)

# Initialize the extractor
extractor = AttributeExtractor(config={
    'confidence_threshold': 0.7,
    'use_llm': True
})
```

## Basic Usage

### Single Entity Attribute Extraction

```python
import asyncio
from attribute_extractor import AttributeExtractor, Entity, EntityType

async def extract_person_attributes():
    # Create extractor
    extractor = AttributeExtractor()
    
    # Create entity
    entity = Entity(
        text="John Smith",
        entity_type=EntityType.PERSON,
        start=0,
        end=10,
        confidence=0.9
    )
    
    # Text containing entity information
    text = "John Smith is a 30-year-old Software Engineer at Google. He lives in California and has a PhD in Computer Science."
    
    # Extract attributes
    attributes = await extractor.extract_attributes(text, entity)
    
    # Process results
    for attr_name, attribute in attributes.items():
        print(f"{attr_name}: {attribute.value} (confidence: {attribute.confidence:.2f})")

# Run the extraction
asyncio.run(extract_person_attributes())
```

**Expected Output:**
```
age: 30 (confidence: 0.85)
occupation: Software Engineer (confidence: 0.80)
company: Google (confidence: 0.80)
location: California (confidence: 0.80)
education: PhD in Computer Science (confidence: 0.80)
```

### Batch Entity Processing

```python
async def extract_multiple_entities():
    extractor = AttributeExtractor()
    
    # Create multiple entities
    entities = [
        Entity("Apple Inc", EntityType.ORGANIZATION, 0, 9, 0.9),
        Entity("Tim Cook", EntityType.PERSON, 20, 28, 0.9),
        Entity("iPhone 15", EntityType.PRODUCT, 40, 49, 0.9)
    ]
    
    text = "Apple Inc, led by CEO Tim Cook, released the iPhone 15 in September 2023 with a starting price of $799."
    
    # Batch extraction
    results = await extractor.extract_entity_attributes_batch(text, entities)
    
    for entity_name, attributes in results.items():
        print(f"\n{entity_name}:")
        for attr_name, attr in attributes.items():
            print(f"  {attr_name}: {attr.normalized_value}")

asyncio.run(extract_multiple_entities())
```

## Entity Type Schemas

The extractor uses specialized schemas for different entity types:

### Person Attributes
- **age**: Age in years
- **occupation**: Job title or profession  
- **location**: Current location or residence
- **education**: Educational background
- **skills**: Professional skills or expertise
- **company**: Current employer or organization
- **nationality**: Country of origin or citizenship

### Organization Attributes
- **founded**: Year founded or established
- **size**: Number of employees or scale
- **location**: Headquarters or main location
- **industry**: Business sector or industry
- **revenue**: Annual revenue or financial information
- **website**: Official website URL
- **ceo**: Chief Executive Officer or leader
- **products**: Main products or services

### Product Attributes
- **price**: Cost or pricing information
- **features**: Key features or capabilities
- **manufacturer**: Company that makes the product
- **category**: Product category or type
- **release_date**: When the product was launched
- **specifications**: Technical specifications

### Event Attributes
- **date**: When the event occurred or will occur
- **location**: Where the event takes place
- **duration**: How long the event lasts
- **participants**: Who is involved in the event
- **organizer**: Who organized the event
- **purpose**: Reason or goal of the event

### Location Attributes
- **population**: Number of residents
- **country**: Country the location is in
- **region**: State, province, or region
- **coordinates**: Geographic coordinates
- **notable_features**: Famous landmarks or characteristics

## Attribute Types

The service supports the following attribute types with automatic type inference:

```python
class AttributeType(Enum):
    TEXT = "TEXT"           # General text information
    NUMBER = "NUMBER"       # Numeric values (age, count, etc.)
    DATE = "DATE"          # Date and time information
    BOOLEAN = "BOOLEAN"    # True/false values
    LIST = "LIST"          # Comma-separated lists
    OBJECT = "OBJECT"      # Complex structured data
    URL = "URL"            # Web addresses
    EMAIL = "EMAIL"        # Email addresses
    PHONE = "PHONE"        # Phone numbers
```

## Value Normalization

The extractor automatically normalizes values based on their type:

### Number Normalization
```python
# Input: "1,000", "$50.99"
# Output: 1000, 50.99
```

### Date Normalization
```python
# Input: "2023"
# Output: "2023-01-01"
```

### Email Normalization
```python
# Input: "Test@Example.COM"
# Output: "test@example.com"
```

### Phone Normalization
```python
# Input: "(123) 456-7890", "1-123-456-7890"
# Output: "123-456-7890"
```

### URL Normalization
```python
# Input: "example.com"
# Output: "https://example.com"
```

## Advanced Usage

### Custom Configuration

```python
config = {
    'confidence_threshold': 0.8,  # Minimum confidence for attributes
    'use_llm': True,             # Enable/disable LLM processing
}

extractor = AttributeExtractor(config)
```

### Statistics and Analytics

```python
async def analyze_extraction_results():
    extractor = AttributeExtractor()
    
    # Extract attributes for multiple entities
    entity_attributes = await extractor.extract_entity_attributes_batch(text, entities)
    
    # Get statistics
    stats = extractor.get_attribute_statistics(entity_attributes)
    
    print(f"Total attributes extracted: {stats['total_attributes']}")
    print(f"Entities with attributes: {stats['entities_with_attributes']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"High confidence attributes: {stats['high_confidence']}")
    print(f"Attribute types: {stats['by_type']}")
```

### Working with Confidence Scores

```python
async def filter_by_confidence():
    extractor = AttributeExtractor()
    attributes = await extractor.extract_attributes(text, entity)
    
    # Filter high-confidence attributes
    high_confidence = {
        name: attr for name, attr in attributes.items() 
        if attr.confidence > 0.8
    }
    
    # Filter by attribute type
    contact_info = {
        name: attr for name, attr in attributes.items()
        if attr.attribute_type in [AttributeType.EMAIL, AttributeType.PHONE, AttributeType.URL]
    }
```

## API Reference

### AttributeExtractor Class

#### Constructor
```python
AttributeExtractor(config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `config`: Configuration dictionary with extractor settings

#### Main Methods

##### extract_attributes()
```python
async def extract_attributes(
    text: str, 
    entity: Entity, 
    methods: List[str] = None
) -> Dict[str, Attribute]
```

**Parameters:**
- `text`: Input text to analyze
- `entity`: Entity to extract attributes for
- `methods`: List of extraction methods (currently only 'llm' is supported)

**Returns:** Dictionary mapping attribute names to Attribute objects

##### extract_entity_attributes_batch()
```python
async def extract_entity_attributes_batch(
    text: str, 
    entities: List[Entity]
) -> Dict[str, Dict[str, Attribute]]
```

**Parameters:**
- `text`: Input text to analyze
- `entities`: List of entities to process

**Returns:** Dictionary mapping entity names to their attributes

##### get_attribute_statistics()
```python
def get_attribute_statistics(
    entity_attributes: Dict[str, Dict[str, Attribute]]
) -> Dict[str, Any]
```

**Parameters:**
- `entity_attributes`: Entity attributes from batch extraction

**Returns:** Statistics dictionary with extraction metrics

### Attribute Class

```python
@dataclass
class Attribute:
    name: str                           # Attribute name
    value: Any                          # Original value
    attribute_type: AttributeType       # Inferred type
    confidence: float                   # Confidence score (0.0-1.0)
    source_text: str = ""              # Source text snippet
    normalized_value: Any = None        # Normalized value
    metadata: Dict[str, Any] = None     # Additional metadata
```

### Entity Class

```python
@dataclass
class Entity:
    text: str                   # Entity text
    entity_type: EntityType     # Entity type
    start: int                  # Start position in text
    end: int                    # End position in text
    confidence: float           # Entity extraction confidence
    properties: Dict[str, Any] = None      # Additional properties
    canonical_form: str = None            # Canonical form
    aliases: List[str] = None             # Entity aliases
```

## Error Handling

The service includes comprehensive error handling:

```python
async def robust_extraction():
    try:
        extractor = AttributeExtractor()
        attributes = await extractor.extract_attributes(text, entity)
        
        if not attributes:
            print("No attributes extracted")
            return
            
        for name, attr in attributes.items():
            if attr.confidence < 0.7:
                print(f"Low confidence attribute: {name} ({attr.confidence:.2f})")
                
    except Exception as e:
        print(f"Extraction failed: {e}")
```

## Performance Considerations

- **Text Length**: For very long texts (>3000 chars), the service truncates input
- **Batch Processing**: Use `extract_entity_attributes_batch()` for multiple entities
- **Confidence Filtering**: Filter results by confidence to improve quality
- **Caching**: Consider caching results for repeated extractions

## Integration with Other Services

### With Entity Extractor
```python
from entity_extractor import EntityExtractor

async def full_pipeline():
    entity_extractor = EntityExtractor()
    attribute_extractor = AttributeExtractor()
    
    # First extract entities
    entities = await entity_extractor.extract_entities(text)
    
    # Then extract attributes for each entity
    all_attributes = {}
    for entity in entities:
        attributes = await attribute_extractor.extract_attributes(text, entity)
        all_attributes[entity.text] = attributes
    
    return all_attributes
```

### With Relation Extractor
```python
async def knowledge_extraction():
    # Extract entities and attributes
    entities = await entity_extractor.extract_entities(text)
    entity_attributes = await attribute_extractor.extract_entity_attributes_batch(text, entities)
    
    # Extract relations between entities
    relations = await relation_extractor.extract_relations(text, entities)
    
    return {
        'entities': entities,
        'attributes': entity_attributes,
        'relations': relations
    }
```

## Testing

The service includes comprehensive unit tests. Run them with:

```bash
python -m pytest tools/services/data_analytics_service/services/knowledge_extraction_service/tests/test_attribute_extractor.py -v
```

## Troubleshooting

### Common Issues

1. **No Attributes Extracted**
   - Check if LLM is enabled: `config['use_llm'] = True`
   - Verify entity is properly positioned in text
   - Ensure text contains relevant attribute information

2. **Low Confidence Scores**
   - Provide more context around entities
   - Check entity type matches the attributes expected
   - Verify text quality and clarity

3. **Type Inference Issues**
   - Review attribute name patterns
   - Check value formats for automatic type detection
   - Consider manual type specification if needed

### Debug Mode

```python
import logging
logging.getLogger('attribute_extractor').setLevel(logging.DEBUG)

# Enable detailed logging
extractor = AttributeExtractor()
```

## License

This service is part of the isA MCP data analytics framework.