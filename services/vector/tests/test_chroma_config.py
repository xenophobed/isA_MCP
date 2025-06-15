import os
import pytest
import logging
import shutil
from pathlib import Path
from dotenv import load_dotenv
from typing import Type, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestVectorConfig:
    config_class = None
    vector_store_type = None
    test_env = {}
    
    @classmethod
    def setup_class(cls):
        """Setup test class with dynamic configuration"""
        try:
            # Load test environment variables
            env_path = Path(__file__).parent / '.test.vector.env'
            if not env_path.exists():
                raise FileNotFoundError(f"Test environment file not found: {env_path}")
            
            load_dotenv(env_path)
            cls.test_env = dict(os.environ)
            
            # Get vector store type
            cls.vector_store_type = os.getenv('VECTOR_STORE_TYPE', 'chroma').lower()
            logger.info(f"Testing vector store type: {cls.vector_store_type}")
            
            # Import appropriate configuration class
            if cls.vector_store_type == 'chroma':
                from app.config.vector.chroma_config import ChromaConfig
                cls.config_class = ChromaConfig
            elif cls.vector_store_type == 'qdrant':
                from app.config.vector.qdrant_config import QdrantConfig
                cls.config_class = QdrantConfig
            else:
                raise ValueError(f"Unsupported vector store type: {cls.vector_store_type}")
            
            logger.info(f"Using configuration class: {cls.config_class.__name__}")
            
        except Exception as e:
            logger.error(f"Error in setup: {e}")
            raise
    
    def setup_method(self):
        """Setup before each test method"""
        self.config = self.config_class()
        
        # Setup test directories if needed
        if self.vector_store_type == 'chroma':
            persist_dir = os.getenv('CHROMA_PERSIST_DIR', './test_chroma_data')
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir)
            os.makedirs(persist_dir, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.getenv('TEST_CLEANUP_ENABLED', 'true').lower() == 'true':
            if self.vector_store_type == 'chroma':
                persist_dir = os.getenv('CHROMA_PERSIST_DIR', './test_chroma_data')
                if os.path.exists(persist_dir):
                    shutil.rmtree(persist_dir)
    
    def test_config_initialization(self):
        """Test configuration initialization"""
        assert self.config is not None, "Configuration should be initialized"
        
        # Test common settings
        assert self.config.settings.vector_size == int(os.getenv('VECTOR_SIZE', '1024'))
        assert self.config.settings.distance_type == os.getenv('VECTOR_DISTANCE', 'cosine').lower()
        
        # Test connection settings
        assert self.config.connection.host == os.getenv(f'{self.vector_store_type.upper()}_HOST', 'localhost')
        assert self.config.connection.port == int(os.getenv(f'{self.vector_store_type.upper()}_PORT', '8000'))
        
        logger.info("Basic configuration test passed")
    
    def test_connection_params(self):
        """Test connection parameters"""
        conn_params = self.config.get_connection_params()
        assert isinstance(conn_params, dict), "Connection params should be a dictionary"
        
        if self.vector_store_type == 'chroma':
            if self.config.connection.client_type == 'local':
                assert 'path' in conn_params
                assert conn_params['client'] == 'local'
            else:
                assert 'host' in conn_params
                assert 'port' in conn_params
                assert conn_params['client'] == 'http'
        
        logger.info("Connection parameters test passed")
    
    def test_vector_settings(self):
        """Test vector settings"""
        vector_settings = self.config.get_vector_settings()
        assert isinstance(vector_settings, dict), "Vector settings should be a dictionary"
        
        # Common settings for all implementations
        assert 'vector_size' in vector_settings
        assert vector_settings['vector_size'] == int(os.getenv('VECTOR_SIZE', '1024'))
        
        # Implementation specific settings
        if self.vector_store_type == 'chroma':
            assert 'distance_func' in vector_settings
            assert vector_settings['distance_func'] == os.getenv('VECTOR_DISTANCE', 'cosine').lower()
        
        logger.info("Vector settings test passed")
    
    def test_validation(self):
        """Test configuration validation"""
        try:
            self.config.validate()
            logger.info("Configuration validation passed")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_service_creation(self):
        """Test service creation with configuration"""
        from app.services.db.vector.vector_factory import VectorFactory
        
        try:
            # Initialize factory with config
            factory = VectorFactory.get_instance()
            factory.set_config(self.config)
            
            # Create service
            service = await factory.get_vector(self.vector_store_type)
            assert service is not None, "Service should be created"
            
            # Test basic service operations
            collection_name = os.getenv(f'{self.vector_store_type.upper()}_COLLECTION', 'test_collection')
            
            # Create collection
            collection = await service.create_collection(collection_name)
            assert collection is not None, "Collection should be created"
            
            # Check collection exists
            exists = await service.collection_exists(collection_name)
            assert exists, "Collection should exist"
            
            # Cleanup
            await factory.cleanup()
            logger.info("Service creation and basic operations test passed")
            
        except Exception as e:
            logger.error(f"Service creation test failed: {e}")
            raise

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
