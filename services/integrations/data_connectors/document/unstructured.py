from typing import Dict, Any
from unstructured.partition.auto import partition
from .base import FileConnector, FileConfig

class UnstructuredConfig(FileConfig):
    """Unstructured.io specific configuration"""
    api_key: str = None
    extract_tables: bool = True
    extract_charts: bool = True

class UnstructuredConnector(FileConnector):
    """
    Unstructured.io implementation of FileConnector.
    Extends the base file connector with document processing capabilities.
    """
    
    async def extract(self, **kwargs) -> Dict[str, Any]:
        """Process document using unstructured.io"""
        if not self.is_connected:
            raise ConnectionError("File not opened")
        
        elements = partition(filename=self.config.file_path)
        
        result = {
            "text": [el.text for el in elements],
        }
        
        if self.config.extract_tables:
            tables = [el for el in elements if el.category == "Table"]
            result["tables"] = [table.text for table in tables]
            
        if self.config.extract_charts:
            charts = [el for el in elements if el.category == "Image"]
            result["charts"] = [chart.text for chart in charts]
            
        return result
