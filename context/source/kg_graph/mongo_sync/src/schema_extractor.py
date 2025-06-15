# src/schema_extractor.py
from typing import Dict, List
from datetime import datetime
from app.config.config_manager import config_manager

logger = config_manager.get_logger(__name__)

class SchemaExtractor:
    def __init__(self, sample_size: int = 1000):
        self.client = None
        self.sample_size = sample_size
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        self.client = await config_manager.get_db('mongodb')
        logger.info("Schema extractor initialized")

    def extract_field_info(self, value: any) -> Dict:
        """Extract type and validation info from a field value."""
        field_info = {
            'type': type(value).__name__,
            'example': str(value),
        }
        
        if isinstance(value, (int, float)):
            field_info.update({
                'min_value': value,
                'max_value': value
            })
        elif isinstance(value, str):
            field_info.update({
                'length': len(value)
            })
        
        return field_info

    async def analyze_collection(self, collection_name: str) -> Dict:
        """Analyze a collection's schema and statistics."""
        if not self.client:
            await self.initialize()
            
        mongo_config = config_manager.get_config('mongodb')
        collection = self.client[mongo_config.COLLECTIONS.get(collection_name, collection_name)]
        
        # Get collection stats
        stats = await collection.stats()
        
        # Sample documents for schema analysis
        pipeline = [{'$sample': {'size': self.sample_size}}]
        samples = await collection.aggregate(pipeline).to_list(length=self.sample_size)
        
        fields = {}
        for doc in samples:
            self._analyze_document(doc, fields)
            
        return {
            'name': collection_name,
            'database': mongo_config.DB_NAME,
            'document_count': stats['count'],
            'avg_document_size': stats.get('avgObjSize', 0),
            'indexes': await collection.index_information(),
            'fields': fields,
            'updated_at': datetime.utcnow()
        }

    def _analyze_document(self, doc: Dict, fields: Dict, prefix: str = ''):
        """Recursively analyze document fields."""
        for key, value in doc.items():
            field_name = f"{prefix}{key}"
            
            if field_name not in fields:
                fields[field_name] = self.extract_field_info(value)
            else:
                # Update min/max values for numeric fields
                if isinstance(value, (int, float)):
                    fields[field_name]['min_value'] = min(
                        fields[field_name]['min_value'],
                        value
                    )
                    fields[field_name]['max_value'] = max(
                        fields[field_name]['max_value'],
                        value
                    )
                
                # Update max length for string fields
                elif isinstance(value, str):
                    fields[field_name]['length'] = max(
                        fields[field_name]['length'],
                        len(value)
                    )
            
            # Recurse into nested documents
            if isinstance(value, dict):
                self._analyze_document(value, fields, f"{field_name}.")