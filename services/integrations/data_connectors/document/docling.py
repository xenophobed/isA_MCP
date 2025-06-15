from typing import Dict, Any
import docling
from .base import FileConnector, FileConfig

class DoclingConfig(FileConfig):
    """Docling specific configuration"""
    api_key: str = None
    extract_tables: bool = True
    extract_charts: bool = True
    extract_sections: bool = True

class DoclingConnector(FileConnector):
    """
    Docling implementation of FileConnector.
    Extends the base file connector with document processing capabilities.
    """
    
    async def extract(self, **kwargs) -> Dict[str, Any]:
        """Process document using Docling"""
        if not self.is_connected:
            raise ConnectionError("File not opened")
        
        doc = docling.Docling().load(self.config.file_path)
        
        result = {
            "text": doc.text,
            "metadata": doc.metadata,
            "sections": []
        }
        
        if self.config.extract_sections:
            for section in doc.sections:
                result["sections"].append({
                    "title": section.title,
                    "content": section.content,
                    "type": section.type
                })
        
        if self.config.extract_tables:
            result["tables"] = [{
                "content": table.content,
                "position": table.position,
                "type": "table"
            } for table in doc.tables]
            
        if self.config.extract_charts:
            result["charts"] = [{
                "path": image.path,
                "caption": image.caption,
                "position": image.position,
                "type": "image"
            } for image in doc.images]
            
        return result 