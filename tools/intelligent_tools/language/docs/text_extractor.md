# Text Extractor Documentation

## Overview

The `text_extractor.py` provides comprehensive AI-powered text analysis and extraction capabilities. It offers named entity recognition, text classification, key information extraction, summarization, and sentiment analysis using advanced natural language processing.

## Available Tools

### `extract_entities`

Extracts named entities from text using AI-powered recognition with confidence scoring.

**Function Signature:**
```python
async def extract_entities(
    text: str,
    entity_types: Optional[List[str]] = None,
    confidence_threshold: float = 0.7
) -> Dict[str, Any]
```

**Parameters:**
- `text` (required): Text content to analyze for entities
- `entity_types` (optional): Specific entity types to extract (currently extracts all standard types)
- `confidence_threshold` (optional): Minimum confidence score for entity inclusion (default: 0.7)

**Returns:**
Dictionary with extracted entities, confidence scores, and metadata

### `classify_text`

Classifies text into predefined categories with support for single or multi-label classification.

**Function Signature:**
```python
async def classify_text(
    text: str,
    categories: List[str],
    multi_label: bool = False
) -> Dict[str, Any]
```

**Parameters:**
- `text` (required): Text content to classify
- `categories` (required): List of possible categories for classification
- `multi_label` (optional): Whether text can belong to multiple categories (default: False)

**Returns:**
Dictionary with classification results, confidence scores, and reasoning

### `extract_key_information`

Extracts structured key information from text based on customizable schema.

