from typing import Dict, Type, Optional, Protocol, Any
import logging
import chromadb
from .base_vector_service import BaseVectorService
from app.config.vector.vector_config import VectorConfig

logger = logging.getLogger(__name__)

class VectorConfigProtocol(Protocol):
    """Protocol for vector database configurations"""
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters"""
        ...
    
    def get_vector_settings(self) -> Dict[str, Any]:
        """Get vector settings"""
        ...

class VectorFactory:
    _instance = None
    _services: Dict[str, BaseVectorService] = {}
    _service_types: Dict[str, Type[BaseVectorService]] = {}
    _config = None
    
    def __init__(self):
        self._default_type = "chroma"
    
    @classmethod
    def get_instance(cls) -> 'VectorFactory':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def register_service(cls, name: str, service_class: Type[BaseVectorService]):
        """Register vector service type"""
        cls._service_types[name] = service_class
    
    def set_config(self, config: VectorConfigProtocol):
        """Set configuration for vector services"""
        self._config = config
    
    async def get_vector(self, service_type: str = None) -> BaseVectorService:
        """Get vector service instance"""
        service_type = service_type or self._default_type
        
        if service_type not in self._services:
            if service_type not in self._service_types:
                raise ValueError(f"Unsupported vector service type: {service_type}")
            
            self._services[service_type] = await self._create_service(service_type)
        
        return self._services[service_type]
    
    async def _create_service(self, service_type: str) -> BaseVectorService:
        """Create service instance"""
        try:
            # Get configuration
            config = self._config
            if not config:
                from app.config.config_manager import config_manager
                config = config_manager.get_config(service_type)
            
            if service_type == "chroma":
                # Create ChromaDB client
                conn_params = config.get_connection_params()
                if conn_params.get('client') == 'local':
                    client = chromadb.PersistentClient(path=conn_params['path'])
                else:
                    client = chromadb.HttpClient(
                        host=conn_params['host'],
                        port=conn_params['port']
                    )
                
                from .implementations.chroma_service import ChromaService
                return ChromaService(client=client, config=config)
                
            elif service_type == "weaviate":
                # Dynamically import weaviate only when needed
                import weaviate
                
                # Create Weaviate client
                conn_params = config.get_connection_params()
                client = weaviate.Client(
                    url=conn_params['url'],
                    auth_client_secret=weaviate.AuthApiKey(api_key=conn_params.get('api_key')),
                    timeout_config=conn_params.get('timeout', 60)
                )
                
                from .implementations.weaviate_service import WeaviateService
                return WeaviateService(client=client, config=config)
                
            elif service_type == "qdrant":
                # Dynamically import qdrant only when needed
                from qdrant_client import QdrantClient
                
                # Create Qdrant client and service
                conn_params = config.get_connection_params()
                client = QdrantClient(
                    url=conn_params['url'],
                    api_key=conn_params['api_key'],
                    timeout=conn_params['timeout']
                )
                
                from .implementations.qdrant_service import QdrantService
                return QdrantService(client=client, config=config)
                
        except Exception as e:
            logger.error(f"Failed to create vector service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup all service instances"""
        for service in self._services.values():
            await service.close()
        self._services.clear()
        self._config = None

# Register default services
from .implementations.chroma_service import ChromaService
VectorFactory._service_types["chroma"] = ChromaService