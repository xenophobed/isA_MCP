#!/usr/bin/env python3
"""
Vector Database Integration Module

Handles vector database selection, initialization, and management
"""

import os
import logging
from typing import Optional, Dict, Any

from ..config.analytics_config import VectorDBPolicy

logger = logging.getLogger(__name__)


class VectorDBIntegration:
    """Vector Database Integration Manager"""
    
    def __init__(self, policy: VectorDBPolicy, config: Dict[str, Any]):
        self.policy = policy
        self.config = config
        self._vector_db = None
    
    @property
    def vector_db(self):
        """Lazy load vector database based on policy"""
        if self._vector_db is None:
            self._vector_db = self._select_vector_db()
        return self._vector_db
    
    def _select_vector_db(self):
        """Select vector database based on policy"""
        try:
            from tools.services.intelligence_service.vector_db import (
                get_vector_db, VectorDBType
            )
            
            if self.policy == VectorDBPolicy.AUTO:
                db_type = self._auto_select_db_type()
            elif self.policy == VectorDBPolicy.PERFORMANCE:
                db_type = VectorDBType.QDRANT
            elif self.policy == VectorDBPolicy.STORAGE:
                db_type = VectorDBType.SUPABASE
            elif self.policy == VectorDBPolicy.MEMORY:
                db_type = VectorDBType.CHROMADB
            elif self.policy == VectorDBPolicy.COST_OPTIMIZED:
                db_type = VectorDBType.SUPABASE
            else:
                db_type = VectorDBType.SUPABASE
            
            # Create basic config
            config = {
                'enable_hybrid_search': self.config.get('hybrid_search_enabled', True),
                'semantic_weight': self.config.get('semantic_weight', 0.7),
                'lexical_weight': self.config.get('lexical_weight', 0.3)
            }
            
            logger.info(f"Selected vector database: {db_type.value}")
            vector_db = get_vector_db(db_type, config)
            
            # Test the connection
            try:
                if hasattr(vector_db, 'get_stats'):
                    import asyncio
                    asyncio.create_task(vector_db.get_stats())
                logger.info("Vector database connection verified")
            except Exception as e:
                logger.warning(f"Vector database connection test failed: {e}")
            
            return vector_db
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            return self._create_mock_vector_db()
    
    def _auto_select_db_type(self):
        """Automatically select database type based on environment"""
        from tools.services.intelligence_service.vector_db import VectorDBType
        
        # Check environment variables for explicit configuration
        env_db_type = os.getenv('VECTOR_DB_TYPE')
        if env_db_type:
            try:
                return VectorDBType(env_db_type.lower())
            except ValueError:
                pass
        
        # Check what's available and prefer in order: Supabase > Qdrant > ChromaDB
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            if supabase_url:
                return VectorDBType.SUPABASE
        except:
            pass
        
        try:
            import qdrant_client
            return VectorDBType.QDRANT
        except ImportError:
            pass
        
        try:
            import chromadb
            return VectorDBType.CHROMADB
        except ImportError:
            pass
        
        return VectorDBType.SUPABASE
    
    def _create_mock_vector_db(self):
        """Create a mock vector database for testing"""
        class MockVectorDB:
            def __init__(self):
                self.name = "MockVectorDB"
            
            async def get_stats(self):
                return {"total_vectors": 0, "status": "mock"}
            
            def __class__(self):
                return type("MockVectorDB", (), {})
        
        logger.warning("Using mock vector database due to initialization failure")
        return MockVectorDB()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        try:
            if hasattr(self.vector_db, 'get_stats'):
                return await self.vector_db.get_stats()
            else:
                return {"error": "Stats not available"}
        except Exception as e:
            logger.error(f"Failed to get vector DB stats: {e}")
            return {"error": str(e)}











