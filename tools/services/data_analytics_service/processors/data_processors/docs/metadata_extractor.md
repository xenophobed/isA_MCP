# Metadata Extractor Service

A concrete service that extracts comprehensive metadata from various data sources (CSV, Excel, JSON, Database).

## Overview

**Input**: File path or connection string  
**Output**: Standardized metadata dictionary

## Quick Start

```python
from metadata_extractor import extract_metadata

# Extract metadata from CSV file
metadata = extract_metadata('data.csv')
print(metadata['tables'])
```

## Supported Sources

- **CSV files** (`.csv`)
- **Excel files** (`.xlsx`, `.xls`) 
- **JSON files** (`.json`)
- **Databases** (PostgreSQL, MySQL, SQLite - planned)

## Usage Examples

### Basic Usage

```python
from metadata_extractor import extract_metadata

# Auto-detect file type and extract metadata
metadata = extract_metadata('/path/to/customers.csv')

# Check extraction success
if 'error' not in metadata:
    print(f" Found {len(metadata['columns'])} columns")
    print(f"=Ê {metadata['tables'][0]['record_count']} records")
else:
    print(f"L Error: {metadata['error']}")
```

### Advanced Usage

```python
from metadata_extractor import MetadataExtractor

# Create extractor instance
extractor = MetadataExtractor()

# Extract metadata with specific source type
metadata = extractor.extract_metadata(
    source_path='data.csv',
    source_type='csv'  # Optional: auto-detected if not provided
)

# Save metadata to file
extractor.save_metadata(metadata, 'output_metadata.json')

# Check supported sources
print(extractor.get_supported_sources())
# Output: ['csv', 'excel', 'json', 'database']
```

## Output Structure

The service returns a standardized metadata dictionary:

```json
{
  "extraction_info": {
    "service": "MetadataExtractor",
    "version": "1.0.0",
    "source_type": "csv",
    "extraction_time": "2025-07-17T20:14:40.761942",
    "extraction_duration_seconds": 0.016,
    "success": true
  },
  "source_info": {
    "file_path": "/path/to/file.csv",
    "file_size_mb": 0.16,
    "total_rows": 1000,
    "total_columns": 12,
    "has_duplicates": false
  },
  "tables": [
    {
      "table_name": "customers_sample",
      "table_type": "file",
      "record_count": 1000,
      "column_count": 12,
      "file_size_mb": 0.16,
      "created_date": "2025-07-17T19:59:42.518756",
      "modified_date": "2025-07-17T19:59:42.518756"
    }
  ],
  "columns": [
    {
      "table_name": "customers_sample",
      "column_name": "Customer Id",
      "data_type": "object",
      "business_type": "identifier",
      "ordinal_position": 2,
      "is_nullable": false,
      "null_percentage": 0.0,
      "unique_count": 1000,
      "unique_percentage": 100.0,
      "sample_values": ["dE014d010c7ab0c", "2B54172c8b65eC3"],
      "avg_length": 15.0,
      "min_length": 15,
      "max_length": 15
    }
  ],
  "data_quality": {
    "overall_quality_score": 1.0,
    "completeness_percentage": 100.0,
    "total_cells": 12000,
    "null_cells": 0
  },
  "business_patterns": {
    "domain_scores": {
      "ecommerce": 1,
      "finance": 0,
      "hr": 0,
      "crm": 1
    },
    "primary_domain": "ecommerce",
    "confidence": 0.083
  },
  "sample_data": [
    {
      "Index": 1,
      "Customer Id": "dE014d010c7ab0c",
      "First Name": "Andrew",
      "Last Name": "Goodman",
      "Company": "Stewart-Flynn"
    }
  ]
}
```

## Key Features

### = Column Analysis
- **Data Types**: Pandas dtypes (int64, object, float64, etc.)
- **Business Types**: Semantic inference (identifier, name, email, phone, monetary, etc.)
- **Statistics**: Min/max values, averages, null percentages, uniqueness
- **Sample Values**: Representative data samples

### =Ê Data Quality Assessment
- **Overall Quality Score**: 0.0 - 1.0 based on completeness
- **Completeness Percentage**: Non-null data percentage
- **Null Analysis**: Per-column null counts and percentages

### <¯ Business Domain Detection
Automatically detects business domains:
- **ecommerce**: product, order, customer, price keywords
- **finance**: amount, transaction, payment, account keywords  
- **hr**: employee, salary, department keywords
- **crm**: customer, contact, lead, sales keywords

### =È Performance
- **Fast Processing**: ~0.016 seconds for 1000-row CSV
- **Memory Efficient**: Processes large files without loading everything into memory
- **Error Handling**: Graceful error handling with detailed error messages

## Error Handling

```python
metadata = extract_metadata('nonexistent.csv')

if 'error' in metadata:
    print(f"Error: {metadata['error']}")
    print(f"Supported types: {metadata.get('supported_types', [])}")
else:
    # Process successful metadata
    process_metadata(metadata)
```

## File Requirements

### CSV Files
- UTF-8 encoding recommended
- First row should contain column headers
- Handles various delimiters automatically

### Excel Files  
- Supports `.xlsx` and `.xls` formats
- Analyzes all sheets separately
- Each sheet becomes a separate "table"

### JSON Files
- Valid JSON format required
- Analyzes structure and infers schema
- Supports both objects and arrays

## Testing

Run the test suite:

```bash
cd processors/data_processors/tests/
python test_metadata_extractor.py
```

Expected output:
```
>ê Testing Metadata Extractor Service
 Metadata extraction successful!
   =Ê Tables: 1
   =Ë Columns: 12
   <¯ Source type: csv
<‰ All tests completed successfully!
```

## Use Cases

1. **Data Discovery**: Understand structure of new datasets
2. **Data Quality Assessment**: Identify completeness and quality issues
3. **Schema Documentation**: Generate automatic documentation
4. **ETL Pipeline Planning**: Understand data before transformation
5. **Business Intelligence**: Identify domain and business patterns

## Integration

The service can be easily integrated into larger data analytics workflows:

```python
# Example: ETL Pipeline Integration
def analyze_data_source(file_path):
    metadata = extract_metadata(file_path)
    
    if 'error' in metadata:
        return {'status': 'failed', 'error': metadata['error']}
    
    return {
        'status': 'success',
        'tables': len(metadata['tables']),
        'columns': len(metadata['columns']),
        'quality_score': metadata['data_quality']['overall_quality_score'],
        'domain': metadata['business_patterns']['primary_domain']
    }
```

## Limitations

- Database extraction requires additional database drivers
- Large files (>1GB) may require streaming processing
- Complex nested JSON structures have simplified schema inference
- Business type inference is based on naming patterns and may not be 100% accurate

## Dependencies

- `pandas`: Data processing and analysis
- `pathlib`: File path handling  
- `json`: JSON processing
- `datetime`: Timestamp handling
- `logging`: Error and info logging