**Function Signature:**
```python
async def extract_key_information(
    text: str,
    schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `text` (required): Text content to extract information from
- `schema` (optional): Custom extraction schema defining what information to extract

**Returns:**
Dictionary with extracted information following the schema structure

### `summarize_text`

Generates intelligent text summaries with configurable length and focus areas.

**Function Signature:**
```python
async def summarize_text(
    text: str,
    summary_length: str = "medium",
    focus_areas: Optional[List[str]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `text` (required): Text content to summarize
- `summary_length` (optional): Target length ("short", "medium", "long", default: "medium")
- `focus_areas` (optional): Specific areas to emphasize in the summary

**Returns:**
Dictionary with summary text, key points, and quality metrics

### `analyze_sentiment`

Performs comprehensive sentiment analysis with multiple granularity levels.

**Function Signature:**
```python
async def analyze_sentiment(
    text: str,
    granularity: str = "overall"
) -> Dict[str, Any]
```

**Parameters:**
- `text` (required): Text content to analyze for sentiment
- `granularity` (optional): Analysis level ("overall", "aspect", "sentence", default: "overall")

**Returns:**
Dictionary with sentiment analysis results and emotional indicators

## Entity Types

The AI automatically extracts the following entity categories:

### PERSON
People's names, including:
```
- First and last names
- Professional titles
- Public figures
- Authors and speakers
```

### ORGANIZATION
Companies and institutions, including:
```
- Corporation names
- Government agencies
- Educational institutions
- Non-profit organizations
```

### LOCATION
Places and geographical references, including:
```
- Cities and countries
- Street addresses
- Landmarks and regions
- Coordinates and directions
```

### DATE
Temporal expressions, including:
```
- Specific dates
- Time periods
- Deadlines and schedules
- Historical timeframes
```

### MONEY
Financial amounts, including:
```
- Currency values
- Investment amounts
- Prices and costs
- Financial metrics
```

### PRODUCT
Products and services, including:
```
- Brand names
- Software applications
- Physical products
- Service offerings
```

### EVENT
Activities and occurrences, including:
```
- Meetings and conferences
- Product launches
- Market events
- Milestones and deadlines
```

## Summary Lengths

### Short
1-2 sentences highlighting critical points only
- Best for: Headlines, quick overviews, status updates
- Typical length: 20-50 words
- Focus: Essential information only

### Medium
1-2 paragraphs covering main points and key details
- Best for: Executive briefings, meeting summaries, reports
- Typical length: 100-200 words
- Focus: Balanced coverage with supporting details

### Long
3-4 paragraphs with comprehensive coverage and context
- Best for: Detailed analysis, research summaries, comprehensive reports
- Typical length: 300-500 words
- Focus: Complete coverage with context and implications

## Usage Examples

### Entity Extraction
```python
from tools.services.intelligence_service.language.text_extractor import extract_entities

# Extract entities with confidence filtering
result = await extract_entities(
    text="Apple Inc. reported Q3 earnings of $125M in Cupertino on September 30, 2024.",
    confidence_threshold=0.8
)

if result['success']:
    entities = result['data']['entities']
    print(f"Organizations: {entities.get('ORGANIZATION', [])}")
    print(f"Locations: {entities.get('LOCATION', [])}")
    print(f"Money: {entities.get('MONEY', [])}")
    print(f"Dates: {entities.get('DATE', [])}")
```

### Text Classification
```python
from tools.services.intelligence_service.language.text_extractor import classify_text

# Single-label classification
result = await classify_text(
    text="This product is amazing! Best purchase I've made this year.",
    categories=["positive", "negative", "neutral"],
    multi_label=False
)

if result['success']:
    classification = result['data']['primary_category']
    confidence = result['confidence']
    print(f"Classification: {classification} (confidence: {confidence:.3f})")
```

### Multi-Label Classification
```python
# Multi-label classification for news articles
result = await classify_text(
    text="Tech company announces cybersecurity breach affecting millions...",
    categories=["technology", "security", "business", "breaking_news"],
    multi_label=True
)

if result['success']:
    classifications = result['data']['classification']
    for category, score in classifications.items():
        print(f"{category}: {score}")
```

### Key Information Extraction
```python
from tools.services.intelligence_service.language.text_extractor import extract_key_information

# Custom schema for meeting notes
schema = {
    "attendees": "List of meeting participants",
    "action_items": "Tasks assigned with owners and deadlines",
    "decisions": "Key decisions made during the meeting",
    "next_steps": "Follow-up actions and next meeting date"
}

result = await extract_key_information(
    text="Meeting notes content...",
    schema=schema
)

if result['success']:
    extracted_info = result['data']
    print(f"Attendees: {extracted_info.get('attendees', 'Not found')}")
    print(f"Action Items: {extracted_info.get('action_items', 'Not found')}")
```

### Text Summarization
```python
from tools.services.intelligence_service.language.text_extractor import summarize_text

# Focused summarization
result = await summarize_text(
    text="Long technical document...",
    summary_length="medium",
    focus_areas=["key findings", "performance metrics", "recommendations"]
)

if result['success']:
    summary = result['data']['summary']
    key_points = result['data']['key_points']
    print(f"Summary: {summary}")
    print(f"Key Points: {key_points}")
```

### Sentiment Analysis
```python
from tools.services.intelligence_service.language.text_extractor import analyze_sentiment

# Overall sentiment analysis
result = await analyze_sentiment(
    text="Customer feedback or review text...",
    granularity="overall"
)

if result['success']:
    sentiment = result['data']['overall_sentiment']
    emotional_indicators = result['data']['emotional_indicators']
    print(f"Sentiment: {sentiment['label']} (score: {sentiment['score']})")
    print(f"Emotional words: {emotional_indicators}")
```

### Class Instance Usage
```python
from tools.services.intelligence_service.language.text_extractor import TextExtractor

# Using the class directly for multiple operations
extractor = TextExtractor()

# Extract entities
entities_result = await extractor.extract_entities(text, confidence_threshold=0.7)

# Classify text
classification_result = await extractor.classify_text(text, ["positive", "negative"])

# Extract key information
info_result = await extractor.extract_key_information(text)

# Summarize text
summary_result = await extractor.summarize_text(text, summary_length="short")

# Analyze sentiment
sentiment_result = await extractor.analyze_sentiment(text)
```

## Response Format

### Entity Extraction Response
```json
{
  "success": true,
  "data": {
    "entities": {
      "PERSON": [
        {"name": "Sarah Johnson", "confidence": 0.95, "position": [45, 57]}
      ],
      "ORGANIZATION": [
        {"name": "TechCorp Inc.", "confidence": 0.92, "position": [0, 12]}
      ],
      "MONEY": [
        {"name": "$125.7 million", "confidence": 0.98, "position": [78, 91]}
      ]
    },
    "total_entities": 15,
    "confidence_scores": {
      "PERSON": 0.94,
      "ORGANIZATION": 0.89,
      "MONEY": 0.96
    }
  },
  "confidence": 0.93,
  "total_entities": 15,
  "billing_info": {
    "cost_usd": 0.00312,
    "input_tokens": 245,
    "output_tokens": 387,
    "total_tokens": 632,
    "operation": "chat",
    "timestamp": "2025-07-14T23:52:22.044436+00:00"
  }
}
```

### Classification Response
```json
{
  "success": true,
  "data": {
    "classification": {
      "negative": 0.94,
      "positive": 0.05,
      "neutral": 0.01
    },
    "primary_category": "negative",
    "confidence": 0.94,
    "reasoning": "Strong negative language and complaints about product performance"
  },
  "confidence": 0.94,
  "categories": ["positive", "negative", "neutral"],
  "multi_label": false,
  "billing_info": {...}
}
```

### Key Information Response
```json
{
  "success": true,
  "data": {
    "attendees": ["Alice (PM)", "Bob (Dev)", "Carol (Designer)", "Dave (QA)"],
    "action_items": [
      "Alice: Complete user story documentation by Oct 18",
      "Bob: Fix authentication bug (Priority: High)"
    ],
    "key_decisions": ["Hire 2 additional frontend developers"],
    "next_steps": ["Client demo scheduled for October 25th"],
    "dates_mentioned": ["October 12, 2024", "October 19, 2024"]
  },
  "confidence": 0.87,
  "schema_used": {...},
  "completeness": 0.9,
  "billing_info": {...}
}
```

### Summary Response
```json
{
  "success": true,
  "data": {
    "summary": "Study examined neural networks for climate prediction using 50,000 temperature readings from 2019-2023. Transformer model achieved 94.2% accuracy for 30-day predictions, LSTM performed well for seasonal forecasting (87.6%), and CNN excelled at spatial patterns (91.3%). Results show practical applications for agriculture and disaster preparedness.",
    "key_points": [
      "Three AI models tested: LSTM, CNN, Transformer",
      "Transformer achieved highest accuracy at 94.2%",
      "Applications include agriculture and disaster planning"
    ],
    "confidence": 0.91,
    "word_count": 58
  },
  "confidence": 0.91,
  "summary_length": "medium",
  "focus_areas": ["key findings", "accuracy metrics"],
  "original_length": 1247,
  "billing_info": {...}
}
```

### Sentiment Response
```json
{
  "success": true,
  "data": {
    "overall_sentiment": {
      "label": "negative",
      "score": 0.88
    },
    "detailed_analysis": "Strong negative sentiment due to product complaints, poor customer service experience, and explicit recommendation against purchase",
    "confidence": 0.88,
    "emotional_indicators": [
      "frustrated", "terrible", "problems", "unhelpful",
      "worst", "NOT recommend"
    ]
  },
  "confidence": 0.88,
  "granularity": "overall",
  "text_length": 634,
  "billing_info": {...}
}
```

### Error Response
```json
{
  "success": false,
  "error": "Text must be a non-empty string",
  "data": {},
  "confidence": 0.0,
  "total_entities": 0
}
```

## Advanced Features

### Confidence Filtering
Filter entities by confidence threshold:
```python
# Only include high-confidence entities
result = await extract_entities(text, confidence_threshold=0.85)

# Include all entities (lower threshold)
result = await extract_entities(text, confidence_threshold=0.3)
```

### Custom Extraction Schema
Define what information to extract:
```python
business_schema = {
    "company_names": "Names of companies mentioned",
    "financial_metrics": "Revenue, profit, costs, and other financial data",
    "key_personnel": "Names and titles of important people",
    "strategic_initiatives": "Major projects or strategic plans",
    "market_conditions": "Information about market trends and conditions"
}

result = await extract_key_information(text, schema=business_schema)
```

### Multi-Granularity Sentiment Analysis
```python
# Overall sentiment
overall = await analyze_sentiment(text, granularity="overall")

# Aspect-based sentiment
aspects = await analyze_sentiment(text, granularity="aspect")

# Sentence-level sentiment
sentences = await analyze_sentiment(text, granularity="sentence")
```

### Smart Text Truncation
- Automatically handles long texts (>3000 chars for most operations)
- Preserves text integrity while staying within processing limits
- Prioritizes beginning content for context preservation

## Error Handling

Common error scenarios and handling:

1. **Empty or Invalid Text**: Returns error with clear message
2. **Empty Categories List**: Validation error for classification
3. **ISA Service Issues**: Detailed error information from AI service
4. **JSON Parsing Failures**: Robust parsing with fallback extraction
5. **Network Issues**: Graceful handling of connection problems

```python
try:
    result = await extract_entities(text)
    if result['success']:
        # Process successful result
        entities = result['data']['entities']
    else:
        logger.error(f"Entity extraction failed: {result['error']}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Performance Notes

- **Billing**: Each operation consumes AI tokens (typically $0.001-0.01 per request)
- **Speed**: Processing typically takes 2-8 seconds depending on complexity
- **Quality**: Longer, well-structured texts generally produce better results
- **Efficiency**: Confidence thresholds can reduce processing time and costs
- **Caching**: Consider caching results for frequently analyzed content

## Integration Examples

### Batch Processing
```python
texts = ["Document 1...", "Document 2...", "Document 3..."]
results = []

for text in texts:
    entities = await extract_entities(text)
    classification = await classify_text(text, ["business", "technical", "personal"])
    sentiment = await analyze_sentiment(text)
    
    results.append({
        'text_id': len(results),
        'entities': entities,
        'classification': classification,
        'sentiment': sentiment
    })
```

### Document Analysis Pipeline
```python
async def analyze_document(document_text):
    """Comprehensive document analysis pipeline"""
    
    # Extract all entities
    entities = await extract_entities(document_text, confidence_threshold=0.7)
    
    # Classify document type
    doc_types = ["legal", "financial", "technical", "marketing", "academic"]
    classification = await classify_text(document_text, doc_types)
    
    # Extract key information
    schema = {
        "main_topics": "Primary topics discussed",
        "key_stakeholders": "Important people or organizations",
        "action_items": "Tasks or actions mentioned",
        "financial_data": "Revenue, costs, or financial metrics"
    }
    key_info = await extract_key_information(document_text, schema=schema)
    
    # Generate summary
    summary = await summarize_text(
        document_text, 
        summary_length="medium",
        focus_areas=["key findings", "main conclusions"]
    )
    
    # Analyze sentiment
    sentiment = await analyze_sentiment(document_text)
    
    return {
        'entities': entities,
        'classification': classification,
        'key_information': key_info,
        'summary': summary,
        'sentiment': sentiment
    }
```

### Quality Validation
```python
def validate_extraction_quality(result):
    """Validate extraction quality and decide on next steps"""
    
    if not result['success']:
        return False, "Extraction failed"
    
    confidence = result.get('confidence', 0.0)
    
    if confidence >= 0.8:
        return True, "High quality extraction"
    elif confidence >= 0.6:
        return True, "Good quality extraction with minor concerns"
    elif confidence >= 0.4:
        return False, "Low quality - consider retry with different parameters"
    else:
        return False, "Poor quality - manual review required"

# Usage
result = await extract_entities(text)
is_valid, message = validate_extraction_quality(result)

if is_valid:
    process_entities(result['data']['entities'])
else:
    logger.warning(f"Quality issue: {message}")
```

## Best Practices

### Input Text Quality
- **Clean Text**: Remove unnecessary formatting and noise
- **Appropriate Length**: 100-5,000 characters work best for most operations
- **Clear Structure**: Well-structured input produces better results
- **Language**: English text produces the most accurate results

### Entity Extraction
- Use confidence thresholds (0.7-0.8) for production applications
- Lower thresholds (0.3-0.5) for discovery and exploration
- Combine with post-processing for domain-specific validation
- Consider entity linking for knowledge base integration

### Text Classification
- Provide 3-7 clear, distinct categories for best results
- Use multi-label for complex documents with multiple themes
- Include "other" or "unknown" category for edge cases
- Validate categories against domain requirements

### Information Extraction
- Design schemas with 4-8 fields for optimal balance
- Use descriptive field names and clear descriptions
- Include examples in schema descriptions when possible
- Validate extracted information against business rules

### Performance Optimization
- Batch similar operations when possible
- Cache results for frequently analyzed content
- Use appropriate confidence thresholds to reduce costs
- Monitor billing costs and optimize based on usage patterns

## Testing

### Test Status (Last Updated: 2025-09-28)

✅ **All Functions Working** - Using `gpt-4.1-nano` model for stable JSON mode support

| Function | Status | Test Result |
|----------|--------|-------------|
| `extract_entities` | ✅ Working | Successfully extracts PERSON, ORGANIZATION, LOCATION, DATE, MONEY entities |
| `classify_text` | ✅ Working | Correctly classifies text into provided categories |
| `extract_key_information` | ✅ Working | Extracts structured information using custom schemas |
| `summarize_text` | ✅ Working | Generates summaries with configurable lengths |
| `analyze_sentiment` | ✅ Working | Analyzes sentiment with confidence scores |

### Running Tests

```bash
# Quick test all functions
python -c "
import asyncio
from tools.services.intelligence_service.language.text_extractor import *
async def test():
    print('Entity extraction:', (await extract_entities('Apple in Cupertino'))['success'])
    print('Classification:', (await classify_text('Great!', ['positive','negative']))['success'])
    print('Key info:', (await extract_key_information('Meeting with Bob'))['success'])
    print('Summarization:', (await summarize_text('AI revolutionizes tech'))['success'])
    print('Sentiment:', (await analyze_sentiment('Terrible service'))['success'])
asyncio.run(test())
"

# Expected: All functions return success: True
```

### Test Coverage
- ✅ Entity extraction with confidence filtering
- ✅ Single and multi-label text classification
- ✅ Custom schema information extraction
- ✅ Text summarization with focus areas (fixed with gpt-4.1-nano)
- ✅ Overall sentiment analysis (fixed with gpt-4.1-nano)
- ✅ Convenience functions testing
- ✅ Error handling and edge cases
- ✅ Performance and billing metrics

### Important Notes

1. **Model Selection**: The code now uses `gpt-4.1-nano` model which reliably supports JSON mode output
2. **Previous Issue**: `gpt-5-nano` model had intermittent issues with JSON mode (returning empty strings)
3. **Solution**: All functions with `response_format={"type": "json_object"}` now explicitly use `gpt-4.1-nano`

## Summary

The text_extractor.py provides comprehensive AI-driven text analysis that:
- **Extracts 7 entity types** with configurable confidence thresholds
- **Supports flexible text classification** with single or multi-label options
- **Extracts structured information** using customizable schemas
- **Generates intelligent summaries** with length and focus control
- **Analyzes sentiment** at multiple granularity levels
- **Handles errors gracefully** with detailed feedback
- **Integrates seamlessly** with existing workflows
- **Delivers consistent, high-quality results** with real-time billing tracking

Use this service as the primary text analysis engine for applications requiring natural language understanding, content categorization, information extraction, and sentiment monitoring. The AI automatically handles complex linguistic analysis while providing detailed metrics and flexible configuration options.